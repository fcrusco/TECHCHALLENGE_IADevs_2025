# Spec: Backend

## Estrutura de Arquivos

```
backend/
├── main.py
├── requirements.txt
├── config.py
├── routers/
│   └── analysis.py
├── services/
│   ├── llm_factory.py
│   ├── vision.py
│   ├── stride.py
│   └── report.py
└── models/
    └── schemas.py
```

## requirements.txt

```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
python-multipart>=0.0.9
openai>=1.40.0
pydantic>=2.7.0
pydantic-settings>=2.3.0
python-dotenv>=1.0.0
pillow>=10.4.0
```

## config.py

```python
from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    llm_provider: Literal["openai", "ollama", "lmstudio"] = "openai"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llava"

    lmstudio_base_url: str = "http://localhost:1234/v1"
    lmstudio_model: str = "local-model"

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"

settings = Settings()
```

## models/schemas.py

```python
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

class ProviderInfo(BaseModel):
    id: ProviderType
    name: str
    available: bool
    model: str
```

## services/llm_factory.py

Factory que retorna um cliente OpenAI configurado para o provider escolhido.

```python
from openai import AsyncOpenAI
from config import settings, ProviderType

def get_llm_client(provider: ProviderType | None = None) -> tuple[AsyncOpenAI, str]:
    """Returns (client, model_name) for the given provider."""
    provider = provider or settings.llm_provider

    if provider == "openai":
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        return client, settings.openai_model

    if provider == "ollama":
        client = AsyncOpenAI(
            base_url=f"{settings.ollama_base_url}/v1",
            api_key="ollama",
        )
        return client, settings.ollama_model

    if provider == "lmstudio":
        client = AsyncOpenAI(
            base_url=settings.lmstudio_base_url,
            api_key="lm-studio",
        )
        return client, settings.lmstudio_model

    raise ValueError(f"Unknown provider: {provider}")
```

## services/vision.py

Detecta componentes da imagem via LLM Vision.

**Prompt de sistema:**
```
You are a software architecture expert. Analyze the provided architecture diagram image.
Identify ALL components visible in the diagram (users, servers, databases, APIs, services, etc).
Return a valid JSON array. Each item must have:
- id: unique string like "comp_1", "comp_2"...
- name: component name as shown in diagram
- type: one of [user, web_browser, mobile_app, api_gateway, web_server, microservice,
         database, cache, message_queue, storage, cdn, firewall,
         auth_service, external_api, monitoring, cloud_service]
- description: brief description of its role in this architecture

Return ONLY the JSON array, no markdown, no explanation.
```

**Comportamento:**
- Converte imagem para base64 com `Pillow` (redimensiona se > 2000px para economizar tokens)
- Usa `response_format={"type": "json_object"}` quando suportado
- Valida resposta contra schema `Component` com Pydantic

## services/stride.py

Gera ameaças STRIDE para a lista de componentes.

**Prompt de sistema:**
```
You are a cybersecurity expert specializing in threat modeling using the STRIDE methodology.
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
Return ONLY valid JSON, no markdown.
```

**Comportamento:**
- Envia todos os componentes em uma única chamada de texto
- Faz parse e valida contra `StrideReport`
- Se o provider não suportar vision, usa apenas os nomes/tipos dos componentes

## services/report.py

Consolida `components` + `stride_report` e gera `summary`.

**Prompt para summary:**
```
Based on this STRIDE threat analysis, write a 2-3 paragraph executive summary in Portuguese.
Highlight: total threats found, highest risk components, most critical threat categories,
and top 3 recommended countermeasures.
```

## routers/analysis.py

```
POST /api/analyze
  - Recebe: file (UploadFile), provider (Form, opcional)
  - Valida: tipo de arquivo (image/*), tamanho (< 20MB)
  - Chama: VisionService → StrideService → ReportService
  - Retorna: AnalysisResponse

GET /api/health
  - Retorna: {"status": "ok", "provider": "openai", "model": "gpt-4o"}

GET /api/providers
  - Retorna: lista de ProviderInfo com available=True/False
  - Testa disponibilidade de Ollama/LM Studio com ping na URL base
```

## main.py

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.analysis import router

app = FastAPI(title="STRIDE Threat Modeling API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
```

## Tratamento de Erros

| Situação | HTTP Status | Mensagem |
|----------|-------------|---------|
| Arquivo não é imagem | 422 | "File must be an image (PNG, JPG, JPEG, WEBP)" |
| Arquivo > 20MB | 422 | "File size exceeds 20MB limit" |
| Provider sem API key | 500 | "OpenAI API key not configured" |
| Provider offline (Ollama/LM Studio) | 503 | "Provider {x} is not available at {url}" |
| LLM retorna JSON inválido | 500 | "Failed to parse LLM response" com raw_response no log |
| Timeout LLM (> 120s) | 504 | "LLM request timed out" |
