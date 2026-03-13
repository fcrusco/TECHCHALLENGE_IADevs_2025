import os
import logging
from pathlib import Path
import pathlib
import random
import numpy as np
import pandas as pd
import joblib
import time
import sys

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, recall_score, f1_score
from imblearn.over_sampling import SMOTE
from utils import medir_tempo

# CONFIGURAÇÃO DE LOGGING

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),      # Azure / Docker
        logging.FileHandler("pipeline.log")     # Local
    ]
)

logger = logging.getLogger("treinamento")
logger.info("===== INICIO DA EXECUCAO =====")

# FUNÇÃO FITNESS

def fitness(model, X, y):
    try:
        scores = cross_val_score(model, X, y, cv=3, scoring="f1")
        logger.info(f"Fitness calculado: {scores.mean():.4f}")
        return scores.mean()
    except Exception as e:
        logger.error(f"Erro ao calcular fitness: {e}")
        return 0


#  CARREGAMENTO E PREPARAÇÃO

logger.info("Carregando dataset...")

try:
    df = pd.read_csv(DATA_DIR / "diabetes.csv")
except Exception as e:
    logger.exception("Erro ao carregar dataset")
    raise e

logger.info(f"Dataset carregado com {df.shape[0]} linhas e {df.shape[1]} colunas.")

cols_zero = ['Glucose','BloodPressure','SkinThickness','Insulin','BMI']
df[cols_zero] = df[cols_zero].replace(0, np.nan)
df.fillna(df.median(), inplace=True)


#  FUNÇÃO PROCESSAMENTO EM LOTES

@medir_tempo("treinamento_random_forest")
def processar_em_lotes(dataset, lote_inicial=150):
    """
    Processa o dataset em lotes simulando carga variável.
    """

    lote = lote_inicial
    dados_processados = []

    logger.info("Iniciando processamento em lotes...")

    for inicio in range(0, len(dataset), lote):
        fim = min(inicio + lote, len(dataset))
        lote_df = dataset.iloc[inicio:fim]

        logger.info(f"Processando lote {inicio//lote + 1} -> linhas {inicio} a {fim}")

        # simula maior carga — aumentando lote dinamicamente
        if len(lote_df) > 120:
            lote += 50
            logger.info(f"Carga alta detectada — aumentando lote para {lote}")
        else:
            lote = max(100, lote - 20)
            logger.info(f"Carga baixa — reduzindo lote para {lote}")

        dados_processados.append(lote_df)

    logger.info("Processamento em lotes finalizado.")
    return pd.concat(dados_processados, axis=0)

df = processar_em_lotes(df)


#  CONTINUA PREPARAÇÃO NORMAL

X = df.drop("Outcome", axis=1)
y = df["Outcome"]

logger.info("Normalizando variáveis...")
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

logger.info("Separando treino e teste...")
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42, stratify=y
)

logger.info("Aplicando SMOTE (balanceamento)...")
smote = SMOTE(random_state=42)
X_train_res, y_train_res = smote.fit_resample(X_train, y_train)

logger.info("Dados preparados com sucesso.")


# TREINAMENTO MODELOS 

logger.info("Treinando modelos base...")

lr_base = LogisticRegression(max_iter=500, random_state=42)
rf_base = RandomForestClassifier(n_estimators=100, random_state=42)

lr_base.fit(X_train_res, y_train_res)
rf_base.fit(X_train_res, y_train_res)

y_pred_lr = lr_base.predict(X_test)
y_pred_rf = rf_base.predict(X_test)

logger.info(
    f"BASE LR -> acc={accuracy_score(y_test,y_pred_lr):.3f} "
    f"recall={recall_score(y_test,y_pred_lr):.3f} "
    f"f1={f1_score(y_test,y_pred_lr):.3f}"
)

logger.info(
    f"BASE RF -> acc={accuracy_score(y_test,y_pred_rf):.3f} "
    f"recall={recall_score(y_test,y_pred_rf):.3f} "
    f"f1={f1_score(y_test,y_pred_rf):.3f}"
)

logger.info({
    "evento": "metricas_finais",
    "modelo": "RandomForest_Otimizado",
    "accuracy": accuracy_score,
    "recall": recall_score,
    "f1": f1_score
})


# ALGORITMO GENÉTICO

def gerar_individuo():
    return {
        "n_estimators": random.randint(50, 200),
        "max_depth": random.choice([None, 4, 6, 8, 10]),
        "min_samples_split": random.randint(2, 10)
    }

def mutacao(ind):
    logger.info(f"Mutacao aplicada no individuo: {ind}")
    if random.random() < 0.5:
        ind["n_estimators"] = random.randint(50, 200)
    else:
        ind["min_samples_split"] = random.randint(2, 10)
    return ind

@medir_tempo("treinamento_random_forest")
def crossover(pai, mae):
    filho = {}
    for k in pai:
        filho[k] = random.choice([pai[k], mae[k]])
    logger.info(f"Crossover gerou filho: {filho}")
    return filho


logger.info("Iniciando otimizacao genetica...")

POP = 5
GERACOES = 3

populacao = [gerar_individuo() for _ in range(POP)]

inicio = time.time()

for g in range(GERACOES):
    logger.info(f"--- Geracao {g+1}/{GERACOES} ---")

    avaliacoes = []

    for individuo in populacao:
        logger.info(f"Avaliando individuo: {individuo}")

        modelo = RandomForestClassifier(
            n_estimators=individuo["n_estimators"],
            max_depth=individuo["max_depth"],
            min_samples_split=individuo["min_samples_split"],
            random_state=42
        )

        score = fitness(modelo, X_train_res, y_train_res)
        avaliacoes.append((score, individuo))

    avaliacoes.sort(reverse=True, key=lambda x: x[0])
    melhores = avaliacoes[:3]

    logger.info(f"Melhor indivíduo da geracao: {melhores[0]}")

    nova_pop = [i[1] for i in melhores]

    while len(nova_pop) < POP:
        pai, mae = random.sample(melhores, 2)
        filho = crossover(pai[1], mae[1])
        filho = mutacao(filho)
        nova_pop.append(filho)

    populacao = nova_pop

fim = time.time()
logger.info(f"Tempo total de execucao do GA: {(fim - inicio):.2f} segundos")


# TREINO COM MELHOR MODELO

best_params = melhores[0][1]
logger.info(f"Melhores parametros encontrados: {best_params}")

rf_otimizado = RandomForestClassifier(**best_params, random_state=42)

rf_otimizado.fit(X_train_res, y_train_res)
y_pred_rf_opt = rf_otimizado.predict(X_test)

logger.info(
    f"OTIMIZADO RF -> acc={accuracy_score(y_test,y_pred_rf_opt):.3f} "
    f"recall={recall_score(y_test,y_pred_rf_opt):.3f} "
    f"f1={f1_score(y_test,y_pred_rf_opt):.3f}"
)


# SALVAR MODELOS

os.makedirs(OUTPUT_DIR, exist_ok=True)

joblib.dump(lr_base, OUTPUT_DIR /"lr_model.pkl")
joblib.dump(rf_base, OUTPUT_DIR / "rf_model.pkl")
joblib.dump(rf_otimizado, OUTPUT_DIR / "rf_optimized.pkl")
joblib.dump(scaler, OUTPUT_DIR / "scaler.pkl")

logger.info("Modelos salvos com sucesso!")
logger.info("===== FIM DA EXECUCAO =====")