import pandas as pd
import numpy as np
import joblib

# Carregar dataset original (para medianas)
df = pd.read_csv('C:/Users/Rafael/Desktop/FIAP/TechChallenge/data/diabetes.csv')

# Carregar modelos e scaler salvos
lr = joblib.load('C:/Users/Rafael/Desktop/FIAP/TechChallenge/outputs/lr_model.pkl')
rf = joblib.load('C:/Users/Rafael/Desktop/FIAP/TechChallenge/outputs/rf_model.pkl')
scaler = joblib.load('C:/Users/Rafael/Desktop/FIAP/TechChallenge/outputs/scaler.pkl')

# Função para inserir dados do paciente
def inserir_dados_paciente():
    print("Insira os dados do paciente:")
    Pregnancies = int(input("Número de gestações: "))
    Glucose = float(input("Glicose (mg/dL): "))
    BloodPressure = float(input("Pressão arterial (mmHg): "))
    SkinThickness = float(input("Espessura da pele (mm): "))
    Insulin = float(input("Insulina (µU/mL): "))
    BMI = float(input("IMC (BMI): "))
    DiabetesPedigreeFunction = float(input("Função de pedigree diabético: "))
    Age = int(input("Idade: "))
    
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
    
    # Tratar zeros e imputar mediana
    cols_zero = ['Glucose','BloodPressure','SkinThickness','Insulin','BMI']
    paciente[cols_zero] = paciente[cols_zero].replace(0, np.nan)
    paciente.fillna(df.median(), inplace=True)
    
    # Escalonar
    paciente_scaled = scaler.transform(paciente)
    
    return paciente_scaled

# Inserir paciente / chamando a funcao
novo_paciente_scaled = inserir_dados_paciente()

# Predições
modelos = {'Regressao Logistica': lr, 'Random Forest': rf}

for nome, modelo in modelos.items():
    resultado = modelo.predict(novo_paciente_scaled)
    proba = modelo.predict_proba(novo_paciente_scaled)
    
    print(f"\n===== {nome} =====")
    print("Predição:", "Diabetes" if resultado[0]==1 else "Não Diabetes")
    
    # Exibir probabilidades de forma legível
    classes = ['Não Diabetes', 'Diabetes']
    proba_percent = [f"{classes[i]}: {p*100:.2f}%" for i, p in enumerate(proba[0])]
    print("Probabilidades:")
    for p in proba_percent:
        print(p)