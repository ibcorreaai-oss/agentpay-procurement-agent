"""Ledger de pagamentos + log de auditoria no Firestore.

Substitui o better-sqlite3 do AgentPay original -- SQLite local nao
sobrevive num container stateless do Cloud Run (cada instancia nova
comeca com filesystem vazio). Firestore e o servico de infra Google
Cloud usado pra satisfazer o requisito da hackathon (junto com o proprio
Cloud Run).

Colecoes:
  payments   -- 1 doc por tentativa de pagamento (chave = idempotency key)
  audit_log  -- 1 doc por decisao do agente auditor (Gemini)
"""

from __future__ import annotations

import datetime as dt
from typing import Optional

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter


class LedgerClient:
    def __init__(self, project: Optional[str] = None, database: str = "agentpay-procurement"):
        # Banco Firestore NOMEADO (nao "(default)") -- descobri ao vivo que
        # passar (ou deixar implicito) o banco especial "(default)" quebra
        # a codificacao de URL do cliente gRPC nesta versao do SDK (erro
        # real reproduzido: "Invalid database id %28default%29"). Um banco
        # nomeado tambem isola os dados do hackathon do resto do projeto
        # GCP compartilhado (Pericia Medica).
        kwargs = {"project": project} if project else {}
        kwargs["database"] = database
        self._db = firestore.Client(**kwargs)
        self._payments = self._db.collection("payments")
        self._audit_log = self._db.collection("audit_log")

    # ---- payments ----

    def get_payment_by_key(self, key: str) -> Optional[dict]:
        doc = self._payments.document(key).get()
        return doc.to_dict() if doc.exists else None

    def record_payment_attempt(self, key: str, provider_id: str, amount_usdc: float, correlation_id: str) -> None:
        """Grava ANTES de tentar pagar -- se o processo morrer no meio do
        pagamento, o proximo run ve isso como PENDING_VERIFY em vez de
        nada (mesmo principio do fix de 23/08: gravar o mais cedo possivel)."""
        self._payments.document(key).set(
            {
                "key": key,
                "provider_id": provider_id,
                "amount_usdc": amount_usdc,
                "status": "PENDING_VERIFY",
                "correlation_id": correlation_id,
                "created_at": dt.datetime.now(dt.timezone.utc),
                "tx_hash": None,
            }
        )

    def mark_confirmed(self, key: str, tx_hash: str) -> None:
        self._payments.document(key).update(
            {
                "status": "CONFIRMED",
                "tx_hash": tx_hash,
                "confirmed_at": dt.datetime.now(dt.timezone.utc),
            }
        )

    def mark_failed(self, key: str, error: str) -> None:
        self._payments.document(key).update(
            {
                "status": "FAILED",
                "error": error,
                "failed_at": dt.datetime.now(dt.timezone.utc),
            }
        )

    def get_payments_since(self, since: dt.datetime) -> list[dict]:
        query = self._payments.where(filter=FieldFilter("created_at", ">=", since))
        return [doc.to_dict() for doc in query.stream()]

    def sum_confirmed_spend_since(self, since: dt.datetime) -> float:
        docs = self.get_payments_since(since)
        return sum(
            d["amount_usdc"]
            for d in docs
            if d.get("status") in ("CONFIRMED", "PENDING_VERIFY") and d.get("amount_usdc")
        )

    # ---- audit log ----

    def record_audit(self, correlation_id: str, decision: dict) -> None:
        self._audit_log.add(
            {
                "correlation_id": correlation_id,
                "ts": dt.datetime.now(dt.timezone.utc),
                **decision,
            }
        )
