from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from web3 import Web3

from procurement_agent.tools import onchain_verify as ov


TOKEN = Web3.to_checksum_address("0x036CbD53842c5426634e7929541eC2318f3dCF7e")
AGENT = Web3.to_checksum_address("0x" + "11" * 20)
PROVIDER = Web3.to_checksum_address("0x" + "22" * 20)


def _topic_from_address(addr: str) -> bytes:
    return bytes.fromhex("0" * 24 + addr[2:].lower())


def _make_receipt(status=1, value_wei=10000, to_addr=PROVIDER, token=TOKEN, include_log=True):
    topics = [
        bytes.fromhex(ov.TRANSFER_TOPIC[2:]),
        _topic_from_address(AGENT),
        _topic_from_address(to_addr),
    ]
    log = SimpleNamespace(address=token, topics=topics, data=value_wei.to_bytes(32, "big"))
    return SimpleNamespace(status=status, logs=[log] if include_log else [], blockNumber=12345)


def _patch_w3(monkeypatch, receipt_or_exc):
    fake_eth = MagicMock()
    if isinstance(receipt_or_exc, Exception):
        fake_eth.get_transaction_receipt.side_effect = receipt_or_exc
    else:
        fake_eth.get_transaction_receipt.return_value = receipt_or_exc
    fake_w3_instance = SimpleNamespace(eth=fake_eth)

    fake_web3_cls = MagicMock()
    fake_web3_cls.return_value = fake_w3_instance
    fake_web3_cls.HTTPProvider.return_value = MagicMock()
    fake_web3_cls.to_checksum_address = staticmethod(Web3.to_checksum_address)
    fake_web3_cls.keccak = staticmethod(Web3.keccak)

    monkeypatch.setattr(ov, "Web3", fake_web3_cls)


def test_verify_success(monkeypatch):
    _patch_w3(monkeypatch, _make_receipt())
    result = ov.verify_transfer("0xabc", ["http://fake-rpc"], TOKEN, PROVIDER)
    assert result.value_wei == 10000
    assert result.to_address == PROVIDER
    assert result.from_address == AGENT


def test_verify_reverted_tx_raises_mismatch(monkeypatch):
    _patch_w3(monkeypatch, _make_receipt(status=0))
    with pytest.raises(ov.VerificationMismatchError):
        ov.verify_transfer("0xabc", ["http://fake-rpc"], TOKEN, PROVIDER)


def test_verify_wrong_recipient_raises_mismatch(monkeypatch):
    other = Web3.to_checksum_address("0x" + "33" * 20)
    _patch_w3(monkeypatch, _make_receipt(to_addr=other))
    with pytest.raises(ov.VerificationMismatchError):
        ov.verify_transfer("0xabc", ["http://fake-rpc"], TOKEN, PROVIDER)


def test_verify_no_transfer_log_raises_mismatch(monkeypatch):
    _patch_w3(monkeypatch, _make_receipt(include_log=False))
    with pytest.raises(ov.VerificationMismatchError):
        ov.verify_transfer("0xabc", ["http://fake-rpc"], TOKEN, PROVIDER)


def test_rpc_down_falls_through_all_urls_and_raises_unavailable(monkeypatch):
    _patch_w3(monkeypatch, ConnectionError("boom"))
    with pytest.raises(ov.RpcUnavailableError):
        ov.verify_transfer(
            "0xabc", ["http://rpc1", "http://rpc2"], TOKEN, PROVIDER,
            max_retries_per_rpc=1, backoff_base_s=0,
        )
