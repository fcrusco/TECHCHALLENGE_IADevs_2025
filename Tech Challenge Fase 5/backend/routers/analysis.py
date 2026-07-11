import logging
import time

import requests as req
from flask import Blueprint, jsonify, request

from config import settings
from models.schemas import ProviderType
from services.graph import STRIDE_MODEL_NAME, STRIDE_MODEL_URL, run_analysis
from services.llm_factory import get_llm_client

logger = logging.getLogger(__name__)

analysis_bp = Blueprint("analysis", __name__)

ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


@analysis_bp.get("/health")
def health():
    _, model = get_llm_client()
    return jsonify({"status": "ok", "provider": settings.llm_provider, "model": model})


@analysis_bp.get("/providers")
def list_providers():
    providers = [
        {
            "id": "openai",
            "name": "OpenAI",
            "available": bool(
                settings.openai_api_key and not settings.openai_api_key.startswith("sk-...")
            ),
            "model": settings.openai_model,
        },
        {
            "id": "ollama",
            "name": "Ollama (local)",
            "available": _ping(settings.ollama_base_url),
            "model": settings.ollama_model,
        },
    ]

    lmstudio_url  = settings.lmstudio_base_url
    lmstudio_base = lmstudio_url[:-3] if lmstudio_url.endswith("/v1") else lmstudio_url
    providers.append({
        "id": "lmstudio",
        "name": "LM Studio (local)",
        "available": _ping(lmstudio_base.rstrip("/")),
        "model": settings.lmstudio_model,
    })

    return jsonify(providers)


@analysis_bp.get("/stride-model")
def stride_model_status():
    """Disponibilidade do modelo STRIDE treinado (texto-somente, usado apenas na
    etapa de análise STRIDE — veja backend/services/graph.py)."""
    return jsonify({
        "id": STRIDE_MODEL_NAME,
        "name": "Modelo treinado STRIDE",
        "available": _ollama_has_model(STRIDE_MODEL_URL, STRIDE_MODEL_NAME),
    })


@analysis_bp.post("/analyze")
def analyze():
    t_start = time.time()
    logger.info("=" * 60)
    logger.info("[analyze] Nova requisição de análise recebida")

    # ── Validação do arquivo ───────────────────────────────────
    file = request.files.get("file")
    if not file:
        return jsonify({"detail": "Nenhum arquivo enviado"}), 422

    content_type = file.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES:
        logger.warning("[analyze] Tipo de arquivo rejeitado: %s", content_type)
        return jsonify({"detail": "O arquivo deve ser uma imagem (PNG, JPG, JPEG, WEBP)"}), 422

    image_bytes = file.read()
    logger.info("[analyze] Arquivo: nome=%s | tamanho=%d bytes | tipo=%s",
                file.filename, len(image_bytes), content_type)

    if len(image_bytes) > MAX_FILE_SIZE:
        return jsonify({"detail": "O tamanho do arquivo excede o limite de 20MB"}), 422

    # ── Resolução do provider ──────────────────────────────────
    provider_param = request.form.get("provider")
    active_provider: ProviderType = provider_param or settings.llm_provider  # type: ignore[assignment]
    local_url   = request.form.get("local_url")   or None
    local_model = request.form.get("local_model") or None
    use_stride_model = request.form.get("use_stride_model", "").lower() in ("true", "1", "on")

    logger.info("[analyze] provider=%s | local_url=%s | local_model=%s | use_stride_model=%s",
                active_provider, local_url, local_model, use_stride_model)

    if active_provider == "openai" and (
        not settings.openai_api_key or settings.openai_api_key.startswith("sk-...")
    ):
        return jsonify({"detail": "Chave da API da OpenAI não configurada"}), 500

    # ── Execução do pipeline LangGraph ─────────────────────────
    logger.info("[analyze] Executando pipeline LangGraph: visão → stride → relatório")
    try:
        result = run_analysis(
            image_bytes=image_bytes,
            provider=active_provider,
            override_url=local_url,
            override_model=local_model,
            use_stride_model=use_stride_model,
        )
    except ValueError as exc:
        logger.error("[analyze] Erro de parse: %s", exc)
        return jsonify({"detail": str(exc)}), 500
    except Exception as exc:
        err = str(exc)
        if "timed out" in err.lower():
            logger.error("[analyze] Timeout do LLM")
            return jsonify({"detail": "A requisição ao LLM expirou (timeout)"}), 504
        logger.exception("[analyze] Erro inesperado no pipeline")
        return jsonify({"detail": f"Falha na análise: {err}"}), 503

    elapsed = time.time() - t_start
    logger.info("[analyze] Pipeline concluído em %.1fs | componentes=%d",
                elapsed, len(result.components))
    logger.info("=" * 60)

    return jsonify(result.model_dump())


def _ping(url: str) -> bool:
    try:
        r = req.get(url, timeout=3)
        return r.status_code < 500
    except Exception:
        return False


def _ollama_has_model(base_url: str, model_name: str) -> bool:
    try:
        r = req.get(f"{base_url.rstrip('/')}/api/tags", timeout=3)
        if r.status_code >= 500:
            return False
        tags = [m.get("name", "").split(":")[0] for m in r.json().get("models", [])]
        return model_name in tags
    except Exception:
        return False
