# API de Avaliação de Diabetes

API REST desenvolvida com FastAPI para expor funcionalidades de treinamento e avaliação de modelos de machine learning para predição de diabetes.

## 📋 Características

- ✅ Documentação automática com Swagger UI
- ✅ Validação de dados com Pydantic
- ✅ Endpoints bem documentados
- ✅ Suporte a CORS
- ✅ Tratamento de erros robusto
- ✅ Integração com Azure Storage (opcional)

## 🚀 Como Usar

### Instalação

Certifique-se de que todas as dependências estão instaladas:

```bash
pip install -r requirements.txt
```

### Configuração

A API utiliza variáveis de ambiente. Crie um arquivo `.env` na raiz do projeto com:

```env
AZURE_STORAGE_CONNECTION_STRING=sua_connection_string_aqui
OPENAI_API_KEY=sua_chave_openai_aqui
```

**Nota**: O Azure Storage é opcional. Se não configurado, a API usará apenas modelos locais.

### Executar a API

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

## 📚 Endpoints

### 1. Health Check

**GET** `/health`

Verifica se a API está funcionando.

**Resposta**:
```json
{
  "status": "online",
  "versao": "1.0.0"
}
```

### 2. Treinamento

**POST** `/treinamento`

Treina os modelos de machine learning (Logistic Regression e Random Forest).

**Nota**: Este processo pode levar alguns minutos.

**Resposta**:
```json
{
  "status": "sucesso",
  "mensagem": "Modelos treinados com sucesso",
  "metricas_base_lr": {
    "accuracy": 0.75,
    "recall": 0.68,
    "f1": 0.71
  },
  "metricas_base_rf": {
    "accuracy": 0.78,
    "recall": 0.72,
    "f1": 0.74
  },
  "metricas_otimizado_rf": {
    "accuracy": 0.80,
    "recall": 0.75,
    "f1": 0.77
  },
  "melhores_parametros": {
    "n_estimators": 150,
    "max_depth": 8,
    "min_samples_split": 5
  },
  "tempo_execucao": 45.23
}
```

### 3. Avaliação

**POST** `/avaliacao`

Avalia um paciente e retorna predições de risco de diabetes.

**Parâmetros**:
- `paciente` (body): Dados do paciente
- `incluir_explicacao` (query, opcional): Se True, gera explicação com IA (padrão: True)

**Exemplo de requisição**:
```json
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

**Resposta**:
```json
{
  "paciente": {
    "Pregnancies": 1,
    "Glucose": 85,
    "BloodPressure": 66,
    "SkinThickness": 29,
    "Insulin": 0,
    "BMI": 26.6,
    "DiabetesPedigreeFunction": 0.351,
    "Age": 31
  },
  "resultados": [
    {
      "modelo": "Regressão Logística",
      "predicao": "Negativo para risco de diabetes",
      "probabilidade_nao_diabetes": 0.85,
      "probabilidade_diabetes": 0.15,
      "predicao_binaria": 0
    },
    {
      "modelo": "Random Forest",
      "predicao": "Negativo para risco de diabetes",
      "probabilidade_nao_diabetes": 0.82,
      "probabilidade_diabetes": 0.18,
      "predicao_binaria": 0
    }
  ],
  "explicacao_ia": "Análise clínica baseada nos dados do paciente..."
}
```

## 🧪 Testando a API

### Usando cURL

**Health Check**:
```bash
curl http://localhost:8000/health
```

**Treinamento**:
```bash
curl -X POST http://localhost:8000/treinamento
```

**Avaliação**:
```bash
curl -X POST http://localhost:8000/avaliacao \
  -H "Content-Type: application/json" \
  -d '{
    "Pregnancies": 1,
    "Glucose": 85,
    "BloodPressure": 66,
    "SkinThickness": 29,
    "Insulin": 0,
    "BMI": 26.6,
    "DiabetesPedigreeFunction": 0.351,
    "Age": 31
  }'
```

### Usando Python

```python
import requests

# Health check
response = requests.get("http://localhost:8000/health")
print(response.json())

# Treinamento
response = requests.post("http://localhost:8000/treinamento")
print(response.json())

# Avaliação
paciente = {
    "Pregnancies": 1,
    "Glucose": 85,
    "BloodPressure": 66,
    "SkinThickness": 29,
    "Insulin": 0,
    "BMI": 26.6,
    "DiabetesPedigreeFunction": 0.351,
    "Age": 31
}
response = requests.post("http://localhost:8000/avaliacao", json=paciente)
print(response.json())
```

## 📖 Documentação Interativa

Acesse a documentação interativa do Swagger em:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Lá você pode testar todos os endpoints diretamente no navegador!

## ⚠️ Observações Importantes

1. **Treinamento**: Execute o endpoint `/treinamento` antes de usar `/avaliacao` pela primeira vez
2. **Modelos**: Os modelos são salvos em `outputs/` e podem ser enviados para Azure Storage
3. **LLM**: A explicação por IA requer `OPENAI_API_KEY` configurada
4. **Azure Storage**: Opcional, mas recomendado para produção

## 🔧 Estrutura da API

```
api/
├── __init__.py          # Package init
├── main.py              # Aplicação FastAPI principal
├── schemas.py           # Modelos Pydantic para validação
├── services.py          # Lógica de negócio
└── README.md           # Esta documentação
```

## 📝 Notas de Desenvolvimento

- A API não modifica o código existente em `src/`
- A lógica foi extraída e adaptada para uso via API
- Todos os endpoints são assíncronos para melhor performance
- Validação automática de dados de entrada
- Tratamento robusto de erros
