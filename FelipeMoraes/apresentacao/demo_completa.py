"""
Script de demonstração completa do sistema
Inclui dados de exemplo para facilitar a apresentação
"""
import sys
from pathlib import Path

# Adicionar o diretório src ao path para importar utils
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

import pandas as pd
import numpy as np
import joblib
from utils import gerar_explicacao_llm

DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"

# Carregar modelos
try:
    df = pd.read_csv(DATA_DIR / "diabetes.csv")
    OUTPUT_DIR.mkdir(exist_ok=True)

    lr = joblib.load(OUTPUT_DIR / "lr_model.pkl")
    rf = joblib.load(OUTPUT_DIR / "rf_model.pkl")
    rf_optimized = joblib.load(OUTPUT_DIR / "rf_optimized.pkl")
    scaler = joblib.load(OUTPUT_DIR / "scaler.pkl")

    print("Modelos carregados com sucesso!")
except Exception as e:
    print("Erro ao carregar modelos:")
    print(e)
    exit(1)

# Dados de exemplo para demonstração
PACIENTES_EXEMPLO = [
    {
        "nome": "Paciente de Alto Risco",
        "dados": {
            "Pregnancies": 6,
            "Glucose": 148,
            "BloodPressure": 72,
            "SkinThickness": 35,
            "Insulin": 0,
            "BMI": 33.6,
            "DiabetesPedigreeFunction": 0.627,
            "Age": 50,
        },
    },
    {
        "nome": "Paciente de Baixo Risco",
        "dados": {
            "Pregnancies": 1,
            "Glucose": 85,
            "BloodPressure": 66,
            "SkinThickness": 29,
            "Insulin": 0,
            "BMI": 26.6,
            "DiabetesPedigreeFunction": 0.351,
            "Age": 31,
        },
    },
]


def avaliar_paciente(paciente_dict, usar_otimizado=True):
    """Avalia um paciente usando os modelos"""

    paciente = pd.DataFrame([paciente_dict])

    # Tratamento de valores zero
    cols_zero = ["Glucose", "BloodPressure", "SkinThickness", "Insulin", "BMI"]
    paciente[cols_zero] = paciente[cols_zero].replace(0, np.nan)
    paciente.fillna(df.median(), inplace=True)

    # Normalização
    paciente_scaled = scaler.transform(paciente)

    # Modelos a usar
    modelos = {
        "Regressão Logística": lr,
        "Random Forest (Base)": rf,
    }

    if usar_otimizado:
        modelos["Random Forest (Otimizado)"] = rf_optimized

    print("\n" + "=" * 60)
    print("      RESULTADOS DA AVALIAÇÃO")
    print("=" * 60)

    for nome, modelo in modelos.items():
        pred = modelo.predict(paciente_scaled)[0]
        proba = modelo.predict_proba(paciente_scaled)[0]

        print(f"\n {nome}")
        print("-" * 60)
        pred_texto = (
            "POSITIVO para risco de diabetes"
            if pred == 1
            else "NEGATIVO para risco de diabetes"
        )
        print(f"Predição: {pred_texto}")
        print(f"Probabilidade Não Diabetes: {proba[0]*100:.2f}%")
        print(f"Probabilidade Diabetes: {proba[1]*100:.2f}%")

    # Usar o modelo otimizado para LLM
    modelo_principal = rf_optimized if usar_otimizado else rf
    pred_principal = modelo_principal.predict(paciente_scaled)[0]
    proba_principal = modelo_principal.predict_proba(paciente_scaled)[0]

    pred_texto = (
        "Positivo para risco de diabetes"
        if pred_principal == 1
        else "Negativo para risco de diabetes"
    )

    # Gerar explicação com LLM
    print("\n" + "=" * 60)
    print("      INTERPRETAÇÃO CLÍNICA (LLM)")
    print("=" * 60)

    try:
        explicacao = gerar_explicacao_llm(
            predicao=pred_texto,
            probabilidades={
                "Não Diabetes": float(proba_principal[0]),
                "Diabetes": float(proba_principal[1]),
            },
            paciente_info=paciente_dict,
            metricas_modelo="Modelo Random Forest otimizado via algoritmo genético.",
        )

        print("\nExplicação:")
        print("-" * 60)
        print(explicacao)

    except Exception as e:
        print(f"\nNão foi possível gerar explicação: {e}")


def main():
    """Função principal de demonstração"""

    print("\n" + "=" * 60)
    print("  SISTEMA DE PREDIÇÃO DE RISCO DE DIABETES")
    print("=" * 60)

    print("\nEscolha uma opção:")
    print("1. Usar paciente de exemplo (Alto Risco)")
    print("2. Usar paciente de exemplo (Baixo Risco)")
    print("3. Inserir dados manualmente")

    escolha = input("\nOpção (1/2/3): ").strip()

    if escolha == "1":
        paciente = PACIENTES_EXEMPLO[0]
        print(f"\nAvaliando: {paciente['nome']}")
        avaliar_paciente(paciente["dados"])

    elif escolha == "2":
        paciente = PACIENTES_EXEMPLO[1]
        print(f"\nAvaliando: {paciente['nome']}")
        avaliar_paciente(paciente["dados"])

    elif escolha == "3":
        print("\n=== Inserir Dados do Paciente ===")
        try:
            dados = {
                "Pregnancies": int(input("Número de gestações: ")),
                "Glucose": float(input("Glicose (mg/dL): ")),
                "BloodPressure": float(input("Pressão arterial (mmHg): ")),
                "SkinThickness": float(input("Espessura da pele (mm): ")),
                "Insulin": float(input("Insulina (µU/mL): ")),
                "BMI": float(input("IMC (BMI): ")),
                "DiabetesPedigreeFunction": float(
                    input("Função de pedigree diabético: ")
                ),
                "Age": int(input("Idade: ")),
            }
            avaliar_paciente(dados)
        except ValueError:
            print("\nEntrada inválida!")
    else:
        print("\nOpção inválida!")


if __name__ == "__main__":
    main()
