import base64
import json
import logging
from io import BytesIO

from langchain_core.messages import HumanMessage
from PIL import Image

from models.schemas import Component, ProviderType
from services.llm_factory import get_llm_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é um especialista em arquitetura de software. Analise a imagem do diagrama de arquitetura fornecida.
Identifique TODOS os componentes visíveis no diagrama (usuários, servidores, bancos de dados, APIs, serviços, etc).
Retorne um array JSON válido. Cada item deve ter:
- id: string única como "comp_1", "comp_2"...
- name: nome do componente como aparece no diagrama
- type: um de [user, web_browser, mobile_app, api_gateway, web_server, microservice,
         database, cache, message_queue, storage, cdn, firewall,
         auth_service, external_api, monitoring, cloud_service]
- description: breve descrição em português do Brasil do papel deste componente na arquitetura

Retorne APENAS o array JSON, sem markdown, sem explicação."""

MAX_IMAGE_DIMENSION = 2000

KNOWN_TYPES = {
    "user", "web_browser", "mobile_app", "api_gateway", "web_server",
    "microservice", "database", "cache", "message_queue", "storage",
    "cdn", "firewall", "auth_service", "external_api", "monitoring", "cloud_service"
}


def _prepare_image_base64(image_bytes: bytes) -> tuple[str, str]:
    img = Image.open(BytesIO(image_bytes))

    if max(img.size) > MAX_IMAGE_DIMENSION:
        img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.LANCZOS)
        logger.debug("[vision] Image resized to fit %dpx", MAX_IMAGE_DIMENSION)

    # Always normalize to PNG: some OpenAI-compatible servers (e.g. LM Studio's
    # llama.cpp backend) reject valid JPEG/WEBP data URIs with
    # "'url' field must be a base64 encoded image".
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if "A" in img.getbands() else "RGB")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8"), "image/png"


def _parse_components(raw: str) -> list[Component]:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("[vision] Invalid JSON from LLM (first 300 chars): %s", raw[:300])
        raise ValueError("Failed to parse component list from LLM response")

    if isinstance(data, dict):
        data = data.get("components", [])

    components: list[Component] = []
    for i, item in enumerate(data, start=1):
        if item.get("type") not in KNOWN_TYPES:
            logger.warning("[vision] Unknown type '%s' for '%s' — defaulting to cloud_service",
                           item.get("type"), item.get("name"))
            item["type"] = "cloud_service"
        if not item.get("id"):
            item["id"] = f"comp_{i}"
        components.append(Component(**item))

    return components


def identify_components(
    image_bytes: bytes,
    provider: ProviderType | None = None,
    override_url: str | None = None,
    override_model: str | None = None,
) -> list[Component]:
    logger.info("[vision] Starting component identification | provider=%s", provider)

    llm, model = get_llm_client(provider, override_url, override_model)
    image_b64, media_type = _prepare_image_base64(image_bytes)
    logger.info("[vision] Image prepared | media_type=%s | model=%s", media_type, model)

    # LangChain HumanMessage with image + text
    message = HumanMessage(content=[
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:{media_type};base64,{image_b64}",
                "detail": "high",
            },
        },
        {"type": "text", "text": SYSTEM_PROMPT},
    ])

    logger.info("[vision] Calling LLM via LangChain...")
    response = llm.invoke([message])
    content = response.content or ""

    logger.info("[vision] LLM responded | chars=%d", len(content))
    logger.debug("[vision] Raw response (first 200): %s", content[:200])

    components = _parse_components(content)
    logger.info("[vision] Identified %d components:", len(components))
    for c in components:
        logger.info("[vision]   [%s] %s | %s", c.id, c.name, c.type)

    return components
