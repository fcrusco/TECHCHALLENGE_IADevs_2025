"""
Anonimizacao de dados medicos sensiveis (LGPD).

Este modulo remove ou substitui dados pessoais identificaveis (PII)
dos textos medicos antes do fine-tuning, garantindo conformidade com a LGPD
(Lei Geral de Protecao de Dados - Lei 13.709/2018).

Duas camadas de anonimizacao:

1. Microsoft Presidio (AnalyzerEngine + AnonymizerEngine):
   Detecta entidades como nomes de pessoas, e-mails, telefones, locais e datas
   usando modelos de NLP (spaCy pt_core_news_sm para portugues).

2. Expressoes regulares customizadas:
   Captura formatos especificos do contexto medico brasileiro que o Presidio
   nao detecta nativamente:
   - CPF: formato 000.000.000-00
   - CRM: formato CRM-0000/SP ou variantes
   - Numero de prontuario: "prontuario no 12345" ou variantes

Como usar:
    from src.preprocessing.anonymizer import anonymize_text, anonymize_record

    texto_limpo = anonymize_text("Dr. Joao, CPF 123.456.789-00")
    # Retorna: "<PACIENTE>, CPF <CPF>"

    registro_limpo = anonymize_record({"question": "...", "answer": "..."})

Para processar um diretorio inteiro de arquivos JSONL:
    python -m src.preprocessing.anonymizer --input data/processed --output data/anonymized
"""
from __future__ import annotations
import re
import json
import argparse
from pathlib import Path
from typing import Any

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig


def _build_engines():
    """
    Inicializa os motores do Presidio com suporte a portugues e ingles.
    
    O modelo spaCy pt_core_news_sm deve estar instalado:
        python -m spacy download pt_core_news_sm
    """
    nlp_config = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "pt", "model_name": "pt_core_news_sm"}],
    }
    provider   = NlpEngineProvider(nlp_configuration=nlp_config)
    analyzer   = AnalyzerEngine(
        nlp_engine=provider.create_engine(),
        supported_languages=["pt", "en"]
    )
    anonymizer = AnonymizerEngine()
    return analyzer, anonymizer


analyzer, anonymizer = _build_engines()

# Entidades que o Presidio detecta e substitui
ENTITIES = ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "LOCATION", "DATE_TIME", "NRP"]

# Como cada entidade sera substituida no texto
OPERATORS = {
    "PERSON":        OperatorConfig("replace", {"new_value": "<PACIENTE>"}),
    "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<EMAIL>"}),
    "PHONE_NUMBER":  OperatorConfig("replace", {"new_value": "<TELEFONE>"}),
    "LOCATION":      OperatorConfig("replace", {"new_value": "<LOCAL>"}),
    "DATE_TIME":     OperatorConfig("replace", {"new_value": "<DATA>"}),
    "NRP":           OperatorConfig("replace", {"new_value": "<CPF/RG>"}),
}

# Padroes extras especificos do contexto medico brasileiro
_EXTRA = [
    (re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),               "<CPF>"),
    (re.compile(r"\bCRM[-\s]?\d{4,6}[-/]?[A-Z]{2}\b", re.I),    "<CRM>"),
    (re.compile(r"\bprontu[ai]rio\s*n[o°]?\s*\d{4,10}\b", re.I), "<PRONTUARIO>"),
]


def anonymize_text(text: str, language: str = "pt") -> str:
    """
    Anonimiza um texto removendo dados pessoais identificaveis.

    Args:
        text: Texto original com possiveis dados sensiveis.
        language: Idioma do texto ("pt" ou "en").

    Returns:
        Texto com dados sensiveis substituidos por placeholders.
    """
    results  = analyzer.analyze(text=text, entities=ENTITIES, language=language)
    anon_text: str = anonymizer.anonymize(
        text=text,
        analyzer_results=results,
        operators=OPERATORS
    ).text
    for pattern, replacement in _EXTRA:
        anon_text = pattern.sub(replacement, anon_text)
    return anon_text


def anonymize_record(record: dict[str, Any]) -> dict[str, Any]:
    """
    Anonimiza os campos de texto de um registro JSONL.
    
    Apenas os campos listados em text_fields sao processados.
    Demais campos (como metadados numericos) sao mantidos intactos.
    """
    text_fields = {"instruction", "input", "output", "content", "text", "question", "answer"}
    return {
        k: anonymize_text(v) if k in text_fields and isinstance(v, str) else v
        for k, v in record.items()
    }


def process_directory(input_dir: str, output_dir: str) -> None:
    """
    Processa todos os arquivos JSONL de um diretorio, anonimizando cada registro.
    
    Args:
        input_dir: Diretorio com arquivos JSONL originais.
        output_dir: Diretorio onde os arquivos anonimizados serao salvos.
    """
    in_path, out_path = Path(input_dir), Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    for jsonl_file in in_path.glob("**/*.jsonl"):
        out_file = out_path / jsonl_file.relative_to(in_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with jsonl_file.open("r", encoding="utf-8") as fin, \
             out_file.open("w", encoding="utf-8") as fout:
            for line in fin:
                fout.write(json.dumps(
                    anonymize_record(json.loads(line)),
                    ensure_ascii=False
                ) + "\n")
        print(f"[anonymizer] {jsonl_file.name} -> {out_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Anonimiza arquivos JSONL removendo dados pessoais (LGPD)."
    )
    parser.add_argument("--input",  required=True, help="Diretorio de entrada")
    parser.add_argument("--output", required=True, help="Diretorio de saida")
    args = parser.parse_args()
    process_directory(args.input, args.output)