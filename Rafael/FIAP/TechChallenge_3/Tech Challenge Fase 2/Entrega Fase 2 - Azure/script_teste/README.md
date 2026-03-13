# Scripts de Teste da API de Diabetes

Esta pasta contém scripts de teste para validar o funcionamento da API de avaliação de diabetes.

## 📋 Scripts Disponíveis

### 1. `teste_01_paciente_sem_diabetes.py`
Testa um paciente com valores clínicos normais, esperando predição **negativa** para diabetes.

**Características do paciente:**
- Glicose: 85 mg/dL (normal)
- IMC: 26.6 (normal)
- Idade: 31 anos

### 2. `teste_02_paciente_com_diabetes.py`
Testa um paciente com valores indicativos de diabetes, esperando predição **positiva**.

**Características do paciente:**
- Glicose: 148 mg/dL (elevada)
- IMC: 33.6 (elevado)
- Idade: 50 anos

### 3. `teste_03_paciente_limitrofe.py`
Testa um paciente com valores intermediários (caso limítrofe), onde a predição pode variar.

**Características do paciente:**
- Glicose: 120 mg/dL (pré-diabetes)
- IMC: 28.5 (sobrepeso)
- Idade: 40 anos

### 4. `teste_04_paciente_idoso_sem_diabetes.py`
Testa um paciente idoso com valores normais, demonstrando que idade avançada não necessariamente indica diabetes.

**Características do paciente:**
- Idade: 65 anos
- Glicose: 95 mg/dL (normal)
- IMC: 24.5 (normal)

### 5. `teste_05_paciente_jovem_com_diabetes.py`
Testa um paciente jovem com valores indicativos de diabetes, demonstrando que idade jovem não impede o diagnóstico.

**Características do paciente:**
- Idade: 25 anos
- Glicose: 180 mg/dL (muito elevada)
- IMC: 35.0 (obesidade)

### 6. `teste_06_paciente_multiplos_casos.py`
Executa testes em lote com múltiplos pacientes, incluindo casos variados com e sem diabetes.

## 🚀 Como Usar

### Pré-requisitos

1. Certifique-se de que a API está rodando:
   ```bash
   cd api
   python main.py
   # ou
   uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. Instale as dependências necessárias:
   ```bash
   pip install requests
   ```

### Executando os Testes

#### Teste Individual
```bash
python script_teste/teste_01_paciente_sem_diabetes.py
python script_teste/teste_02_paciente_com_diabetes.py
python script_teste/teste_03_paciente_limitrofe.py
python script_teste/teste_04_paciente_idoso_sem_diabetes.py
python script_teste/teste_05_paciente_jovem_com_diabetes.py
```

#### Teste em Lote
```bash
python script_teste/teste_06_paciente_multiplos_casos.py
```

#### Executar Todos os Testes
```bash
# Windows PowerShell
Get-ChildItem script_teste\teste_*.py | ForEach-Object { python $_.FullName }

# Linux/Mac
for script in script_teste/teste_*.py; do python "$script"; done
```

## 📊 Estrutura dos Dados do Paciente

Todos os scripts utilizam o seguinte formato de dados:

```python
paciente = {
    "Pregnancies": int,           # Número de gestações (>= 0)
    "Glucose": float,             # Glicose em mg/dL (>= 0)
    "BloodPressure": float,       # Pressão arterial em mmHg (>= 0)
    "SkinThickness": float,       # Espessura da pele em mm (>= 0)
    "Insulin": float,             # Insulina em µU/mL (>= 0)
    "BMI": float,                 # IMC - Body Mass Index (>= 0)
    "DiabetesPedigreeFunction": float,  # Função de pedigree diabético (>= 0)
    "Age": int                    # Idade em anos (0-120)
}
```

## 🔍 O que os Testes Verificam

- ✅ Conectividade com a API
- ✅ Formato correto das respostas
- ✅ Predições dos modelos (Regressão Logística e Random Forest)
- ✅ Probabilidades de cada classe
- ✅ Explicações geradas por IA (quando habilitado)
- ✅ Consistência entre diferentes modelos
- ✅ Casos extremos (jovens com diabetes, idosos sem diabetes)

## ⚙️ Configuração

Por padrão, os scripts assumem que a API está rodando em `http://localhost:8000`.

Para alterar a URL da API, edite a variável `API_URL` no início de cada script:

```python
API_URL = "http://localhost:8000"  # Altere aqui se necessário
```

## 📝 Notas

- Os testes incluem explicações geradas por IA por padrão (exceto no teste em lote para melhor performance)
- Para desabilitar explicações IA, altere `incluir_explicacao=False` nos scripts
- Os valores dos pacientes são baseados em casos reais do dataset de diabetes
- Alguns casos podem apresentar predições diferentes entre os modelos, o que é esperado em casos limítrofes

## 🐛 Troubleshooting

### Erro de Conexão
```
❌ ERRO: Não foi possível conectar à API.
```
**Solução**: Certifique-se de que a API está rodando antes de executar os testes.

### Modelos Não Encontrados
```
❌ Erro: Modelos não encontrados
```
**Solução**: Execute o treinamento primeiro através do endpoint `/treinamento` ou via API:
```bash
curl -X POST http://localhost:8000/treinamento
```

### Erro de Validação
```
❌ Erro na requisição: 422
```
**Solução**: Verifique se os dados do paciente estão no formato correto e dentro dos limites permitidos.
