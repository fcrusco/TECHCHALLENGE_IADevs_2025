# Tech Challenge – Fase 2

## 1. Visão Geral

Este projeto foi desenvolvido como parte do **Tech Challenge – Fase 2**, com foco na otimização de modelos de Machine Learning aplicados ao diagnóstico médico, utilizando como base o trabalho desenvolvido durante a Fase 1 do curso, utilizando um dataset clínico de diabetes para avaliação de risco. A solução utiliza **algoritmos genéticos** para otimização de hiperparâmetros, **integração com LLMs** (OpenAI) para interpretação dos resultados.

---

## 2. Funcionalidades Principais do Projeto

* Treinamento de modelos de classificação (Regressão Logística e Random Forest);
* Otimização de hiperparâmetros via Algoritmos Genéticos;
* Avaliação de desempenho com métricas clínicas (Accuracy, Recall, F1-score);
* Geração de explicações clínicas em linguagem natural utilizando LLM;
* **API REST com FastAPI** para acesso programático às funcionalidades;
* **Interface Web (Frontend)** para interação via navegador;
* Logging e monitoramento de execução;
* Implantação em nuvem no Azure App Service.

---

## 3. Estrutura do Projeto Entregável

```
tech-challenge-fase2/
│
├── src/
│   ├── treinamento.py          # Executável Python que utilizamos para o treinamento do modelo
│   ├── avaliacaoDiabetica.py   # Executável para avaliação dos pacientes
│   ├── utils.py                # Executável com métodos utils utilizados em todo o projeto, como por exemplo a integração com o LLM
│   └── __init__.py
│
├── api/                        # API REST com FastAPI
│   ├── main.py                 # Aplicação FastAPI principal
│   ├── schemas.py              # Modelos Pydantic para validação
│   ├── services.py             # Lógica de negócio (treinamento e avaliação)
│   ├── requirements.txt        # Dependências da API
│   └── README.md               # Documentação da API
│
├── front/                      # Interface Web (Frontend)
│   ├── index.html              # Página principal com interface de avaliação
│   ├── app.js                  # JavaScript para consumir as APIs
│   ├── style.css               # Estilos CSS
│   ├── server.py               # Servidor Flask para servir arquivos estáticos
│   ├── requirements.txt        # Dependências do frontend
│   └── README.md               # Documentação do frontend
│
├── data/
│   └── diabetes.csv            # Dataset utilizado para o projeto
│
├── outputs/                    # Modelos treinados e artefatos
│   ├── lr_model.pkl
│   ├── rf_model.pkl
│   ├── rf_optimized.pkl
│   └── scaler.pkl
│
├── infra/
│   ├── main.tf                 # Infraestrutura como Código (Terraform)
│   └── ARQUITETURA.md          # Documentação detalhada da arquitetura
│
├── startup.sh                  # Script de inicialização utilizado na nuvem (utilizamos Azure)
├── requirements.txt            # Dependências do projeto (bibliotecas do Python)
├── README.md                   # Documentação do projeto
├── ANALISE_SISTEMA.md          # Análise detalhada do sistema e validação de requisitos
└── relatorio_tecnico.pdf       # Relatório técnico entregável com detalhamento do projeto
```

---

## 4. Ambiente Virtual

Utilizamos o **Python 3.13** e um ambiente virtual **venv** para o desenvolvimento deste projeto.

### Criando o ambiente viável

```bash
python -m venv .venv
source .venv/bin/activate   # Linux / Mac
.venv\Scripts\activate      # Windows
```

### Instalando as dependências do Python

```bash
pip install -r requirements.txt
```

---

## 5. Execução local e função dos executáveis

### 5.1. Execução via Scripts Python (Modo Original)

#### Treinamento e otimização dos modelos

```bash
python src/treinamento.py
```

#### Avaliação de risco de diabetes

```bash
python src/avaliacaoDiabetica.py
```

### 5.2. Execução via API REST (Novo)

A API REST permite acesso programático a todas as funcionalidades do sistema através de endpoints HTTP.

#### Instalando dependências da API

```bash
pip install -r api/requirements.txt
```

#### Executando a API

```bash
# Opção 1: Usando uvicorn diretamente
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Opção 2: Executando o arquivo main.py
python api/main.py
```

A API estará disponível em:
- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

#### Endpoints Disponíveis

**Health Check:**
```bash
GET /health
```

**Treinamento de Modelos:**
```bash
POST /treinamento
```

**Avaliação de Paciente:**
```bash
POST /avaliacao
Content-Type: application/json

{
  "Pregnancies": 1,
  "Glucose": 85,
  "BloodPressure": 66,
  "SkinThickness": 29,
  "Insulin": 0,
  "BMI": 26.6,
  "DiabetesPedigreeFunction": 0.351,
  "Age": 31
}
```

Para mais detalhes sobre a API, consulte `api/README.md`.

### 5.3. Execução via Interface Web (Novo)

O frontend oferece uma interface gráfica amigável para interagir com o sistema.

#### Instalando dependências do frontend

```bash
pip install -r front/requirements.txt
```

