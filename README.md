# Medical AI Assistant - LLaMA 3.2 Fine-tuning + LangChain

Assistente virtual medico com fine-tuning do `meta-llama/Llama-3.2-3B-Instruct`
sobre o dataset MedQuAD, pipeline LangChain com RAG e camadas de seguranca para
uso clinico responsavel.

---

## Estrutura do Projeto

```
medical-assistant/
├── data/
│   ├── raw/            # MedQuAD bruto (populado apos download)
│   ├── processed/      # train.jsonl, val.jsonl, test.jsonl (gerados pelo dataset_builder)
│   └── anonymized/     # Dados anonimizados (gerados pelo anonymizer)
├── outputs/
│   └── llama-medical/  # Modelo fine-tunado (baixado do Kaggle apos treinamento)
├── src/
│   ├── preprocessing/
│   │   ├── anonymizer.py   # Anonimizacao de PII via Microsoft Presidio (LGPD)
│   │   ├── curator.py      # Filtragem de qualidade e deduplicacao do dataset
│   │   └── formatter.py    # Formatacao dos dados no template LLaMA 3 Instruct
│   ├── finetuning/
│   │   ├── dataset_builder.py  # Converte XMLs do MedQuAD em JSONL curado e formatado
│   │   ├── trainer.py          # Verificacao do Ollama e teste de sanidade pos-treino
│   │   └── evaluator.py        # Avaliacao quantitativa com ROUGE-L e BLEU
│   ├── assistant/
│   │   ├── pipeline.py   # Pipeline LangChain LCEL (LLM + RAG + guardrails + auditoria)
│   │   ├── retriever.py  # Busca semantica com FAISS e embeddings multilinguais
│   │   ├── memory.py     # Historico de mensagens da sessao
│   │   └── tools.py      # Ferramentas LangChain (exames, protocolos, alertas)
│   ├── security/
│   │   ├── guardrails.py      # Limites de atuacao do assistente
│   │   ├── logger.py          # Log de auditoria em JSONL
│   │   └── explainability.py  # Rastreabilidade de fontes nas respostas
│   └── utils/
│       └── config.py          # Configuracoes centralizadas (.env + YAML)
├── notebooks/
│   ├── 01_data_exploration.ipynb    # Analise exploratoria do MedQuAD
│   ├── 02_preprocessing_demo.ipynb  # Demonstralção de anonimizacao e curadoria
│   ├── 03_assistant_demo.ipynb      # Demonstração do pipeline completo
│   └── 04_kaggle_finetuning.ipynb   # Fine-tuning no Kaggle
├── tests/
│   ├── test_anonymizer.py
│   ├── test_guardrails.py
│   └── test_pipeline.py
├── configs/
│   ├── model_config.yaml
│   └── pipeline_config.yaml
├── logs/                  # audit.jsonl gerado automaticamente ao usar o assistente
├── main.py                # Terminal interativo do assistente
├── requirements.txt
├── .env.example
└── README.md
```

---

````
Requisitos:
- Ollama rodando localmente: ollama serve
- Modelo baixado: ollama pull llama3.2:1b
- Dataset processado em data/processed/
- Vector store em data/vectorstore/ (gerado pelo retriever)
```

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

ETAPA 2 - Fine-tuning (Kaggle, GPU T4)
  04_kaggle_finetuning.ipynb
  LLaMA 3.2 3B + QLoRA 4-bit + MedQuAD
  -> adaptadores LoRA salvos em /kaggle/working/llama-medical/
          |
          | download + extrair
          v

ETAPA 3 - Uso local
  outputs/llama-medical/  <- adaptadores LoRA
  python main.py
  -> carrega modelo fine-tunado (ou Ollama como fallback)
  -> RAG com FAISS busca documentos MedQuAD relevantes
  -> LLM gera resposta em portugues com base no contexto
  -> guardrails verificam a resposta
  -> resposta com fontes e registrada no log de auditoria
```

---

## Passo a Passo Completo

### Pre-requisito - Acesso ao LLaMA 3.2 no HuggingFace

