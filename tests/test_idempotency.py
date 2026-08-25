from procurement_agent.tools.idempotency import payment_key, is_duplicate


class FakeLedger:
    def __init__(self, existing: dict | None = None):
        self._existing = existing or {}

    def get_payment_by_key(self, key):
        return self._existing.get(key)


def test_key_is_deterministic():
    k1 = payment_key("2026-08-25", "scrape402", 0.01)
    k2 = payment_key("2026-08-25", "scrape402", 0.01)
    assert k1 == k2


def test_key_differs_by_provider():
    k1 = payment_key("2026-08-25", "scrape402", 0.01)
    k2 = payment_key("2026-08-25", "demo_provider", 0.01)
    assert k1 != k2


def test_key_differs_by_amount():
    k1 = payment_key("2026-08-25", "scrape402", 0.01)
    k2 = payment_key("2026-08-25", "scrape402", 0.02)
    assert k1 != k2


def test_not_duplicate_when_absent():
    assert is_duplicate(FakeLedger(), "somekey") is False


def test_duplicate_when_confirmed():
    key = payment_key("2026-08-25", "scrape402", 0.01)
    ledger = FakeLedger({key: {"status": "CONFIRMED"}})
    assert is_duplicate(ledger, key) is True


def test_duplicate_when_pending_verify():
    key = payment_key("2026-08-25", "scrape402", 0.01)
    ledger = FakeLedger({key: {"status": "PENDING_VERIFY"}})
    assert is_duplicate(ledger, key) is True


def test_not_duplicate_when_failed():
    key = payment_key("2026-08-25", "scrape402", 0.01)
    ledger = FakeLedger({key: {"status": "FAILED"}})
    assert is_duplicate(ledger, key) is False
