"""
Guardrails: limites de atuacao do assistente medico.

Define o que o assistente pode e nao pode fazer, garantindo que ele
atue como ferramenta de apoio ao medico, nunca como substituto.

Dois tipos de restricoes:

1. Bloqueios absolutos (BLOCKED_PATTERNS):
   - Emissao de prescricoes diretas
   - Diagnosticos definitivos
   - Alteracao de prontuarios
   Se detectados na pergunta ou resposta, a interacao e completamente bloqueada.

2. Avisos de validacao (VALIDATION_PATTERNS):
   - Temas como dosagem, cirurgia, internacao, quimioterapia, anestesia
   A resposta e permitida, mas um aviso e adicionado indicando que
   o tema requer validacao por medico responsavel.

Como funciona na pratica:
- O pipeline chama check() antes de processar a pergunta (verifica entrada)
- E chama novamente apos gerar a resposta (verifica saida)
- Se bloqueado: retorna erro e registra no log com blocked=True
- Se apenas aviso: adiciona nota de seguranca ao final da resposta
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GuardrailResult:
    """Resultado da verificacao de guardrails."""
    allowed: bool
    warnings: list[str] = field(default_factory=list)
    blocked_reason: Optional[str] = None
    requires_human_validation: bool = False


# Padroes que causam bloqueio completo da interacao
BLOCKED_PATTERNS = [
    (re.compile(r"\bprescrev[ae]\b", re.I),              "Emissao de prescricao nao e permitida"),
    (re.compile(r"\bdiagnostico definitivo\b", re.I),    "Diagnostico definitivo requer medico"),
    (re.compile(r"\balter[ae]\s+prontu[ai]rio\b", re.I), "Alteracao de prontuario nao permitida"),
]

# Padroes que geram aviso mas nao bloqueiam
VALIDATION_PATTERNS = [
    re.compile(r"\bdosagem\b",         re.I),
    re.compile(r"\bcirurgia\b",        re.I),
    re.compile(r"\binterna(?:cao|cão|ção|ção)\b", re.I),
    re.compile(r"\bquimioterapia\b",   re.I),
    re.compile(r"\banestesia\b",       re.I),
]


class Guardrails:
    """Aplica as restricoes de seguranca nas perguntas e respostas."""

    def check(self, query: str, response: str = "") -> GuardrailResult:
        """
        Verifica se a pergunta ou resposta viola os limites de atuacao.

        Args:
            query: Pergunta do medico.
            response: Resposta gerada pelo LLM (opcional, para verificacao pos-geracao).

        Returns:
            GuardrailResult com allowed=False se bloqueado, ou warnings se apenas aviso.
        """
        combined = f"{query} {response}"

        for pattern, reason in BLOCKED_PATTERNS:
            if pattern.search(combined):
                return GuardrailResult(
                    allowed=False,
                    blocked_reason=reason,
                    warnings=[reason]
                )

        requires_validation = any(p.search(combined) for p in VALIDATION_PATTERNS)
        warnings = (
            ["ATENCAO: Este tema requer validacao por medico responsavel antes de qualquer acao clinica."]
            if requires_validation else []
        )
        return GuardrailResult(
            allowed=True,
            warnings=warnings,
            requires_human_validation=requires_validation,
        )

    def safety_note(self, result: GuardrailResult) -> str:
        """
        Gera uma nota de seguranca para adicionar ao final da resposta.
        Retorna string vazia se nao houver avisos.
        """
        if not result.warnings:
            return ""
        return "\n\n---\n" + "\n".join(result.warnings) + "\n---"