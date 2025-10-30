import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import os

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from imblearn.over_sampling import SMOTE  # Para lidar com desbalanceamento

df = pd.read_csv('C:/Users/Rafael/Desktop/FIAP/TechChallenge/data/diabetes.csv')

############    inspecionando os dados    ############
print(df.head())
print(df.describe())

sns.countplot(x='Outcome', data=df)
plt.title("Distribuição de Outcome")
plt.show()

# -----------------------------
#    Mapa de Correlação
# -----------------------------
plt.figure(figsize=(10,8))
sns.heatmap(df.corr(), annot=True, cmap='coolwarm')
plt.title("Mapa de Correlação")
plt.show()

############    Normalizando os dados    ############
cols_zero = ['Glucose','BloodPressure','SkinThickness','Insulin','BMI']
df[cols_zero] = df[cols_zero].replace(0, np.nan)
print(df.isnull().sum())
df.fillna(df.median(), inplace=True)

X = df.drop('Outcome', axis=1)
y = df['Outcome']

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# -----------------------------
#    Dividindo treino e teste
# -----------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42, stratify=y
)

# -----------------------------
#  lidando com o desbalanceamento
# -----------------------------
smote = SMOTE(random_state=42)
X_train_res, y_train_res = smote.fit_resample(X_train, y_train)

# -----------------------------
#   Parte de treinamento
# -----------------------------
lr = LogisticRegression(random_state=42)
lr.fit(X_train_res, y_train_res)
y_pred_lr = lr.predict(X_test)

rf = RandomForestClassifier(random_state=42, n_estimators=100)
rf.fit(X_train_res, y_train_res)
y_pred_rf = rf.predict(X_test)


############   Salvando os modelos treinados    ############
os.makedirs('outputs', exist_ok=True)

joblib.dump(lr, 'C:/Users/Rafael/Desktop/FIAP/TechChallenge/outputs/lr_model.pkl')
joblib.dump(rf, 'C:/Users/Rafael/Desktop/FIAP/TechChallenge/outputs/rf_model.pkl')
joblib.dump(scaler, 'C:/Users/Rafael/Desktop/FIAP/TechChallenge/outputs/scaler.pkl')

# -----------------------------
#  Avaliação
# -----------------------------
def avaliar_modelo(y_true, y_pred, modelo_name):
    print(f"Resultados para {modelo_name}:")
    print(classification_report(y_true, y_pred))
    cm = confusion_matrix(y_true, y_pred)
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
    plt.title(f"Matriz de Confusão - {modelo_name}")
    plt.xlabel("Predito")
    plt.ylabel("Real")
    plt.show()

avaliar_modelo(y_test, y_pred_lr, "Regressão Logística")
avaliar_modelo(y_test, y_pred_rf, "Random Forest")