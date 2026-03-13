"""
Verificacao e teste do modelo apos o fine-tuning.

O fine-tuning real foi realizado no Kaggle usando o notebook
notebooks/04_kaggle_finetuning.ipynb, com GPU T4, QLoRA 4-bit
sobre o modelo meta-llama/Llama-3.2-3B-Instruct.

Este modulo verifica se o Ollama esta ativo e realiza um teste de sanidade
com amostras reais do MedQuAD para confirmar que o modelo responde
adequadamente a perguntas clinicas.

Por que o fine-tuning foi feito no Kaggle e nao localmente:
- O LLaMA 3.2 3B requer pelo menos 8GB de VRAM para treino
- Maquinas locais comuns nao tem GPU suficiente
- O Kaggle oferece gratuitamente 30h/semana de GPU T4 (16GB VRAM)
- O modelo treinado foi salvo localmente em outputs/llama-medical/

Como executar o teste de sanidade:
    python -m src.finetuning.trainer

Pre-requisitos:
    - Ollama rodando: ollama serve
    - Modelo baixado: ollama pull llama3.2:1b
    - Dataset processado em data/processed/
"""
from __future__ import annotations
import json
import requests
from pathlib import Path
from src.utils.config import Config


SYSTEM_PROMPT = (
    "You are a medical assistant trained on clinical guidelines. "
    "Provide accurate medical information and always recommend "
    "human validation for critical decisions."
)


def check_ollama() -> bool:
    """
    Verifica se o Ollama esta rodando e se o modelo configurado esta disponivel.
    
    Returns:
        True se tudo estiver ok, False caso contrario.
    """
    try:
        resp   = requests.get(f"{Config.OLLAMA_BASE_URL}/api/tags", timeout=5)
        models = [m["name"] for m in resp.json().get("models", [])]
        if Config.OLLAMA_MODEL not in models:
            print(f"[trainer] Modelo '{Config.OLLAMA_MODEL}' nao encontrado.")
            print(f"[trainer] Execute: ollama pull {Config.OLLAMA_MODEL}")
            return False
        print(f"[trainer] Ollama ativo | Modelo: {Config.OLLAMA_MODEL}")
        return True
    except requests.ConnectionError:
        print(f"[trainer] Ollama nao esta rodando em {Config.OLLAMA_BASE_URL}")
        print("[trainer] Execute: ollama serve")
        return False


def run_sanity_check(n_samples: int = 5) -> None:
    """
    Testa o modelo com amostras reais do conjunto de teste MedQuAD.
    
    Para cada amostra, envia a pergunta ao modelo e exibe a resposta,
    permitindo uma avaliacao qualitativa rapida do comportamento do modelo.
    
    Args:
        n_samples: Numero de amostras a testar (padrao: 5).
    """
    test_file = Path(Config.model["dataset"]["test_file"])
    if not test_file.exists():
        print(f"[trainer] Dataset nao encontrado: {test_file}")
        print("[trainer] Execute primeiro: python -m src.finetuning.dataset_builder")
        return

    samples = []
    with test_file.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= n_samples:
                break
            samples.append(json.loads(line))

    print(f"\n[trainer] Testando {len(samples)} amostras do MedQuAD...\n")

    for i, sample in enumerate(samples, 1):
        # Extrai a pergunta do template LLaMA 3
        text = sample.get("text", "")
        if "<|start_header_id|>user<|end_header_id|>" in text:
            question = (
                text.split("<|start_header_id|>user<|end_header_id|>")[-1]
                    .split("<|eot_id|>")[0]
                    .strip()
            )
        else:
            question = text[:200]

        payload = {
            "model": Config.OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": question},
            ],
            "stream": False,
        }
        resp   = requests.post(f"{Config.OLLAMA_BASE_URL}/api/chat", json=payload, timeout=60)
        answer = resp.json().get("message", {}).get("content", "")

        print(f"--- Amostra {i} ---")
        print(f"Pergunta: {question[:120]}...")
        print(f"Resposta: {answer[:300]}...")
        print()


if __name__ == "__main__":
    if check_ollama():
        run_sanity_check()
