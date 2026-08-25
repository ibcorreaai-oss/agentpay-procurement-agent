from unittest.mock import MagicMock, patch

from procurement_agent.tools.onchain_verify import RpcUnavailableError, VerificationMismatchError, VerifiedTransfer
from procurement_agent.tools.reconciliation import reconcile_pending_payments


def _fake_doc(doc_id, tx_hash):
    doc = MagicMock()
    doc.id = doc_id
    doc.to_dict.return_value = {"tx_hash": tx_hash, "status": "PENDING_VERIFY"}
    return doc


def _fake_ledger(docs):
    ledger = MagicMock()
    ledger._payments.where.return_value.stream.return_value = docs
    return ledger


def test_confirms_payment_when_verification_succeeds():
    ledger = _fake_ledger([_fake_doc("key1", "0xabc")])
    with patch("procurement_agent.tools.reconciliation.verify_transfer") as mock_verify:
        mock_verify.return_value = VerifiedTransfer(tx_hash="0xabc", from_address="0xA", to_address="0xB", value_wei=1000, block_number=1)
        results = reconcile_pending_payments(ledger, ["http://rpc"], "0xToken", "0xB")

    assert results[0].outcome == "confirmed"
    ledger.mark_confirmed.assert_called_once_with("key1", "0xabc")


def test_stays_pending_when_rpc_unavailable():
    ledger = _fake_ledger([_fake_doc("key2", "0xdef")])
    with patch("procurement_agent.tools.reconciliation.verify_transfer", side_effect=RpcUnavailableError("down")):
        results = reconcile_pending_payments(ledger, ["http://rpc"], "0xToken", "0xB")

    assert results[0].outcome == "still_pending"
    ledger.mark_confirmed.assert_not_called()
    ledger.mark_failed.assert_not_called()


def test_marks_failed_on_verification_mismatch():
    ledger = _fake_ledger([_fake_doc("key3", "0xghi")])
    with patch("procurement_agent.tools.reconciliation.verify_transfer", side_effect=VerificationMismatchError("bad")):
        results = reconcile_pending_payments(ledger, ["http://rpc"], "0xToken", "0xB")

    assert results[0].outcome == "mismatch"
    ledger.mark_failed.assert_called_once()


def test_skips_docs_without_tx_hash():
    ledger = _fake_ledger([_fake_doc("key4", None)])
    results = reconcile_pending_payments(ledger, ["http://rpc"], "0xToken", "0xB")
    assert results == []
