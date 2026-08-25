"""Sem dependencias -- so pra `ensure_0x_prefix` ser testavel isolado,
sem puxar fastapi/web3/x402 (ver main.py pra onde e usado e por que)."""


def ensure_0x_prefix(tx_hash: str) -> str:
    """`FacilitatorWeb3Signer.write_contract`/`send_transaction` do SDK
    x402 oficial fazem `tx_hash.hex()` e devolvem sem o prefixo "0x" --
    na versao instalada do pacote `hexbytes` (2.0.0), `.hex()` segue o
    `bytes.hex()` padrao do Python (nunca inclui "0x"), so `str(hexbytes)`
    inclui. O settlement rejeitava com "signer returned an invalid
    transaction hash", achado tentando um pagamento real de verdade."""
    return tx_hash if tx_hash.startswith("0x") else "0x" + tx_hash
