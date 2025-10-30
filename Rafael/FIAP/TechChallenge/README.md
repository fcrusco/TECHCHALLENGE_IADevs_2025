📋 Descrição do Projeto

Este projeto tem como objetivo desenvolver um modelo de Machine Learning capaz de prever a probabilidade de um paciente ter diabetes com base em informações clínicas coletadas.
A solução foi desenvolvida como parte do Tech Challenge - FIAP (IA Devs 2025), e utiliza técnicas de pré-processamento, normalização, modelagem e avaliação de desempenho.

O modelo final é testado com novos dados de pacientes, permitindo prever o risco de diabetes e exibir as probabilidades calculadas pelos modelos.

🎯 Objetivos

Tratar e normalizar o dataset de diabetes.

Treinar e comparar modelos de Regressão Logística e Random Forest.

Avaliar os modelos utilizando métricas como precisão, recall, f1-score e matriz de confusão.

Testar o modelo com novos dados de pacientes inseridos manualmente.

📈 Tecnologias Utilizadas

Python 3.11

Pandas e NumPy → manipulação de dados

Scikit-learn → modelagem e métricas

Matplotlib e Seaborn → visualização

Joblib → salvar e carregar modelos

Jupyter Notebook / VSCode → ambiente de desenvolvimento

🧩 Dataset Utilizado

O dataset utilizado é o Pima Indians Diabetes Database, amplamente conhecido na comunidade de Machine Learning.
Ele contém informações médicas de pacientes, como níveis de glicose, pressão arterial, espessura da pele, insulina, IMC e idade.

Fonte: Kaggle - Pima Indians Diabetes Database

Principais Colunas:
Coluna	Descrição
Pregnancies	Número de gestações
Glucose	Concentração de glicose no plasma
BloodPressure	Pressão arterial diastólica
SkinThickness	Espessura da pele (tríceps)
Insulin	Nível de insulina sérica
BMI	Índice de Massa Corporal
DiabetesPedigreeFunction	Histórico familiar de diabetes
Age	Idade
Outcome	Resultado (1 = diabetes, 0 = não diabetes)
⚙️ Pré-Processamento dos Dados

Durante a análise inicial, observou-se que diversas colunas continham o valor “0”, o que não representa uma medição válida — por exemplo, pressão arterial zero não é um valor possível.

Portanto, o tratamento seguiu as seguintes etapas:

Substituição de zeros por valores nulos (NaN) nas colunas:

['Glucose', 'BloodPressure', 'SkinThickness', 'Insulin', 'BMI']


Preenchimento dos valores nulos com a mediana de cada coluna (evitando distorções causadas por outliers).

Normalização dos dados utilizando o StandardScaler, que transforma todas as colunas para média 0 e desvio padrão 1, garantindo melhor desempenho dos algoritmos.

🤖 Modelos Treinados

Foram utilizados dois algoritmos principais de classificação:

Modelo	Descrição
Regressão Logística	Modelo estatístico linear ideal para classificação binária.
Random Forest	Conjunto de múltiplas árvores de decisão, melhorando a precisão e reduzindo overfitting.

Após o treinamento, os modelos e o scaler foram salvos em arquivos .pkl com joblib, permitindo reutilização sem necessidade de re-treinar.

📊 Avaliação dos Modelos

Para avaliar o desempenho, foi criada uma função chamada avaliar_modelo(), que gera:

Classification Report (Precision, Recall, F1-score)

Matriz de Confusão com visualização via Seaborn

Essas métricas ajudam a entender o equilíbrio entre acertos e erros dos modelos nas classes “diabetes” e “não diabetes”.

🧪 Teste com Novos Pacientes

Após o treinamento, o projeto permite inserir dados de novos pacientes manualmente no console, simulando uma aplicação real.

O sistema:

Recebe os dados clínicos informados pelo usuário.

Aplica o mesmo tratamento (substituição, mediana e normalização).

Passa os dados aos modelos treinados.

Exibe o resultado e as probabilidades de cada classe.

Exemplo de saída:

===== Random Forest =====
Predição: Diabetes
Probabilidades:
Não Diabetes: 32.45%
Diabetes: 67.55%

