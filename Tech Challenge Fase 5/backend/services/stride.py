import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from models.schemas import Component, StrideReport, StrideThreat, ProviderType
from services.llm_factory import get_llm_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a cybersecurity expert specializing in threat modeling using the STRIDE methodology.
Given a list of software architecture components, perform a complete STRIDE threat analysis.

For each component, identify relevant threats for each STRIDE category:
- Spoofing: threats to authentication/identity
- Tampering: threats to data/code integrity
- Repudiation: threats to audit trail and accountability
- Information Disclosure: threats to data confidentiality
- Denial of Service: threats to availability
- Elevation of Privilege: threats to authorization boundaries

Return a valid JSON object with exactly these keys:
spoofing, tampering, repudiation, information_disclosure, denial_of_service, elevation_of_privilege

Each key maps to an array of threat objects:
{"component_id":"comp_1","component_name":"Name","threat":"description","risk_level":"low|medium|high|critical","countermeasures":["item1","item2"]}

Limit to 2 countermeasures per threat for conciseness.
Return ONLY valid JSON, no markdown, no extra text."""

VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}
CATEGORIES = [
    "spoofing", "tampering", "repudiation",
    "information_disclosure", "denial_of_service", "elevation_of_privilege"
]


def _build_components_text(components: list[Component]) -> str:
    lines = ["Architecture components to analyze:"]
    for comp in components:
        lines.append(f"- id:{comp.id} name:{comp.name} type:{comp.type} desc:{comp.description}")
    return "\n".join(lines)


def _repair_json(raw: str) -> str:
    """Close unclosed arrays/objects to recover from truncated LLM output."""
    raw = raw.rstrip().rstrip(",")
    depth: list[str] = []
    in_string = False
    escape = False

    for char in raw:
        if escape:
            escape = False
            continue
        if char == "\\" and in_string:
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth.append("}")
        elif char == "[":
            depth.append("]")
        elif char in "}]" and depth and depth[-1] == char:
            depth.pop()

    return raw + "".join(reversed(depth))


def _parse_stride_report(raw: str) -> StrideReport:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    data = None
    try:
        data = json.loads(raw)
        logger.info("[stride] JSON parsed successfully")
    except json.JSONDecodeError as exc:
        logger.warning("[stride] JSON parse failed (%s) — attempting repair", exc)
        repaired = _repair_json(raw)
        try:
            data = json.loads(repaired)
            logger.info("[stride] JSON recovered after repair")
        except json.JSONDecodeError:
            logger.error("[stride] JSON unrecoverable | first 400 chars: %s", raw[:400])
            raise ValueError("Failed to parse STRIDE report from LLM response")

    parsed: dict[str, list[StrideThreat]] = {}
    for cat in CATEGORIES:
        threats: list[StrideThreat] = []
        for t in data.get(cat, []):
            if t.get("risk_level") not in VALID_RISK_LEVELS:
                t["risk_level"] = "medium"
            threats.append(StrideThreat(**t))
        parsed[cat] = threats
        logger.info("[stride]   %-30s %d threats", cat, len(threats))

    return StrideReport(**parsed)


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

    # LangChain SystemMessage + HumanMessage
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
