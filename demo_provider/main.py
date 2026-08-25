"""Provedor de dados x402 proprio, self-hosted, testnet (Base Sepolia).

Por que existe: o unico provedor de terceiros real que achamos
(scrape402.xyz) so aceita Base MAINNET -- pagar nele de verdade exigiria
comprar USDC real, o que nao e algo que um agente deva fazer sozinho
(nem eu, nem o dinheiro do Igor deveria ser gasto so pra validar o
fluxo). Este servidor usa o MESMO protocolo x402 oficial (SDK
`x402`, esquema "exact"/EIP-3009) contra a testnet Base Sepolia --
zero custo real, mesmo protocolo, mesma seguranca, so que o
"facilitator" que liquida a transacao somos nos mesmos (uma wallet
EOA de testnet, gas patrocinado por faucet, nao a Circle).

Dado vendido: preco de gas ao vivo da rede Base Sepolia (mesmo dado que
o AgentPay original vendia -- `/api/paid-data` la, `/gas-price` aqui).
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from web3 import Web3
from x402 import x402Facilitator, x402ResourceServer
from x402.http.middleware.fastapi import payment_middleware
from x402.mechanisms.evm.exact import register_exact_evm_facilitator, register_exact_evm_server
from x402.mechanisms.evm.signers import FacilitatorWeb3Signer

NETWORK = "eip155:84532"  # Base Sepolia
RPC_URL = "https://sepolia.base.org"
PRICE = "$0.001"

FACILITATOR_KEY_PATH = os.path.join(os.path.dirname(__file__), "..", "procurement_agent", ".facilitator_key_KEEP_SAFE")


def _load_facilitator_key() -> str:
    env_key = os.environ.get("FACILITATOR_PRIVATE_KEY")
    if env_key:
        return env_key
    with open(FACILITATOR_KEY_PATH, encoding="utf-8") as f:
        return f.read().strip()


try:
    from demo_provider._hex_prefix import ensure_0x_prefix  # noqa: E402
except ImportError:
    from _hex_prefix import ensure_0x_prefix  # noqa: E402  (rodando como modulo flat no container)


class _FixedFacilitatorWeb3Signer(FacilitatorWeb3Signer):
    """Aplica `ensure_0x_prefix` no retorno de write_contract/
    send_transaction, sem editar a lib de terceiro."""

    def write_contract(self, *args, **kwargs) -> str:
        return ensure_0x_prefix(super().write_contract(*args, **kwargs))

    def send_transaction(self, *args, **kwargs) -> str:
        return ensure_0x_prefix(super().send_transaction(*args, **kwargs))


_signer = _FixedFacilitatorWeb3Signer(private_key=_load_facilitator_key(), rpc_url=RPC_URL)
PAY_TO_ADDRESS = _signer.address

_facilitator = x402Facilitator()
register_exact_evm_facilitator(_facilitator, _signer, networks=NETWORK)

_server = x402ResourceServer(_facilitator)
register_exact_evm_server(_server, networks=NETWORK)

ROUTES = {
    "POST /gas-price": {
        "accepts": {
            "scheme": "exact",
            "payTo": PAY_TO_ADDRESS,
            "price": PRICE,
            "network": NETWORK,
        }
    }
}

app = FastAPI(title="Demo x402 Data Provider (Base Sepolia)")


@app.middleware("http")
async def _x402_middleware(request, call_next):
    return await payment_middleware(ROUTES, _server)(request, call_next)


@app.get("/health")
async def health():
    return {"status": "ok", "pay_to": PAY_TO_ADDRESS, "network": NETWORK}


@app.post("/gas-price")
async def gas_price():
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    gwei = w3.from_wei(w3.eth.gas_price, "gwei")
    return {
        "network": "Base Sepolia",
        "gas_price_gwei": float(gwei),
        "source": "eth_gasPrice via sepolia.base.org",
    }
