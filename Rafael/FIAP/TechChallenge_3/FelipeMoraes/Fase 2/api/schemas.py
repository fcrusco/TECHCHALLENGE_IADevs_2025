"""
Schemas Pydantic para validação de dados da API.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List


class PacienteInput(BaseModel):
    """Schema para entrada de dados do paciente."""
    
    Pregnancies: int = Field(..., ge=0, description="Número de gestações")
    Glucose: float = Field(..., ge=0, description="Glicose (mg/dL)")
    BloodPressure: float = Field(..., ge=0, description="Pressão arterial (mmHg)")
    SkinThickness: float = Field(..., ge=0, description="Espessura da pele (mm)")
    Insulin: float = Field(..., ge=0, description="Insulina (µU/mL)")
    BMI: float = Field(..., ge=0, description="IMC (Body Mass Index)")
    DiabetesPedigreeFunction: float = Field(..., ge=0, description="Função de pedigree diabético")
    Age: int = Field(..., ge=0, le=120, description="Idade")
    
    class Config:
        json_schema_extra = {
            "example": {
                "Pregnancies": 1,
                "Glucose": 85,
                "BloodPressure": 66,
                "SkinThickness": 29,
                "Insulin": 0,
                "BMI": 26.6,
                "DiabetesPedigreeFunction": 0.351,
                "Age": 31
            }
        }


class PredicaoResultado(BaseModel):
    """Schema para resultado de predição de um modelo."""
    
    modelo: str = Field(..., description="Nome do modelo utilizado")
    predicao: str = Field(..., description="Predição (Positivo/Negativo para risco de diabetes)")
    probabilidade_nao_diabetes: float = Field(..., description="Probabilidade de não ter diabetes (0-1)")
    probabilidade_diabetes: float = Field(..., description="Probabilidade de ter diabetes (0-1)")
    predicao_binaria: int = Field(..., description="Predição binária (0 ou 1)")


class AvaliacaoResponse(BaseModel):
    """Schema para resposta completa de avaliação."""
    
    paciente: Dict = Field(..., description="Dados do paciente processados")
    resultados: List[PredicaoResultado] = Field(..., description="Resultados de predição de cada modelo")
    explicacao_ia: Optional[str] = Field(None, description="Explicação gerada por IA (se disponível)")


class TreinamentoResponse(BaseModel):
    """Schema para resposta do treinamento."""
    
    status: str = Field(..., description="Status do treinamento")
    mensagem: str = Field(..., description="Mensagem descritiva")
    metricas_base_lr: Optional[Dict] = Field(None, description="Métricas do modelo Logistic Regression base")
    metricas_base_rf: Optional[Dict] = Field(None, description="Métricas do modelo Random Forest base")
    metricas_otimizado_rf: Optional[Dict] = Field(None, description="Métricas do modelo Random Forest otimizado")
    melhores_parametros: Optional[Dict] = Field(None, description="Melhores parâmetros encontrados pelo algoritmo genético")
    tempo_execucao: Optional[float] = Field(None, description="Tempo de execução em segundos")


class HealthResponse(BaseModel):
    """Schema para resposta de health check."""
    
    status: str = Field(..., description="Status da API")
    versao: str = Field(..., description="Versão da API")
