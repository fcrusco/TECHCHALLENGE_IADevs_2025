"""
Construcao do dataset de fine-tuning a partir do MedQuAD.

Este script e o primeiro passo do pipeline de fine-tuning. Ele:
1. Le todos os arquivos XML do repositorio MedQuAD
2. Extrai os pares (pergunta, resposta) de cada arquivo
3. Aplica curadoria de qualidade (remove duplicatas, conteudo nao medico, etc.)
4. Formata os dados no template de instrucao do LLaMA 3
5. Divide em splits de treino, validacao e teste
6. Salva os splits em formato JSONL em data/processed/

Estrutura do XML MedQuAD:
    <QAPairs>
        <QAPair pid="1">
            <Question qid="1" qtype="information">What is X?</Question>
            <Answer>X is...</Answer>
        </QAPair>
    </QAPairs>

O dataset MedQuAD (github.com/abachaa/MedQuAD) contem 16.407 pares
de perguntas e respostas clinicas em ingles, organizados em 47 colecoes
de diferentes fontes medicas (NIH, CDC, NCI, etc.).

Resultados esperados apos a curadoria:
- train.jsonl: ~11.657 amostras (80%)
- val.jsonl:   ~1.457 amostras (10%)
- test.jsonl:  ~1.457 amostras (10%)

Como executar:
    python -m src.finetuning.dataset_builder --config configs/model_config.yaml

Pre-requisito:
    git clone https://github.com/abachaa/MedQuAD.git data/raw/medquad
"""
from __future__ import annotations
import json
import random
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

from src.preprocessing.curator import curate_stream
from src.preprocessing.formatter import format_record


def parse_medquad_xml(xml_path: Path) -> list[dict]:
    """
    Extrai pares (pergunta, resposta) de um arquivo XML do MedQuAD.
    
    O MedQuAD contem 47 colecoes de XMLs de diferentes fontes medicas.
    Cada arquivo pode conter multiplos pares QA.
    
    Args:
        xml_path: Caminho para o arquivo XML.
        
    Returns:
        Lista de dicionarios com campos "question", "answer" e "source".
    """
    records = []
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        for qa in root.findall(".//QAPair"):
            q_el = qa.find("Question")
            a_el = qa.find("Answer")
            if q_el is not None and a_el is not None:
                q = (q_el.text or "").strip()
                a = (a_el.text or "").strip()
                if q and a:
                    records.append({
                        "question": q,
                        "answer":   a,
                        "source":   f"MedQuAD:{xml_path.stem}",
                    })
    except ET.ParseError as e:
        print(f"[dataset_builder] Erro ao parsear {xml_path.name}: {e}")
    return records


def load_medquad(medquad_dir: str) -> list[dict]:
    """
    Carrega todos os XMLs do repositorio MedQuAD.
    
    Percorre recursivamente o diretorio em busca de arquivos .xml.
    
    Args:
        medquad_dir: Caminho para o repositorio MedQuAD clonado.
        
    Returns:
        Lista com todos os pares QA extraidos.
        
    Raises:
        FileNotFoundError: Se nenhum arquivo XML for encontrado.
    """
    all_records: list[dict] = []
    xml_files = list(Path(medquad_dir).rglob("*.xml"))

    if not xml_files:
        raise FileNotFoundError(
            f"Nenhum XML encontrado em: {medquad_dir}\n"
            "Clone o MedQuAD primeiro:\n"
            "  git clone https://github.com/abachaa/MedQuAD.git data/raw/medquad"
        )

    for xml_file in xml_files:
        records = parse_medquad_xml(xml_file)
        all_records.extend(records)

    return all_records


def build_dataset(config: dict) -> None:
    """
    Executa o pipeline completo de construcao do dataset.
    
    Fluxo:
    1. Carrega XMLs do MedQuAD
    2. Exibe exemplo de registro para verificacao
    3. Aplica curadoria (remove duplicatas, conteudo nao medico, etc.)
    4. Formata cada registro no template LLaMA 3
    5. Embaralha os dados com seed fixo (reproducibilidade)
    6. Divide em train/val/test conforme proporcoes do config
    7. Salva os splits em data/processed/
    
    Args:
        config: Dicionario com configuracoes do model_config.yaml.
    """
    from src.utils.config import Config

    medquad_dir = Config.MEDQUAD_DIR
    raw_records = load_medquad(medquad_dir)
    print(f"[dataset_builder] Total bruto: {len(raw_records)}")

    if raw_records:
        print(f"[dataset_builder] Exemplo de registro:")
        ex = raw_records[0]
        print(f"  question: {ex.get('question', '')[:80]}...")
        print(f"  answer:   {ex.get('answer',   '')[:80]}...")

    curated   = list(curate_stream(iter(raw_records)))
    formatted = [format_record(r) for r in curated]

    # Seed fixo garante que os splits sejam sempre os mesmos
    random.seed(42)
    random.shuffle(formatted)

    dc    = config["dataset"]
    n     = len(formatted)
    n_test = int(n * dc["test_split"])
    n_val  = int(n * dc["val_split"])

    splits = {
        "test":  formatted[:n_test],
        "val":   formatted[n_test:n_test + n_val],
        "train": formatted[n_test + n_val:],
    }

    out_dir = Path(dc["train_file"]).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    for split_name, records in splits.items():
        out_file = out_dir / f"{split_name}.jsonl"
        with out_file.open("w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"[dataset_builder] {split_name}: {len(records)} amostras -> {out_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Constroi o dataset de fine-tuning a partir do MedQuAD."
    )
    parser.add_argument(
        "--config",
        default="configs/model_config.yaml",
        help="Caminho para o arquivo de configuracao YAML"
    )
    args = parser.parse_args()
    with open(args.config) as f:
        cfg = yaml.safe_load(f)
    build_dataset(cfg)