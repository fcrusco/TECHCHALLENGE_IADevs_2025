import logging

from langchain_core.messages import HumanMessage, SystemMessage

from models.schemas import AnalysisResponse, Component, StrideReport, ProviderType
from services.llm_factory import get_llm_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Based on this STRIDE threat analysis, write a 2-3 paragraph executive summary in Portuguese.
Highlight: total threats found, highest risk components, most critical threat categories,
and top 3 recommended countermeasures. Be concise and direct."""


def _build_analysis_text(components: list[Component], stride_report: StrideReport) -> str:
    all_threats = (
        stride_report.spoofing + stride_report.tampering + stride_report.repudiation
        + stride_report.information_disclosure + stride_report.denial_of_service
        + stride_report.elevation_of_privilege
    )
    critical = [t for t in all_threats if t.risk_level == "critical"]
    high     = [t for t in all_threats if t.risk_level == "high"]

    lines = [
        f"Components: {len(components)} | Threats: {len(all_threats)} | Critical: {len(critical)} | High: {len(high)}",
        "Components: " + ", ".join(f"{c.name}({c.type})" for c in components),
        f"Spoofing:{len(stride_report.spoofing)} Tampering:{len(stride_report.tampering)} "
        f"Repudiation:{len(stride_report.repudiation)} InfoDisclosure:{len(stride_report.information_disclosure)} "
        f"DoS:{len(stride_report.denial_of_service)} PrivEsc:{len(stride_report.elevation_of_privilege)}",
    ]
    if critical:
        lines.append("Most critical: " + "; ".join(f"[{t.component_name}] {t.threat}" for t in critical[:3]))

    return "\n".join(lines)


def generate_report(
    components: list[Component],
    stride_report: StrideReport,
    provider: ProviderType | None = None,
    override_url: str | None = None,
    override_model: str | None = None,
    model_used: str = "",
    provider_used: ProviderType = "openai",
) -> AnalysisResponse:
    logger.info("[report] Generating executive summary | provider=%s", provider)

    llm, model = get_llm_client(provider, override_url, override_model)
    logger.info("[report] Using model=%s", model)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=_build_analysis_text(components, stride_report)),
    ]

    logger.info("[report] Calling LLM via LangChain...")
    response = llm.invoke(messages)
    summary = response.content or "Relatório de análise STRIDE gerado com sucesso."

    logger.info("[report] Summary generated | chars=%d", len(summary))

    return AnalysisResponse(
        components=components,
        stride_report=stride_report,
        summary=summary,
        provider_used=provider_used,
        model_used=model_used or model,
    )