1. Acesse: huggingface.co/meta-llama/Llama-3.2-3B-Instruct
2. Clique em "Request access" e preencha o formulario
3. Aguarde a aprovacao (geralmente minutos a horas)
4. Gere um token READ em: huggingface.co/settings/tokens
5. Guarde o token - sera usado no Kaggle

(do passo 1 ao 5 já esta feito, escrevi esses passos apenas para saberem o que foi feito)

---

### ETAPA 1 - Configurar o projeto localmente

```bash
# Entre na pasta do projeto
cd medical-assistant

# Crie o ambiente virtual
python -m venv venv
source venv/bin/activate      # Linux/Mac
# venv\Scripts\activate       # Windows

# Instale as dependencias
pip install -r requirements.txt
python -m spacy download pt_core_news_sm

# Configure as variaveis de ambiente
cp .env.example .env
```

---

### ETAPA 2 - Baixar o dataset MedQuAD

```bash
git clone https://github.com/abachaa/MedQuAD.git data/raw/medquad
```

---

### ETAPA 3 - Preparar o dataset

```bash
python -m src.finetuning.dataset_builder --config configs/model_config.yaml
```

Resultado esperado em data/processed/:
- train.jsonl (~11.657 amostras - 80%)
- val.jsonl   (~1.457 amostras - 10%)
- test.jsonl  (~1.457 amostras - 10%)

---

### ETAPA 4 - Fine-tuning no Kaggle

1. Acesse kaggle.com e crie uma conta
2. Verifique seu numero de telefone em "Settings" (necessario para GPU)
3. Crie um novo notebook: Code > New Notebook
4. Ative a GPU: Session Options > Accelerator > GPU T4 x2
5. Ative a internet: Session Options > Internet > On
6. Faca upload do arquivo: notebooks/04_kaggle_finetuning.ipynb
7. Faca upload dos arquivos train.jsonl e val.jsonl via "+ Add Input"
8. Execute as celulas na ordem
9. Ao final, baixe o arquivo llama-medical.zip gerado na aba Output

---

### ETAPA 5 - Configurar o modelo treinado localmente

1. Extraia o llama-medical.zip
2. Mova a pasta para: medical-assistant/outputs/llama-medical/
3. Abra o arquivo .env e confirme:
   FINETUNED_MODEL_PATH=./outputs/llama-medical
   USE_OLLAMA_FALLBACK=false

---

### ETAPA 6 - Construir o vector store

```bash
python -m src.assistant.retriever
```

Este passo cria o indice FAISS em data/vectorstore/.
Demora alguns minutos (gera embeddings para ~14.000 documentos).
Executar apenas uma vez - o indice fica salvo para reutilizacao.

---

### ETAPA 7 - Usar o assistente

```bash
python main.py
```

O terminal interativo sera aberto. Digite perguntas clinicas em portugues.
Comandos disponiveis: "sair" para encerrar | "log" para ver o log de auditoria

---

### Opcao alternativa - Usar Ollama como fallback

Caso o modelo fine-tunado ainda nao esteja disponivel, voce pode usar
o Ollama para testar o pipeline completo:

```bash
# Instale o Ollama: ollama.com
ollama serve
ollama pull llama3.2:1b
```

No .env:
```
USE_OLLAMA_FALLBACK=true
OLLAMA_MODEL=llama3.2:1b
```

---

### ETAPA 8 - Executar os testes

```bash
pytest tests/ -v
```

---

## Seguranca e Limites de Atuacao

O assistente nunca:
- Emite prescricoes sem validacao humana
- Fornece diagnosticos definitivos
- Permite alteracoes de prontuario

O assistente alerta quando a consulta envolve dosagens, cirurgias,
internacao, quimioterapia ou anestesia.

Toda interacao e registrada em logs/audit.jsonl com:
- interaction_id (UUID unico)
- timestamp (UTC)
- user_id
- query_hash (SHA256 da pergunta, por privacidade)
- sources_used (documentos MedQuAD utilizados)
- guardrail_flags (alertas disparados)
- blocked (se a interacao foi bloqueada)

---

## Fluxo do Pipeline

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
[LLM - LLaMA 3.2 fine-tunado]
  Gera resposta em portugues com base nos documentos recuperados
      |
      v
[Guardrails - saida]
  Adiciona aviso se tema critico (dosagem, cirurgia, etc.)
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