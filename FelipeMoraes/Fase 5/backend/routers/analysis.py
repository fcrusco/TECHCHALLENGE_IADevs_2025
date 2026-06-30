import logging

import requests as req
from flask import Blueprint, jsonify, request

from config import settings
from models.schemas import ProviderType
from services.llm_factory import get_llm_client
from services.report import generate_report
from services.stride import analyze_stride
from services.vision import identify_components

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
    providers = []

    providers.append({
        "id": "openai",
        "name": "OpenAI (GPT-4o)",
        "available": bool(
            settings.openai_api_key and not settings.openai_api_key.startswith("sk-...")
        ),
        "model": settings.openai_model,
    })

    providers.append({
        "id": "ollama",
        "name": "Ollama (local)",
        "available": _ping(settings.ollama_base_url),
        "model": settings.ollama_model,
    })

    lmstudio_url = settings.lmstudio_base_url
    lmstudio_base = lmstudio_url[:-3] if lmstudio_url.endswith("/v1") else lmstudio_url
    providers.append({
        "id": "lmstudio",
        "name": "LM Studio (local)",
        "available": _ping(lmstudio_base.rstrip("/")),
        "model": settings.lmstudio_model,
    })

    return jsonify(providers)


@analysis_bp.post("/analyze")
def analyze():
    file = request.files.get("file")
    if not file:
        return jsonify({"detail": "No file provided"}), 422

    content_type = file.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES:
        return jsonify({"detail": "File must be an image (PNG, JPG, JPEG, WEBP)"}), 422

    image_bytes = file.read()
    if len(image_bytes) > MAX_FILE_SIZE:
        return jsonify({"detail": "File size exceeds 20MB limit"}), 422

    provider_param = request.form.get("provider")
    active_provider: ProviderType = provider_param or settings.llm_provider  # type: ignore[assignment]

    if active_provider == "openai" and (
        not settings.openai_api_key or settings.openai_api_key.startswith("sk-...")
    ):
        return jsonify({"detail": "OpenAI API key not configured"}), 500

    _, model = get_llm_client(active_provider)
    logger.info("Starting analysis with provider=%s model=%s", active_provider, model)

    try:
        components = identify_components(image_bytes, active_provider)
        logger.info("Identified %d components", len(components))

        stride_report = analyze_stride(components, active_provider)
        logger.info("STRIDE analysis complete")

        result = generate_report(
            components=components,
            stride_report=stride_report,
            provider=active_provider,
            model_used=model,
            provider_used=active_provider,
        )
    except ValueError as exc:
        return jsonify({"detail": str(exc)}), 500
    except Exception as exc:
        err = str(exc)
        if "timed out" in err.lower():
            return jsonify({"detail": "LLM request timed out"}), 504
        logger.exception("Unexpected error during analysis")
        return jsonify({"detail": f"Analysis failed: {err}"}), 503

    return jsonify(result.model_dump())


def _ping(url: str) -> bool:
    try:
        r = req.get(url, timeout=3)
        return r.status_code < 500
    except Exception:
        return False
