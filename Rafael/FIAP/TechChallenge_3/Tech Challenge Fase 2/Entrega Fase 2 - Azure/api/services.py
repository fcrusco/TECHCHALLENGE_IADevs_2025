"""
Serviços de negócio extraídos dos scripts originais.
"""
import os
import sys
import logging
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from typing import Dict, Tuple, Optional
import traceback

# Adiciona o diretório src ao path para importar utils
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from utils import medir_tempo, gerar_explicacao_llm
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, recall_score, f1_score
from imblearn.over_sampling import SMOTE
from azure.storage.blob import BlobServiceClient

# Configuração de diretórios
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"

# Configuração de logging
logger = logging.getLogger("api.services")


def get_azure_client():
    """Obtém cliente do Azure Storage."""
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string:
        return None
    
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service.get_container_client("modelos")
    
    try:
        container_client.create_container()
    except:
        pass
    
    return container_client


def upload_model(local_path: Path, blob_name: str):
    """Faz upload do modelo para Azure Storage."""
    container_client = get_azure_client()
    if not container_client:
        logger.warning("Azure Storage não configurado, pulando upload")
        return
    
    try:
        with open(local_path, "rb") as f:
            container_client.upload_blob(name=blob_name, data=f, overwrite=True)
        logger.info(f"Modelo {blob_name} enviado para Azure Storage")
    except Exception as e:
        logger.error(f"Erro ao fazer upload do modelo {blob_name}: {e}")


def download_model(blob_name: str, local_path: Path):
    """Baixa modelo do Azure Storage."""
    container_client = get_azure_client()
    if not container_client:
        logger.warning("Azure Storage não configurado, usando modelo local")
        return False
    
    try:
        with open(local_path, "wb") as f:
            f.write(container_client.download_blob(blob_name).readall())
        logger.info(f"Modelo {blob_name} baixado do Azure Storage")
        return True
    except Exception as e:
        logger.warning(f"Erro ao baixar modelo {blob_name}: {e}")
        return False


