"""Cria a wallet set + wallet do agente na Circle Developer-Controlled
Wallets, uma vez so, depois que CIRCLE_API_KEY e CIRCLE_ENTITY_SECRET ja
existirem (ver docs/MANUAL_SETUP_CHECKLIST.md).

Uso:
    export CIRCLE_API_KEY=...
    export CIRCLE_ENTITY_SECRET=...
    python scripts/setup_circle_wallet.py

Imprime CIRCLE_WALLET_ID e CIRCLE_WALLET_ADDRESS pra colar no .env.
Idempotente o suficiente pra rodar de novo sem duplicar (usa
idempotency_key derivada, mas o mais seguro e so rodar 1 vez e guardar
o resultado).
"""

from __future__ import annotations

import os
import sys
import uuid

from circle.web3 import developer_controlled_wallets as dcw
from circle.web3 import utils as circle_utils

BASE_SEPOLIA = "BASE-SEPOLIA"  # comecar em testnet


def main() -> int:
    api_key = os.environ.get("CIRCLE_API_KEY")
    entity_secret = os.environ.get("CIRCLE_ENTITY_SECRET")
    if not api_key or not entity_secret:
        print("Defina CIRCLE_API_KEY e CIRCLE_ENTITY_SECRET antes de rodar.", file=sys.stderr)
        return 1

    api_client = circle_utils.init_developer_controlled_wallets_client(
        api_key=api_key, entity_secret=entity_secret
    )
    wallet_sets_api = dcw.WalletSetsApi(api_client)
    wallets_api = dcw.WalletsApi(api_client)

    print("Criando wallet set...")
    ciphertext = circle_utils.generate_entity_secret_ciphertext(api_key, entity_secret)
    wallet_set_resp = wallet_sets_api.create_wallet_set(
        dcw.CreateWalletSetRequest(
            entity_secret_ciphertext=ciphertext,
            idempotency_key=str(uuid.uuid4()),
            name="agentpay-procurement-agent",
        )
    )
    wallet_set_id = wallet_set_resp.data.wallet_set.id
    print(f"wallet_set_id = {wallet_set_id}")

    print("Criando wallet do agente (Base Sepolia, testnet)...")
    ciphertext2 = circle_utils.generate_entity_secret_ciphertext(api_key, entity_secret)
    wallet_resp = wallets_api.create_wallet(
        dcw.CreateWalletRequest(
            entity_secret_ciphertext=ciphertext2,
            idempotency_key=str(uuid.uuid4()),
            wallet_set_id=wallet_set_id,
            blockchains=[BASE_SEPOLIA],
            account_type="EOA",
            count=1,
        )
    )
    wallet = wallet_resp.data.wallets[0]

    print()
    print("=" * 60)
    print("Cole isso no .env (local e no Cloud Run):")
    print(f"CIRCLE_WALLET_ID={wallet.id}")
    print(f"CIRCLE_WALLET_ADDRESS={wallet.address}")
    print("=" * 60)
    print()
    print(f"Financie via faucet.circle.com (Base Sepolia, USDC) pro endereco: {wallet.address}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
