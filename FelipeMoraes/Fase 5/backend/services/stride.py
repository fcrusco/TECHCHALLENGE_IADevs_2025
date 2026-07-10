import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from models.schemas import Component, StrideReport, StrideThreat, ProviderType
from services.llm_factory import get_llm_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é um especialista em cibersegurança. Realize a análise de ameaças STRIDE sobre os componentes fornecidos.

Retorne APENAS um objeto JSON válido com estas chaves exatas:
spoofing, tampering, repudiation, information_disclosure, denial_of_service, elevation_of_privilege

Cada valor é um array de:
{"component_id":"comp_1","component_name":"Nome","threat":"descrição curta em português do Brasil","risk_level":"low|medium|high|critical","countermeasures":["uma contramedida em português do Brasil"]}

Regras:
- No máximo 1 ameaça por componente por categoria STRIDE
- No máximo 30 ameaças no total, somando todas as categorias
- Apenas 1 contramedida por ameaça
- Mantenha os textos de ameaça e contramedida curtos (menos de 80 caracteres cada)
- Retorne APENAS o objeto JSON, sem markdown, sem explicação"""

VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}
CATEGORIES = [
    "spoofing", "tampering", "repudiation",
    "information_disclosure", "denial_of_service", "elevation_of_privilege"
]


def _build_components_text(components: list[Component]) -> str:
    lines = ["Componentes da arquitetura para analisar:"]
    for comp in components:
        lines.append(f"- id:{comp.id} name:{comp.name} type:{comp.type} desc:{comp.description}")
    return "\n".join(lines)


# ── JSON recovery helpers ──────────────────────────────────────────────────────

def _repair_json(raw: str) -> str:
    """Recover truncated JSON.

    Pass 1 – if we end inside an unclosed string (token-limit cut), truncate back
             to the last '}' that was outside a string.
    Pass 2 – close all remaining unclosed arrays / objects.
    """
    last_obj_close = -1
    in_string = False
    escape = False

    for i, ch in enumerate(raw):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "}":
            last_obj_close = i

    if in_string:
        if last_obj_close >= 0:
            # Truncated beyond last complete object — cut there
            raw = raw[:last_obj_close + 1]
        else:
            # No complete object at all — close the open string so Pass 2
            # can at least close the partial object and array brackets
            raw = raw + '"'

    raw = raw.rstrip().rstrip(",")
    depth: list[str] = []
    in_string = False
    escape = False

    for ch in raw:
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth.append("}")
        elif ch == "[":
            depth.append("]")
        elif ch in "}]" and depth and depth[-1] == ch:
            depth.pop()

    return raw + "".join(reversed(depth))


def _extract_array(text: str, key: str) -> list:
    """Extract the JSON array for `key` using bracket-depth parsing.

    Works even when the surrounding JSON is malformed — we find the '[' that
    belongs to the key and walk forward counting depth until it closes (or the
    string ends, in which case we repair and retry).
    """
    marker = f'"{key}"'
    idx = text.find(marker)
    if idx < 0:
        return []

    colon = text.find(":", idx + len(marker))
    if colon < 0:
        return []

    bracket = text.find("[", colon)
    if bracket < 0:
        return []

    depth = 0
    in_string = False
    escape = False

    for i in range(bracket, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                chunk = text[bracket: i + 1]
                try:
                    return json.loads(chunk)
                except json.JSONDecodeError:
                    try:
                        return json.loads(_repair_json(chunk))
                    except (json.JSONDecodeError, ValueError):
                        return []

    # Array never closed — take what we have and repair
    chunk = text[bracket:]
    try:
        return json.loads(_repair_json(chunk))
    except (json.JSONDecodeError, ValueError):
        return []


def _extract_per_category(raw: str) -> dict:
    """Last-resort recovery: extract each STRIDE category array independently."""
    logger.warning("[stride] Falling back to per-category array extraction")
    result = {}
    for cat in CATEGORIES:
        result[cat] = _extract_array(raw, cat)
        if result[cat]:
            logger.info("[stride]   recovered %-30s %d entries", cat, len(result[cat]))
        else:
            logger.warning("[stride]   could not recover %s", cat)
    return result


# ── Parse ──────────────────────────────────────────────────────────────────────

def _parse_stride_report(raw: str) -> StrideReport:
    raw = raw.strip()
    # Strip markdown code fence if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    data: dict | None = None

    # Attempt 1: direct parse
    try:
        data = json.loads(raw)
        logger.info("[stride] JSON parsed successfully")
    except json.JSONDecodeError as exc:
        logger.warning("[stride] JSON parse failed (%s) — attempting repair", exc)

        # Attempt 2: repair (handles truncated strings + unclosed brackets)
        try:
            repaired = _repair_json(raw)
            data = json.loads(repaired)
            logger.info("[stride] JSON recovered after repair | repaired_chars=%d", len(repaired))
        except (json.JSONDecodeError, ValueError):
            pass

    # Attempt 3: per-category extraction (handles missing commas, garbage chars, etc.)
    if data is None:
        data = _extract_per_category(raw)
        total = sum(len(v) for v in data.values())
        if total == 0:
            logger.error("[stride] All recovery attempts failed | first 400 chars: %s", raw[:400])
            raise ValueError("Failed to parse STRIDE report from LLM response")

    parsed: dict[str, list[StrideThreat]] = {}
    for cat in CATEGORIES:
        threats: list[StrideThreat] = []
        for t in data.get(cat, []):
            if not isinstance(t, dict):
                continue
            if t.get("risk_level") not in VALID_RISK_LEVELS:
                t["risk_level"] = "medium"
            try:
                threats.append(StrideThreat(**t))
            except Exception:
                pass
        parsed[cat] = threats
        logger.info("[stride]   %-30s %d threats", cat, len(threats))

    return StrideReport(**parsed)


# ── Public API ─────────────────────────────────────────────────────────────────

def analyze_stride(
    components: list[Component],
    provider: ProviderType | None = None,
    override_url: str | None = None,
    override_model: str | None = None,
) -> StrideReport:
    logger.info("[stride] Starting STRIDE analysis | %d components | provider=%s",
                len(components), provider)

    llm, model = get_llm_client(provider, override_url, override_model)
    logger.info("[stride] Using model=%s", model)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=_build_components_text(components)),
    ]

    logger.info("[stride] Calling LLM via LangChain...")
    response = llm.invoke(messages)
    content = response.content or ""

    logger.info("[stride] LLM responded | chars=%d", len(content))
    logger.debug("[stride] Raw response (first 300): %s", content[:300])

    return _parse_stride_report(content)
