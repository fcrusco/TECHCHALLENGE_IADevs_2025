"""
Ponto de entrada do Assistente Medico.

Este script inicializa o pipeline completo e abre um terminal interativo
onde o medico pode digitar perguntas clinicas e receber respostas contextualizadas.

Como funciona:
- O pipeline carrega o modelo fine-tunado (LLaMA 3.2 via QLoRA, treinado no Kaggle).
  Se o modelo nao estiver disponivel localmente, usa o Ollama como fallback.
- Cada pergunta passa pelos guardrails de seguranca antes de ser processada.
- O RAG (Retrieval-Augmented Generation) busca documentos relevantes no MedQuAD
  usando busca semantica (FAISS + embeddings multilinguais).
- A resposta e gerada pelo LLM com base no contexto recuperado.
- Toda interacao e registrada em logs/audit.jsonl para auditoria.

Comandos disponiveis no terminal:
- "sair": encerra o assistente
- "log": exibe as ultimas entradas do log de auditoria

Como executar:
    python main.py

Requisitos:
- Ollama rodando localmente: ollama serve
- Modelo baixado: ollama pull llama3.2:1b
- Dataset processado em data/processed/
- Vector store em data/vectorstore/ (gerado pelo retriever)
"""

import os
from dotenv import load_dotenv

# O load_dotenv precisa ser chamado antes de qualquer import do src,
# pois os modulos leem as variaveis de ambiente no momento da importacao.
load_dotenv(override=True)

from src.assistant.pipeline import MedicalAssistantPipeline


HEADER = """
=================================================================
  ASSISTENTE MEDICO - LLaMA Fine-tuning + LangChain RAG
=================================================================
  Dataset : MedQuAD (14.571 pares clinicos curados)
  Modelo  : LLaMA 3.2 + QLoRA fine-tuning (treinado no Kaggle)
  Pipeline: LangChain LCEL + FAISS + Guardrails + Auditoria LGPD

  Comandos: "sair" para encerrar | "log" para ver auditoria
=================================================================
"""

LOG_FILE = "./logs/audit.jsonl"


def get_doctor_name() -> tuple[str, str]:
    """
    Solicita o nome do medico ao iniciar o assistente.

    Retorna uma tupla com:
    - display_name: como o nome aparece no terminal (ex: "Dr. Rafael")
    - user_id: versao sem espacos para uso nos logs (ex: "dr_rafael")
    """
    print("Antes de comecar, informe seu nome.")
    name = input("Seu nome: ").strip()

    if not name:
        name = "Medico"

    # Remove espacos extras e capitaliza
    name = name.strip().title()

    display_name = f"Dr. {name}"
    user_id      = f"dr_{name.lower().replace(' ', '_')}"

    return display_name, user_id


def show_log(n: int = 3) -> None:
    """
    Exibe as ultimas N entradas do log de auditoria.

    O log e gravado em logs/audit.jsonl no formato JSONL.
    Cada linha representa uma interacao com campos:
    interaction_id, user_id, timestamp, blocked, guardrail_flags.
    """
    import json
    from pathlib import Path

    path = Path(LOG_FILE)
    if not path.exists() or path.stat().st_size == 0:
        print("  [log] Nenhuma interacao registrada ainda.\n")
        return

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    print(f"\n  Ultimas {min(n, len(lines))} entradas do log de auditoria:")

    for line in lines[-n:]:
        try:
            entry = json.loads(line)
            if entry.get("event") == "interaction_logged":
                print(f"  ID       : {entry.get('interaction_id', 'N/A')}")
                print(f"  Usuario  : {entry.get('user_id', 'N/A')}")
                print(f"  Bloqueado: {entry.get('blocked', False)}")
                print(f"  Timestamp: {entry.get('timestamp', 'N/A')}")
                print()
        except Exception:
            pass


def run() -> None:
    """
    Loop principal do assistente medico interativo.

    Inicializa o pipeline e aguarda perguntas do usuario em loop.
    Cada resposta exibe a resposta do LLM, as fontes MedQuAD utilizadas,
    alertas de guardrail, nivel de confianca e o ID da interacao para auditoria.
    """
    print(HEADER)

    display_name, user_id = get_doctor_name()

    print()
    print(f"  Bem-vindo, {display_name}!")
    print()
    print("Inicializando pipeline...")
    print()

    pipeline = MedicalAssistantPipeline(user_id=user_id)

    print()
    print("Pipeline pronto. Pode fazer sua pergunta clinica.")
    print()

    while True:
        try:
            query = input(f"{display_name}: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nEncerrando assistente.")
            break

        if not query:
            continue

        if query.lower() == "sair":
            print("Encerrando assistente.")
            break

        if query.lower() == "log":
            show_log()
            continue

        print()
        print("Processando...")
        print()

        response = pipeline.run(query, user_id=user_id)

        print("-" * 65)
        print("Assistente:")
        print()
        print(response["answer"])

        if response["warnings"]:
            print()
            print("Alertas de seguranca:")
            for w in response["warnings"]:
                print(f"  - {w}")

        print()
        print(f"Fontes MedQuAD utilizadas: {len(response['sources'])}")
        for s in response["sources"]:
            print(f"  - {s['title']} (relevancia: {s['score']})")

        print()
        print(f"Confianca    : {response['confidence']}")
        print(f"Interaction ID: {response['interaction_id']}")
        print("-" * 65)
        print()


if __name__ == "__main__":
    run()