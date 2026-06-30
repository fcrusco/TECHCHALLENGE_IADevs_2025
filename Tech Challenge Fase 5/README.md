# STRIDE Threat Modeling — Hackaton Fase 5

Sistema de **modelagem de ameaças com IA** para a FIAP Software Security. O usuário faz upload de um diagrama de arquitetura de software (imagem) e a IA identifica os componentes automaticamente, aplica a metodologia **STRIDE** e gera um relatório completo de vulnerabilidades e contramedidas.

---

## Objetivos do Projeto

- Interpretar automaticamente diagramas de arquitetura via IA (LLM Vision)
- Identificar componentes: usuários, servidores, bancos de dados, APIs, etc.
- Gerar Relatório de Modelagem de Ameaças baseado na metodologia **STRIDE**
- Apresentar vulnerabilidades e contramedidas específicas por componente
- Exportar relatório em **JSON** ou **PDF**

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.11+ · Flask · Flask-CORS |
| Orquestração IA | **LangGraph** (pipeline visual → STRIDE → relatório) |
| LLM calls | **LangChain** (`langchain-openai`) |
| LLM padrão | OpenAI GPT-4o (vision multimodal) |
| LLM alternativo | Ollama · LM Studio (API OpenAI-compatible) |
| Frontend | HTML + CSS + JS puro — dark mode |
| Relatório | JSON estruturado + exportação PDF via browser |

---

## Arquitetura do Pipeline (LangGraph)

```
                    ┌────────────────────────────────────────────┐
                    │            LangGraph Pipeline               │
                    │                                            │
  image_bytes  ───► │  vision_node  ──►  stride_node  ──►  report_node │ ──► AnalysisResponse
                    │  (LLM Vision)      (LLM texto)     (LLM texto)   │
                    └────────────────────────────────────────────┘
```

Cada nó é uma chamada LangChain independente com logging completo de entrada, saída e tokens.

---

## Estrutura do Projeto

```
Fase 5/
├── .env.example              # Variáveis de ambiente (copie para .env)
├── README.md
├── images/
│   └── logo_fiap.png
├── backend/
│   ├── main.py               # Flask entry point — serve frontend + API + logging
│   ├── requirements.txt
│   ├── config.py             # Settings via pydantic-settings
│   ├── routers/
│   │   └── analysis.py       # Blueprint Flask: /api/analyze, /api/health, /api/providers
│   ├── services/
│   │   ├── llm_factory.py    # Factory ChatOpenAI + LLMLogger callback
│   │   ├── graph.py          # LangGraph StateGraph: vision → stride → report
│   │   ├── vision.py         # Node 1: identifica componentes via LLM Vision
│   │   ├── stride.py         # Node 2: análise STRIDE por componente
│   │   └── report.py         # Node 3: resumo executivo em português
│   └── models/
│       └── schemas.py        # Schemas Pydantic (Component, StrideReport, etc.)
└── frontend/
    ├── index.html            # SPA single-page
    ├── css/
    │   └── styles.css        # Dark mode, paleta STRIDE, responsivo
    └── js/
        └── app.js            # Upload, drag-and-drop, render, export JSON/PDF
```

---

## Configuração

### 1. Copiar variáveis de ambiente

```bash
cp .env.example .env
```

Edite o `.env`:

```env
# Provider padrão
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-sua-chave-aqui
OPENAI_MODEL=gpt-4o
```

---

## Como Executar

Um único comando sobe o backend e serve o frontend:

```bash
cd backend
pip install -r requirements.txt
python main.py
```

