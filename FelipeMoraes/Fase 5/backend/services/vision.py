import base64
import json
import logging
from io import BytesIO

from PIL import Image

from models.schemas import Component, ProviderType
from services.llm_factory import get_llm_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a software architecture expert. Analyze the provided architecture diagram image.
Identify ALL components visible in the diagram (users, servers, databases, APIs, services, etc).
Return a valid JSON array. Each item must have:
- id: unique string like "comp_1", "comp_2"...
- name: component name as shown in diagram
- type: one of [user, web_browser, mobile_app, api_gateway, web_server, microservice,
         database, cache, message_queue, storage, cdn, firewall,
         auth_service, external_api, monitoring, cloud_service]
- description: brief description of its role in this architecture

Return ONLY the JSON array, no markdown, no explanation."""

MAX_IMAGE_DIMENSION = 2000

KNOWN_TYPES = {
    "user", "web_browser", "mobile_app", "api_gateway", "web_server",
    "microservice", "database", "cache", "message_queue", "storage",
    "cdn", "firewall", "auth_service", "external_api", "monitoring", "cloud_service"
}


def _prepare_image_base64(image_bytes: bytes) -> tuple[str, str]:
    """Resize if needed and return (base64_data, media_type)."""
    img = Image.open(BytesIO(image_bytes))
    media_type = "image/png"

    if img.format == "JPEG":
        media_type = "image/jpeg"
    elif img.format == "WEBP":
        media_type = "image/webp"

    if max(img.size) > MAX_IMAGE_DIMENSION:
        img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.LANCZOS)

    buffer = BytesIO()
    save_format = "PNG" if media_type == "image/png" else img.format or "PNG"
    img.save(buffer, format=save_format)
    return base64.b64encode(buffer.getvalue()).decode("utf-8"), media_type


def _parse_components(raw: str) -> list[Component]:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Vision LLM returned invalid JSON: %s", raw[:500])
        raise ValueError("Failed to parse LLM response")

    if isinstance(data, dict):
        data = data.get("components", [])

    components: list[Component] = []
    for i, item in enumerate(data, start=1):
        if item.get("type") not in KNOWN_TYPES:
            item["type"] = "cloud_service"
        if not item.get("id"):
            item["id"] = f"comp_{i}"
        components.append(Component(**item))

    return components


def identify_components(image_bytes: bytes, provider: ProviderType | None = None) -> list[Component]:
    client, model = get_llm_client(provider)
    image_b64, media_type = _prepare_image_base64(image_bytes)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{image_b64}",
                            "detail": "high",
                        },
                    },
                    {"type": "text", "text": SYSTEM_PROMPT},
                ],
            }
        ],
        max_tokens=2000,
        timeout=120,
    )

    content = response.choices[0].message.content or ""
    return _parse_components(content)
