# Hackaton Tech Challenge Fase 5 FIAP - Detecção de ameaças STRIDE

Sistema de **modelagem de ameaças com IA** para o Tech Challenge - Fase 5. O usuário faz upload de um diagrama de arquitetura de software via imagem e a IA identifica os componentes automaticamente, aplica a metodologia **STRIDE** e gera um relatório completo de vulnerabilidades e contramedidas.

---

## Objetivos do Projeto

- Interpretar automaticamente diagramas de arquitetura via IA
- Identificar componentes: usuários, servidores, bancos de dados, APIs, etc.
- Gerar Relatório de Modelagem de Ameaças baseado na metodologia **STRIDE**
- Apresentar vulnerabilidades e contramedidas específicas por componente
- Exportar relatório em **PDF**
- Acompanhar o progresso da análise em tempo real (log de cada etapa durante a execução)

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.11+ · Flask |
| Orquestração IA | **LangGraph** (pipeline visão → componentes → STRIDE → relatório) |
| LLM calls | **LangChain** (`langchain-openai`) |
| Providers suportados | OpenAI (GPT-4o) · Ollama (local) · LM Studio (local) — escolha livre na interface |
| Modelo STRIDE próprio | Qwen2.5-3B fine-tuned localmente (ver seção própria) |
| Modelo de Visão próprio | YOLOv8n treinado do zero em dataset 100% sintético (ver seção "Modelo Treinado Visão") |
| Frontend | Templates Jinja + Bootstrap 5 (dark mode), server-rendered |
| Relatório | Markdown enriquecido + exportação JSON/PDF (via impressão do navegador) |

---

## Arquitetura do Pipeline (LangGraph / agents)

```
                    ┌──────────────────────────────────────────────────────────────────┐
                    │                         Pipeline (agents/nodes.py)                 │
  imagem  ────────► │  analyze_image_node → extract_components_node → analyze_stride_node → generate_report_node │
                    │      (LLM visão)          (LLM texto)               (LLM texto)            (LLM texto)      │
                    └──────────────────────────────────────────────────────────────────┘
                                                                              │
                                                          (opcional) roteia para o Modelo treinado STRIDE
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
├── main.py                   # ← App principal (Flask, server-rendered com templates/)
├── run.py                    # Alternativa para subir o app principal: python run.py
├── agents/                   # Pipeline LangGraph (nós + grafo + estado)
│   ├── nodes.py               # analyze_image / extract_components / analyze_stride / generate_report
│   ├── vision_local.py         # Detecção local de componentes via modelo YOLO treinado (ver training/vision/)
│   ├── graph.py               # StateGraph opcional (main.py chama os nós diretamente)
│   └── state.py                # ThreatModelState (TypedDict)
├── utils/
│   ├── knowledge.py           # Base de conhecimento STRIDE (fallback + classificação de tipo)
│   └── report.py               # Enriquecimento do relatório (tabelas, matriz de risco, CSV)
├── templates/                 # UI server-rendered (Jinja + Bootstrap 5)
│   ├── base.html
│   ├── index.html              # Upload + seleção de provider + Modelo treinado STRIDE
│   └── results.html            # Resultado da análise
├── training/                  # Fine-tuning do "Modelo treinado STRIDE" (ver seção própria)
│   ├── seed_kb.py               # Base de ameaças STRIDE curada manualmente (ground truth)
│   ├── architectures.py         # Templates de arquiteturas sintéticas para gerar dados
│   ├── build_dataset.py         # Gera training/data/stride_sft.jsonl
│   ├── finetune.py              # Fine-tuning LoRA (PEFT) do Qwen2.5-3B-Instruct
│   ├── merge_adapter.py         # Mescla o adapter LoRA nos pesos base
│   ├── evaluate.py              # Teste qualitativo do modelo treinado
│   ├── setup_model.py           # ← Verifica GGUF em disco e registra no Ollama se disponível
│   ├── data/stride_sft.jsonl    # Dataset de treino gerado (39 exemplos / 768 ameaças)
│   ├── output/
│   │   └── Modelfile            # Config do Ollama (template ChatML + parâmetros)
│   └── vision/                  # Detector de componentes YOLOv8n (ver seção "Modelo Treinado Visão")
│       ├── shapes.py             # Ícones procedurais por classe (PIL, sem depender de ícones de terceiros)
│       ├── generate_dataset.py   # Gera diagramas sintéticos anotados em formato YOLO
│       ├── train.py              # Treina o YOLOv8n sobre o dataset gerado
│       ├── evaluate.py           # Roda o modelo sobre imagens reais de teste (training/vision/samples/)
│       └── output/
│           └── stride-vision-yolov8n.pt  # Modelo final treinado (~6MB — vai direto no repo)
└── backend/ + frontend/       # ← App alternativo: API JSON + SPA (ver seção "App Alternativo")
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
LLM_PROVIDER=lmstudio
OPENAI_API_KEY=sk-sua-chave-aqui
OPENAI_MODEL=gpt-4o
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:4b
LM_STUDIO_URL=http://localhost:1234/v1
LM_STUDIO_MODEL=google/gemma-4-12b-qat
LM_STUDIO_MAX_TOKENS=4098
```

---

## Como Executar

### 1. Instalar dependências (apenas na primeira vez)

```powershell
pip install -r requirements.txt
```

### 2. Iniciar o servidor

```powershell
python main.py
```

