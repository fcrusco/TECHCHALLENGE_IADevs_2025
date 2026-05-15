#!/usr/bin/env python3
import re
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Instale requests: pip install requests")
    sys.exit(1)

# ── Configuração ──────────────────────────────────────────────────────────────

OUTPUT_DIR = Path(__file__).parent / "videos"

SOURCES = [
    (
        "https://www.mediafire.com/file/wdn9yeaaq9ahu5b/bilateralsalpingectomy%20small.mp4",
        "video_01.mp4",
    ),
    (
        "https://www.mediafire.com/file/5tft6f2ct507qgh/ovariancystsmall.mp4",
        "video_02.mp4",
    ),
    (
        "https://www.mediafire.com/watch/0jaum566975tv1j/Laparoscopic-Dermoid-Cystectomy.mp4",
        "video_03.mp4",
    ),
    (
        "https://mfi.re/watch/37n7orbermu0xmx/World_Laparoscopy_Hospital_TLH_by_Enseal.mp4",
        "video_04.mp4",
    ),
    (
        "http://www.mediafire.com/file/vk295e8vvmfqgb0/dtod.mp4",
        "video_05.mp4",
    ),
    (
        "http://www.mediafire.com/file/26c52fibeqmah69/doom.wmv",
        "video_06.wmv",
    ),
    (
        "http://www.mediafire.com/file/ge21ouvpn3z9fko/ovariancystectomy.wmv",
        "video_07.wmv",
    ),
]

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
_HEADERS = {
    "User-Agent": _UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "DNT": "1",
}
_HEADERS_DL = {**_HEADERS, "Referer": "https://www.mediafire.com/"}

# URL da API pública do MediaFire
_MF_API = "https://www.mediafire.com/api/1.5/file/get_links.php"


# ── Extração do quick_key ─────────────────────────────────────────────────────

def _extract_key(url: str) -> str | None:
    """Extrai o quick_key do arquivo a partir da URL da página."""
    m = re.search(r"/(?:file|watch)/([a-zA-Z0-9]+)/", url)
    return m.group(1) if m else None


# ── Método 1: API pública do MediaFire ───────────────────────────────────────

