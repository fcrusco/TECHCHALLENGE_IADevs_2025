import json
import logging

from fastapi import HTTPException

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
{
  "component_id": "comp_1",
  "component_name": "Component Name",
  "threat": "Specific threat description",
  "risk_level": "low|medium|high|critical",
  "countermeasures": ["countermeasure 1", "countermeasure 2"]
}

Be specific and actionable. Focus on threats relevant to each component type.
Return ONLY valid JSON, no markdown."""

VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}


def _build_components_text(components: list[Component]) -> str:
    lines = ["Architecture components to analyze:"]
    for comp in components:
        lines.append(f"- id: {comp.id}, name: {comp.name}, type: {comp.type}, description: {comp.description}")
    return "\n".join(lines)


def _parse_stride_report(raw: str) -> StrideReport:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("STRIDE LLM returned invalid JSON: %s", raw[:500])
        raise HTTPException(status_code=500, detail="Failed to parse LLM response") from exc

    categories = ["spoofing", "tampering", "repudiation",
                  "information_disclosure", "denial_of_service", "elevation_of_privilege"]

    parsed: dict[str, list[StrideThreat]] = {}
    for cat in categories:
        threats_raw = data.get(cat, [])
        threats: list[StrideThreat] = []
        for t in threats_raw:
            if t.get("risk_level") not in VALID_RISK_LEVELS:
                t["risk_level"] = "medium"
            threats.append(StrideThreat(**t))
        parsed[cat] = threats

    return StrideReport(**parsed)


async def analyze_stride(components: list[Component], provider: ProviderType | None = None) -> StrideReport:
    client, model = get_llm_client(provider)
    components_text = _build_components_text(components)

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": components_text},
            ],
            max_tokens=4000,
            timeout=120,
        )
    except Exception as exc:
        err = str(exc)
        if "timed out" in err.lower():
            raise HTTPException(status_code=504, detail="LLM request timed out")
        raise HTTPException(status_code=503, detail=f"LLM request failed: {err}") from exc

    content = response.choices[0].message.content or ""
    return _parse_stride_report(content)
