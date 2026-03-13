"""
Avaliacao quantitativa do modelo no conjunto de teste MedQuAD.

Apos o fine-tuning, este modulo mede a qualidade das respostas
usando duas metricas padrao de NLP:

ROUGE-L (Recall-Oriented Understudy for Gisting Evaluation - Longest):
- Mede a sobreposicao de sequencias de palavras entre a resposta gerada
  e a resposta de referencia do MedQuAD.
- Varia de 0 a 1. Valores tipicos para modelos medicos: 0.3 a 0.6.
- Foca na estrutura da resposta (ordem das palavras).

BLEU (Bilingual Evaluation Understudy):
- Mede a precisao de n-gramas (sequencias de n palavras) na resposta gerada
  em relacao a referencia.
- Mais sensivel a respostas curtas.
- Valores tipicos: 0.1 a 0.4.

Importante: estas metricas sao aproximacoes. Uma resposta clinicamente
correta mas com vocabulario diferente do MedQuAD pode ter score baixo.
A avaliacao qualitativa (leitura das respostas) e sempre recomendada.

Como executar:
    python -m src.finetuning.evaluator --test_file data/processed/test.jsonl

Os resultados sao salvos em eval_results.json com um resumo e os detalhes
de cada amostra avaliada.
"""
from __future__ import annotations
import json
import argparse
from pathlib import Path

import requests
from rouge_score import rouge_scorer
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

from src.utils.config import Config


SYSTEM_PROMPT = (
    "You are a medical assistant. Answer the question based on clinical knowledge. "
    "Be concise and accurate."
)


def _ask_ollama(question: str) -> str:
    """
    Envia uma pergunta ao Ollama e retorna a resposta do modelo.
    
    Args:
        question: Pergunta clinica em ingles (formato MedQuAD).
        
    Returns:
        Resposta gerada pelo modelo.
    """
    payload = {
        "model": Config.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": question},
        ],
        "stream": False,
    }
    resp = requests.post(f"{Config.OLLAMA_BASE_URL}/api/chat", json=payload, timeout=120)
    return resp.json().get("message", {}).get("content", "")


def evaluate(
    test_file: str,
    output_file: str = "eval_results.json",
    max_samples: int = 100
) -> dict:
    """
    Avalia o modelo em amostras do conjunto de teste MedQuAD.
    
    Para cada amostra:
    1. Extrai a pergunta e resposta de referencia do template LLaMA 3
    2. Gera uma resposta com o modelo via Ollama
    3. Calcula ROUGE-L e BLEU comparando com a referencia
    4. Acumula as metricas e salva os resultados
    
    Args:
        test_file: Caminho para o arquivo test.jsonl.
        output_file: Caminho para salvar os resultados em JSON.
        max_samples: Numero maximo de amostras a avaliar (padrao: 100).
        
    Returns:
        Dicionario com metricas medias (avg_rougeL, avg_bleu, n_samples).
    """
    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
    smooth = SmoothingFunction().method1

    samples = []
    with Path(test_file).open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= max_samples:
                break
            samples.append(json.loads(line))

    print(f"[evaluator] Avaliando {len(samples)} amostras com {Config.OLLAMA_MODEL}...")

    rouge_scores, bleu_scores, results = [], [], []

    for i, sample in enumerate(samples, 1):
        text = sample.get("text", "")
        if "<|start_header_id|>user<|end_header_id|>" not in text:
            continue

        question  = (
            text.split("<|start_header_id|>user<|end_header_id|>")[-1]
                .split("<|eot_id|>")[0]
                .strip()
        )
        reference = (
            text.split("<|start_header_id|>assistant<|end_header_id|>")[-1]
                .replace("<|eot_id|>", "")
                .strip()
        )

        generated = _ask_ollama(question)
        rouge     = scorer.score(reference, generated)["rougeL"].fmeasure
        bleu      = sentence_bleu(
            [reference.split()],
            generated.split(),
            smoothing_function=smooth
        )

        rouge_scores.append(rouge)
        bleu_scores.append(bleu)
        results.append({
            "question":  question[:100],
            "reference": reference[:200],
            "generated": generated[:200],
            "rougeL":    rouge,
            "bleu":      bleu,
        })

        if i % 10 == 0:
            avg = sum(rouge_scores) / len(rouge_scores)
            print(f"[evaluator] {i}/{len(samples)} -- ROUGE-L medio: {avg:.4f}")

    summary = {
        "model":      Config.OLLAMA_MODEL,
        "avg_rougeL": round(sum(rouge_scores) / len(rouge_scores), 4),
        "avg_bleu":   round(sum(bleu_scores)  / len(bleu_scores),  4),
        "n_samples":  len(results),
    }
    print(f"[evaluator] ROUGE-L={summary['avg_rougeL']} | BLEU={summary['avg_bleu']}")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results}, f, ensure_ascii=False, indent=2)
    print(f"[evaluator] Resultados salvos em: {output_file}")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Avalia o modelo com metricas ROUGE-L e BLEU no conjunto de teste MedQuAD."
    )
    parser.add_argument("--test_file",   default="data/processed/test.jsonl")
    parser.add_argument("--output",      default="eval_results.json")
    parser.add_argument("--max_samples", type=int, default=100)
    args = parser.parse_args()
    evaluate(args.test_file, args.output, args.max_samples)