Acesse: [http://localhost:8000](http://localhost:8000)

---

## Logs do Backend

O sistema exibe logs detalhados de cada etapa no terminal:

```
12:34:01  INFO      main — Provider  : openai
12:34:01  INFO      main — Frontend  : http://0.0.0.0:8000
12:34:10  INFO      routers.analysis — [analyze] New analysis request received
12:34:10  INFO      routers.analysis — [analyze] File: arch.png | 245312 bytes | image/png
12:34:10  INFO      routers.analysis — [analyze] provider=openai | local_url=None
12:34:10  INFO      routers.analysis — [analyze] Invoking LangGraph pipeline: vision → stride → report
12:34:10  INFO      services.graph   — [graph:vision] node start
12:34:10  INFO      services.llm_factory — ┌─ LLM call start | model=gpt-4o | messages=1
12:34:14  INFO      services.llm_factory — └─ LLM call done  | 4.2s | finish=stop | chars=843 | tokens: prompt=1204 completion=210 total=1414
12:34:14  INFO      services.graph   — [graph:vision] node complete | 8 components | model=gpt-4o
12:34:14  INFO      services.graph   — [graph:stride] node start | 8 components
12:34:14  INFO      services.llm_factory — ┌─ LLM call start | model=gpt-4o | messages=2
12:34:28  INFO      services.llm_factory — └─ LLM call done  | 13.8s | finish=stop | chars=4512 | tokens: prompt=892 completion=1130 total=2022
12:34:28  INFO      services.graph   — [graph:stride] node complete | 48 total threats
12:34:28  INFO      services.graph   — [graph:report] node start
12:34:28  INFO      services.llm_factory — ┌─ LLM call start | model=gpt-4o | messages=2
12:34:31  INFO      services.llm_factory — └─ LLM call done  | 3.1s | finish=stop | chars=612 | tokens: prompt=410 completion=153 total=563
12:34:31  INFO      services.graph   — [graph:report] node complete | summary chars=612
12:34:31  INFO      routers.analysis — [analyze] Pipeline complete in 21.3s | components=8
```

---

## API Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/health` | Status + provider ativo |
| `GET` | `/api/providers` | Lista providers com disponibilidade |
| `POST` | `/api/analyze` | Upload imagem → relatório STRIDE |

### POST /api/analyze — Form fields

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `file` | UploadFile | Diagrama PNG/JPG/JPEG/WEBP (máx 20MB) |
| `provider` | string (opt) | `openai` \| `ollama` \| `lmstudio` |
| `local_url` | string (opt) | URL do servidor local (informada pelo usuário no frontend) |
| `local_model` | string (opt) | Modelo local (informado pelo usuário no frontend) |

### Response

```json
{
  "components": [{ "id": "comp_1", "name": "API Gateway", "type": "api_gateway", "description": "..." }],
  "stride_report": {
    "spoofing": [{ "component_id": "comp_1", "component_name": "API Gateway", "threat": "...", "risk_level": "high", "countermeasures": ["..."] }],
    "tampering": [], "repudiation": [], "information_disclosure": [], "denial_of_service": [], "elevation_of_privilege": []
  },
  "summary": "Resumo executivo em português...",
  "provider_used": "openai",
  "model_used": "gpt-4o"
}
```

---

## Fluxo Detalhado

```
Usuário faz upload de imagem
        │
        ▼
Flask /api/analyze
        │
        ▼
LangGraph: run_analysis()
        │
        ├── vision_node   ← LangChain ChatOpenAI (vision)
        │   HumanMessage([image_url, text_prompt])
        │   → identifica componentes → lista JSON
        │
        ├── stride_node   ← LangChain ChatOpenAI (texto)
        │   SystemMessage(STRIDE prompt) + HumanMessage(componentes)
        │   → ameaças por categoria STRIDE → JSON reparado se truncado
        │
        └── report_node   ← LangChain ChatOpenAI (texto)
            SystemMessage(summary prompt) + HumanMessage(dados)
            → resumo executivo em português
        │
        ▼
AnalysisResponse (Pydantic) → jsonify → Frontend
```

---

## Providers LLM

| Provider | Tipo | Configuração |
|----------|------|-------------|
| **OpenAI** | Nuvem | `OPENAI_API_KEY` no `.env` |
| **Ollama** | Local | `ollama run llava` + URL/model configuráveis na interface |
| **LM Studio** | Local | Servidor local ativo + URL/model configuráveis na interface |

Para Ollama e LM Studio, a URL e o modelo são editáveis diretamente no frontend sem reiniciar o servidor.

---

## Metodologia STRIDE

| Letra | Ameaça | Propriedade Violada |
|-------|--------|---------------------|
| **S** | Spoofing (Falsificação) | Autenticidade |
| **T** | Tampering (Adulteração) | Integridade |
| **R** | Repudiation (Repúdio) | Não-repúdio |
| **I** | Information Disclosure (Divulgação) | Confidencialidade |
| **D** | Denial of Service (Negação de Serviço) | Disponibilidade |
| **E** | Elevation of Privilege (Elevação de Privilégio) | Autorização |

---

## Exportação do Relatório

- **JSON** — dados brutos estruturados para integração com outras ferramentas
- **PDF** — relatório formatado gerado via `window.print()` do browser (sem dependências externas), incluindo resumo executivo, tabela de componentes e ameaças STRIDE por categoria
