"""Dedup/idempotencia generalizada por (provedor, valor, escopo de tempo).

O AgentPay original so precisava de "1 pagamento por dia" (uma unica
decisao diaria). Este agente pode decidir pagar MULTIPLAS vezes por
execucao (compara varios provedores, pode comprar de mais de um) -- a
growth idea "Transaction idempotency & double-spend detection" do
Evolution Review de 23/08 pedia exatamente essa generalizacao, nunca
aplicada la. Aqui vira o guard real.

Fica deliberadamente sem estado proprio: quem guarda "ja pago" e o
ledger do Firestore (fonte unica de verdade) -- este modulo so calcula a
chave e decide, dado o que o ledger ja tem.
"""

from __future__ import annotations

import hashlib


def payment_key(scope: str, provider_id: str, amount_usdc: float) -> str:
    """Chave deterministica: mesmo (escopo, provedor, valor) sempre gera a
    mesma chave. `scope` normalmente e a data (YYYY-MM-DD) ou um
    correlation_id de execucao, dependendo da granularidade desejada.
    """
    raw = f"{scope}|{provider_id}|{amount_usdc:.6f}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def is_duplicate(ledger_client, key: str) -> bool:
    """True se essa chave ja tem um pagamento CONFIRMED ou PENDING_VERIFY
    registrado no ledger (nao paga de novo em nenhum dos dois casos --
    PENDING_VERIFY vira job de reconciliacao, nao de novo pagamento)."""
    existing = ledger_client.get_payment_by_key(key)
    if existing is None:
        return False
    return existing.get("status") in ("CONFIRMED", "PENDING_VERIFY")
