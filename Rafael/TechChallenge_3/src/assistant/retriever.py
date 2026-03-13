"""
Retriever RAG: busca semantica nos documentos MedQuAD.

Este modulo e responsavel por:
1. Construir o indice vetorial FAISS a partir dos dados processados do MedQuAD
2. Carregar o indice ja construido do disco
3. Realizar buscas semanticas (por similaridade de significado, nao por palavras-chave)

Como funciona a busca semantica:
- Cada documento do MedQuAD e convertido em um vetor de numeros (embedding)
  usando o modelo sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2.
  Esse modelo foi escolhido por suportar multiplos idiomas, incluindo portugues.
- Os vetores sao indexados no FAISS (biblioteca da Meta para busca vetorial eficiente).
- Quando o usuario faz uma pergunta, ela tambem e convertida em vetor
  e o FAISS encontra os documentos mais similares semanticamente.
- Os documentos encontrados sao passados como contexto para o LLM.

O vector store e salvo em data/vectorstore/ para nao precisar reconstruir a cada execucao.

Para construir o vector store pela primeira vez:
    python -m src.assistant.retriever
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

from src.utils.config import Config


class MedicalRetriever:
    """
    Gerencia o indice FAISS de documentos MedQuAD.

    Atributos principais apos inicializacao:
    - embeddings: modelo de embeddings multilingual
    - _store: indice FAISS com todos os documentos
    - store_path: caminho onde o indice e salvo/carregado
    """

    def __init__(self, config: Optional[dict] = None):
        rc = (config or Config.pipeline)["retriever"]
        # Modelo de embeddings multilingual - converte texto em vetores numericos.
        # Suporta portugues e ingles, importante pois o MedQuAD e em ingles
        # mas as perguntas dos medicos podem ser em portugues.
        self.embeddings = HuggingFaceEmbeddings(
            model_name=rc["embedding_model"],
            model_kwargs={"device": "cpu"}
        )
        self.top_k           = rc["top_k"]
        self.score_threshold = rc["score_threshold"]
        self.store_path      = Path(rc["vector_store_path"])
        self._store: Optional[FAISS] = None

    def load_or_build(self, processed_dir: Optional[str] = None) -> None:
        """
        Tenta carregar o vector store do disco. Se nao existir, constroi a partir
        dos documentos processados.

        O vector store e salvo em data/vectorstore/ e pode ser reutilizado
        em todas as execucoes sem precisar reconstruir.
        """
        if self.store_path.exists():
            self._store = FAISS.load_local(
                str(self.store_path),
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            print(f"[retriever] Vector store carregado: {self.store_path}")
        elif processed_dir:
            self._build(processed_dir)
        else:
            raise FileNotFoundError(
                f"Vector store nao encontrado em {self.store_path}. "
                "Execute: python -m src.assistant.retriever"
            )

    def _build(self, processed_dir: str) -> None:
        """
        Constroi o indice FAISS a partir dos arquivos JSONL processados.

        Le todos os arquivos .jsonl em data/processed/, extrai o campo "text"
        de cada registro e cria os embeddings. O processo demora alguns minutos
        pois precisa gerar embeddings para todos os ~14.000 documentos.

        Apos a construcao, salva o indice em data/vectorstore/ para reuso.
        """
        docs: list[Document] = []
        for jsonl in Path(processed_dir).glob("**/*.jsonl"):
            with jsonl.open("r", encoding="utf-8") as f:
                for line in f:
                    r = json.loads(line)
                    content = r.get("text", "")
                    if content:
                        docs.append(Document(
                            page_content=content,
                            metadata={
                                "source_id": r.get("source", jsonl.stem),
                                "title":     r.get("source", "MedQuAD"),
                            },
                        ))
        self._store = FAISS.from_documents(docs, self.embeddings)
        self.store_path.mkdir(parents=True, exist_ok=True)
        self._store.save_local(str(self.store_path))
        print(f"[retriever] Vector store construido: {len(docs)} documentos em {self.store_path}")

    def retrieve(self, query: str) -> list[dict]:
        """
        Busca os documentos mais relevantes para a pergunta informada.

        Retorna uma lista de dicionarios com:
        - page_content: texto do documento
        - metadata: source_id e title
        - score: similaridade (0 a 1, quanto maior mais relevante)
        """
        if self._store is None:
            self.load_or_build()
        results = self._store.similarity_search_with_score(query, k=self.top_k)
        docs = []
        for doc, dist in results:
            sim = max(0.0, 1.0 - dist / 2)
            if sim >= self.score_threshold:
                docs.append({
                    "page_content": doc.page_content,
                    "metadata":     doc.metadata,
                    "score":        round(sim, 4),
                })
        return docs


if __name__ == "__main__":
    """
    Modo de linha de comando: constroi o vector store a partir dos dados processados.
    
    Execute este script uma unica vez antes de usar o assistente:
        python -m src.assistant.retriever
    
    O processo demora alguns minutos. Apos concluido, o indice fica salvo
    em data/vectorstore/ e sera reutilizado automaticamente.
    """
    import os
    processed_dir = os.getenv("DATA_PROCESSED_DIR", "./data/processed")
    print(f"[retriever] Construindo vector store a partir de: {processed_dir}")
    r = MedicalRetriever()
    r._build(processed_dir)
    print("[retriever] Vector store criado com sucesso.")
