# Tech Challenge – Fase 2

## 1. Visão Geral

Este projeto foi desenvolvido como parte do **Tech Challenge – Fase 2**, com foco na otimização de modelos de Machine Learning aplicados ao diagnóstico médico, utilizando como base o trabalho desenvolvido durante a Fase 1 do curso, utilizando um dataset clínico de diabetes para avaliação de risco. A solução utiliza **algoritmos genéticos** para otimização de hiperparâmetros, **integração com LLMs** (OpenAI) para interpretação dos resultados.

---

## 2. Funcionalidades Principais do Projeto

* Treinamento de modelos de classificação (Regressão Logística e Random Forest);
* Otimização de hiperparâmetros via Algoritmos Genéticos;
* Avaliação de desempenho com métricas clínicas (Accuracy, Recall, F1-score);
* Geração de explicações clínicas em linguagem natural utilizando LLM;
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
├── data/
│   └── diabetes.csv            # Dataset utilizado para o projeto
│
│
├── infra/
│   └── main.tf                 # Infraestrutura como Código (Terraform)
│
├── startup.sh                  # Script de inicialização utilizado na nuvem (utilizamos Azure)
├── requirements.txt            # Dependências do projeto (bibliotecas do Python)
├── README.md                   # Documentação do projeto
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

### Treinamento e otimização dos modelos

```bash
python src/treinamento.py
```

### Avaliação de risco de diabetes

```bash
python src/avaliacaoDiabetica.py
```

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

Os logs são registrados no arquivo **pipeline.txt** e enviados para o **stdout** para monitoração em nuvem.


---

## 9. Tecnologias e softwares utilizados no desenvolvimento do projeto

* Python 3.13
* Scikit-learn
* Imbalanced-learn (SMOTE)
* Pandas / NumPy
* OpenAI API (LLM)
* Microsoft Azure App Service
* Terraform

---

## 10. Grupo Responsável

Projeto desenvolvido pelo grupo formado pelos alunos:

* Rafael Iornandes 
* Felipe Lessa de Moraes
* Fabio Crusco da Silva
* Fabio Alves de Lima

---
