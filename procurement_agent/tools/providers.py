"""Handshake x402 (cotacao) + pagamento de verdade contra provedores de
dados. Usa o SDK oficial `x402` (mesmo que o scrape402 e outros
provedores reais esperam) em vez de reimplementar o protocolo na mao --
decisao tomada depois de checar o codigo-fonte oficial (coinbase/x402)
e ver que o esquema "exact" exige assinatura EIP-712 (EIP-3009
transferWithAuthorization), nao um transfer simples.

Fluxo de 2 fases, deliberado: `get_quote()` NUNCA paga (so cotacao, GET
simples) -- o pagamento so acontece em `pay_and_fetch()`, chamado
depois que o orcamento (budget_guard) E o auditor (Gemini) aprovarem.
Isso evita que o SDK pague automaticamente no primeiro 402 (comportamento
padrao dele), que pularia nosso gate de aprovacao.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import requests
import x402
from x402 import x402ClientSync
from x402.http.clients.requests import x402HTTPAdapter
from x402.http.constants import PAYMENT_REQUIRED_HEADER, PAYMENT_RESPONSE_HEADER, X_PAYMENT_RESPONSE_HEADER
from x402.http.utils import decode_payment_required_header, decode_payment_response_header
from x402.mechanisms.evm.exact.register import register_exact_evm_client

from procurement_agent.logging_setup import get_logger, log_event

logger = get_logger(__name__)


@dataclass(frozen=True)
class DataProvider:
    provider_id: str
    resource_url: str
    method: str = "GET"
    request_kwargs: dict[str, Any] = field(default_factory=dict)


@dataclass
class Quote:
    provider_id: str
    resource_url: str
    price_usdc: float
    max_amount_required_atomic: str
    pay_to: str
    asset: str
    network: str
    scheme: str
    description: str
    method: str = "GET"
    request_kwargs: dict[str, Any] = field(default_factory=dict)


def _to_usdc(atomic_amount: str, decimals: int = 6) -> float:
    return int(atomic_amount) / (10**decimals)


def _requirement_amount_atomic(req: Any) -> str:
    """V1 chama o campo `max_amount_required`, V2 chama so `amount` --
    o SDK expõe o objeto ja tipado por versao, entao lemos o que existir."""
    if hasattr(req, "max_amount_required"):
        return req.max_amount_required
    return req.amount


def _description(parsed: Any, req: Any) -> str:
    """V1 tem `description` na propria PaymentRequirements; V2 move pra
    `resource.description` no objeto PaymentRequired de fora."""
    if hasattr(req, "description"):
        return req.description
    resource = getattr(parsed, "resource", None)
    return getattr(resource, "description", "") if resource else ""


def get_quote(provider: DataProvider, timeout_s: float = 10.0) -> Optional[Quote]:
    """So cotacao -- NUNCA paga. Retorna None se o provedor nao devolveu
    um 402 valido (fora do ar, endpoint gratis, schema quebrado, etc)."""
    try:
        resp = requests.request(
            provider.method, provider.resource_url, timeout=timeout_s, **provider.request_kwargs
        )
    except requests.RequestException as exc:
        log_event(logger, 30, "provedor inacessivel na cotacao", provider_id=provider.provider_id, error=str(exc))
        return None

    if resp.status_code != 402:
        log_event(
            logger, 30, "provedor nao pediu pagamento (status inesperado)",
            provider_id=provider.provider_id, status=resp.status_code,
        )
        return None

    # V2 pode mandar a cotacao no header PAYMENT-REQUIRED (nosso proprio
    # servidor faz isso) OU no corpo da resposta (scrape402 faz isso) --
    # o SDK oficial trata os dois casos no lado cliente, entao replicamos
    # aqui: tenta o header primeiro, cai pro body se nao tiver.
    header_value = resp.headers.get(PAYMENT_REQUIRED_HEADER)
    try:
        if header_value:
            parsed = decode_payment_required_header(header_value)
        else:
            parsed = x402.parse_payment_required(resp.json())
    except Exception as exc:  # payload malformado de um provedor de terceiros
        log_event(logger, 30, "402 nao seguiu o schema x402", provider_id=provider.provider_id, error=str(exc))
        return None

    if not parsed.accepts:
        return None

    req = parsed.accepts[0]
    amount_atomic = _requirement_amount_atomic(req)
    return Quote(
        provider_id=provider.provider_id,
        resource_url=provider.resource_url,
        price_usdc=_to_usdc(amount_atomic),
        max_amount_required_atomic=amount_atomic,
        pay_to=req.pay_to,
        asset=req.asset,
        network=req.network,
        scheme=req.scheme,
        description=_description(parsed, req),
        method=provider.method,
        request_kwargs=provider.request_kwargs,
    )


@dataclass
class PaidFetchResult:
    data: dict
    tx_hash: Optional[str]
    settlement_success: Optional[bool]


def pay_and_fetch(quote: Quote, signer) -> PaidFetchResult:
    """Paga de verdade (assinatura EIP-712 via `signer`, ex.: CircleEvmSigner)
    e retorna o corpo da resposta ja liberada + o hash da transacao de
    settlement (pra verificacao on-chain INDEPENDENTE depois -- nunca
    confiamos so na palavra do facilitator/SDK de que o pagamento foi
    liquidado, mesmo principio "nunca confia no cliente" do AgentPay
    original). So chamar depois do budget guard + auditoria aprovarem --
    isso EXECUTA o pagamento."""
    client = x402ClientSync()
    register_exact_evm_client(client, signer, networks=[quote.network])

    session = requests.Session()
    session.mount("https://", x402HTTPAdapter(client))
    session.mount("http://", x402HTTPAdapter(client))

    resp = session.request(quote.method, quote.resource_url, timeout=30, **quote.request_kwargs)
    resp.raise_for_status()

    settle_header = resp.headers.get(PAYMENT_RESPONSE_HEADER) or resp.headers.get(X_PAYMENT_RESPONSE_HEADER)
    tx_hash = None
    settlement_success = None
    if settle_header:
        try:
            settle = decode_payment_response_header(settle_header)
            tx_hash = settle.transaction
            settlement_success = settle.success
        except Exception as exc:
            log_event(logger, 30, "nao consegui decodificar o header de settlement", error=str(exc))

    log_event(
        logger, 20, "pagamento x402 concluido e dado recebido",
        provider_id=quote.provider_id, price_usdc=quote.price_usdc, tx_hash=tx_hash,
    )

    return PaidFetchResult(data=resp.json(), tx_hash=tx_hash, settlement_success=settlement_success)
