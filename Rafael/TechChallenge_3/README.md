# Medical AI Assistant - LLaMA 3.2 Fine-tuning + LangChain

Assistente virtual medico com fine-tuning do `meta-llama/Llama-3.2-1B-Instruct`
sobre o dataset MedQuAD, pipeline LangChain com RAG e camadas de seguranca para
uso clinico responsavel.

---

## Como testar o projeto

Se voce so quer rodar o assistente para ver funcionando, siga apenas estes passos.
Nao e necessario fazer nada no Kaggle nem ter token do HuggingFace.

### 1. Pre-requisitos de software

- Ollama (para rodar o modelo de linguagem localmente)
  Download: https://ollama.com
  Apos instalar, abra o Ollama. Ele ficara rodando na bandeja do sistema.

---

### 2. Baixar o projeto

```bash
git clone 
cd 
```

---

### 3. Baixar o modelo de linguagem

Com o Ollama aberto, rode no terminal:

```bash
ollama pull llama3.2:1b
```

Isso baixa o modelo (1.3 GB). Aguarde a conclusao.

---

### 4. Criar o ambiente virtual e instalar as dependencias

```bash
# Criar o ambiente virtual
python -m venv venv

# Ativar o ambiente virtual
# No Windows:
venv\Scripts\activate
# No Mac/Linux:
source venv/bin/activate

# Instalar as dependencias
pip install -r requirements.txt

# Instalar o modelo de linguagem do spaCy (necessario para anonimizacao)
python -m spacy download pt_core_news_sm
```

---

### 5. Configurar o arquivo de ambiente

```bash
# Windows
copy .env.example .env

# Mac/Linux
cp .env.example .env
```

Abra o arquivo `.env` e confirme que estas linhas estao assim:

```
USE_OLLAMA_FALLBACK=true
OLLAMA_MODEL=llama3.2:1b
```

---

### 6. Construir o indice de busca semantica 

```bash
python -m src.assistant.retriever
```

Este comando le os documentos do MedQuAD em `data/processed/` e constroi
o indice FAISS em `data/vectorstore/`. Demora alguns minutos.
So precisa ser feito uma vez. Na proxima execucao o indice ja estara pronto.

---

### 7. Iniciar o assistente

```bash
python main.py
```

O terminal vai pedir seu nome e em seguida abrir o chat interativo.
Comandos disponiveis: `sair` para encerrar | `log` para ver o historico de auditoria.

---

### Perguntas para testar

Experimente estas perguntas para ver as diferentes funcionalidades:

Resposta clinica normal:
- Quais sao os sintomas da pneumonia?
- Como e feito o diagnostico do diabetes tipo 2?
- Quais sao as causas da insuficiencia renal cronica?

Alerta de validacao humana (guardrail de aviso):
- Qual a dosagem recomendada de metformina?
- Quando e indicada a internacao por pneumonia?

Bloqueio completo (guardrail de restricao):
- Voce pode prescrever um remedio para pressao alta?

Auditoria:
- Apos algumas perguntas, digite `log` para ver o registro de todas as interacoes.

---

### Solucao de problemas comuns

**Erro: "model requires more system memory"**
O Ollama nao tem RAM suficiente. Feche o navegador e outros programas antes de rodar.
O modelo `llama3.2:1b` precisa de aproximadamente 1.5 GB de RAM livre.

**Erro: "connection refused" ou "Ollama nao esta rodando"**
O Ollama precisa estar aberto antes de rodar o `main.py`.
Abra o Ollama pelo menu iniciar ou rode `ollama serve` em um terminal separado.

**Erro: "vector store nao encontrado"**
Execute o passo 6 antes de rodar o `main.py`:
`python -m src.assistant.retriever`

**O terminal mostra caracteres estranhos no .env**
Se o .env foi editado no Windows, pode haver problema de encoding.
Abra o arquivo no Bloco de Notas, va em Arquivo > Salvar Como e escolha
codificacao UTF-8 antes de salvar.

---

## Estrutura do Projeto

```
medical-assistant/
├── data/
│   ├── raw/            # MedQuAD bruto
│   ├── processed/      # train.jsonl, val.jsonl, test.jsonl
│   └── vectorstore/    # Indice FAISS (gerado pelo retriever)
├── outputs/
│   └── llama-medical/  # Modelo fine-tunado (opcional, gerado no Kaggle)
├── src/
│   ├── preprocessing/
│   │   ├── anonymizer.py   # Anonimizacao de PII via Microsoft Presidio (LGPD)
│   │   ├── curator.py      # Filtragem de qualidade e deduplicacao do dataset
│   │   └── formatter.py    # Formatacao dos dados no template LLaMA 3 Instruct
│   ├── finetuning/
│   │   ├── dataset_builder.py  # Converte XMLs do MedQuAD em JSONL curado
│   │   ├── trainer.py          # Verificacao do Ollama e teste de sanidade
│   │   └── evaluator.py        # Avaliacao com ROUGE-L e BLEU
│   ├── assistant/
│   │   ├── pipeline.py   # Pipeline LangChain LCEL (LLM + RAG + guardrails + auditoria)
│   │   ├── retriever.py  # Busca semantica com FAISS e embeddings multilinguais
│   │   ├── memory.py     # Historico de mensagens da sessao
│   │   └── tools.py      # Ferramentas LangChain (exames, protocolos, alertas)
│   ├── security/
│   │   ├── guardrails.py      # Limites de atuacao do assistente
│   │   ├── logger.py          # Log de auditoria em JSONL (conformidade LGPD)
│   │   └── explainability.py  # Rastreabilidade de fontes nas respostas
│   └── utils/
│       └── config.py          # Configuracoes centralizadas (.env + YAML)
├── notebooks/
│   └── 04_kaggle_finetuning.ipynb  # Fine-tuning no Kaggle
├── logs/               # audit.jsonl gerado automaticamente ao usar o assistente
├── main.py             # Terminal interativo do assistente
├── requirements.txt
├── .env.example
└── README.md
```

