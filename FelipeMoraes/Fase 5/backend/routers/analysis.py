import logging

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from config import settings
from models.schemas import AnalysisResponse, ProviderInfo, ProviderType
from services.llm_factory import get_llm_client
from services.report import generate_report
from services.stride import analyze_stride
from services.vision import identify_components

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


@router.get("/health")
async def health():
    _, model = get_llm_client()
    return {"status": "ok", "provider": settings.llm_provider, "model": model}


@router.get("/providers", response_model=list[ProviderInfo])
async def list_providers():
    providers: list[ProviderInfo] = []

    # OpenAI: available when key is set
    providers.append(ProviderInfo(
        id="openai",
        name="OpenAI (GPT-4o)",
        available=bool(settings.openai_api_key and not settings.openai_api_key.startswith("sk-...")),
        model=settings.openai_model,
    ))

    # Ollama: ping base URL
    ollama_ok = await _ping(settings.ollama_base_url)
    providers.append(ProviderInfo(
        id="ollama",
        name="Ollama (local)",
        available=ollama_ok,
        model=settings.ollama_model,
    ))

    # LM Studio: ping base URL (strip trailing /v1 suffix for root ping)
    lmstudio_url = settings.lmstudio_base_url
    lmstudio_base = lmstudio_url[:-3] if lmstudio_url.endswith("/v1") else lmstudio_url
    lmstudio_ok = await _ping(lmstudio_base.rstrip("/"))
    providers.append(ProviderInfo(
        id="lmstudio",
        name="LM Studio (local)",
        available=lmstudio_ok,
        model=settings.lmstudio_model,
    ))

    return providers


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    file: UploadFile = File(...),
    provider: ProviderType | None = Form(None),
):
    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail="File must be an image (PNG, JPG, JPEG, WEBP)",
        )

    image_bytes = await file.read()

    # Validate file size
    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=422, detail="File size exceeds 20MB limit")

    active_provider: ProviderType = provider or settings.llm_provider

    # Guard: OpenAI needs a real key
    if active_provider == "openai" and (
        not settings.openai_api_key or settings.openai_api_key.startswith("sk-...")
    ):
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")

    _, model = get_llm_client(active_provider)

    logger.info("Starting analysis with provider=%s model=%s", active_provider, model)

    components = await identify_components(image_bytes, active_provider)
    logger.info("Identified %d components", len(components))

    stride_report = await analyze_stride(components, active_provider)
    logger.info("STRIDE analysis complete")

    result = await generate_report(
        components=components,
        stride_report=stride_report,
        provider=active_provider,
        model_used=model,
        provider_used=active_provider,
    )

    return result


async def _ping(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(url)
            return response.status_code < 500
    except Exception:
        return False
