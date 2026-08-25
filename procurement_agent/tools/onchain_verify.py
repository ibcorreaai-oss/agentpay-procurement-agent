"""Verificacao on-chain independente de um pagamento USDC (ERC-20 Transfer).

Porta pra Python o padrao ja validado em producao no AgentPay original
(parsing do evento Transfer via viem, nunca confiar no cliente) + o fix
de 23/08 (idempotencia/RPC) + a growth idea de retry com backoff em 5xx
(nunca aplicada la, aplicada aqui pela primeira vez).

Taxonomia de erro (mesma do fix de 23/08, cada uma tratada diferente
pelo chamador):
  - RpcUnavailableError: RPC caiu (5xx/timeout) -- pagamento pode ja ter
    sido confirmado pela Circle, so a VERIFICACAO falhou. Nunca reenviar
    pagamento por causa disso -- marcar como pendente e reconciliar depois.
  - VerificationMismatchError: RPC respondeu, mas o recibo nao bate com o
    esperado (valor/endereco errado, ou status revertido). Isso sim e grave.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from web3 import Web3
from web3.exceptions import Web3RPCError

from procurement_agent.logging_setup import get_logger, log_event

logger = get_logger(__name__)

TRANSFER_TOPIC = Web3.keccak(text="Transfer(address,address,uint256)").hex()
if not TRANSFER_TOPIC.startswith("0x"):
    TRANSFER_TOPIC = "0x" + TRANSFER_TOPIC


class RpcUnavailableError(Exception):
    """RPC transitoriamente indisponivel -- nao prova que o pagamento falhou."""


class VerificationMismatchError(Exception):
    """RPC respondeu, mas o recibo nao confirma o pagamento esperado."""


@dataclass
class VerifiedTransfer:
    tx_hash: str
    from_address: str
    to_address: str
    value_wei: int
    block_number: int


def _topic_to_address(topic: bytes) -> str:
    return Web3.to_checksum_address("0x" + topic.hex()[-40:])


def verify_transfer(
    tx_hash: str,
    rpc_urls: list[str],
    token_address: str,
    expected_to: str,
    max_retries_per_rpc: int = 3,
    backoff_base_s: float = 2.0,
) -> VerifiedTransfer:
    """Confirma no-chain que `tx_hash` moveu USDC (`token_address`) pra
    `expected_to`. Tenta cada RPC de `rpc_urls` em ordem, com retry+backoff
    exponencial (2s/4s/8s) em erro transiente antes de cair pro proximo RPC.
    So levanta VerificationMismatchError depois de um RPC responder de
    verdade -- nunca antes disso.
    """
    token_address = Web3.to_checksum_address(token_address)
    expected_to = Web3.to_checksum_address(expected_to)

    last_transient_error: Optional[Exception] = None

    for rpc_url in rpc_urls:
        w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 15}))
        for attempt in range(1, max_retries_per_rpc + 1):
            try:
                receipt = w3.eth.get_transaction_receipt(tx_hash)
                if receipt is None:
                    raise RpcUnavailableError(f"receipt ainda nao disponivel em {rpc_url}")

                if receipt.status != 1:
                    raise VerificationMismatchError(
                        f"tx {tx_hash} revertida on-chain (status={receipt.status})"
                    )

                transfer_logs = [
                    lg
                    for lg in receipt.logs
                    if lg.address == token_address
                    and len(lg.topics) == 3
                    and lg.topics[0].hex().lower().replace("0x", "") == TRANSFER_TOPIC.lower().replace("0x", "")
                ]
                if not transfer_logs:
                    raise VerificationMismatchError(
                        f"tx {tx_hash} confirmada, mas nenhum log Transfer do token {token_address} encontrado"
                    )

                match = None
                for lg in transfer_logs:
                    to_addr = _topic_to_address(lg.topics[2])
                    if to_addr == expected_to:
                        match = lg
                        break

                if match is None:
                    raise VerificationMismatchError(
                        f"tx {tx_hash} tem Transfer do token certo, mas nenhum pro destinatario esperado {expected_to}"
                    )

                from_addr = _topic_to_address(match.topics[1])
                value_wei = int.from_bytes(match.data, byteorder="big")

                log_event(
                    logger,
                    20,
                    "on-chain transfer verificado",
                    tx_hash=tx_hash,
                    from_address=from_addr,
                    to_address=expected_to,
                    value_wei=value_wei,
                    rpc_url=rpc_url,
                )

                return VerifiedTransfer(
                    tx_hash=tx_hash,
                    from_address=from_addr,
                    to_address=expected_to,
                    value_wei=value_wei,
                    block_number=receipt.blockNumber,
                )

            except VerificationMismatchError:
                raise  # definitivo, nao adianta tentar de novo nem trocar de RPC
            except (Web3RPCError, ConnectionError, TimeoutError, RpcUnavailableError) as exc:
                last_transient_error = exc
                log_event(
                    logger,
                    30,
                    "RPC indisponivel, tentando de novo",
                    tx_hash=tx_hash,
                    rpc_url=rpc_url,
                    attempt=attempt,
                    error=str(exc),
                )
                if attempt < max_retries_per_rpc:
                    time.sleep(backoff_base_s * (2 ** (attempt - 1)))

    raise RpcUnavailableError(
        f"todos os RPCs falharam pra tx {tx_hash} depois de retry: {last_transient_error}"
    )