Acesse: [http://localhost:5000](http://localhost:5000)

Se preferir, `python run.py` faz a mesma coisa (`run.py` só importa o `app` de `main.py` e chama `app.run()` — existe por compatibilidade).

O Ollama só precisa estar rodando se você for usar o provider "Ollama (local)" e/ou o **Modelo treinado STRIDE**:

```powershell
# Em outro terminal — precisa ficar rodando
ollama serve
```

Se aparecer `Error: listen tcp 127.0.0.1:11434: bind: ...` o Ollama **já está rodando** em outro terminal/processo — não é um erro, pode ignorar.

### Resumo dos processos necessários

| Processo | Comando | Necessário para |
|----------|---------|------------------|
| App Flask | `python main.py` | Sempre — serve a UI e a API em `localhost:5000` |
| Ollama | `ollama serve` | Só se for usar o provider "Ollama (local)" e/ou o **Modelo treinado STRIDE** |
| LM Studio | Abrir o app, carregar um modelo e ativar o servidor local (aba Developer) | Só se for usar o provider "LM Studio (local)" (padrão do `.env`) |

**LM Studio — modelo testado, modelos de raciocínio e Max Tokens**

O modelo usado nos testes deste projeto foi o **`google/gemma-4-12b-qat`** — é o valor padrão já preenchido na caixa "Modelo" ao selecionar o provider LM Studio, e o campo mostra esse aviso na interface.

O campo **Max Tokens** na interface controla o limite de saída do LM Studio (padrão: **4098**). `google/gemma-4-12b-qat`, como outros modelos de "raciocínio", gasta uma quantidade grande e variável de tokens **pensando** antes de escrever a resposta visível — com um limite baixo (ex.: 1024) a resposta é cortada no meio do "pensamento" e a etapa de extração de componentes recebe um JSON incompleto, retornando 0 componentes (relatório genérico, sem nada específico do diagrama). Mantenha pelo menos 4098; se ainda assim vier um resultado vazio com um diagrama grande/complexo, aumente ainda mais.

Como rede de segurança adicional, `extract_components_node` (agents/nodes.py) detecta quando a resposta veio cortada por limite de tokens (`finish_reason=length`) e tenta de novo automaticamente com um budget bem maior (6144) antes de desistir e cair no relatório genérico — não depende só do valor configurado na interface.

### Download do Modelo treinado STRIDE

O arquivo GGUF (~3.3 GB) **não está incluído no repositório** (muito grande para o Git) e **não é baixado automaticamente**. Você precisa fazer o download manualmente uma única vez:

1. **Baixe o arquivo** (~3.3 GB) pelo link abaixo:
   [stride-qwen2.5-3b-q8_0.gguf — OneDrive](https://1drv.ms/u/c/00d0a6a099986c76/IQCQa17fkDcwRqPt04rnq-QzAcwb1jkWhpkIjwjtfkCwfxs?e=YO1bcI)

2. **Salve o arquivo** na pasta `training/output/`:
   ```
   training/output/stride-qwen2.5-3b-q8_0.gguf
   ```

3. **Registre no Ollama** (com o Ollama já rodando):
   ```powershell
   cd training/output
   ollama create stride-qwen2.5-3b -f Modelfile
   ```

Enquanto o GGUF não estiver em disco, a interface mostra o link de download diretamente no painel do provider — basta selecionar **"Ollama Local - Fine Tuning (Sem Visão)"** e seguir as instruções exibidas.

Se o GGUF já estiver em disco mas o Ollama não tiver o modelo registrado, a interface também mostra os comandos de registro.

> **Validado:** `python main.py` sobe sem erros e serve a UI e a API corretamente. O fluxo
> completo foi testado via upload real (`POST /analyze`) com Ollama (visão, `gemma3:4b`) +
> Modelo treinado STRIDE — 8 componentes identificados, 15 ameaças geradas e roteadas
> corretamente (log `Modelo STRIDE : stride-qwen2.5-3b`), relatório renderizado com sucesso.
> O caminho sem o modelo treinado (STRIDE gerado pelo mesmo provider da visão) também foi
> testado e funciona (20 ameaças em 10 componentes no mesmo diagrama).
>
> **Validado (opção "100% Local", visão YOLO + STRIDE treinado juntos):** upload real de uma das
> arquiteturas de avaliação do PDF via `provider=vision-trained` — 21 componentes detectados
> localmente (YOLO, sem LLM), 18 ameaças geradas pelo `stride-qwen2.5-3b` e relatório renderizado
> com sucesso, análise completa em **~25s**. Essa mesma chamada, antes de uma otimização (ver
> abaixo), levava **~224s** (quase 4 minutos) só na etapa STRIDE.
>
> **Validado (LM Studio com `google/gemma-4-12b-qat`, Max Tokens 4098):** upload real da mesma
> arquitetura via `provider=lmstudio` — componentes extraídos corretamente com nomes reais do
> diagrama (`Usuários SEI`, `AWS Shield`, `Amazon CloudFront`, `AWS WAF`, `Virtual Private Cloud
> (VPC)`, `Public Subnet`, `Private Subnet`, entre outros), relatório completo renderizado. Antes
> do ajuste de Max Tokens/mecanismo de retry (ver seção "LM Studio — modelo testado..." acima),
> essa mesma combinação retornava 0 componentes (JSON cortado no meio pelo modelo de raciocínio).

**Otimização: `max_tokens` não era respeitado contra Ollama/LM Studio.** Ao testar a opção 100%
local ponta a ponta, a etapa STRIDE (via `stride-qwen2.5-3b`) levou 210s numa única chamada e
devolveu ~194 mil caracteres (bem acima do limite de ~30 ameaças definido no prompt). Causa raiz:
versões recentes do `langchain_openai` renomeiam o parâmetro `max_tokens` para
`max_completion_tokens` (nome atual da API da OpenAI) — mas o Ollama e o LM Studio (servidores
`llama.cpp`) só reconhecem `max_tokens` e ignoram `max_completion_tokens` silenciosamente, então o
limite nunca era aplicado e o modelo gerava até estourar sozinho. A correção
(`agents/nodes.py`, função `_get_llm`) passa `extra_body={"max_tokens": ...}` além do parâmetro
normal, forçando o nome de campo correto no payload para os providers `ollama` e `lmstudio`.
Depois da correção, a mesma chamada caiu de 210s para **8.8s** — e isso vale para **toda** chamada
via Ollama/LM Studio no app, não só a etapa STRIDE (visão, extração de componentes e relatório
também respeitam o limite corretamente agora).

---

## Logs do Backend

O sistema exibe logs detalhados de cada etapa no terminal **e também na interface**: a tela de
carregamento consulta `GET /progress/<run_id>` a cada 600ms e mostra os mesmos passos em tempo
real enquanto a análise roda (não é mais um texto genérico com temporizador fixo).

Exemplo do log no terminal:

```
17:07:12  INFO     __main__              ============================================================
17:07:12  INFO     __main__              NOVA ANÁLISE INICIADA
17:07:12  INFO     __main__                Arquivo         : arch.png (245.3 KB)
17:07:12  INFO     __main__                Provider        : ollama
17:07:12  INFO     __main__                URL/Modelo local: http://localhost:11434 / gemma3:4b
17:07:12  INFO     __main__                Modelo STRIDE   : stride-qwen2.5-3b
17:07:12  INFO     __main__              ============================================================
17:07:12  INFO     __main__              [1/4] analyze_image_node — iniciando
17:07:12  INFO     agents.nodes            provider: ollama | modelo: gemma3:4b
17:07:20  INFO     agents.nodes            analyze_image_node → LLM            resposta 4649 chars (~1162 tokens) em 8.2s
17:07:20  INFO     __main__              [1/4] analyze_image_node — concluído em 8.9s | descrição: 4649 chars
17:07:20  INFO     __main__              [2/4] extract_components_node — iniciando
17:07:24  INFO     __main__              [2/4] extract_components_node — concluído em 4.3s | 8 componentes | 3 limites de confiança | 7 fluxos de dados
17:07:24  INFO     __main__              [3/4] analyze_stride_node — iniciando
17:07:24  INFO     agents.nodes            usando modelo STRIDE treinado: ollama/stride-qwen2.5-3b
17:07:29  INFO     agents.nodes            Modelo treinado: 15 ameaças em 6 componentes
17:07:29  INFO     __main__              [4/4] generate_report_node — iniciando
17:07:37  INFO     __main__              ANÁLISE CONCLUÍDA em 28.2s — run_id: 8f600f07-...
17:07:37  INFO     __main__                Modelo visão  : gemma3:4b (ollama)
17:07:37  INFO     __main__                Modelo STRIDE : stride-qwen2.5-3b
```

---

## Rotas

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/` | Página de upload (seleção de provider) |
| `GET` | `/providers` | JSON com disponibilidade de cada provider — `openai`, `ollama`, `lmstudio`, `stride-trained` (Fine Tuning Sem Visão) e `vision-trained` (Fine Tuning Com Visão) |
| `GET` | `/stride-model` | JSON com disponibilidade do Modelo treinado STRIDE isoladamente (legado, mantido para compatibilidade — a interface usa `/providers`) |
| `GET` | `/progress/<run_id>` | JSON com os passos já concluídos da análise em andamento (`{"steps": [...], "done": bool}`) — consultado via polling pela tela de carregamento |
| `POST` | `/analyze` | Recebe o diagrama + form fields, roda o pipeline, redireciona para `/results/<run_id>` |
| `GET` | `/results/<run_id>` | Página com o resultado completo da análise |
| `GET` | `/download/<run_id>/<fmt>` | Exporta o relatório: `fmt` = `md` \| `json` (PDF é gerado no navegador via impressão, não por essa rota) |

### POST /analyze — Form fields

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `diagram` | UploadFile | Diagrama PNG/JPG/JPEG/WEBP |
| `provider` | string | `openai` \| `ollama` \| `lmstudio` \| `stride-trained` — ver "Providers LLM" abaixo |
| `local_url` / `local_model` | string (opt) | URL/modelo quando `provider` é `ollama`, `lmstudio` ou `stride-trained` |
| `lm_max_tokens` | int (opt) | Limite de tokens de saída, só relevante para `lmstudio` |
| `run_id` | string (opt) | UUID gerado no navegador (`crypto.randomUUID()`) usado para consultar `/progress/<run_id>` durante a execução |
| `use_stride_model` | `"true"` (opt) | Alternativa direta (via API) ao `provider=stride-trained` — força o uso do Modelo treinado STRIDE mantendo `provider` como o real (`ollama`/`lmstudio`/`openai`) para a etapa de visão |

---

## Fluxo Detalhado

```
Usuário faz upload do diagrama (form em /)
        │  (gera um run_id no navegador e começa a consultar
        │   GET /progress/<run_id> a cada 600ms)
        ▼
Flask POST /analyze
        │  (cada etapa abaixo registra uma linha em _progress[run_id],
        │   consultada pela tela de carregamento em tempo real)
        ├── analyze_image_node       ← LangChain ChatOpenAI (visão)
        │   HumanMessage([image_url, texto])
        │   → descrição textual detalhada da arquitetura
        │
        ├── extract_components_node  ← LangChain ChatOpenAI (texto)
        │   → converte a descrição em componentes estruturados (JSON)
        │
        ├── analyze_stride_node      ← LangChain ChatOpenAI (texto)
        │   → ameaças STRIDE por componente
        │   Se use_stride_model=true: chama o Modelo treinado STRIDE com o
        │   prompt/schema exatos do treino, e converte a resposta para o
        │   formato nativo deste pipeline (ver training/ e nodes.py)
        │
        └── generate_report_node     ← LangChain ChatOpenAI (texto)
            → relatório STRIDE em Markdown
        │
        ▼
utils/report.enrich_report() — adiciona tabelas, matriz de risco e plano de remediação
        │
        ▼
Resultado salvo em memória (run_id) → redireciona para /results/<run_id>
```

---

## Providers LLM

| Provider | Tipo | Configuração |
|----------|------|-------------|
| **OpenAI** | Nuvem | `OPENAI_API_KEY` no `.env` |
| **Ollama** | Local | Um modelo com **visão** ativo (ex.: `ollama pull gemma3:4b` ou `llava`) + URL/model configuráveis na interface |
| **LM Studio** | Local | Servidor local ativo + URL/model configuráveis na interface |
| **Ollama Local - Fine Tuning (Sem Visão)** | Local | A etapa de **visão** usa Ollama normalmente, mas a caixa "Modelo" some — assume-se o modelo fixo apropriado. Força a etapa de **análise STRIDE** a usar o modelo fine-tuned `stride-qwen2.5-3b` (ver seção própria abaixo) |
| **Ollama Local - Fine Tuning (Com Visão)** | Local | Força a etapa de **visão** a usar o detector YOLO treinado localmente (`stride-vision-yolov8n`, sem LLM) e a etapa de **análise STRIDE** a usar `stride-qwen2.5-3b` — a caixa "Modelo" some; a URL configurada passa a valer só para o LLM da etapa de **relatório** final (ver seção "Modelo Treinado Visão" abaixo) |

Para Ollama e LM Studio, a URL e o modelo são editáveis diretamente na interface sem reiniciar o servidor. Nas duas opções "Ollama Local - Fine Tuning", a caixa "Modelo" fica escondida (o front assume os modelos fine-tuned fixos correspondentes) — só a URL do servidor Ollama continua editável. O seletor de provider consulta `GET /providers` ao carregar a página e marca como "(offline)" os providers indisponíveis — eles continuam selecionáveis para que o usuário veja as instruções de como habilitá-los (a opção "Fine Tuning (Sem Visão)" aparece offline se o Ollama não tiver o modelo `stride-qwen2.5-3b` registrado, e a interface exibe o link de download e os comandos de registro diretamente no painel).

> **Nota:** o campo "Modelo" para Ollama vem preenchido com `gemma3:4b` por padrão, mas esse modelo
> precisa estar baixado (`ollama pull gemma3:4b`) para funcionar. Se você tiver outro modelo com
> visão baixado (ex.: `llava`), digite o nome dele no campo — confira o que está disponível
> com `ollama list`.

---

## Treinamento dos Modelos Fine-Tuned (Visão Geral)

O projeto treina **dois modelos próprios** localmente, um para cada etapa do pipeline que hoje
depende de LLMs de terceiros. Esta seção é um resumo rápido de "o que é cada um e como treinar" —
os detalhes completos (arquitetura, prompt/schema, limitações conhecidas, testes reais) estão nas
duas seções seguintes ("Modelo Treinado STRIDE" e "Modelo Treinado Visão").

| | Modelo STRIDE (texto) | Modelo de Visão (YOLO) |
|---|---|---|
| Etapa que substitui | `analyze_stride_node` (gerar ameaças STRIDE) | `analyze_image_node` + `extract_components_node` (identificar componentes na imagem) |
| Modelo base | Qwen2.5-3B-Instruct + LoRA | YOLOv8n (nano) |
| Dataset de treino | 39 arquiteturas sintéticas, parafraseadas por um LLM (`training/data/stride_sft.jsonl`, 768 ameaças) | ~1400 diagramas sintéticos desenhados via PIL (`training/vision/data/`, anotação automática) |
| Onde ficam os scripts | [`training/`](training/) | [`training/vision/`](training/vision/) |
| Requisitos de treino | GPU 12GB+ VRAM, LM Studio aberto (só pra parafrasear o dataset) | GPU acelera, mas roda em CPU também (YOLOv8n é leve) |
| Saída final | `training/output/stride-qwen2.5-3b-q8_0.gguf` (~3.3GB) — **download manual**, não vai pro Git | `training/vision/output/stride-vision-yolov8n.pt` (~6MB) — **já vai no repositório** |
| Como é servido | Registrado no Ollama (`ollama create ...`) | Carregado direto no processo Flask (`ultralytics`), sem servidor externo |
| Opção correspondente na UI | "Ollama Local - Fine Tuning (Sem Visão)" | "Ollama Local - Fine Tuning (Com Visão)" (usa os dois modelos treinados juntos) |

### Treinar os dois do zero — resumo dos comandos

```powershell
# ── Modelo STRIDE (texto) — ver seção completa "Modelo Treinado STRIDE" abaixo ──
cd training
pip install -r requirements.txt          # + torch certo pra sua GPU (ver pytorch.org)
python build_dataset.py                  # usa o LM Studio local pra parafrasear o dataset
python finetune.py                       # LoRA sobre Qwen2.5-3B-Instruct (~2min numa RTX 5080)
python merge_adapter.py                  # mescla o adapter LoRA nos pesos base
# converter pra GGUF (llama.cpp) e registrar no Ollama — comandos completos na seção abaixo

# ── Modelo de Visão (YOLO) — ver seção completa "Modelo Treinado Visão" abaixo ──
cd ../training/vision
pip install -r requirements.txt
python generate_dataset.py               # dataset 100% sintético, sem LLM nem GPU
python train.py                          # treina o YOLOv8n sobre o dataset gerado
python evaluate.py                       # testa em imagens reais (training/vision/samples/)
```

### Ícones reais (opcional — melhora a classificação do modelo de visão)

O modelo de visão nasce treinado só com ícones **desenhados proceduralmente** (sem depender de
nada de terceiros — ver "Dataset 100% sintético" mais abaixo). Pra melhorar a precisão em
diagramas com ícones oficiais de nuvem (como os do PDF de avaliação do hackathon), dá pra baixar
os pacotes gratuitos da AWS/Azure e rodar um script que organiza tudo automaticamente nas pastas
de classe certas:

- **AWS**: https://aws.amazon.com/architecture/icons/
- **Azure**: https://learn.microsoft.com/en-us/azure/architecture/icons/

```powershell
cd training/vision
python prepare_assets.py --source "C:/caminho/para/pasta-extraida-do-pacote"
# imprime quantos ícones foram encontrados por classe — repita uma vez por pacote (AWS, Azure)

python generate_dataset.py && python train.py   # regenera o dataset e retreina usando os ícones reais
```

Resultados reais desse processo (antes/depois de usar ícones da AWS) e a explicação de por que o
dataset é gerado assim em vez de anotado manualmente estão na seção "Usando ícones reais" mais
abaixo, dentro de "Modelo Treinado Visão".

---

## Modelo Treinado STRIDE (Fine-tuning Local)

Além dos providers genéricos acima (que usam modelos prontos), o projeto inclui um **modelo próprio, fine-tuned especificamente para gerar ameaças STRIDE**. Ele foi treinado localmente com LoRA sobre o **Qwen2.5-3B-Instruct**, usando um dataset sintético gerado a partir de uma base de conhecimento curada manualmente.

### Escopo: só a etapa STRIDE, não a visão

O modelo é **texto-somente** (sem capacidade de visão). Por isso ele **não** substitui o pipeline inteiro — ele entra apenas na etapa `analyze_stride_node`, enquanto a etapa `analyze_image_node` (ler o diagrama e identificar componentes) continua usando o provider normal selecionado na interface (OpenAI, Ollama com um modelo de visão, ou LM Studio).

### Adaptação de prompt/schema

O modelo foi fine-tuned exclusivamente sobre o **prompt e o schema JSON** usados em `backend/services/stride.py` (o app alternativo — ver abaixo): JSON agrupado por categoria STRIDE (`spoofing`, `tampering`, ...), com vocabulário de tipos de componente restrito (16 tipos). O pipeline principal (`agents/nodes.py`) usa um prompt e schema **diferentes** (agrupado por nome de componente, com campos extras como `attack_vector`/`vulnerability`/`cwe_reference`, e um vocabulário de 20 tipos).

Para o modelo treinado funcionar corretamente dentro de `agents/nodes.py`, a função `_call_stride_model()` faz a ponte: monta o prompt exato do treino (mapeando tipos não vistos no treino, como `load_balancer` ou `application_server`, para o tipo mais próximo do vocabulário original), chama o modelo, e converte a resposta de volta para o formato nativo do pipeline. Os campos que o modelo treinado não gera (`attack_vector`, `vulnerability`, `cwe_reference`) recebem um texto genérico indicando isso.

> Sem essa conversão, o modelo — que nunca viu esse prompt/schema durante o treino — retorna
> respostas incompletas (testamos e caiu de ~15-20 ameaças para 2 ameaças no mesmo diagrama).

### Onde ele está no projeto

Todo o pipeline de treinamento vive em [training/](training/):

| Arquivo/Pasta | O que é | No repositório |
|---|---|---|
| `training/seed_kb.py` | ~60 ameaças STRIDE reais, escritas manualmente, uma para cada combinação (tipo de componente × categoria STRIDE). É a "verdade fundamental" de onde o dataset é derivado. | sim |
| `training/architectures.py` | 8 modelos de arquitetura (ex.: "loja virtual", "banco digital", "plataforma de microsserviços") que combinam vários tipos de componente em sistemas realistas. | sim |
| `training/build_dataset.py` | Combina os dois acima, gera ~39 arquiteturas sintéticas concretas, e usa um LLM local (LM Studio) para reescrever/parafrasear os textos (mantendo categoria STRIDE, severidade e CWE fixos) — evita que o modelo apenas decore o texto literal do `seed_kb.py`. | sim |
| `training/data/stride_sft.jsonl` | Dataset final gerado (39 exemplos, 768 ameaças), no formato chat (`system`/`user`/`assistant`) idêntico ao prompt real de produção (`backend/services/stride.py`). | sim |
| `training/finetune.py` | Fine-tuning LoRA do Qwen2.5-3B-Instruct usando `transformers` + `peft`. | sim |
| `training/setup_model.py` | Verifica se o GGUF está em disco e registra no Ollama se disponível. Chamado por `main.py` / `run.py` na inicialização. O download do GGUF é manual (ver seção "Download do Modelo"). | sim |
| `training/output/Modelfile` | Define como o Ollama deve servir o `.gguf` (inclui o template de chat ChatML do Qwen — sem isso o Ollama não formata os prompts corretamente). | sim |
| `training/merge_adapter.py` | Mescla o adapter LoRA nos pesos originais do Qwen, gerando um modelo completo e independente. | sim |
| `training/output/stride-qwen2.5-3b-lora/` | Adapter LoRA treinado (checkpoint, ~120MB). Gerado por `finetune.py`. | nao — ignorado pelo .gitignore |
| `training/output/stride-qwen2.5-3b-merged/` | Modelo completo mesclado (safetensors, ~6GB). Gerado por `merge_adapter.py`. | nao — ignorado pelo .gitignore |
| `training/output/stride-qwen2.5-3b-q8_0.gguf` | **Modelo final em produção** (GGUF Q8_0, ~3.3GB). **Download manual** — link na seção "Download do Modelo" e na interface web. | nao — ignorado pelo .gitignore |
| `training/evaluate.py` | Script de teste rápido: roda o adapter em cima de arquiteturas que não estavam no treino, para checar qualitativamente a saída. | sim |
| `agents/nodes.py` (`_call_stride_model`) | Ponte entre o prompt/schema do treino e o schema nativo do pipeline principal (ver acima). | sim |

### Como o treinamento foi feito (para reproduzir)

Requisitos: GPU NVIDIA com uns 12GB+ de VRAM livres, e o [LM Studio](https://lmstudio.ai) aberto localmente (usado só para gerar/parafrasear o dataset).

```powershell
cd training

# 0. Instalar dependências (Python global da máquina, NÃO um venv do projeto)
#    Instale antes o torch certo para sua GPU: https://pytorch.org/get-started/locally/
pip install -r requirements.txt

# 1. Gerar o dataset de treino (chama o LM Studio local para parafrasear)
python build_dataset.py
# → gera data/stride_sft.jsonl

# 2. Fine-tuning LoRA (roda ~2min numa RTX 5080; ajusta pelo tamanho da GPU)
python finetune.py
# → salva o adapter em output/stride-qwen2.5-3b-lora/

# 3. Avaliar qualitativamente (opcional, mas recomendado)
python evaluate.py

# 4. Mesclar o adapter LoRA nos pesos base
python merge_adapter.py
# → gera output/stride-qwen2.5-3b-merged/

# 5. Converter para GGUF (precisa do conversor do llama.cpp — não incluso no repo)
#    git clone --depth 1 --filter=blob:none --no-checkout https://github.com/ggml-org/llama.cpp
#    git sparse-checkout set convert_hf_to_gguf.py convert_hf_to_gguf_update.py gguf-py conversion
#    git checkout
#    pip install gguf sentencepiece protobuf
python <caminho-para>/llama.cpp/convert_hf_to_gguf.py output/stride-qwen2.5-3b-merged `
  --outtype q8_0 --outfile output/stride-qwen2.5-3b-q8_0.gguf

# 6. Registrar no Ollama (alternativa mais rápida: python training/setup_model.py)
cd output
ollama create stride-qwen2.5-3b -f Modelfile
```

> **Pontos de atenção descobertos na prática:**
> - Sempre feche o LM Studio (ou descarregue o modelo) antes de treinar — a VRAM concorrente entre os dois processos já causou lentidão extrema (~20x) e uma tela azul nesta máquina.
> - Use `per_device_eval_batch_size=1` (não o padrão 8) — um batch de avaliação maior estoura VRAM ao converter logits para fp32 num vocabulário de ~152k tokens.
> - O `Modelfile` do Ollama **precisa** de um `TEMPLATE` explícito em ChatML — por padrão o Ollama não extrai o chat template embutido no GGUF, e sem ele o modelo recebe um prompt sem estrutura de papéis (system/user) e produz respostas completamente fora do esperado.
> - Rode os scripts de `training/` com o **Python global** da máquina (`torch`/`peft`/etc.), não com um venv do projeto — são ambientes separados.
> - O modelo é sensível ao **prompt/schema exatos** do treino — usá-lo com um prompt diferente (mesmo que semanticamente equivalente) degrada muito a qualidade da saída (ver seção "Adaptação de prompt/schema" acima).

### Limitações conhecidas

- Dataset pequeno (39 exemplos sintéticos) — o modelo tende a repetir frases entre componentes do mesmo tipo e nunca gera severidade `low` (não havia nenhum exemplo `low` no `seed_kb.py`).
- Sem capacidade de visão — não pode substituir o `analyze_image_node`.
- Os campos `attack_vector`, `vulnerability` e `cwe_reference` do relatório ficam genéricos quando o modelo treinado é usado (ele não os gera — ver "Adaptação de prompt/schema").

### Como usar na interface

1. Tenha o Ollama rodando (`ollama serve`) e o modelo `stride-qwen2.5-3b` registrado (ver seção "Download do Modelo" acima). Confirme com `ollama list`.
2. Abra [http://localhost:5000](http://localhost:5000) — o seletor **Provedor** consulta `GET /providers` automaticamente ao carregar a página.
3. Escolha a opção **"Ollama Local - Fine Tuning (Sem Visão)"** no dropdown. Se estiver offline (modelo não registrado no Ollama), a opção aparece com "(offline)" no nome e pode ser selecionada — a interface exibe o link de download do GGUF e os comandos para registrar no Ollama.
4. Com essa opção selecionada, os campos **URL do servidor** e **Modelo** continuam visíveis — eles configuram o modelo usado só para a etapa de **visão** (identificar os componentes na imagem, ex.: `gemma3:4b`); a etapa de análise STRIDE sempre usa `stride-qwen2.5-3b` fixo, independente do que estiver nesses campos. Um aviso abaixo do formulário explica isso, e mostra instruções de como habilitar (`ollama serve` + registrar o modelo) se estiver offline, com um botão "Verificar novamente".
5. Faça upload do diagrama e analise. No resultado, a linha de informações mostra os dois modelos usados: `Provedor: ollama · Modelo (visão): gemma3:4b · Modelo (STRIDE): stride-qwen2.5-3b`.

> Internamente, ao selecionar essa opção o formulário envia `provider=stride-trained`; o backend
> (`main.py`) traduz isso para `provider=ollama` + `use_stride_model=True` antes de rodar o
> pipeline — `stride-trained` não é um provider de LLM de verdade, é só uma opção de interface
> que combina "visão via Ollama" com "STRIDE via modelo treinado" em uma única escolha.

---

## Modelo Treinado Visão (Detecção Local de Componentes)

Além do modelo STRIDE acima (texto), o projeto inclui um **detector de objetos treinado do zero**
para a etapa de **identificação de componentes na imagem** — é exatamente o que o edital do
hackathon pede: "Construir ou buscar um Dataset contendo imagens de Arquitetura de Software",
"Anotar o Dataset para treinar o modelo supervisionado" e "Treinar o modelo". Sem esse modelo, a
identificação de componentes depende inteiramente de uma VLM de terceiros (GPT-4o/Ollama/LM Studio).

### Escopo: só a etapa de visão, não STRIDE nem relatório

O modelo é um detector de objetos (**YOLOv8n**, via [ultralytics](https://github.com/ultralytics/ultralytics))
que recebe a imagem e retorna caixas delimitadoras + classe de cada componente. Ele **substitui**
`analyze_image_node` + `extract_components_node` numa única etapa (a detecção já retorna
componentes estruturados, não precisa de um segundo passo de LLM para extrair JSON de texto
livre) — ver `analyze_image_local_node` em `agents/nodes.py`. Ele **não** substitui a etapa STRIDE
nem a de relatório (que continuam usando um LLM de texto).

### Dataset 100% sintético — sem depender de ícones de terceiros

Diferente de tentar reunir e anotar manualmente um dataset de diagramas reais (trabalho manual
significativo e problemas de licença se usasse os ícones oficiais AWS/Azure/GCP), o dataset é
**gerado programaticamente**: `training/vision/shapes.py` desenha um ícone por classe (retângulo
arredondado, cilindro, nuvem, boneco de palito, escudo, pasta, etc.) usando só primitivas do PIL,
em dois estilos — **"icon"** (bloco colorido preenchido, no estilo de diagramas de nuvem) e
**"generic"** (contorno com leve tremor, simulando diagrama hand-drawn). Como a posição de cada
ícone é escolhida pelo próprio gerador, a bounding box de cada componente é conhecida exatamente
— **zero anotação manual**.

`training/vision/generate_dataset.py` compõe diagramas completos (4 a 10 componentes por imagem,
layout em grid com jitter, setas de conexão decorativas, rótulo de texto por componente) e grava
tudo em formato YOLO (`training/vision/data/images|labels/{train,val}/` + `dataset.yaml`).

### Classes (vocabulário de `agents/nodes.py`)

`user, web_server, api_gateway, load_balancer, application_server, database, cache,
message_queue, authentication_service, cdn, firewall, storage, microservice, container, function,
network, external_service, monitoring, dns, vpn` (20 classes).

### Onde ele está no projeto

| Arquivo/Pasta | O que é |
|---|---|
| `training/vision/shapes.py` | Ícones procedurais por classe (2 estilos) — sem depender de ícones de terceiros. |
| `training/vision/generate_dataset.py` | Gera o dataset sintético anotado em formato YOLO. |
| `training/vision/train.py` | Treina o YOLOv8n (`ultralytics`) sobre o dataset gerado. |
| `training/vision/evaluate.py` | Roda o modelo treinado sobre imagens reais de teste (`training/vision/samples/`). |
| `training/vision/requirements.txt` | Dependências do treino (`ultralytics`, `pillow`, `pyyaml`). |
| `training/vision/prepare_assets.py` | Organiza ícones oficiais AWS/Azure/GCP (baixados manualmente pelo usuário) nas pastas `assets/icons/<classe>/` — ver seção "Usando ícones reais" abaixo. |
| `training/vision/output/stride-vision-yolov8n.pt` | Modelo final treinado (~6MB — pequeno o bastante para ir direto no repositório, ao contrário do GGUF de 3.3GB do modelo STRIDE). |
| `agents/vision_local.py` | Carrega o modelo treinado e roda a inferência dentro do processo Flask (import de `ultralytics` fica dentro da função, só é pago por quem usa esta opção). |
| `agents/nodes.py` (`analyze_image_local_node`) | Nó combinado que substitui `analyze_image_node` + `extract_components_node` quando esta opção é usada. |

### Como treinar (para reproduzir)

```powershell
cd training/vision

# 0. Instalar dependências (pode ser o Python global da máquina, como no
#    treino do modelo STRIDE — precisa de torch; GPU acelera bastante mas
#    roda em CPU também para o YOLOv8n)
pip install -r requirements.txt

# 1. Gerar o dataset sintético (rápido — não usa LLM nem GPU, só PIL)
python generate_dataset.py
# → gera data/images|labels/{train,val}/ e data/dataset.yaml

# 2. Treinar
python train.py
# → salva output/stride-vision-yolov8n.pt

# 3. Avaliar qualitativamente sobre imagens reais
#    Exporte as 2 arquiteturas de avaliação do PDF do hackathon como PNG
#    e salve em training/vision/samples/, depois:
python evaluate.py
# → detecções anotadas em training/vision/samples_output/
```

### Como usar na interface

Precisa de `ultralytics` instalado no **mesmo ambiente do app Flask** (diferente do modelo
STRIDE, que roda via Ollama fora do processo Python — um modelo de visão custom só roda dentro do
processo que faz a inferência):

```powershell
pip install ultralytics
```

Depois, escolha **"Ollama Local - Fine Tuning (Com Visão)"** no seletor de Provedor — a
interface mostra se o peso do modelo já está em disco e se o `stride-qwen2.5-3b` está registrado
no Ollama, com o comando de treino caso falte algo.

### Limitações conhecidas

- Dataset ainda majoritariamente sintético (posições, layout e composição sempre gerados) — mesmo
  usando ícones reais da AWS (ver "Usando ícones reais" abaixo), a generalização para diagramas
  reais não é perfeita. As 2 arquiteturas de avaliação do PDF do hackathon servem de teste
  qualitativo, não de validação estatística.
  > **Testado nas 2 arquiteturas do PDF (após integrar ícones reais da AWS via
  > `prepare_assets.py`):** a **localização** dos componentes é forte (a maioria das detecções sai
  > com >90% de confiança, caixa bem ajustada ao ícone). A **classificação** melhorou bastante em
  > relação à versão só com ícones procedurais (ex.: os 3 "Application Load Balancer" do diagrama
  > AWS agora saem corretos), mas ainda erra em vários casos — parte por confusão real entre
  > classes visualmente parecidas (RDS/ElastiCache classificados como `cdn`; API Gateway e
  > "Developer portal" trocados entre si no diagrama Azure) e parte porque vários ícones do
  > diagrama AWS (CloudTrail, AWS Backup, KMS, SES) simplesmente não têm correspondência em
  > nenhuma das 20 classes do vocabulário — não há rótulo "certo" possível para eles. Dá pra
  > melhorar mais com mais épocas, dataset maior e o pacote de ícones do Azure (não usado nesta
  > rodada), mas o MVP foi considerado suficiente para o escopo do hackathon (dataset construído,
  > anotado e modelo supervisionado treinado para identificar componentes).
- Só detecta **componentes** — não infere conexões, fluxos de dados nem limites de confiança
  (por isso `trust_boundaries`/`data_flows` ficam vazios quando esta opção é usada). É exatamente
  o escopo pedido pelo edital para a parte de visão; fluxos de dados continuam fora do MVP.

### Usando ícones reais (opcional — melhora a classificação em diagramas com ícones oficiais)

`shapes.render_icon()` já usa um PNG real de `training/vision/assets/icons/<classe>/` no lugar do
desenho procedural, se existir, com fallback automático. `training/vision/prepare_assets.py`
automatiza organizar pacotes de ícones oficiais baixados manualmente nessas pastas:

```powershell
cd training/vision

# 1. Baixe manualmente e extraia os pacotes oficiais (gratuitos para uso em
#    diagramas de arquitetura):
#    AWS:   https://aws.amazon.com/architecture/icons/
#    Azure: https://learn.microsoft.com/en-us/azure/architecture/icons/

# 2. Rode uma vez por pacote extraído — organiza os ícones certos nas pastas
#    de classe via busca por palavra-chave no nome do arquivo
python prepare_assets.py --source "C:/caminho/para/Asset-Package_AWS"
python prepare_assets.py --source "C:/caminho/para/Azure_Public_Service_Icons"
# imprime, por classe, quantos ícones foram encontrados — classes sem ícone
# continuam usando o desenho procedural (fallback automático)

# 3. Se o pacote só tiver SVG (comum no Azure), instale o conversor opcional:
pip install cairosvg

# 4. Regenere o dataset e retreine
python generate_dataset.py
python train.py
```

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

Na página de resultado (`/results/<run_id>`), aba "Exportar", a interface tem **um único botão: "Exportar .pdf"**. Ele troca para a aba "Relatório" e abre a caixa de impressão do navegador (`window.print()`); um CSS específico (`@media print` em `templates/base.html`) esconde tudo (navegação, cards de métricas, abas, botões) e mostra só o conteúdo de `#tab-report` — forçando `display`/`opacity`/`visibility` independente do estado das abas do Bootstrap, para não sair em branco. Use a opção "Salvar como PDF" da caixa de impressão do navegador.

> As exportações em Markdown (`GET /download/<run_id>/md`), JSON (`GET /download/<run_id>/json`)
> e CSV (`GET /download/<run_id>/csv`) continuam existindo no backend por compatibilidade, mas
> não têm mais botão na interface — foram substituídas pela exportação em PDF.

---

## App Alternativo (backend/ + frontend/)

O projeto também inclui uma segunda implementação, com **API JSON separada do frontend** (SPA em HTML/CSS/JS puro) em vez do server-rendered do app principal. É funcionalmente equivalente (mesmos providers, mesmo Modelo treinado STRIDE), mas com uma API REST própria — útil se você quiser consumir a análise de outro cliente que não seja a UI.

> Nesse app alternativo, o Modelo Treinado STRIDE ainda é um **checkbox separado** do seletor de
> provider (não foi migrado para uma opção de dropdown como no app principal) — a mesma lógica de
> backend (`use_stride_model=True`), só a UI é diferente.

```powershell
cd backend
pip install -r requirements.txt
python main.py
```

Acesse [http://localhost:8000](http://localhost:8000) (porta diferente do app principal, dá pra rodar os dois ao mesmo tempo). Endpoints: `GET /api/health`, `GET /api/providers`, `GET /api/stride-model`, `POST /api/analyze` (retorna JSON em vez de redirecionar para uma página HTML). Detalhes da API, schemas e exemplos de resposta estão nos arquivos de `backend/routers/analysis.py` e `backend/models/schemas.py`.
