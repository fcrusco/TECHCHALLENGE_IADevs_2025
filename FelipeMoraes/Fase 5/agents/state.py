from typing import TypedDict, List, Dict, Any, Optional, Annotated
from operator import add


class ArchitectureComponent(TypedDict):
    name: str
    type: str
    description: str
    trust_boundary: Optional[str]
    connections: List[str]
    is_external: bool


class STRIDEThreat(TypedDict):
    threat_id: str
    stride_category: str
    stride_letter: str
    description: str
    severity: str
    attack_vector: str
    vulnerability: str
    countermeasure: str
    cwe_reference: str


class ThreatModelState(TypedDict):
    image_path: str
    image_base64: Optional[str]

    # ── seleção de provider/modelo ──────────────────────────────
    provider: Optional[str]           # "openai" | "ollama" | "lmstudio"
    override_url: Optional[str]
    override_model: Optional[str]
    use_stride_model: Optional[bool]  # usa o Modelo treinado STRIDE só na etapa de análise STRIDE

    raw_description: Optional[str]

    components: Optional[List[ArchitectureComponent]]
    trust_boundaries: Optional[List[str]]
    data_flows: Optional[List[Dict[str, str]]]

    threats: Optional[Dict[str, List[STRIDEThreat]]]

    report_markdown: Optional[str]
    report_json: Optional[Dict[str, Any]]

    current_step: str
    error: Optional[str]
    messages: Annotated[List[Any], add]

    # ── modelo/provider efetivamente usados (para exibição) ─────
    model_used: Optional[str]
    provider_used: Optional[str]
    stride_model_used: Optional[str]
