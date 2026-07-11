"""Fine-tuning LoRA do Qwen2.5-3B-Instruct sobre o dataset STRIDE.

Treina o modelo base para reproduzir exatamente o contrato de system prompt
de backend/services/stride.py, de forma que o adapter resultante seja um
substituto direto (drop-in) para aquela chamada de LLM. O loss é calculado
apenas no turno do assistant (o JSON do relatório STRIDE); os tokens de
system+user ficam mascarados.

Uso:
    python finetune.py
"""

import os

# Precisa ser definido antes do torch inicializar o alocador CUDA. Sequências
# de tamanho variável (batch size 1, sem padding fixo) causavam fragmentação
# do alocador, fazendo o uso de VRAM subir para 96%+ e os passos inflarem de
# ~12s para ~300s — expandable_segments deixa o alocador crescer/encolher os
# blocos já reservados em vez de procurar novos, o que resolve exatamente isso.
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import json
import logging
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    DataCollatorForSeq2Seq,
    Trainer,
    TrainerCallback,
    TrainingArguments,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("finetune")

BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"
DATA_PATH = Path(__file__).parent / "data" / "stride_sft.jsonl"
OUTPUT_DIR = Path(__file__).parent / "output" / "stride-qwen2.5-3b-lora"
MAX_SEQ_LEN = 2304  # cobre o máximo real (2168) com uma margem pequena; também usado como tamanho FIXO de padding
N_EVAL = 4  # exemplos separados para validar o loss
VRAM_FRACTION = 0.85  # limite rígido para o PyTorch dar OOM de forma limpa em vez do driver travar perto de 100%


class VramLogCallback(TrainerCallback):
    """Imprime o uso de VRAM em tempo real a cada passo, para acompanhar no terminal."""

    def on_step_end(self, args, state, control, **kwargs):
        alloc = torch.cuda.memory_allocated() / 1024**3
        reserved = torch.cuda.memory_reserved() / 1024**3
        logger.info("  [vram] alocado=%.2fGB reservado=%.2fGB (passo %d)", alloc, reserved, state.global_step)


def load_examples() -> list[dict]:
    with DATA_PATH.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def build_features(tokenizer, messages: list[dict]) -> dict:
    """Tokeniza uma conversa completa, mascarando os labels de todos os tokens
    exceto a resposta do assistant, para que o loss treine só a saída STRIDE."""
    system, user, assistant = messages[0], messages[1], messages[2]

    prompt_text = tokenizer.apply_chat_template(
        [system, user], tokenize=False, add_generation_prompt=True
    )
    full_text = tokenizer.apply_chat_template(
        [system, user, assistant], tokenize=False, add_generation_prompt=False
    )

    prompt_ids = tokenizer(prompt_text, add_special_tokens=False)["input_ids"]
    full_ids = tokenizer(full_text, add_special_tokens=False)["input_ids"]

    if len(full_ids) > MAX_SEQ_LEN:
        full_ids = full_ids[:MAX_SEQ_LEN]

    labels = list(full_ids)
    n_prompt = min(len(prompt_ids), len(labels))
    for i in range(n_prompt):
        labels[i] = -100

    return {"input_ids": full_ids, "attention_mask": [1] * len(full_ids), "labels": labels}


def main() -> None:
    torch.cuda.set_per_process_memory_fraction(VRAM_FRACTION)
    logger.info("Limite de VRAM do processo: %.0f%% (%.1fGB de %.1fGB)",
                VRAM_FRACTION * 100,
                VRAM_FRACTION * torch.cuda.get_device_properties(0).total_memory / 1024**3,
                torch.cuda.get_device_properties(0).total_memory / 1024**3)

    logger.info("Carregando tokenizer/modelo base: %s", BASE_MODEL)
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, torch_dtype=torch.bfloat16, device_map="cuda",
    )
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()

    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    examples = load_examples()
    logger.info("Exemplos carregados: %d", len(examples))

    features = [build_features(tokenizer, ex["messages"]) for ex in examples]
    lengths = [len(f["input_ids"]) for f in features]
    logger.info("Tamanho das sequências — min:%d max:%d media:%.0f", min(lengths), max(lengths), sum(lengths) / len(lengths))

    eval_features = features[:N_EVAL]
    train_features = features[N_EVAL:]

    train_ds = Dataset.from_list(train_features)
    eval_ds = Dataset.from_list(eval_features)

    # Padding de tamanho fixo (todo batch tem exatamente o mesmo formato) para
    # o alocador CUDA reutilizar os mesmos blocos reservados a cada passo em
    # vez de fragmentar a cada novo tamanho de sequência — foi isso que
    # resolveu o estouro de 12s/passo -> 300s/passo e a VRAM subindo a 96%+.
    collator = DataCollatorForSeq2Seq(
        tokenizer, padding="max_length", max_length=MAX_SEQ_LEN, label_pad_token_id=-100
    )

    args = TrainingArguments(
        output_dir=str(OUTPUT_DIR / "checkpoints"),
        num_train_epochs=4,
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        eval_accumulation_steps=1,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,
        bf16=True,
        logging_steps=1,
        eval_strategy="epoch",
        save_strategy="no",
        report_to=[],
        gradient_checkpointing=False,  # já habilitado manualmente acima
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=collator,
        callbacks=[VramLogCallback()],
    )

    logger.info("Iniciando treinamento...")
    trainer.train()

    logger.info("Salvando adapter LoRA em %s", OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(OUTPUT_DIR))
    tokenizer.save_pretrained(str(OUTPUT_DIR))
    logger.info("Concluido.")


if __name__ == "__main__":
    main()