def _via_api(quick_key: str, session: requests.Session) -> str | None:
    """
    Consulta a API pública do MediaFire para obter o link direto.
    Retorna a URL ou None se a API não responder / arquivo não for público.
    """
    try:
        r = session.get(
            _MF_API,
            params={
                "quick_key": quick_key,
                "type": "direct_download",
                "response_format": "json",
            },
            headers=_HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        for link in data.get("response", {}).get("links", []):
            url = link.get("direct_download") or link.get("normal_download")
            if url:
                return url
    except Exception:
        pass
    return None


# ── Método 2: scraping manual (segue redirects sem ler body intermediário) ───

def _fetch_final_html(start_url: str, session: requests.Session, max_hops: int = 12) -> str:
    """
    Segue redirects manualmente com stream=True para não ler o body
    das respostas intermediárias (evita o travamento do requests).
    Retorna o HTML final (até 400 KB).
    """
    url = start_url
    for _ in range(max_hops):
        r = session.get(
            url,
            headers=_HEADERS,
            timeout=20,
            allow_redirects=False,  # ← não lê bodies intermediários
            stream=True,
        )
        if r.status_code in (301, 302, 303, 307, 308):
            location = r.headers.get("Location", "")
            r.close()
            if not location:
                break
            # Converte redirect relativo em absoluto
            if location.startswith("/"):
                from urllib.parse import urlparse
                p = urlparse(url)
                location = f"{p.scheme}://{p.netloc}{location}"
            url = location
            continue

        # Resposta final — lê até 400 KB (suficiente para o link)
        html_bytes = b""
        for chunk in r.iter_content(chunk_size=8_192):
            html_bytes += chunk
            if len(html_bytes) >= 400_000:
                break
        r.close()
        return html_bytes.decode("utf-8", errors="ignore")

    return ""


def _via_scrape(page_url: str, session: requests.Session) -> str | None:
    html = _fetch_final_html(page_url, session)
    if not html:
        return None

    patterns = [
        r'"(https://download\d*\.mediafire\.com/[^"]+)"',
        r"'(https://download\d*\.mediafire\.com/[^']+)'",
        r'id="downloadButton"[^>]*href="([^"]+)"',
        r'href="([^"]+)"[^>]*id="downloadButton"',
        r'aria-label="[Dd]ownload(?:\s+file)?"[^>]*href="([^"]+)"',
        r'href="([^"]+)"[^>]*aria-label="[Dd]ownload(?:\s+file)?"',
        r'class="[^"]*popsok[^"]*"[^>]*href="([^"]+)"',
        r'"url"\s*:\s*"(https://download[^"]+)"',
        r'<source[^>]+src="(https://[^"]+\.(?:mp4|wmv|avi|mov)[^"]*)"',
    ]

    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            url = m.group(1).replace("&amp;", "&").replace("&#038;", "&").strip()
            if url.startswith("http"):
                return url

    return None


# ── Obter link direto (API → scraping) ───────────────────────────────────────

def _get_direct_url(page_url: str, session: requests.Session) -> str | None:
    quick_key = _extract_key(page_url)

    if quick_key:
        url = _via_api(quick_key, session)
        if url:
            return url

    return _via_scrape(page_url, session)


# ── Download com barra de progresso ──────────────────────────────────────────

def _download(direct_url: str, dest: Path, session: requests.Session) -> None:
    with session.get(direct_url, headers=_HEADERS_DL, stream=True, timeout=120) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0))
        downloaded = 0
        bar_len = 32

        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=256 * 1024):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    mb = downloaded / 1_048_576
                    if total:
                        pct = downloaded / total * 100
                        filled = int(bar_len * downloaded / total)
                        bar = "█" * filled + "░" * (bar_len - filled)
                        total_mb = total / 1_048_576
                        print(
                            f"\r    [{bar}] {pct:5.1f}%  {mb:.1f}/{total_mb:.1f} MB ",
                            end="", flush=True,
                        )
                    else:
                        print(f"\r    {mb:.1f} MB baixados...", end="", flush=True)
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    force = "--force" in sys.argv

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Destino : {OUTPUT_DIR.resolve()}")
    print(f"Total   : {len(SOURCES)} vídeos\n")

    session = requests.Session()
    ok: list[str] = []
    skipped: list[str] = []
    failed: list[str] = []

    for idx, (page_url, filename) in enumerate(SOURCES, 1):
        dest = OUTPUT_DIR / filename
        print(f"[{idx:02d}/{len(SOURCES)}] {filename}")
        print(f"  Página : {page_url}")

        if dest.exists() and not force:
            size_mb = dest.stat().st_size / 1_048_576
            print(f"  ✓ Já existe ({size_mb:.1f} MB) — use --force para re-baixar\n")
            skipped.append(filename)
            continue

        try:
            print("  [1/2] API MediaFire...", end="", flush=True)
            key = _extract_key(page_url)
            direct_url = _via_api(key, session) if key else None

            if direct_url:
                print(" OK")
            else:
                print(" sem resposta")
                print("  [2/2] Scraping da página...", end="", flush=True)
                direct_url = _via_scrape(page_url, session)
                if direct_url:
                    print(" OK")
                else:
                    print(" falhou")

            if not direct_url:
                print(f"  ✗ Link direto não encontrado")
                print(f"    Baixe manualmente: {page_url}\n")
                failed.append(filename)
                continue

            preview = direct_url[:80] + ("..." if len(direct_url) > 80 else "")
            print(f"  Link   : {preview}")
            print(f"  Baixando...")
            _download(direct_url, dest, session)

            size_mb = dest.stat().st_size / 1_048_576
            print(f"  ✓ Salvo — {size_mb:.1f} MB\n")
            ok.append(filename)

        except requests.HTTPError as e:
            print(f"\n  ✗ HTTP {e.response.status_code}: {e}")
            dest.unlink(missing_ok=True)
            failed.append(filename)
            print()

        except Exception as e:
            print(f"\n  ✗ Erro: {e}")
            dest.unlink(missing_ok=True)
            failed.append(filename)
            print()

        time.sleep(1)

    print("─" * 55)
    print(f"Baixados : {len(ok)}")
    print(f"Pulados  : {len(skipped)}")
    print(f"Falhas   : {len(failed)}")

    if failed:
        print("\nVídeos com falha — baixar manualmente:")
        for page_url, filename in SOURCES:
            if filename in failed:
                print(f"  {filename}: {page_url}")
        sys.exit(1)


if __name__ == "__main__":
    main()
