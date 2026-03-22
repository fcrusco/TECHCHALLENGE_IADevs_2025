"""
Explainability: rastreabilidade das fontes nas respostas do assistente.

Um dos requisitos do projeto e que o assistente indique a origem das informacoes
usadas em cada resposta. Este modulo resolve isso associando cada resposta
aos documentos MedQuAD que foram recuperados pelo RAG.

Como funciona:
1. O RAG recupera os top-K documentos mais similares a pergunta
2. Este modulo calcula o overlap (sobreposicao) entre as palavras do documento
   e as palavras da resposta gerada
3. Documentos com overlap acima de 10% sao considerados "usados" na resposta
4. A lista de fontes e incluida ao final da resposta para o medico saber
   quais documentos embasaram aquela informacao

A metrica de overlap e uma aproximacao simples. Em producao, tecnicas mais
sofisticadas (como attention weights do transformer) poderiam ser usadas,
mas escapam ao escopo deste projeto academico.

O nivel de confianca (confidence) e calculado como a media dos scores
de relevancia dos top-3 documentos atribuidos.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SourceAttribution:
    """Representa a atribuicao de uma resposta a um documento fonte."""
    source_id:       str
    title:           str
    excerpt:         str
    relevance_score: float


@dataclass
class ExplainedResponse:
    """Resposta com metadados de explainability."""
    answer:       str
    attributions: list[SourceAttribution] = field(default_factory=list)
    confidence:   float = 0.0

    def format_with_sources(self) -> str:
        """
        Formata a resposta adicionando a lista de fontes utilizadas ao final.
        Se nao houver fontes atribuidas, retorna apenas a resposta.
        """
        if not self.attributions:
            return self.answer
        notes = "\n\n**Fontes utilizadas:**\n"
        for i, a in enumerate(self.attributions, 1):
            notes += f"[{i}] {a.title} (relevancia: {a.relevance_score:.2f})\n"
        return self.answer + notes


class ExplainabilityModule:
    """Associa respostas geradas pelo LLM aos documentos MedQuAD utilizados."""

    def build_attribution(
        self,
        retrieved_docs: list[dict],
        response: str
    ) -> ExplainedResponse:
        """
        Constroi a atribuicao de fontes para uma resposta.

        Args:
            retrieved_docs: Documentos recuperados pelo RAG, cada um com
                            page_content, metadata e score.
            response: Texto da resposta gerada pelo LLM.

        Returns:
            ExplainedResponse com lista de fontes e nivel de confianca.
        """
        attributions: list[SourceAttribution] = []

        for doc in retrieved_docs:
            meta    = doc.get("metadata", {})
            content = doc.get("page_content", "")
            score   = doc.get("score", 0.0)

            # Verifica se o documento realmente contribuiu para a resposta
            # usando sobreposicao de vocabulario (Jaccard simplificado)
            if self._overlap(content, response) < 0.1:
                continue

            attributions.append(SourceAttribution(
                source_id=meta.get("source_id", "unknown"),
                title=meta.get("title", "MedQuAD"),
                excerpt=content[:200] + "..." if len(content) > 200 else content,
                relevance_score=score,
            ))

        # Ordena por relevancia decrescente
        attributions.sort(key=lambda a: a.relevance_score, reverse=True)

        # Calcula confianca como media dos scores dos top-3 documentos
        top3 = attributions[:3]
        confidence = (
            min(sum(a.relevance_score for a in top3) / max(len(top3), 1), 1.0)
            if top3 else 0.3
        )

        return ExplainedResponse(
            answer=response,
            attributions=attributions,
            confidence=round(confidence, 3)
        )

    @staticmethod
    def _overlap(doc: str, response: str) -> float:
        """
        Calcula a sobreposicao de vocabulario entre o documento e a resposta.
        
        Remove palavras de parada (stop words) comuns em portugues e ingles
        antes de calcular, para evitar falsos positivos com palavras muito comuns.
        
        Retorna valor entre 0 (sem sobreposicao) e 1 (sobreposicao total).
        """
        stop = {"de", "da", "do", "e", "a", "o", "em", "que",
                "the", "of", "and", "is", "in", "to", "for"}
        d = {w.lower() for w in re.findall(r"\b\w+\b", doc)      if w.lower() not in stop}
        r = {w.lower() for w in re.findall(r"\b\w+\b", response) if w.lower() not in stop}
        return len(d & r) / len(d | r) if d and r else 0.0
