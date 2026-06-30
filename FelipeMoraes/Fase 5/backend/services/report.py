import logging

from models.schemas import AnalysisResponse, Component, StrideReport, ProviderType
from services.llm_factory import get_llm_client

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = """Based on this STRIDE threat analysis, write a 2-3 paragraph executive summary in Portuguese.
Highlight: total threats found, highest risk components, most critical threat categories,
and top 3 recommended countermeasures."""


def _build_analysis_text(components: list[Component], stride_report: StrideReport) -> str:
    all_threats = (
        stride_report.spoofing
        + stride_report.tampering
        + stride_report.repudiation
        + stride_report.information_disclosure
        + stride_report.denial_of_service
        + stride_report.elevation_of_privilege
    )

    critical = [t for t in all_threats if t.risk_level == "critical"]
    high = [t for t in all_threats if t.risk_level == "high"]

    lines = [
        f"Components analyzed: {len(components)}",
        f"Total threats found: {len(all_threats)}",
        f"Critical threats: {len(critical)}",
        f"High threats: {len(high)}",
        "",
        "Components:",
    ]
    for c in components:
        lines.append(f"- {c.name} ({c.type}): {c.description}")

    lines += [
        "",
        "STRIDE summary by category:",
        f"- Spoofing: {len(stride_report.spoofing)} threats",
        f"- Tampering: {len(stride_report.tampering)} threats",
        f"- Repudiation: {len(stride_report.repudiation)} threats",
        f"- Information Disclosure: {len(stride_report.information_disclosure)} threats",
        f"- Denial of Service: {len(stride_report.denial_of_service)} threats",
        f"- Elevation of Privilege: {len(stride_report.elevation_of_privilege)} threats",
    ]

    if critical:
        lines.append("")
        lines.append("Most critical threats:")
        for t in critical[:5]:
            lines.append(f"- [{t.component_name}] {t.threat}")
            lines.append(f"  Countermeasures: {', '.join(t.countermeasures[:2])}")

    return "\n".join(lines)


def generate_report(
    components: list[Component],
    stride_report: StrideReport,
    provider: ProviderType | None = None,
    model_used: str = "",
    provider_used: ProviderType = "openai",
) -> AnalysisResponse:
    client, model = get_llm_client(provider)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": _build_analysis_text(components, stride_report)},
        ],
        max_tokens=800,
        timeout=60,
    )

    summary = response.choices[0].message.content or "Relatório de análise STRIDE gerado com sucesso."

    return AnalysisResponse(
        components=components,
        stride_report=stride_report,
        summary=summary,
        provider_used=provider_used,
        model_used=model_used or model,
    )