---

## Arquitetura e Fluxo de Dados

```
ETAPA 1 - Preparacao dos dados (local)
  git clone MedQuAD -> data/raw/medquad/
  dataset_builder.py -> data/processed/
    train.jsonl (11.657 amostras)
    val.jsonl   (1.457 amostras)
    test.jsonl  (1.457 amostras)
          |
          | upload
          v

ETAPA 2 - Fine-tuning (Kaggle, GPU T4, realizado uma unica vez)
  04_kaggle_finetuning.ipynb
  LLaMA 3.2 3B + QLoRA 4-bit + MedQuAD
  -> adaptadores LoRA salvos em /kaggle/working/llama-medical/
          |
          | download + extrair para outputs/llama-medical/
          v

ETAPA 3 - Uso local
  python main.py
  -> carrega modelo fine-tunado (ou Ollama llama3.2:1b como fallback)
  -> RAG com FAISS busca documentos MedQuAD relevantes
  -> LLM gera resposta em portugues com base no contexto
  -> guardrails verificam a resposta
  -> resposta com fontes registrada no log de auditoria
```

---

## Fluxo interno de cada pergunta

```
Pergunta do medico
      |
      v
[Guardrails - entrada]
  Bloqueia se: prescricao, diagnostico definitivo, alteracao de prontuario
      |
      v
[Retriever RAG - FAISS]
  Busca os 5 documentos MedQuAD mais similares semanticamente
      |
      v
[LLM - LLaMA 3.2 fine-tunado / Ollama fallback]
  Gera resposta em portugues com base nos documentos recuperados
      |
      v
[Guardrails - saida]
  Adiciona aviso se tema critico (dosagem, cirurgia, internacao, etc.)
      |
      v
[Explainability]
  Associa documentos MedQuAD a resposta gerada
      |
      v
[Logger de Auditoria]
  Registra a interacao completa em logs/audit.jsonl
      |
      v
Resposta ao medico (com fontes + alertas + ID de auditoria)
```

---

## Para quem quiser reproduzir o fine-tuning

### Pre-requisito - Acesso ao LLaMA 3.2 no HuggingFace

1. Acesse: huggingface.co/meta-llama/Llama-3.2-1B-Instruct
2. Clique em "Request access" e preencha o formulario
3. Aguarde a aprovacao (geralmente minutos a horas)
4. Gere um token READ em: huggingface.co/settings/tokens

### Preparar o dataset

```bash
git clone https://github.com/abachaa/MedQuAD.git data/raw/medquad
python -m src.finetuning.dataset_builder --config configs/model_config.yaml
```

### Fine-tuning no Kaggle

1. Acesse kaggle.com e crie uma conta
2. Verifique seu numero de telefone em "Settings" (necessario para GPU)
3. Crie um novo notebook e faca upload de: notebooks/04_kaggle_finetuning.ipynb
4. Ative a GPU: Session Options > Accelerator > GPU T4 x2
5. Ative a internet: Session Options > Internet > On
6. Faca upload dos arquivos train.jsonl e val.jsonl via "+ Add Input"
7. Execute as celulas na ordem
8. Baixe o arquivo llama-medical.zip gerado na aba Output
9. Extraia e mova para: medical-assistant/outputs/llama-medical/

No .env, ajuste:
```
FINETUNED_MODEL_PATH=./outputs/llama-medical
USE_OLLAMA_FALLBACK=false
```

---

## Seguranca e conformidade LGPD

O assistente nunca emite prescricoes, diagnosticos definitivos ou permite
alteracoes de prontuario. Temas criticos (dosagem, cirurgia, internacao,
quimioterapia, anestesia) disparam aviso de validacao humana obrigatoria.

Toda interacao e registrada em logs/audit.jsonl com:
- interaction_id: UUID unico por interacao
- timestamp: data e hora UTC
- user_id: identificador do medico
- query_hash: hash SHA256 da pergunta (texto original nao e salvo)
- sources_used: documentos MedQuAD utilizados na resposta
- guardrail_flags: alertas disparados
- blocked: se a interacao foi bloqueada
