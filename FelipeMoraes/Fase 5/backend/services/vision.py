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
        logger.debug("[vision] Imagem redimensionada para caber em %dpx", MAX_IMAGE_DIMENSION)

    # Sempre normaliza para PNG: alguns servidores compatíveis com a API da
    # OpenAI (ex.: o backend llama.cpp do LM Studio) rejeitam data URIs
    # JPEG/WEBP válidas com "'url' field must be a base64 encoded image".
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if "A" in img.getbands() else "RGB")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8"), "image/png"


def _extract_json_from_text(raw: str) -> str:
    """Extract the first JSON array or object from arbitrary LLM text."""
    import re
    # Code fence: ```json ... ``` or ``` ... ```
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if m:
        return m.group(1).strip()
    # Bare array
    m = re.search(r"(\[[\s\S]*\])", raw)
    if m:
        return m.group(1)
    # Bare object
    m = re.search(r"(\{[\s\S]*\})", raw)
    if m:
        return m.group(1)
    return raw


def _parse_components(raw: str) -> list[Component]:
    raw = raw.strip()

    # Attempt 1: direct parse
    data = None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Attempt 2: extract JSON from surrounding text (GPT-4o sometimes adds prose)
        logger.debug("[vision] Direct JSON parse failed — trying extraction")
        extracted = _extract_json_from_text(raw)
        try:
            data = json.loads(extracted)
        except json.JSONDecodeError:
            logger.error("[vision] JSON inválido (primeiros 400 chars): %s", raw[:400])
            raise ValueError("Falha ao parsear a lista de componentes na resposta do LLM")

    # Handle dict wrappers like {"components": [...]} or {"data": [...]}
    if isinstance(data, dict):
        for key in ("components", "data", "items", "result", "results"):
            if key in data and isinstance(data[key], list):
                data = data[key]
                break
        else:
            # Take the first list value found
            for v in data.values():
                if isinstance(v, list):
                    data = v
                    break
            else:
                logger.error("[vision] Resposta é um dict sem lista de componentes: %s", list(data.keys()))
                raise ValueError("LLM retornou um objeto JSON sem lista de componentes")

    components: list[Component] = []
    for i, item in enumerate(data, start=1):
        if item.get("type") not in KNOWN_TYPES:
            logger.warning("[vision] Tipo desconhecido '%s' para '%s' — usando cloud_service como padrão",
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
    logger.info("[vision] Iniciando identificação de componentes | provider=%s", provider)

    llm, model = get_llm_client(provider, override_url, override_model)
    image_b64, media_type = _prepare_image_base64(image_bytes)
    logger.info("[vision] Imagem preparada | media_type=%s | modelo=%s", media_type, model)

    # HumanMessage do LangChain com imagem + texto
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

    logger.info("[vision] Chamando o LLM via LangChain...")
    response = llm.invoke([message])
    content = response.content or ""

    logger.info("[vision] LLM respondeu | chars=%d", len(content))
    logger.info("[vision] Resposta bruta (primeiros 300): %s", content[:300])

    components = _parse_components(content)
    logger.info("[vision] %d componentes identificados:", len(components))
    for c in components:
        logger.info("[vision]   [%s] %s | %s", c.id, c.name, c.type)

    return components
