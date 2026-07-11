"""
Pipeline LangGraph para Modelagem de Ameaças STRIDE.

Fluxo do grafo:
  START → vision_node → stride_node → report_node → END

Cada nó recebe o AnalysisState completo e retorna um dict
com os campos a atualizar no estado.
"""
import logging
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from models.schemas import AnalysisResponse, Component, ProviderType, StrideReport

logger = logging.getLogger(__name__)

# Modelo STRIDE fine-tuned (Qwen2.5-3B LoRA, ver training/), servido localmente
# via Ollama. Não tem capacidade de visão, então só substitui a etapa de
# análise STRIDE — a etapa de visão continua usando o provider selecionado.
STRIDE_MODEL_PROVIDER = "ollama"
STRIDE_MODEL_URL = "http://localhost:11434"
STRIDE_MODEL_NAME = "stride-qwen2.5-3b"


class AnalysisState(TypedDict):
    # ── entradas ──────────────────────────────────────────────
    image_bytes: bytes
    provider: str | None
    override_url: str | None
    override_model: str | None
    use_stride_model: bool
    # ── intermediário ─────────────────────────────────────────
    components: list[dict]          # list[Component.model_dump()]
    stride_data: dict | None        # StrideReport.model_dump()
    # ── saída ─────────────────────────────────────────────────
    summary: str | None
    model_used: str
    provider_used: str
    stride_model_used: str | None


# ── Nó: Visão ───────────────────────────────────────────────────────────────
def vision_node(state: AnalysisState) -> dict:
    """Chama o VisionService para identificar os componentes da arquitetura na imagem."""
    from services.vision import identify_components
    from services.llm_factory import get_llm_client

    logger.info("[graph:vision] início do nó")

    provider     = state.get("provider")
    override_url = state.get("override_url")
    override_mdl = state.get("override_model")

    components = identify_components(
        state["image_bytes"], provider, override_url, override_mdl
    )
    _, model = get_llm_client(provider, override_url, override_mdl)

    logger.info("[graph:vision] nó concluído | %d componentes | modelo=%s",
                len(components), model)

    return {
        "components":    [c.model_dump() for c in components],
        "model_used":    model,
        "provider_used": provider or "openai",
    }


# ── Nó: STRIDE ──────────────────────────────────────────────────────────────
def stride_node(state: AnalysisState) -> dict:
    """Chama o StrideService para gerar as ameaças STRIDE de cada componente."""
    from services.stride import analyze_stride

    logger.info("[graph:stride] início do nó | %d componentes", len(state["components"]))

    components = [Component(**c) for c in state["components"]]

    if state.get("use_stride_model"):
        logger.info("[graph:stride] usando modelo STRIDE treinado: %s/%s",
                     STRIDE_MODEL_PROVIDER, STRIDE_MODEL_NAME)
        stride = analyze_stride(components, STRIDE_MODEL_PROVIDER, STRIDE_MODEL_URL, STRIDE_MODEL_NAME)
        stride_model_used = STRIDE_MODEL_NAME
    else:
        stride = analyze_stride(
            components,
            state.get("provider"),
            state.get("override_url"),
            state.get("override_model"),
        )
        stride_model_used = None

    all_threats = (
        stride.spoofing + stride.tampering + stride.repudiation
        + stride.information_disclosure + stride.denial_of_service
        + stride.elevation_of_privilege
    )
    logger.info("[graph:stride] nó concluído | %d ameaças no total", len(all_threats))

    return {"stride_data": stride.model_dump(), "stride_model_used": stride_model_used}


# ── Nó: Relatório ─────────────────────────────────────────────────────────────
def report_node(state: AnalysisState) -> dict:
    """Chama o ReportService para gerar o resumo executivo."""
    from services.report import generate_report

    logger.info("[graph:report] início do nó")

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

    logger.info("[graph:report] nó concluído | resumo com %d caracteres", len(result.summary))
    return {"summary": result.summary}


# ── Montagem e compilação do grafo ───────────────────────────────────────────
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
logger.info("[graph] Pipeline de análise LangGraph compilado (visão → stride → relatório)")


# ── Helper: executa o grafo e retorna o AnalysisResponse ─────────────────────
def run_analysis(
    image_bytes: bytes,
    provider: ProviderType | None = None,
    override_url: str | None = None,
    override_model: str | None = None,
    use_stride_model: bool = False,
) -> AnalysisResponse:
    """Executa o pipeline de análise completo e retorna uma resposta estruturada."""
    import time
    t0 = time.time()
    logger.info("[graph] início do run_analysis | provider=%s | use_stride_model=%s", provider, use_stride_model)

    initial_state: AnalysisState = {
        "image_bytes":   image_bytes,
        "provider":      provider,
        "override_url":  override_url,
        "override_model": override_model,
        "use_stride_model": use_stride_model,
        "components":    [],
        "stride_data":   None,
        "summary":       None,
        "model_used":    "",
        "provider_used": provider or "openai",
        "stride_model_used": None,
    }

    final_state = analysis_graph.invoke(initial_state)

    components = [Component(**c) for c in final_state["components"]]
    stride     = StrideReport(**final_state["stride_data"])

    logger.info("[graph] run_analysis concluído em %.1fs", time.time() - t0)

    return AnalysisResponse(
        components=components,
        stride_report=stride,
        summary=final_state["summary"] or "",
        provider_used=final_state["provider_used"],  # type: ignore[arg-type]
        model_used=final_state["model_used"],
        stride_model_used=final_state.get("stride_model_used"),
    )
