"""
API FastAPI para treinamento e avaliação de modelos de diabetes.

Esta API expõe funcionalidades dos scripts de treinamento e avaliação
de forma RESTful, com documentação automática via Swagger.
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
import logging
import traceback
import os

from api.schemas import (
    PacienteInput,
    AvaliacaoResponse,
    TreinamentoResponse,
    HealthResponse,
    PredicaoResultado
)
from api.services import avaliar_paciente, treinar_modelos

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("api")

# Criação da aplicação FastAPI
app = FastAPI(
    title="API de Avaliação de Diabetes",
    description="""
    API para treinamento e avaliação de modelos de machine learning para predição de diabetes.
    
    ## Funcionalidades
    
    * **Treinamento**: Treina modelos de Logistic Regression e Random Forest usando algoritmo genético
    * **Avaliação**: Avalia pacientes e retorna predições com explicações geradas por IA
    
    ## Modelos
    
    A API utiliza dois modelos principais:
    - **Regressão Logística**: Modelo linear para classificação
    - **Random Forest**: Modelo ensemble otimizado com algoritmo genético
    
    Todos os modelos são treinados com dados balanceados usando SMOTE.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar origens permitidas
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define o caminho para o arquivo de log. 
# Como o main.py está em /api, subimos um nível para encontrar o log na raiz.
LOG_FILE_PATH = Path(__file__).resolve().parent.parent / "pipeline.log"

@app.get("/download-log")
async def download_log():
    """
    Endpoint para baixar o arquivo de log gerado pelo pipeline de treinamento.
    """
    if not LOG_FILE_PATH.exists():
        raise HTTPException(
            status_code=404, 
            detail="Arquivo de log ainda não foi gerado ou não foi encontrado."
        )
    
    return FileResponse(
        path=LOG_FILE_PATH, 
        filename="pipeline_execution.log", 
        media_type="text/plain"
    )


@app.get("/", response_model=HealthResponse, tags=["Health"])
async def root():
    """
    Endpoint raiz - Health check da API.
    
    Retorna o status da API e informações básicas.
    """
    return HealthResponse(
        status="online",
        versao="1.0.0"
    )


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check da API.
    
    Use este endpoint para verificar se a API está funcionando corretamente.
    """
    return HealthResponse(
        status="online",
        versao="1.0.0"
    )


@app.post("/treinamento", response_model=TreinamentoResponse, tags=["Treinamento"])
async def treinar():
    """
    Treina os modelos de machine learning.
    
    Este endpoint executa o processo completo de treinamento:
    
    1. Carrega e prepara o dataset
    2. Treina modelos base (Logistic Regression e Random Forest)
    3. Otimiza Random Forest usando algoritmo genético
    4. Salva os modelos treinados
    5. Faz upload dos modelos para Azure Storage (se configurado)
    
    **Nota**: Este processo pode levar alguns minutos para completar.
    
    **Retorna**:
    - Métricas de performance dos modelos
    - Melhores parâmetros encontrados pelo algoritmo genético
    - Tempo de execução
    """
    try:
        logger.info("Iniciando treinamento via API...")
        resultado = treinar_modelos()
        logger.info("Treinamento concluído com sucesso")
        return TreinamentoResponse(**resultado)
    except Exception as e:
        logger.error(f"Erro no treinamento: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao treinar modelos: {str(e)}"
        )


@app.post("/avaliacao", response_model=AvaliacaoResponse, tags=["Avaliação"])
async def avaliar(
    paciente: PacienteInput,
    incluir_explicacao: bool = True
):
    """
    Avalia um paciente e retorna predições de risco de diabetes.
    
    Este endpoint utiliza os modelos treinados para fazer predições sobre
    o risco de diabetes de um paciente com base em suas características clínicas.
    
    **Parâmetros**:
    - **paciente**: Dados clínicos do paciente (Pregnancies, Glucose, BloodPressure, etc.)
    - **incluir_explicacao**: Se True, gera explicação usando LLM (padrão: True)
    
    **Retorna**:
    - Predições de ambos os modelos (Logistic Regression e Random Forest)
    - Probabilidades de cada classe
    - Explicação gerada por IA (se solicitado)
    
    **Exemplo de uso**:
    ```json
    {
        "Pregnancies": 1,
        "Glucose": 85,
        "BloodPressure": 66,
        "SkinThickness": 29,
        "Insulin": 0,
        "BMI": 26.6,
        "DiabetesPedigreeFunction": 0.351,
        "Age": 31
    }
    ```
    """
    try:
        logger.info(f"Avaliando paciente via API...")
        
        # Converte Pydantic model para dict (compatível com v1 e v2)
        try:
            # Pydantic v2
            paciente_dict = paciente.model_dump()
        except AttributeError:
            # Pydantic v1
            paciente_dict = paciente.dict()
        
        # Avalia paciente
        resultado = avaliar_paciente(paciente_dict, incluir_explicacao)
        
        logger.info("Avaliação concluída com sucesso")
        return AvaliacaoResponse(**resultado)
        
    except FileNotFoundError as e:
        logger.error(f"Modelos não encontrados: {e}")
        raise HTTPException(
            status_code=404,
            detail="Modelos não encontrados. Execute o treinamento primeiro através do endpoint /treinamento"
        )
    except Exception as e:
        logger.error(f"Erro na avaliação: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao avaliar paciente: {str(e)}"
        )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Handler global para exceções não tratadas.
    """
    logger.error(f"Erro não tratado: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
