"""Reconcilia pagamentos que ficaram PENDING_VERIFY com tx_hash gravado
(o facilitator confirmou, mas a nossa verificacao independente falhou
por RPC instavel na hora). Mesmo padrao ja usado no AgentPay original
pro incidente de 22/08 -- generalizado aqui pra qualquer provedor.

Nao roda sozinho automaticamente (sem timer/cron) -- e uma ferramenta
de manutencao, chamada manualmente ou por um job futuro."""

from __future__ import annotations

from dataclasses import dataclass

from google.cloud.firestore_v1.base_query import FieldFilter

from procurement_agent.ledger.firestore_client import LedgerClient
from procurement_agent.logging_setup import get_logger, log_event
from procurement_agent.tools.onchain_verify import (
    RpcUnavailableError,
    VerificationMismatchError,
    verify_transfer,
)

logger = get_logger(__name__)


@dataclass
class ReconciliationResult:
    key: str
    tx_hash: str
    outcome: str  # "confirmed" | "still_pending" | "mismatch"


def reconcile_pending_payments(
    ledger: LedgerClient,
    rpc_urls: list[str],
    token_address: str,
    expected_to: str,
) -> list[ReconciliationResult]:
    """Busca todos os docs PENDING_VERIFY com tx_hash preenchido e tenta
    verificar de novo. O ledger nao guarda a network por pagamento hoje,
    entao `rpc_urls` deve cobrir todas as redes usadas pelos provedores
    configurados (ex.: RPCs de testnet + mainnet combinados)."""
    results: list[ReconciliationResult] = []
    for doc in ledger._payments.where(filter=FieldFilter("status", "==", "PENDING_VERIFY")).stream():
        data = doc.to_dict()
        tx_hash = data.get("tx_hash")
        if not tx_hash:
            continue

        try:
            verified = verify_transfer(
                tx_hash=tx_hash, rpc_urls=rpc_urls, token_address=token_address, expected_to=expected_to
            )
            ledger.mark_confirmed(doc.id, verified.tx_hash)
            log_event(logger, 20, "reconciliado com sucesso", key=doc.id, tx_hash=tx_hash)
            results.append(ReconciliationResult(key=doc.id, tx_hash=tx_hash, outcome="confirmed"))
        except RpcUnavailableError:
            results.append(ReconciliationResult(key=doc.id, tx_hash=tx_hash, outcome="still_pending"))
        except VerificationMismatchError as exc:
            ledger.mark_failed(doc.id, f"reconciliacao: verificacao nao bateu: {exc}")
            results.append(ReconciliationResult(key=doc.id, tx_hash=tx_hash, outcome="mismatch"))

    return results
