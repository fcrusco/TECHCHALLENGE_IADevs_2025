"""
Script para visualizar e analisar resultados do algoritmo genético
"""
import sys
from pathlib import Path

# Adicionar o diretório src ao path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import accuracy_score, recall_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE

DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"


def carregar_dados():
    """Carrega e prepara os dados"""
    df = pd.read_csv(DATA_DIR / "diabetes.csv")

    cols_zero = ["Glucose", "BloodPressure", "SkinThickness", "Insulin", "BMI"]
    df[cols_zero] = df[cols_zero].replace(0, np.nan)
    df.fillna(df.median(), inplace=True)

    X = df.drop("Outcome", axis=1)
    y = df["Outcome"]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y
    )

    smote = SMOTE(random_state=42)
    X_train_res, y_train_res = smote.fit_resample(X_train, y_train)

    return X_train_res, y_train_res, X_test, y_test


def comparar_modelos():
    """Compara os modelos base e otimizado"""

    print("\n" + "=" * 70)
    print("  COMPARAÇÃO DE MODELOS - ALGORITMO GENÉTICO")
    print("=" * 70)

    # Carregar dados
    X_train_res, y_train_res, X_test, y_test = carregar_dados()

    # Carregar modelos
    try:
        lr = joblib.load(OUTPUT_DIR / "lr_model.pkl")
        rf_base = joblib.load(OUTPUT_DIR / "rf_model.pkl")
        rf_optimized = joblib.load(OUTPUT_DIR / "rf_optimized.pkl")
    except Exception as e:
        print(f"Erro ao carregar modelos: {e}")
        return

    modelos = {
        "Regressão Logística": lr,
        "Random Forest (Base)": rf_base,
        "Random Forest (Otimizado)": rf_optimized,
    }

    print("\nMÉTRICAS DE PERFORMANCE:\n")
    print("-" * 70)
    print(f"{'Modelo':<30} {'Accuracy':<12} {'Recall':<12} {'F1-Score':<12}")
    print("-" * 70)

    resultados = {}

    for nome, modelo in modelos.items():
        y_pred = modelo.predict(X_test)

        acc = accuracy_score(y_test, y_pred)
        rec = recall_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)

        resultados[nome] = {
            "accuracy": acc,
            "recall": rec,
            "f1": f1,
        }

        print(f"{nome:<30} {acc:<12.4f} {rec:<12.4f} {f1:<12.4f}")

    print("-" * 70)

    # Calcular melhorias
    if "Random Forest (Base)" in resultados and "Random Forest (Otimizado)" in resultados:
        base = resultados["Random Forest (Base)"]
        opt = resultados["Random Forest (Otimizado)"]

        print("\nMELHORIAS COM ALGORITMO GENÉTICO:\n")
        print(
            f"Accuracy:  {base['accuracy']:.4f} -> {opt['accuracy']:.4f} ({(opt['accuracy']-base['accuracy'])*100:+.2f}%)"
        )
        print(
            f"Recall:    {base['recall']:.4f} -> {opt['recall']:.4f} ({(opt['recall']-base['recall'])*100:+.2f}%)"
        )
        print(
            f"F1-Score:  {base['f1']:.4f} -> {opt['f1']:.4f} ({(opt['f1']-base['f1'])*100:+.2f}%)"
        )

    # Mostrar parâmetros do modelo otimizado
    print("\n" + "=" * 70)
    print("  PARÂMETROS DO MODELO OTIMIZADO")
    print("=" * 70)

    print("\nParâmetros encontrados pelo algoritmo genético:")
    print(f"   n_estimators: {rf_optimized.n_estimators}")
    print(f"   max_depth: {rf_optimized.max_depth}")
    print(f"   min_samples_split: {rf_optimized.min_samples_split}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    comparar_modelos()
