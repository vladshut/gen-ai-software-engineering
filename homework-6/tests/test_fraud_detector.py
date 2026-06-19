"""Unit tests for the fraud detector additive scoring + decision bands."""

from decimal import Decimal

from agents import fraud_detector as fd


def _txn(amount, **overrides):
    txn = {
        "transaction_id": "TXNX",
        "timestamp": "2026-03-16T09:00:00Z",
        "amount": Decimal(str(amount)),
        "currency": "USD",
        "transaction_type": "transfer",
        "metadata": {"country": "US"},
        "status": "validated",
    }
    txn.update(overrides)
    return txn


def test_structuring_case_flagged():
    # TXN003 analogue: 9999.99 -> structuring +50 -> flagged_review
    result = fd.assess_transaction(_txn("9999.99"))
    assert result["fraud_score"] == 50
    assert result["fraud_signals"]["structuring"] == 50
    assert result["status"] == "flagged_review"


def test_near_threshold_just_below_structuring():
    # 9799.99 is just below the structuring band -> no structuring points.
    result = fd.assess_transaction(_txn("9799.99"))
    assert "structuring" not in result["fraud_signals"]
    assert result["fraud_score"] == 0
    assert result["status"] == "approved"


def test_structuring_lower_boundary_inclusive():
    result = fd.assess_transaction(_txn("9800.00"))
    assert result["fraud_signals"]["structuring"] == 50


def test_high_value_boundary():
    # exactly 10000 -> high value (+40), not structuring (upper bound exclusive)
    result = fd.assess_transaction(_txn("10000.00", transaction_type="transfer"))
    assert result["fraud_signals"]["high_value"] == 40
    assert "structuring" not in result["fraud_signals"]
    assert result["status"] == "review"  # 40 is in 25..49 band


def test_very_high_value_additive():
    # 75000 wire US -> high(40)+veryhigh(20)+wire(10) = 70 -> flagged
    result = fd.assess_transaction(_txn("75000.00", transaction_type="wire_transfer"))
    assert result["fraud_score"] == 70
    assert result["status"] == "flagged_review"


def test_unusual_timing_and_cross_border():
    # EUR/DE at 02:47 -> unusual(20) + cross-border(15) = 35 -> review
    result = fd.assess_transaction(
        _txn("500.00", currency="EUR", timestamp="2026-03-16T02:47:00Z",
             metadata={"country": "DE"})
    )
    assert result["fraud_signals"]["unusual_timing"] == 20
    assert result["fraud_signals"]["cross_border"] == 15
    assert result["status"] == "review"


def test_wire_transfer_high_risk_rail():
    result = fd.assess_transaction(_txn("100.00", transaction_type="wire_transfer"))
    assert result["fraud_signals"]["high_risk_rail"] == 10


def test_rejected_passthrough_untouched():
    txn = _txn("100.00", status="rejected", rejection_reason="bad currency")
    result = fd.assess_transaction(txn)
    assert result["status"] == "rejected"
    assert "fraud_score" not in result


def test_unparseable_timestamp_no_timing_points():
    result = fd.assess_transaction(_txn("100.00", timestamp="garbage"))
    assert "unusual_timing" not in result["fraud_signals"]


def test_missing_metadata_defaults_domestic():
    txn = _txn("100.00")
    del txn["metadata"]
    result = fd.assess_transaction(txn)
    assert "cross_border" not in result["fraud_signals"]


def test_decide_bands():
    assert fd.decide(0) == "approved"
    assert fd.decide(24) == "approved"
    assert fd.decide(25) == "review"
    assert fd.decide(49) == "review"
    assert fd.decide(50) == "flagged_review"
    assert fd.decide(100) == "flagged_review"


def test_score_accepts_non_decimal_amount():
    # amount as a plain string still scores correctly.
    scored = fd.score_transaction({"amount": "25000.00", "timestamp": "2026-03-16T09:00:00Z",
                                   "transaction_type": "wire_transfer", "metadata": {"country": "US"}})
    assert scored["score"] == 50  # high(40) + wire(10)


def test_assess_batch():
    batch = [_txn("100.00"), _txn("9999.99")]
    results = fd.assess_batch(batch)
    assert [r["status"] for r in results] == ["approved", "flagged_review"]
