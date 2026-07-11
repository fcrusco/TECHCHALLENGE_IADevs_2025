import logging

from langchain_core.messages import HumanMessage, SystemMessage

from models.schemas import AnalysisResponse, Component, StrideReport, ProviderType
from services.llm_factory import get_llm_client

logger = logging.getLogger(__name__)

_FOOTER_PATTERNS = [
    "relatório gerado automaticamente",
    "generated automatically",
    "this report was generated",
    "langchain",
    "langgraph",
    "lm studio",
    "openai",
    "sistema de modelagem de ameaças stride",
]


def _clean_summary(text: str) -> str:
    """Remove auto-generated footers that some LLMs append."""
    text = text.strip()
    lines = text.splitlines()
    clean: list[str] = []
    for line in lines:
        low = line.lower()
        if any(p in low for p in _FOOTER_PATTERNS):
            break
        clean.append(line)
    result = "\n".join(clean).strip()
    return result or text  # fallback to original if we stripped everything


SYSTEM_PROMPT = """Com base nesta análise de ameaças STRIDE, escreva um resumo executivo de 2 a 3 parágrafos em português do Brasil.
Destaque: total de ameaças encontradas, componentes de maior risco, categorias de ameaça mais críticas,
e as 3 principais contramedidas recomendadas. Seja conciso e direto."""


def _build_analysis_text(components: list[Component], stride_report: StrideReport) -> str:
    all_threats = (
        stride_report.spoofing + stride_report.tampering + stride_report.repudiation
        + stride_report.information_disclosure + stride_report.denial_of_service
        + stride_report.elevation_of_privilege
    )
    critical = [t for t in all_threats if t.risk_level == "critical"]
    high     = [t for t in all_threats if t.risk_level == "high"]

    lines = [
        f"Componentes: {len(components)} | Ameaças: {len(all_threats)} | Críticas: {len(critical)} | Altas: {len(high)}",
        "Componentes: " + ", ".join(f"{c.name}({c.type})" for c in components),
        f"Spoofing:{len(stride_report.spoofing)} Tampering:{len(stride_report.tampering)} "
        f"Repudiation:{len(stride_report.repudiation)} InfoDisclosure:{len(stride_report.information_disclosure)} "
        f"DoS:{len(stride_report.denial_of_service)} PrivEsc:{len(stride_report.elevation_of_privilege)}",
    ]
    if critical:
        lines.append("Mais críticas: " + "; ".join(f"[{t.component_name}] {t.threat}" for t in critical[:3]))

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
    logger.info("[report] Gerando resumo executivo | provider=%s", provider)

    llm, model = get_llm_client(provider, override_url, override_model)
    logger.info("[report] Usando modelo=%s", model)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=_build_analysis_text(components, stride_report)),
    ]

    logger.info("[report] Chamando o LLM via LangChain...")
    response = llm.invoke(messages)
    summary = _clean_summary(response.content or "")

    logger.info("[report] Resumo gerado | chars=%d", len(summary))

    return AnalysisResponse(
        components=components,
        stride_report=stride_report,
        summary=summary,
        provider_used=provider_used,
        model_used=model_used or model,
    )
