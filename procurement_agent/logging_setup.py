"""Logging estruturado (JSON) com correlation ID por execução.

Cloud Logging no Cloud Run le stdout como texto simples por padrao, mas
reconhece automaticamente linhas JSON com um campo "severity" e as trata
como entradas estruturadas (pesquisaveis, filtraveis por severidade) --
isso substitui o padrao antigo de print()/Telegram ad-hoc por telemetria
de verdade, sem precisar de nenhuma infra extra.

Implementa a growth idea "Structured logging com correlation IDs" do
Evolution Review de 23/08 do AgentPay, nunca aplicada (tier N3, so
proposta) -- ver engineering_memory.jsonl do AgentPay original.
"""

from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


def new_correlation_id() -> str:
    """Gera e registra um novo correlation ID pro contexto de execucao atual."""
    cid = uuid.uuid4().hex[:16]
    _correlation_id.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    """Registra um correlation ID ja existente (ex.: o invocation_id do
    ADK) pro contexto de execucao atual, em vez de gerar um novo."""
    _correlation_id.set(cid)


def get_correlation_id() -> str:
    return _correlation_id.get()


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "correlation_id": get_correlation_id(),
            "ts": time.time(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        extra = getattr(record, "extra_fields", None)
        if extra:
            payload.update(extra)
        return json.dumps(payload, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setFormatter(_JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def log_event(logger: logging.Logger, level: int, message: str, **fields) -> None:
    """Log com campos estruturados extras (span/duracao/tx_hash/etc)."""
    logger.log(level, message, extra={"extra_fields": fields})