def carregar_modelos() -> Tuple[object, object, object]:
    """
    Carrega modelos treinados.
    Retorna: (lr_model, rf_model, scaler)
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Tenta baixar do Azure, se não conseguir usa local
    lr_path = OUTPUT_DIR / "lr_model.pkl"
    rf_path = OUTPUT_DIR / "rf_model.pkl"
    scaler_path = OUTPUT_DIR / "scaler.pkl"
    
    download_model("lr_model.pkl", lr_path)
    download_model("rf_model.pkl", rf_path)
    download_model("scaler.pkl", scaler_path)
    
    if not all([lr_path.exists(), rf_path.exists(), scaler_path.exists()]):
        raise FileNotFoundError("Modelos não encontrados. Execute o treinamento primeiro.")
    
    lr = joblib.load(lr_path)
    rf = joblib.load(rf_path)
    scaler = joblib.load(scaler_path)
    
    return lr, rf, scaler


def preparar_dados_paciente(paciente_data: Dict, df_referencia: pd.DataFrame) -> Tuple[pd.DataFrame, np.ndarray]:
    """
    Prepara dados do paciente para predição.
    Retorna: (paciente_raw, paciente_scaled)
    """
    paciente = pd.DataFrame([paciente_data])
    
    # Substitui valores impossíveis
    cols_zero = ['Glucose', 'BloodPressure', 'SkinThickness', 'Insulin', 'BMI']
    paciente[cols_zero] = paciente[cols_zero].replace(0, np.nan)
    
    # Preenche com medianas do dataset
    paciente.fillna(df_referencia.median(), inplace=True)
    
    # Carrega scaler e aplica
    scaler_path = OUTPUT_DIR / "scaler.pkl"
    if not scaler_path.exists():
        download_model("scaler.pkl", scaler_path)
    
    scaler = joblib.load(scaler_path)
    paciente_scaled = scaler.transform(paciente)
    
    return paciente, paciente_scaled


def avaliar_paciente(paciente_data: Dict, incluir_explicacao: bool = True) -> Dict:
    """
    Avalia um paciente usando os modelos treinados.
    """
    try:
        # Carrega dataset de referência
        df = pd.read_csv(DATA_DIR / "diabetes.csv")
        
        # Carrega modelos
        lr, rf, _ = carregar_modelos()
        
        # Prepara dados do paciente
        paciente_raw, paciente_scaled = preparar_dados_paciente(paciente_data, df)
        
        # Faz predições
        modelos = {
            'Regressão Logística': lr,
            'Random Forest': rf
        }
        
        resultados = []
        
        for nome, modelo in modelos.items():
            pred = modelo.predict(paciente_scaled)
            proba = modelo.predict_proba(paciente_scaled)
            
            pred_texto = "Positivo para risco de diabetes" if pred[0] == 1 else "Negativo para risco de diabetes"
            
            resultados.append({
                "modelo": nome,
                "predicao": pred_texto,
                "probabilidade_nao_diabetes": float(proba[0][0]),
                "probabilidade_diabetes": float(proba[0][1]),
                "predicao_binaria": int(pred[0])
            })
        
        # Gera explicação com LLM (usando Random Forest)
        explicacao_ia = None
        if incluir_explicacao:
            try:
                pred_rf = rf.predict(paciente_scaled)
                proba_rf = rf.predict_proba(paciente_scaled)
                pred_texto_rf = "Positivo para risco de diabetes" if pred_rf[0] == 1 else "Negativo para risco de diabetes"
                
                classes = ['Não Diabetes', 'Diabetes']
                probabilidades = {classes[i]: float(proba_rf[0][i]) for i in range(len(classes))}
                
                explicacao_ia = gerar_explicacao_llm(
                    predicao=pred_texto_rf,
                    probabilidades=probabilidades,
                    paciente_info=paciente_raw.to_dict(orient="records")[0],
                    metricas_modelo="Avaliação baseada no modelo treinado."
                )
            except Exception as e:
                logger.warning(f"Erro ao gerar explicação LLM: {e}")
        
        return {
            "paciente": paciente_raw.to_dict(orient="records")[0],
            "resultados": resultados,
            "explicacao_ia": explicacao_ia
        }
        
    except Exception as e:
        logger.error(f"Erro ao avaliar paciente: {e}")
        logger.error(traceback.format_exc())
        raise


def treinar_modelos() -> Dict:
    """
    Treina os modelos de machine learning.
    Retorna métricas e informações do treinamento.
    """
    import time
    import random
    
    logger.info("===== INICIO DO TREINAMENTO =====")
    inicio_total = time.time()
    
    try:
        # Carregamento e preparação
        logger.info("Carregando dataset...")
        df = pd.read_csv(DATA_DIR / "diabetes.csv")
        logger.info(f"Dataset carregado com {df.shape[0]} linhas e {df.shape[1]} colunas.")
        
        # Tratamento de valores zero
        cols_zero = ['Glucose', 'BloodPressure', 'SkinThickness', 'Insulin', 'BMI']
        df[cols_zero] = df[cols_zero].replace(0, np.nan)
        df.fillna(df.median(), inplace=True)
        
        # Processamento em lotes
        @medir_tempo("treinamento_random_forest")
        def processar_em_lotes(dataset, lote_inicial=150):
            lote = lote_inicial
            dados_processados = []
            
            for inicio in range(0, len(dataset), lote):
                fim = min(inicio + lote, len(dataset))
                lote_df = dataset.iloc[inicio:fim]
                
                if len(lote_df) > 120:
                    lote += 50
                else:
                    lote = max(100, lote - 20)
                
                dados_processados.append(lote_df)
            
            return pd.concat(dados_processados, axis=0)
        
        df = processar_em_lotes(df)
        
        # Preparação normal
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
        
        # Treinamento modelos base
        logger.info("Treinando modelos base...")
        lr_base = LogisticRegression(max_iter=500, random_state=42)
        rf_base = RandomForestClassifier(n_estimators=100, random_state=42)
        
        lr_base.fit(X_train_res, y_train_res)
        rf_base.fit(X_train_res, y_train_res)
        
        y_pred_lr = lr_base.predict(X_test)
        y_pred_rf = rf_base.predict(X_test)
        
        metricas_lr = {
            "accuracy": float(accuracy_score(y_test, y_pred_lr)),
            "recall": float(recall_score(y_test, y_pred_lr)),
            "f1": float(f1_score(y_test, y_pred_lr))
        }
        
        metricas_rf = {
            "accuracy": float(accuracy_score(y_test, y_pred_rf)),
            "recall": float(recall_score(y_test, y_pred_rf)),
            "f1": float(f1_score(y_test, y_pred_rf))
        }
        
        logger.info(f"BASE LR -> {metricas_lr}")
        logger.info(f"BASE RF -> {metricas_rf}")
        
        # Algoritmo Genético
        def fitness(model, X, y):
            try:
                scores = cross_val_score(model, X, y, cv=3, scoring="f1")
                return scores.mean()
            except Exception as e:
                logger.error(f"Erro ao calcular fitness: {e}")
                return 0
        
        def gerar_individuo():
            return {
                "n_estimators": random.randint(50, 200),
                "max_depth": random.choice([None, 4, 6, 8, 10]),
                "min_samples_split": random.randint(2, 10)
            }
        
        def mutacao(ind):
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
            return filho
        
        logger.info("Iniciando otimização genética...")
        POP = 5
        GERACOES = 3
        
        populacao = [gerar_individuo() for _ in range(POP)]
        inicio_ga = time.time()
        
        for g in range(GERACOES):
            logger.info(f"--- Geração {g+1}/{GERACOES} ---")
            
            avaliacoes = []
            for individuo in populacao:
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
            
            nova_pop = [i[1] for i in melhores]
            
            while len(nova_pop) < POP:
                pai, mae = random.sample(melhores, 2)
                filho = crossover(pai[1], mae[1])
                filho = mutacao(filho)
                nova_pop.append(filho)
            
            populacao = nova_pop
        
        fim_ga = time.time()
        logger.info(f"Tempo total de execução do GA: {(fim_ga - inicio_ga):.2f} segundos")
        
        # Treino com melhor modelo
        best_params = melhores[0][1]
        logger.info(f"Melhores parâmetros encontrados: {best_params}")
        
        rf_otimizado = RandomForestClassifier(**best_params, random_state=42)
        rf_otimizado.fit(X_train_res, y_train_res)
        y_pred_rf_opt = rf_otimizado.predict(X_test)
        
        metricas_rf_opt = {
            "accuracy": float(accuracy_score(y_test, y_pred_rf_opt)),
            "recall": float(recall_score(y_test, y_pred_rf_opt)),
            "f1": float(f1_score(y_test, y_pred_rf_opt))
        }
        
        logger.info(f"OTIMIZADO RF -> {metricas_rf_opt}")
        
        # Salvar modelos
        OUTPUT_DIR.mkdir(exist_ok=True)
        joblib.dump(lr_base, OUTPUT_DIR / "lr_model.pkl")
        joblib.dump(rf_base, OUTPUT_DIR / "rf_model.pkl")
        joblib.dump(rf_otimizado, OUTPUT_DIR / "rf_optimized.pkl")
        joblib.dump(scaler, OUTPUT_DIR / "scaler.pkl")
        
        logger.info("Modelos salvos com sucesso!")
        
        # Upload para Azure
        upload_model(OUTPUT_DIR / "lr_model.pkl", "lr_model.pkl")
        upload_model(OUTPUT_DIR / "rf_model.pkl", "rf_model.pkl")
        upload_model(OUTPUT_DIR / "rf_optimized.pkl", "rf_optimized.pkl")
        upload_model(OUTPUT_DIR / "scaler.pkl", "scaler.pkl")
        
        fim_total = time.time()
        tempo_execucao = fim_total - inicio_total
        
        logger.info("===== FIM DO TREINAMENTO =====")
        
        return {
            "status": "sucesso",
            "mensagem": "Modelos treinados com sucesso",
            "metricas_base_lr": metricas_lr,
            "metricas_base_rf": metricas_rf,
            "metricas_otimizado_rf": metricas_rf_opt,
            "melhores_parametros": best_params,
            "tempo_execucao": tempo_execucao
        }
        
    except Exception as e:
        logger.error(f"Erro no treinamento: {e}")
        logger.error(traceback.format_exc())
        raise
