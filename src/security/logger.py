"""
Logger de auditoria para todas as interacoes do assistente.

Registra cada interacao em logs/audit.jsonl no formato JSONL (uma linha por registro).
O arquivo pode ser analisado facilmente com qualquer ferramenta de processamento JSON.

Campos registrados em cada interacao:
- interaction_id: UUID unico para rastreamento
- timestamp: data e hora UTC da interacao
- user_id: identificador do medico que fez a pergunta
- query_hash: hash SHA256 da pergunta (primeiros 16 caracteres)
  Armazena o hash em vez do texto original por privacidade (LGPD)
- response_length: tamanho da resposta em caracteres
- sources_used: lista de IDs dos documentos MedQuAD utilizados
- guardrail_flags: lista de alertas disparados pelos guardrails
- blocked: booleano indicando se a interacao foi bloqueada

Este log atende ao requisito de auditoria e rastreabilidade exigido
em sistemas de saude que utilizam IA (conformidade LGPD e CFM).
"""
from __future__ import annotations
import json
import uuid
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import structlog
from src.utils.config import Config

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)
_log = structlog.get_logger()


class AuditLogger:
    """
    Registra interacoes do assistente medico para auditoria.
    
    O arquivo de log e criado automaticamente em logs/audit.jsonl.
    Cada chamada a log_interaction adiciona uma nova linha ao arquivo.
    """

    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir    = log_dir or Config.LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.audit_file = self.log_dir / "audit.jsonl"

    def log_interaction(
        self,
        user_id: str,
        query: str,
        response: str,
        sources: list[str],
        guardrail_flags: list[str],
        blocked: bool = False,
        extra: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Registra uma interacao completa no log de auditoria.

        Args:
            user_id: Identificador do medico.
            query: Pergunta original (sera hasheada antes de salvar).
            response: Resposta gerada pelo assistente.
            sources: Lista de IDs dos documentos MedQuAD utilizados.
            guardrail_flags: Lista de alertas disparados pelos guardrails.
            blocked: True se a interacao foi bloqueada pelos guardrails.
            extra: Campos adicionais opcionais.

        Returns:
            interaction_id: UUID unico para rastreamento desta interacao.
        """
        interaction_id = str(uuid.uuid4())
        record = {
            "interaction_id":  interaction_id,
            "timestamp":       datetime.now(timezone.utc).isoformat(),
            "user_id":         user_id,
            "query_hash":      hashlib.sha256(query.encode()).hexdigest()[:16],
            "response_length": len(response),
            "sources_used":    sources,
            "guardrail_flags": guardrail_flags,
            "blocked":         blocked,
            **(extra or {}),
        }
        with self.audit_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        _log.info("interaction_logged",
                  interaction_id=interaction_id,
                  user_id=user_id,
                  blocked=blocked)
        return interaction_id

    def log_error(self, user_id: str, error: str, context: Optional[dict] = None) -> None:
        """
        Registra um erro interno no log de auditoria.

        Args:
            user_id: Identificador do medico que estava usando o sistema.
            error: Mensagem de erro.
            context: Informacoes adicionais sobre o contexto do erro.
        """
        record = {
            "event":     "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id":   user_id,
            "error":     error,
            **(context or {}),
        }
        with self.audit_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        _log.error("assistant_error", user_id=user_id, error=error[:200])