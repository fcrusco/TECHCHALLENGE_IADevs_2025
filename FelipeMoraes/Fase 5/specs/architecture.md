# Spec: Arquitetura do Sistema

## Fluxo Principal

```
Usuário
  │
  │  upload imagem (diagrama arquitetura)
  ▼
Frontend (HTML/CSS/JS)
  │
  │  POST /api/analyze  multipart/form-data
  ▼
Backend FastAPI
  │
  ├─► VisionService
  │     Envia imagem → LLM Vision
  │     Recebe: lista de componentes identificados
  │
  ├─► StrideService
  │     Para cada componente → LLM texto
  │     Gera ameaças STRIDE + contramedidas
  │
  └─► ReportService
        Consolida tudo em JSON estruturado
        Gera resumo executivo
  │
  │  JSON response
  ▼
Frontend
  Renderiza:
  - Lista de componentes detectados
  - Tabela STRIDE por categoria
  - Resumo executivo
  - Nível de risco por componente (low/medium/high/critical)
```

## Componentes de Software

### 1. Frontend (SPA)
- Arquivo único `index.html` + `css/styles.css` + `js/app.js`
- Dark mode via CSS custom properties
- Header: logo FIAP + "Tech Challenge - Fase 5"
- Funcionalidades:
  - Drag-and-drop ou clique para upload de imagem
  - Seletor de provider LLM (OpenAI / Ollama / LM Studio)
  - Preview da imagem enviada
  - Loading state com spinner
  - Renderização do relatório em seções expansíveis por categoria STRIDE
  - Download do relatório como JSON

### 2. Backend (FastAPI)
- Uvicorn como ASGI server
- CORS habilitado para qualquer origem em desenvolvimento
- Configuração via `.env` / pydantic-settings
- Sem banco de dados — stateless, cada request é independente
- Upload limitado a 20MB

### 3. LLM Factory
Abstração que permite trocar o provider sem alterar os services:

```python
# Uso nos services:
llm = get_llm_client(provider="openai")  # ou "ollama" / "lmstudio"
```

Todos os providers expõem a mesma interface (OpenAI SDK):
- OpenAI: usa `openai.AsyncOpenAI`
- Ollama: usa `openai.AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")`
- LM Studio: usa `openai.AsyncOpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")`

### 4. Vision Service
- Converte imagem para base64
- Monta prompt estruturado pedindo identificação de componentes
- Retorna lista JSON de componentes com: id, name, type, description
- Tipos de componentes suportados:
  - `user` — Usuários/atores externos
  - `web_browser` — Navegadores
  - `mobile_app` — Aplicativos móveis
  - `api_gateway` — API Gateways / Load Balancers
  - `web_server` — Servidores web / aplicação
  - `microservice` — Microserviços
  - `database` — Bancos de dados
  - `cache` — Caches (Redis, Memcached)
  - `message_queue` — Filas de mensagem
  - `storage` — Armazenamento de arquivos
  - `cdn` — CDN / Edge
  - `firewall` — Firewalls / WAF
  - `auth_service` — Serviços de autenticação
  - `external_api` — APIs externas / terceiros
  - `monitoring` — Monitoramento / logs
  - `cloud_service` — Serviços de nuvem genéricos

### 5. STRIDE Service
- Para cada componente, gera uma análise STRIDE completa
- Uma única chamada LLM por componente (ou batch de componentes para modelos que suportam)
- Retorna ameaças agrupadas por categoria STRIDE
- Cada ameaça tem: component_id, threat (descrição), risk_level, countermeasures[]

### 6. Report Service
- Recebe components + stride_data
- Consolida em schema final
- Gera `summary` — parágrafo executivo com os achados mais críticos
- Calcula estatísticas: total ameaças por categoria, componentes de alto risco

## Decisões de Design

- **Stateless**: Sem banco, sessão ou cache. Cada análise é independente.
- **Provider unificado via OpenAI SDK**: Ollama e LM Studio têm APIs compatíveis com OpenAI, então um único SDK serve para os três providers.
- **Duas chamadas LLM por análise**: (1) vision para detectar componentes, (2) texto para STRIDE. Evita prompts muito longos e mantém as respostas focadas.
- **Frontend sem build step**: HTML/CSS/JS puro para manter zero dependências de frontend e facilitar demonstração.
