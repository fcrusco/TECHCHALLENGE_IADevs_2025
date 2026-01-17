import os
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv
import time
from sklearn.metrics import accuracy_score, recall_score, f1_score

# LOGGING
logger = logging.getLogger(__name__)

# função para medir tempo de execução
def medir_tempo(etapa):
    def decorator(func):
        def wrapper(*args, **kwargs):
            inicio = time.time()
            resultado = func(*args, **kwargs)
            fim = time.time()
            logging.info(f"ETAPA={etapa} | TEMPO={fim - inicio:.2f}s")
            return resultado
        return wrapper
    return decorator


#  func pra metrica
def calcular_metricas(y_true, y_pred):
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "recall": recall_score(y_true, y_pred),
        "f1": f1_score(y_true, y_pred)
    }


#  conexao com openai e llm
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def gerar_explicacao_llm(predicao, probabilidades, paciente_info, metricas_modelo):
    """
    Gera explicações em linguagem natural usando LLM.
    """

    prompt = f"""
Você é um assistente médico que apoia um(a) profissional de saúde.

Objetivo: gerar um resumo CLÍNICO, conciso e objetivo (máx. 6-8 linhas).

IMPORTANTE:
- Não usar linguagem leiga.
- Não dar recomendações ao paciente.
- Não sugerir consulta médica.
- Não afirmar diagnóstico; descreva como "probabilidade" ou "risco".
- Focar em interpretação dos dados e possíveis hipóteses clínicas.

RESULTADO DO MODELO
Predição: {predicao}
Probabilidades: {probabilidades}

DADOS DO PACIENTE
{json.dumps(paciente_info, indent=2, ensure_ascii=False)}

MÉTRICAS DO MODELO
{metricas_modelo}

Produza o texto em formato de parágrafo único, claro e técnico.
"""

    resposta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=450
    )

    return resposta.choices[0].message.content.strip()
