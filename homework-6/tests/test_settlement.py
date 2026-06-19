"""Unit tests for the settlement processor."""

from decimal import Decimal

from agents import settlement_processor as sp


def _settle(status, amount="1500.00", currency="USD"):
    return sp.settle_transaction(
        {
            "transaction_id": "TXNX",
            "amount": Decimal(amount),
            "currency": currency,
            "status": status,
        }
    )


def test_approved_settles_usd():
    r = _settle("approved", "1500.00", "USD")
    assert r["status"] == "settled"
    assert r["settlement"] == "settled"
    assert r["amount_usd"] == Decimal("1500.00")
    assert r["fee_usd"] == Decimal("1.50")
    assert r["net_usd"] == Decimal("1498.50")
    assert r["prior_decision"] == "approved"


def test_review_settles_with_fx():
    # 500 EUR -> 540 USD, fee 0.54, net 539.46
    r = _settle("review", "500.00", "EUR")
    assert r["status"] == "settled"
    assert r["amount_usd"] == Decimal("540.00")
    assert r["fee_usd"] == Decimal("0.54")
    assert r["net_usd"] == Decimal("539.46")
    assert r["fx_rate"] == Decimal("1.08")


def test_flagged_is_held_not_settled():
    r = _settle("flagged_review", "25000.00")
    assert r["status"] == "held"
    assert r["settlement"] == "not_settled"
    assert "net_usd" not in r


def test_rejected_stays_rejected():
    r = _settle("rejected", "200.00", "USD")
    assert r["status"] == "rejected"
    assert r["settlement"] == "not_settled"


def test_min_fee_floor_applied():
    # tiny amount -> 0.1% below 0.01 -> fee floored at 0.01
    r = _settle("approved", "1.00", "USD")
    assert r["fee_usd"] == Decimal("0.01")
    assert r["net_usd"] == Decimal("0.99")


def test_unknown_status_not_settled():
    r = sp.settle_transaction({"transaction_id": "T", "amount": Decimal("1"),
                               "currency": "USD", "status": "weird"})
    assert r["settlement"] == "not_settled"
    assert r["status"] == "weird"


def test_amount_as_string_handled():
    r = sp.settle_transaction({"transaction_id": "T", "amount": "100.00",
                               "currency": "USD", "status": "approved"})
    assert r["amount_usd"] == Decimal("100.00")


def test_settle_batch():
    batch = [
        {"transaction_id": "A", "amount": Decimal("100"), "currency": "USD", "status": "approved"},
        {"transaction_id": "B", "amount": Decimal("100"), "currency": "USD", "status": "flagged_review"},
    ]
    results = sp.settle_batch(batch)
    assert [r["status"] for r in results] == ["settled", "held"]
