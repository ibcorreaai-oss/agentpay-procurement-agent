"""Testa o workaround do bug real do SDK x402 (write_contract/
send_transaction devolvendo tx_hash sem prefixo "0x", achado tentando
um pagamento real de verdade -- ver demo_provider/main.py). So testa a
funcao pura, sem instanciar nada do FastAPI/web3/Circle."""

import importlib.util
import os

_SPEC = importlib.util.spec_from_file_location(
    "_ensure_0x_prefix_module",
    os.path.join(os.path.dirname(__file__), "..", "demo_provider", "_hex_prefix.py"),
)


def _load_ensure_0x_prefix():
    import sys

    module_path = os.path.join(os.path.dirname(__file__), "..", "demo_provider", "_hex_prefix.py")
    spec = importlib.util.spec_from_file_location("_hex_prefix", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ensure_0x_prefix


ensure_0x_prefix = _load_ensure_0x_prefix()


def test_adds_missing_0x_prefix():
    assert ensure_0x_prefix("ab" * 32) == "0x" + "ab" * 32


def test_keeps_existing_0x_prefix():
    assert ensure_0x_prefix("0x" + "cd" * 32) == "0x" + "cd" * 32
