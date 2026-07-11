"""Mescla o adapter LoRA nos pesos do modelo base para que possa ser
convertido em um único arquivo GGUF autocontido (sem precisar carregar
o adapter separadamente na inferência via Ollama/LM Studio).

Uso:
    python merge_adapter.py
"""

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"
ADAPTER_DIR = "output/stride-qwen2.5-3b-lora"
MERGED_DIR = "output/stride-qwen2.5-3b-merged"


def main() -> None:
    print(f"Carregando base {BASE_MODEL} + adapter {ADAPTER_DIR}...")
    tokenizer = AutoTokenizer.from_pretrained(ADAPTER_DIR)
    base = AutoModelForCausalLM.from_pretrained(BASE_MODEL, dtype=torch.bfloat16, device_map="cpu")
    model = PeftModel.from_pretrained(base, ADAPTER_DIR)

    print("Mesclando adapter nos pesos base...")
    merged = model.merge_and_unload()

    print(f"Salvando modelo mesclado em {MERGED_DIR}...")
    merged.save_pretrained(MERGED_DIR, safe_serialization=True)
    tokenizer.save_pretrained(MERGED_DIR)
    print("Concluido.")


if __name__ == "__main__":
    main()