#### Executando o frontend

```bash
python front/server.py
```

A interface estará disponível em: http://localhost:5000

**Funcionalidades da Interface:**
- **Aba Avaliação**: Formulário para inserir dados do paciente e obter predições
- **Aba Treinamento**: Botão para iniciar o treinamento dos modelos
- Visualização de resultados com explicações geradas por IA
- Design responsivo e moderno

**Nota**: O frontend precisa que a API esteja rodando. Por padrão, ele tenta se conectar a `http://localhost:8000`. Para configurar uma URL diferente, defina a variável de ambiente `API_BASE_URL`:

```bash
export API_BASE_URL=http://sua-api-url:8000
python front/server.py
```

Para mais detalhes sobre o frontend, consulte `front/README.md`.

---

## 6. Execução em Nuvem (Azure)

A aplicação foi implantada utilizando o componente **Azure App Service (Linux, Python 3.14)** no plano **Azure for Students**.

### Principais características da implantação:

* Fizemos o deploy via repositório GITHUB;
* Instalação de dependências e inicialização dos componentes por meio do arquivo `startup.sh`;
* Variáveis sensíveis gerenciadas por *Application Settings* (no caso a key da OPEN AI);
* Monitoramento via Log Stream e Azure Application Insights.

### Script de inicialização da aplicação (startup.sh)

```bash
#!/bin/bash
echo "=== Instalando dependencias ==="
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo "=== Iniciando aplicacao ==="
python src/treinamento.py
```

---

## 7. Infraestrutura como Código (Implementação na Azure Cloud)

A implementação da infraestrutura em nuvem do projeto está escrita em **Terraform**, permitindo versionamento e uma forma mais fácil de reproduzir a implementação em nuvem.

Os arquivos do terraform estão localizados no diretório:

```
infra/
```

---

## 8. Monitoramento e Logs

O projeto utiliza o módulo `logging` do Python para registrar e criar os logs para:

* Métricas de desempenho dos modelos criados pelo treinamento;
* Tempo de execução de cada uma das etapas;
* Eventos do algoritmo genético;
* Erros e exceções.

Os logs são registrados no arquivo **pipeline.log** e enviados para o **stdout** para monitoração em nuvem.


---

## 9. Tecnologias e softwares utilizados no desenvolvimento do projeto

### Backend e Machine Learning
* Python 3.13
* Scikit-learn
* Imbalanced-learn (SMOTE)
* Pandas / NumPy
* OpenAI API (LLM)
* Joblib (persistência de modelos)

### API REST
* FastAPI
* Uvicorn (servidor ASGI)
* Pydantic (validação de dados)
* CORS Middleware

### Frontend
* HTML5 / CSS3 / JavaScript (Vanilla)
* Flask (servidor estático)

### Infraestrutura e Deploy
* Microsoft Azure App Service
* Azure Storage Account (Blob Storage)
* Terraform (Infraestrutura como Código)
* Azure for Students (plano F1 - Free Tier)

### Ferramentas de Desenvolvimento
* Git / GitHub
* Python-dotenv (gerenciamento de variáveis de ambiente)
* Azure Storage Blob SDK

---

## 10. Documentação Adicional

O projeto conta com documentação detalhada em arquivos separados:

* **`ANALISE_SISTEMA.md`**: Análise completa do sistema, validação de requisitos, localização de implementações e desafios enfrentados
* **`infra/ARQUITETURA.md`**: Documentação detalhada da arquitetura de infraestrutura na Azure, incluindo diagramas e componentes
* **`api/README.md`**: Documentação específica da API REST com exemplos de uso
* **`front/README.md`**: Documentação do frontend e instruções de uso

## 11. Arquitetura do Sistema

O sistema foi desenvolvido em três camadas principais:

1. **Camada de Processamento (src/)**: Scripts Python originais para treinamento e avaliação
2. **Camada de API (api/)**: API REST que expõe as funcionalidades de forma programática
3. **Camada de Apresentação (front/)**: Interface web para interação do usuário

### Fluxo de Dados

```
[Frontend] → [API REST] → [Serviços de ML] → [Modelos Treinados]
                ↓
         [Azure Storage] (persistência de modelos)
                ↓
         [OpenAI API] (geração de explicações)
```

### Integração com Azure Storage

O sistema suporta armazenamento de modelos em Azure Blob Storage:
- Modelos são salvos localmente em `outputs/`
- Upload automático para Azure Storage após treinamento
- Download automático do Azure Storage antes de avaliação (se disponível)
- Fallback para modelos locais se Azure Storage não estiver configurado

**Variáveis de Ambiente Necessárias:**
- `OPENAI_API_KEY`: Chave da API OpenAI para geração de explicações
- `AZURE_STORAGE_CONNECTION_STRING`: Connection string do Azure Storage (opcional)

## 12. Grupo Responsável

Projeto desenvolvido pelo grupo formado pelos alunos:

* Rafael Iornandes 
* Felipe Lessa de Moraes
* Fabio Crusco da Silva
* Fabio Alves de Lima

---
