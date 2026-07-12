"""Setup do Modelo treinado STRIDE.

Verifica se o GGUF está em disco e se está registrado no Ollama.
O download do GGUF é manual — o link está no README e na interface web.

Uso direto:
    python training/setup_model.py
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Link de download manual — stride-qwen2.5-3b-q8_0.gguf (~3.3 GB)
ONEDRIVE_DOWNLOAD_URL = (
    "https://1drv.ms/u/c/00d0a6a099986c76/"
    "IQCQa17fkDcwRqPt04rnq-QzAcwb1jkWhpkIjwjtfkCwfxs?e=YO1bcI"
)
_MODEL_FILENAME = "stride-qwen2.5-3b-q8_0.gguf"
_OLLAMA_MODEL_NAME = "stride-qwen2.5-3b"
_OUTPUT_DIR = Path(__file__).parent / "output"


def gguf_on_disk(output_dir: Path = _OUTPUT_DIR) -> bool:
    return (output_dir / _MODEL_FILENAME).exists()


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
    """Verifica se o modelo STRIDE está disponível no Ollama e registra se possível.

    Fluxo:
      1. Modelo já registrado no Ollama → retorna True imediatamente.
      2. GGUF não está em disco → loga instruções de download manual e retorna False.
      3. GGUF em disco + Ollama rodando → registra o modelo e retorna True/False.
      4. GGUF em disco + Ollama parado → loga instruções de registro manual e retorna False.
    """
    if _ollama_has_model():
        if not silent:
            logger.info("[setup] Modelo %s já disponível.", _OLLAMA_MODEL_NAME)
        return True

    gguf_path = _OUTPUT_DIR / _MODEL_FILENAME

    if not gguf_path.exists():
        logger.warning(
            "[setup] GGUF não encontrado em: %s\n"
            "  Baixe manualmente (~3.3 GB) em:\n    %s\n"
            "  e salve como: %s",
            gguf_path, ONEDRIVE_DOWNLOAD_URL, gguf_path,
        )
        print(
            f"\n[setup] Modelo STRIDE nao encontrado em disco.\n"
            f"  Baixe o arquivo (~3.3 GB) em:\n    {ONEDRIVE_DOWNLOAD_URL}\n"
            f"  e salve em:\n    {gguf_path}\n"
            f"  Depois inicie o Ollama e rode:\n"
            f"    cd training/output && ollama create {_OLLAMA_MODEL_NAME} -f Modelfile\n"
        )
        return False

    if _ollama_running():
        return register_with_ollama()

    logger.warning(
        "[setup] GGUF encontrado mas Ollama nao esta rodando.\n"
        "  Para registrar:\n"
        "    ollama serve          # em outro terminal\n"
        "    cd training/output\n"
        "    ollama create %s -f Modelfile",
        _OLLAMA_MODEL_NAME,
    )
    print(
        f"\n[setup] GGUF encontrado em {gguf_path}\n"
        f"  Inicie o Ollama e registre:\n"
        f"    cd training/output && ollama create {_OLLAMA_MODEL_NAME} -f Modelfile\n"
    )
    return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
    ok = ensure_stride_model()
    sys.exit(0 if ok else 1)
