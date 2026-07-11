"""Workflow LangGraph para modelagem de ameaças STRIDE."""

from langgraph.graph import END, START, StateGraph

from agents.nodes import (
    analyze_image_node,
    analyze_stride_node,
    extract_components_node,
    generate_report_node,
)
from agents.state import ThreatModelState


def _should_continue_after_components(state: ThreatModelState) -> str:
    """Só encaminha para a análise STRIDE se os componentes foram extraídos com sucesso."""
    if state.get("error"):
        return END
    components = state.get("components", [])
    if not components:
        return END
    return "analyze_stride"


def build_threat_model_graph() -> StateGraph:
    """Monta e compila o workflow LangGraph de modelagem de ameaças."""
    builder = StateGraph(ThreatModelState)

    builder.add_node("analyze_image", analyze_image_node)
    builder.add_node("extract_components", extract_components_node)
    builder.add_node("analyze_stride", analyze_stride_node)
    builder.add_node("generate_report", generate_report_node)

    builder.add_edge(START, "analyze_image")
    builder.add_edge("analyze_image", "extract_components")
    builder.add_conditional_edges(
        "extract_components",
        _should_continue_after_components,
        {"analyze_stride": "analyze_stride", END: END},
    )
    builder.add_edge("analyze_stride", "generate_report")
    builder.add_edge("generate_report", END)

    return builder.compile()


threat_model_graph = build_threat_model_graph()


def run_threat_model(
    image_path: str | None = None,
    image_base64: str | None = None,
    provider: str | None = None,
    override_url: str | None = None,
    override_model: str | None = None,
    use_stride_model: bool = False,
) -> ThreatModelState:
    """Executa o pipeline completo de modelagem de ameaças sobre um diagrama de arquitetura."""
    if not image_path and not image_base64:
        raise ValueError("É necessário informar image_path ou image_base64")

    initial_state: ThreatModelState = {
        "image_path": image_path or "uploaded_image.png",
        "image_base64": image_base64,
        "provider": provider,
        "override_url": override_url,
        "override_model": override_model,
        "use_stride_model": use_stride_model,
        "raw_description": None,
        "components": None,
        "trust_boundaries": None,
        "data_flows": None,
        "threats": None,
        "report_markdown": None,
        "report_json": None,
        "current_step": "start",
        "error": None,
        "messages": [],
        "model_used": None,
        "provider_used": None,
        "stride_model_used": None,
    }

    result = threat_model_graph.invoke(initial_state)
    return result
