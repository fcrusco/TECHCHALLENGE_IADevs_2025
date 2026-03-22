"""
Curadoria e filtragem de qualidade do dataset MedQuAD.

Antes do fine-tuning, os dados brutos do MedQuAD passam por este modulo
para garantir que apenas amostras de qualidade sejam usadas no treinamento.

Criterios de rejeicao:
- Perguntas muito curtas (menos de 10 caracteres): geralmente incompletas
- Respostas muito curtas (menos de 20 caracteres): sem conteudo clinico util
- Respostas muito longas (mais de 8192 caracteres): ultrapassam o contexto do modelo
- Conteudo nao medico: registros sem palavras-chave clinicas relevantes
- Duplicatas: mesmo texto de pergunta aparece mais de uma vez

Por que curadoria importa:
- Dados de baixa qualidade degradam o fine-tuning
- Duplicatas causam overfitting (o modelo memoriza ao inves de generalizar)
- Conteudo fora de dominio medico "confunde" o modelo durante o treino

Resultados com o MedQuAD completo (16.407 registros):
- Mantidos: 14.571 (88%)
- Rejeitados: 1.836 (12%)
  - 1.345 duplicatas
  - 321 nao medicos
  - 169 muito longos
  - 1 muito curto

Como usar:
    from src.preprocessing.curator import curate_stream
    registros_limpos = list(curate_stream(iter(registros_brutos)))

Para processar um diretorio inteiro:
    python -m src.preprocessing.curator --input data/raw --output data/processed
"""
from __future__ import annotations
import json
import hashlib
import argparse
from pathlib import Path
from typing import Iterator

MIN_QUESTION_LEN = 10
MIN_ANSWER_LEN   = 20
MAX_ANSWER_LEN   = 8192

# Palavras-chave que indicam conteudo medico valido.
# Registros que nao contem nenhuma dessas palavras sao rejeitados.
MEDICAL_KEYWORDS = {
    "patient", "treatment", "diagnosis", "symptom", "medication", "dose",
    "disease", "therapy", "clinical", "medical", "health", "drug", "surgery",
    "cancer", "diabetes", "infection", "pain", "chronic", "condition",
    "disorder", "syndrome", "cause", "prevent", "risk", "genetic",
    "paciente", "tratamento", "diagnostico", "sintoma", "medicamento",
}


def _hash(text: str) -> str:
    """Gera hash MD5 do texto para deteccao de duplicatas."""
    return hashlib.md5(text.encode()).hexdigest()


def _is_valid(record: dict) -> tuple[bool, str]:
    """
    Verifica se um registro atende aos criterios de qualidade.
    
    Suporta tanto campos "question"/"answer" (formato MedQuAD)
    quanto "instruction"/"output" (formato alternativo).
    
    Returns:
        Tupla (valido, motivo_rejeicao).
    """
    q = (record.get("question") or record.get("instruction") or "").strip()
    a = (record.get("answer")   or record.get("output")      or "").strip()

    if len(q) < MIN_QUESTION_LEN:
        return False, "question_too_short"
    if len(a) < MIN_ANSWER_LEN:
        return False, "answer_too_short"
    if len(a) > MAX_ANSWER_LEN:
        return False, "answer_too_long"

    combined = (q + " " + a).lower()
    if not any(kw in combined for kw in MEDICAL_KEYWORDS):
        return False, "not_medical"

    return True, "ok"


def curate_stream(records: Iterator[dict]) -> Iterator[dict]:
    """
    Filtra um stream de registros aplicando os criterios de qualidade.
    
    Processa os registros um por um (streaming) para eficiencia de memoria.
    Imprime estatisticas ao final do processamento.
    
    Args:
        records: Iterator de dicionarios com dados brutos.
        
    Yields:
        Registros que passaram em todos os criterios de qualidade.
    """
    seen: set[str] = set()
    stats = {"total": 0, "kept": 0, "rejected": {}}

    for record in records:
        stats["total"] += 1
        ok, reason = _is_valid(record)

        if not ok:
            stats["rejected"][reason] = stats["rejected"].get(reason, 0) + 1
            continue

        h = _hash(record.get("question", record.get("instruction", "")))
        if h in seen:
            stats["rejected"]["duplicate"] = stats["rejected"].get("duplicate", 0) + 1
            continue

        seen.add(h)
        stats["kept"] += 1
        yield record

    print(
        f"[curator] Total: {stats['total']} | "
        f"Mantidos: {stats['kept']} | "
        f"Rejeitados: {stats['rejected']}"
    )


def process_directory(input_dir: str, output_dir: str) -> None:
    """
    Processa todos os arquivos JSONL de um diretorio aplicando curadoria.
    
    Args:
        input_dir: Diretorio com arquivos JSONL brutos.
        output_dir: Diretorio onde os arquivos curados serao salvos.
    """
    in_path, out_path = Path(input_dir), Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    for jsonl_file in in_path.glob("**/*.jsonl"):
        out_file = out_path / jsonl_file.relative_to(in_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        def _records():
            with jsonl_file.open("r", encoding="utf-8") as f:
                for line in f:
                    yield json.loads(line)

        with out_file.open("w", encoding="utf-8") as fout:
            for r in curate_stream(_records()):
                fout.write(json.dumps(r, ensure_ascii=False) + "\n")

        print(f"[curator] {jsonl_file.name} -> {out_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Aplica curadoria de qualidade em arquivos JSONL do MedQuAD."
    )
    parser.add_argument("--input",  required=True, help="Diretorio de entrada")
    parser.add_argument("--output", required=True, help="Diretorio de saida")
    args = parser.parse_args()
    process_directory(args.input, args.output)
