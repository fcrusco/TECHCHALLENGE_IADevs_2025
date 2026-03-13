"""
Configurações centralizadas — carregadas de YAML e .env
"""
import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def load_yaml(path: str) -> dict:
    with open(BASE_DIR / path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class Config:
    model: dict    = load_yaml("configs/model_config.yaml")
    pipeline: dict = load_yaml("configs/pipeline_config.yaml")

    # Modelo fine-tunado (gerado pelo Colab)
    FINETUNED_MODEL_PATH: str = os.getenv("FINETUNED_MODEL_PATH", "./outputs/llama-medical")

    # Fallback Ollama (usado antes de ter o modelo fine-tunado)
    USE_OLLAMA_FALLBACK: bool = os.getenv("USE_OLLAMA_FALLBACK", "true").lower() == "true"
    OLLAMA_BASE_URL:     str  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL:        str  = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

    # Dataset
    MEDQUAD_DIR: str = os.getenv("MEDQUAD_DIR", "./data/raw/medquad")

    # Diretórios
    LOG_DIR:           Path = BASE_DIR / os.getenv("LOG_DIR", "logs")
    VECTOR_STORE_PATH: str  = BASE_DIR / os.getenv("VECTOR_STORE_PATH", "data/vectorstore")

    # Segurança
    ENABLE_GUARDRAILS: bool = os.getenv("ENABLE_GUARDRAILS", "true").lower() == "true"
