import pandas as pd
import numpy as np
import joblib
import traceback
from utils import gerar_explicacao_llm
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"

#   CARREGAR MODELOS + DATASET

try:
    df = pd.read_csv(DATA_DIR / "diabetes.csv")

    OUTPUT_DIR.mkdir(exist_ok=True)

    lr = joblib.load(OUTPUT_DIR / "lr_model.pkl")
    rf = joblib.load(OUTPUT_DIR / "rf_model.pkl")
    scaler = joblib.load(OUTPUT_DIR / "scaler.pkl")
except Exception as e:
    print("Erro ao carregar arquivos do modelo:")
    print(e)
    print(traceback.format_exc())
    exit()

#  FUNCAO INSERIR DADOS DO PACIENTE

def inserir_dados_paciente():
    print("\n=== Avaliação de Risco de Diabetes ===")

    try:
        Pregnancies = int(input("Número de gestações: "))
        Glucose = float(input("Glicose (mg/dL): "))
        BloodPressure = float(input("Pressão arterial (mmHg): "))
        SkinThickness = float(input("Espessura da pele (mm): "))
        Insulin = float(input("Insulina (µU/mL): "))
        BMI = float(input("IMC (BMI): "))
        DiabetesPedigreeFunction = float(input("Função de pedigree diabético: "))
        Age = int(input("Idade: "))

    except ValueError:
        print("\n Entrada invalida, digite apenas numeros.")
        return None

    paciente = pd.DataFrame({
        'Pregnancies':[Pregnancies],
        'Glucose':[Glucose],
        'BloodPressure':[BloodPressure],
        'SkinThickness':[SkinThickness],
        'Insulin':[Insulin],
        'BMI':[BMI],
        'DiabetesPedigreeFunction':[DiabetesPedigreeFunction],
        'Age':[Age]
    })

    # Substitui valores impossíveis
    cols_zero = ['Glucose','BloodPressure','SkinThickness','Insulin','BMI']
    paciente[cols_zero] = paciente[cols_zero].replace(0, np.nan)

    # Preenche com medianas do dataset
    paciente.fillna(df.median(), inplace=True)

    # Escalonamento
    paciente_scaled = scaler.transform(paciente)

    return paciente, paciente_scaled


# ================================
#     EXECUÇÃO PRINCIPAL
# ================================
paciente_raw, paciente_scaled = inserir_dados_paciente()

if paciente_scaled is None:
    exit()

modelos = {
    'Regressão Logística': lr,
    'Random Forest': rf
}

print("\n==============================")
print("      RESULTADOS")
print("==============================")

for nome, modelo in modelos.items():
    pred = modelo.predict(paciente_scaled)
    proba = modelo.predict_proba(paciente_scaled)

    print(f"\n {nome}")
    print("------------------------------")

    pred_texto = "Positivo para risco de diabetes" if pred[0] == 1 else "Negativo para risco de diabetes"
    print("Predição:", pred_texto)

    classes = ['Não Diabetes', 'Diabetes']
    for i, p in enumerate(proba[0]):
        print(f"{classes[i]}: {p*100:.2f}%")

# Usar o último modelo (Random Forest) para LLM
pred = rf.predict(paciente_scaled)
proba = rf.predict_proba(paciente_scaled)
pred_texto = "Positivo para risco de diabetes" if pred[0] == 1 else "Negativo para risco de diabetes"
classes = ['Não Diabetes', 'Diabetes']

# -------- LLM EXPLICA RESULTADO --------
try:
    explicacao = gerar_explicacao_llm(
        predicao=pred_texto,
        probabilidades={classes[i]: float(proba[0][i]) for i in range(len(classes))},
        paciente_info=paciente_raw.to_dict(orient="records")[0],
        metricas_modelo="Avaliação baseada no modelo treinado."
    )

    print("\n Interpretação da i.a:")
    print("-------------------------------------")
    print(explicacao)

except Exception as e:
    print("\n Não foi possível gerar explicação da IA.")
    print(e)
