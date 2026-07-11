from pydantic import BaseModel
from typing import Literal


ProviderType = Literal["openai", "ollama", "lmstudio"]
RiskLevel = Literal["low", "medium", "high", "critical"]
ComponentType = Literal[
    "user", "web_browser", "mobile_app", "api_gateway",
    "web_server", "microservice", "database", "cache",
    "message_queue", "storage", "cdn", "firewall",
    "auth_service", "external_api", "monitoring", "cloud_service"
]


class Component(BaseModel):
    id: str
    name: str
    type: ComponentType
    description: str


class StrideThreat(BaseModel):
    component_id: str
    component_name: str
    threat: str
    risk_level: RiskLevel
    countermeasures: list[str]


class StrideReport(BaseModel):
    spoofing: list[StrideThreat]
    tampering: list[StrideThreat]
    repudiation: list[StrideThreat]
    information_disclosure: list[StrideThreat]
    denial_of_service: list[StrideThreat]
    elevation_of_privilege: list[StrideThreat]


class AnalysisResponse(BaseModel):
    components: list[Component]
    stride_report: StrideReport
    summary: str
    provider_used: ProviderType
    model_used: str
    stride_model_used: str | None = None


class ProviderInfo(BaseModel):
    id: ProviderType
    name: str
    available: bool
    model: str
