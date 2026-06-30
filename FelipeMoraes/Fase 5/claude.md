# Tech Challenge — Fase 5: STRIDE Threat Modeling

## Visão Geral

Sistema de **Modelagem de Ameaças com IA** para a FIAP Software Security. O usuário faz upload de um diagrama de arquitetura de software (imagem) e o sistema:
1. Detecta os componentes automaticamente via LLM Vision
2. Aplica a metodologia **STRIDE** a cada componente
3. Gera um relatório com vulnerabilidades e contramedidas

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.11+ · FastAPI · Uvicorn |
| LLM padrão | OpenAI GPT-4o (vision multimodal) |
| LLM alternativo | Ollama · LM Studio (OpenAI-compatible API) |
| Frontend | HTML + CSS + JS puro — dark mode |
| Relatório | JSON estruturado renderizado no front |

## Estrutura de Diretórios

```
Fase 5/
├── claude.md
├── .env.example
├── specs/
│   ├── architecture.md     # Arquitetura e fluxo do sistema
│   ├── backend.md          # Spec FastAPI / services / endpoints
│   ├── frontend.md         # Spec UI dark mode
│   └── stride.md           # Referência metodologia STRIDE
├── skills/
│   ├── dev.md              # Skill: subir ambiente de desenvolvimento
│   └── analyze.md          # Skill: testar análise de imagem
├── backend/
│   ├── main.py             # FastAPI entry point
│   ├── requirements.txt
│   ├── config.py           # Settings via pydantic-settings (.env)
│   ├── routers/
│   │   └── analysis.py     # POST /api/analyze, GET /api/health
│   ├── services/
│   │   ├── llm_factory.py  # Factory OpenAI / Ollama / LM Studio
│   │   ├── vision.py       # Identifica componentes da imagem
│   │   ├── stride.py       # Engine de análise STRIDE por componente
│   │   └── report.py       # Consolida e formata relatório final
│   └── models/
│       └── schemas.py      # Pydantic request/response models
└── frontend/
    ├── index.html          # SPA single-page
    ├── css/
    │   └── styles.css      # Tema dark, variáveis CSS
    └── js/
        └── app.js          # Upload, fetch, render report
```

## Configuração do Ambiente

Copie `.env.example` para `.env` e configure o provider desejado:

```env
# openai | ollama | lmstudio
LLM_PROVIDER=openai

OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llava

LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_MODEL=local-model

BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
```

## Como Executar

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend (em outro terminal, da raiz do projeto)
python -m http.server 3000 --directory frontend
# Acesse: http://localhost:3000
```

## API Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/health` | Health check + provider ativo |
| `GET` | `/api/providers` | Lista providers configurados |
| `POST` | `/api/analyze` | Upload imagem → relatório STRIDE |

### POST /api/analyze — Request
`multipart/form-data`:
- `file`: PNG / JPG / JPEG / WEBP do diagrama
- `provider` (opcional): `openai` | `ollama` | `lmstudio`

### POST /api/analyze — Response
```json
{
  "components": [
    {
      "id": "comp_1",
      "name": "API Gateway",
      "type": "api_gateway",
      "description": "Ponto de entrada das requisições externas"
    }
  ],
  "stride_report": {
    "spoofing": [
      {
        "component_id": "comp_1",
        "threat": "Falsificação de identidade do client",
        "risk_level": "high",
        "countermeasures": ["Implementar OAuth 2.0", "Validar JWT em cada requisição"]
      }
    ],
    "tampering": [...],
    "repudiation": [...],
    "information_disclosure": [...],
    "denial_of_service": [...],
    "elevation_of_privilege": [...]
  },
  "summary": "Resumo executivo do relatório...",
  "provider_used": "openai",
  "model_used": "gpt-4o"
}
```

## Metodologia STRIDE

| Letra | Ameaça | Propriedade de Segurança Violada |
|-------|--------|----------------------------------|
| **S** | Spoofing (Falsificação) | Autenticidade |
| **T** | Tampering (Adulteração) | Integridade |
| **R** | Repudiation (Repúdio) | Não-repúdio |
| **I** | Information Disclosure (Divulgação) | Confidencialidade |
| **D** | Denial of Service (Negação de Serviço) | Disponibilidade |
| **E** | Elevation of Privilege (Elevação de Privilégio) | Autorização |

## Convenções de Código

- **Toda chamada LLM** passa exclusivamente por `services/llm_factory.py`
- **Type hints** em todas as funções Python
- **Async** em todos os endpoints e chamadas I/O
- **Schemas Pydantic** para todos os dados de entrada e saída
- Frontend usa **CSS custom properties** para o tema — sem valores hard-coded
- Sem comentários que descrevem O QUE o código faz; apenas comentários para WHY não-óbvios

## Skills Disponíveis

Ver pasta `skills/`:
- `dev.md` — Como subir o ambiente completo de desenvolvimento
- `analyze.md` — Como testar a análise com uma imagem
