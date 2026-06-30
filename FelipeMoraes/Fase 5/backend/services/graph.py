"""
LangGraph pipeline for STRIDE Threat Modeling.

Graph flow:
  START → vision_node → stride_node → report_node → END

Each node receives the full AnalysisState and returns a dict
of fields to update in the state.
"""
import logging
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from models.schemas import AnalysisResponse, Component, ProviderType, StrideReport

logger = logging.getLogger(__name__)


class AnalysisState(TypedDict):
    # ── inputs ────────────────────────────────────────────────
    image_bytes: bytes
    provider: str | None
    override_url: str | None
    override_model: str | None
    # ── intermediate ──────────────────────────────────────────
    components: list[dict]          # list[Component.model_dump()]
    stride_data: dict | None        # StrideReport.model_dump()
    # ── output ────────────────────────────────────────────────
    summary: str | None
    model_used: str
    provider_used: str


# ── Node: Vision ──────────────────────────────────────────────────────────────
def vision_node(state: AnalysisState) -> dict:
    """Calls VisionService to identify architecture components from the image."""
    from services.vision import identify_components
    from services.llm_factory import get_llm_client

    logger.info("[graph:vision] node start")

    provider     = state.get("provider")
    override_url = state.get("override_url")
    override_mdl = state.get("override_model")

    components = identify_components(
        state["image_bytes"], provider, override_url, override_mdl
    )
    _, model = get_llm_client(provider, override_url, override_mdl)

    logger.info("[graph:vision] node complete | %d components | model=%s",
                len(components), model)

    return {
        "components":    [c.model_dump() for c in components],
        "model_used":    model,
        "provider_used": provider or "openai",
    }


# ── Node: STRIDE ──────────────────────────────────────────────────────────────
def stride_node(state: AnalysisState) -> dict:
    """Calls StrideService to generate STRIDE threats for each component."""
    from services.stride import analyze_stride

    logger.info("[graph:stride] node start | %d components", len(state["components"]))

    components = [Component(**c) for c in state["components"]]
    stride = analyze_stride(
        components,
        state.get("provider"),
        state.get("override_url"),
        state.get("override_model"),
    )

    all_threats = (
        stride.spoofing + stride.tampering + stride.repudiation
        + stride.information_disclosure + stride.denial_of_service
        + stride.elevation_of_privilege
    )
    logger.info("[graph:stride] node complete | %d total threats", len(all_threats))

    return {"stride_data": stride.model_dump()}


# ── Node: Report ──────────────────────────────────────────────────────────────
def report_node(state: AnalysisState) -> dict:
    """Calls ReportService to generate the executive summary."""
    from services.report import generate_report

    logger.info("[graph:report] node start")

    components = [Component(**c) for c in state["components"]]
    stride     = StrideReport(**state["stride_data"])

    result = generate_report(
        components=components,
        stride_report=stride,
        provider=state.get("provider"),
        override_url=state.get("override_url"),
        override_model=state.get("override_model"),
        model_used=state.get("model_used", ""),
        provider_used=state.get("provider_used", "openai"),  # type: ignore[arg-type]
    )

    logger.info("[graph:report] node complete | summary chars=%d", len(result.summary))
    return {"summary": result.summary}


# ── Build & compile graph ─────────────────────────────────────────────────────
def _build_graph() -> StateGraph:
    g = StateGraph(AnalysisState)

    g.add_node("vision", vision_node)
    g.add_node("stride", stride_node)
    g.add_node("report", report_node)

    g.add_edge(START,    "vision")
    g.add_edge("vision", "stride")
    g.add_edge("stride", "report")
    g.add_edge("report", END)

    return g.compile()


analysis_graph = _build_graph()
logger.info("[graph] LangGraph analysis pipeline compiled (vision → stride → report)")


# ── Helper: run the graph and return AnalysisResponse ────────────────────────
def run_analysis(
    image_bytes: bytes,
    provider: ProviderType | None = None,
    override_url: str | None = None,
    override_model: str | None = None,
) -> AnalysisResponse:
    """Execute the full analysis pipeline and return a structured response."""
    import time
    t0 = time.time()
    logger.info("[graph] run_analysis start | provider=%s", provider)

    initial_state: AnalysisState = {
        "image_bytes":   image_bytes,
        "provider":      provider,
        "override_url":  override_url,
        "override_model": override_model,
        "components":    [],
        "stride_data":   None,
        "summary":       None,
        "model_used":    "",
        "provider_used": provider or "openai",
    }

    final_state = analysis_graph.invoke(initial_state)

    components = [Component(**c) for c in final_state["components"]]
    stride     = StrideReport(**final_state["stride_data"])

    logger.info("[graph] run_analysis complete in %.1fs", time.time() - t0)

    return AnalysisResponse(
        components=components,
        stride_report=stride,
        summary=final_state["summary"] or "",
        provider_used=final_state["provider_used"],  # type: ignore[arg-type]
        model_used=final_state["model_used"],
    )
