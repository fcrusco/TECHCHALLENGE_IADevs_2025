"""
Formatador de dados para o template de instrucao do LLaMA 3.

O LLaMA 3 espera os dados de fine-tuning em um formato especifico de chat
com tokens especiais que delimitam o sistema, o usuario e o assistente.
Este modulo converte os pares (pergunta, resposta) do MedQuAD para esse formato.

Template LLaMA 3 (Instruct):
    <|begin_of_text|>
    <|start_header_id|>system<|end_header_id|>
    [instrucao do sistema]<|eot_id|>
    <|start_header_id|>user<|end_header_id|>
    [pergunta]<|eot_id|>
    <|start_header_id|>assistant<|end_header_id|>
    [resposta]<|eot_id|>

Por que esse formato importa:
- O modelo foi pre-treinado para reconhecer esses tokens especiais
- Durante o fine-tuning, o modelo aprende a responder no estilo do assistente
  usando os exemplos formatados corretamente
- O system prompt define o comportamento geral do modelo medico

O campo "text" gerado e exatamente o que o SFTTrainer do Kaggle consome.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any


# Instrucao que define o comportamento do assistente medico.
# Esta instrucao e inserida em todas as amostras de treino,
# ensinando o modelo a sempre agir como assistente medico responsavel.
SYSTEM_PROMPT = (
    "You are a medical assistant trained on clinical guidelines. "
    "Provide accurate medical information, always cite the source, "
    "and recommend human validation for critical decisions. "
    "Never issue direct prescriptions without medical review."
)

# Template com os tokens especiais do LLaMA 3 Instruct.
# Esses tokens sao reconhecidos pelo tokenizador do LLaMA 3
# e indicam as diferentes partes da conversa.
LLAMA3_TEMPLATE = (
    "<|begin_of_text|>"
    "<|start_header_id|>system<|end_header_id|>\n\n{system}<|eot_id|>"
    "<|start_header_id|>user<|end_header_id|>\n\n{user}<|eot_id|>"
    "<|start_header_id|>assistant<|end_header_id|>\n\n{assistant}<|eot_id|>"
)


def format_record(record: dict[str, Any]) -> dict[str, str]:
    """
    Formata um registro MedQuAD para o template LLaMA 3.

    Args:
        record: Dicionario com campos "question"/"answer" (MedQuAD)
                ou "instruction"/"output" (formato alternativo).

    Returns:
        Dicionario com campo "text" no formato LLaMA 3 e "source" do documento.
    """
    question = record.get("question", record.get("instruction", ""))
    answer   = record.get("answer",   record.get("output", ""))
    return {
        "text":   LLAMA3_TEMPLATE.format(
            system=SYSTEM_PROMPT,
            user=question,
            assistant=answer
        ),
        "source": record.get("source", "MedQuAD"),
    }


def format_file(input_path: Path, output_path: Path) -> None:
    """
    Formata todos os registros de um arquivo JSONL.
    
    Args:
        input_path: Arquivo JSONL de entrada com pares pergunta/resposta.
        output_path: Arquivo JSONL de saida com registros no formato LLaMA 3.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with input_path.open("r", encoding="utf-8") as fin, \
         output_path.open("w", encoding="utf-8") as fout:
        for line in fin:
            fout.write(json.dumps(
                format_record(json.loads(line)),
                ensure_ascii=False
            ) + "\n")
    print(f"[formatter] {input_path.name} -> {output_path}")