"""Setup do Modelo treinado STRIDE.

Verifica se o GGUF está em disco e se está registrado no Ollama.
Se não estiver, baixa do OneDrive e registra automaticamente.

Uso direto:
    python training/setup_model.py
"""

from __future__ import annotations

import base64
import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Arquivo compartilhado no OneDrive — stride-qwen2.5-3b-q8_0.gguf (~3.3 GB)
_ONEDRIVE_SHARE_URL = (
    "https://1drv.ms/u/c/00d0a6a099986c76/"
    "IQCQa17fkDcwRqPt04rnq-QzAcwb1jkWhpkIjwjtfkCwfxs?e=pefYwt"
)
_MODEL_FILENAME = "stride-qwen2.5-3b-q8_0.gguf"
_OLLAMA_MODEL_NAME = "stride-qwen2.5-3b"
_OUTPUT_DIR = Path(__file__).parent / "output"


def _onedrive_direct_url(share_url: str) -> str:
    """Converte URL de compartilhamento OneDrive em URL de download direto via API."""
    encoded = (
        base64.b64encode(share_url.encode())
        .decode()
        .rstrip("=")
        .replace("/", "_")
        .replace("+", "-")
    )
    return f"https://api.onedrive.com/v1.0/shares/u!{encoded}/root/content"


def _ollama_running(base_url: str = "http://localhost:11434") -> bool:
    try:
        import requests as req
        return req.get(base_url, timeout=3).status_code < 500
    except Exception:
        return False


def _ollama_has_model(base_url: str = "http://localhost:11434") -> bool:
    try:
        import requests as req
        r = req.get(f"{base_url}/api/tags", timeout=3)
        tags = [m.get("name", "").split(":")[0] for m in r.json().get("models", [])]
        return _OLLAMA_MODEL_NAME in tags
    except Exception:
        return False


def download_gguf(dest_dir: Path = _OUTPUT_DIR) -> Path:
    """Baixa o GGUF do OneDrive com progresso no terminal."""
    import requests as req

    dest_dir.mkdir(parents=True, exist_ok=True)
    gguf_path = dest_dir / _MODEL_FILENAME

    if gguf_path.exists():
        logger.info("[setup] Modelo já existe: %s", gguf_path)
        return gguf_path

    direct_url = _onedrive_direct_url(_ONEDRIVE_SHARE_URL)
    logger.info("[setup] Iniciando download de %s (~3.3 GB)...", _MODEL_FILENAME)
    print(f"\n[setup] Baixando {_MODEL_FILENAME} (~3.3 GB) do OneDrive...")

    tmp_path = gguf_path.with_suffix(".gguf.tmp")
    try:
        with req.get(direct_url, stream=True, allow_redirects=True, timeout=30) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with open(tmp_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8 * 1024 * 1024):  # 8 MB
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded / total * 100
                        mb = downloaded / 1_048_576
                        total_mb = total / 1_048_576
                        print(
                            f"\r[setup]   {mb:,.0f} MB / {total_mb:,.0f} MB  ({pct:.1f}%)",
                            end="", flush=True,
                        )
        tmp_path.rename(gguf_path)
        print()
        logger.info("[setup] Download concluído: %s", gguf_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise

    return gguf_path


def register_with_ollama(output_dir: Path = _OUTPUT_DIR) -> bool:
    """Registra o modelo no Ollama usando o Modelfile do diretório de saída."""
    modelfile = output_dir / "Modelfile"
    if not modelfile.exists():
        logger.error("[setup] Modelfile não encontrado em: %s", modelfile)
        return False

    logger.info("[setup] Registrando %s no Ollama...", _OLLAMA_MODEL_NAME)
    print(f"[setup] Registrando {_OLLAMA_MODEL_NAME} no Ollama (pode levar alguns segundos)...")

    result = subprocess.run(
        ["ollama", "create", _OLLAMA_MODEL_NAME, "-f", str(modelfile)],
        capture_output=True,
        text=True,
        cwd=str(output_dir),  # Modelfile usa FROM ./<arquivo> — cwd precisa ser output_dir
    )

    if result.returncode == 0:
        logger.info("[setup] Modelo %s registrado com sucesso.", _OLLAMA_MODEL_NAME)
        print(f"[setup] {_OLLAMA_MODEL_NAME} registrado com sucesso.")
        return True

    logger.error("[setup] Falha ao registrar no Ollama:\n%s", result.stderr)
    return False


def ensure_stride_model(silent: bool = False) -> bool:
    """Garante que o modelo STRIDE esteja disponível no Ollama.

    Fluxo:
      1. Modelo já registrado no Ollama → retorna True imediatamente.
      2. GGUF não está em disco → baixa do OneDrive.
      3. Ollama está rodando → registra o modelo.
      4. Ollama não está rodando → informa onde o GGUF foi salvo e como registrar manualmente.
    """
    if _ollama_has_model():
        if not silent:
            logger.info("[setup] Modelo %s já disponível.", _OLLAMA_MODEL_NAME)
        return True

    gguf_path = _OUTPUT_DIR / _MODEL_FILENAME

    if not gguf_path.exists():
        try:
            download_gguf()
        except Exception as exc:
            logger.error("[setup] Falha no download: %s", exc)
            print(f"\n[setup] ERRO no download: {exc}")
            return False

    if _ollama_running():
        return register_with_ollama()

    logger.warning(
        "[setup] Ollama não está rodando. GGUF salvo em: %s\n"
        "  Para registrar manualmente:\n"
        "    ollama serve          # em outro terminal\n"
        "    cd training/output\n"
        "    ollama create %s -f Modelfile",
        gguf_path,
        _OLLAMA_MODEL_NAME,
    )
    print(
        f"\n[setup] Ollama não está rodando. GGUF salvo em:\n  {gguf_path}\n"
        f"  Para registrar manualmente quando o Ollama estiver ativo:\n"
        f"    cd training/output\n"
        f"    ollama create {_OLLAMA_MODEL_NAME} -f Modelfile\n"
    )
    return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
    ok = ensure_stride_model()
    sys.exit(0 if ok else 1)
