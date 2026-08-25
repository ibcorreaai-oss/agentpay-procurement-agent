import datetime as dt

from procurement_agent.tools.budget_guard import check_budget


class FakeLedger:
    def __init__(self, spent_today: float):
        self._spent_today = spent_today

    def sum_confirmed_spend_since(self, since):
        return self._spent_today


NOW = dt.datetime(2026, 8, 25, 12, 0, tzinfo=dt.timezone.utc)


def test_allows_small_payment_within_caps():
    decision = check_budget(FakeLedger(spent_today=0.0), amount_usdc=0.01, now=NOW)
    assert decision.allowed is True
    assert decision.remaining_today_usdc == 5.00


def test_rejects_amount_above_per_call_cap():
    decision = check_budget(FakeLedger(spent_today=0.0), amount_usdc=0.10, per_call_cap_usdc=0.05, now=NOW)
    assert decision.allowed is False
    assert "teto por chamada" in decision.reason


def test_rejects_when_daily_cap_would_be_exceeded():
    decision = check_budget(FakeLedger(spent_today=4.99), amount_usdc=0.02, daily_cap_usdc=5.00, now=NOW)
    assert decision.allowed is False
    assert "teto diario" in decision.reason


def test_allows_exact_remaining_amount():
    decision = check_budget(FakeLedger(spent_today=4.95), amount_usdc=0.05, daily_cap_usdc=5.00, per_call_cap_usdc=0.05, now=NOW)
    assert decision.allowed is True
    assert round(decision.remaining_today_usdc, 4) == 0.05
