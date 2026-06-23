"""Unit tests for the compliance checker agent."""

from agents import compliance_checker as cc


def _txn(**overrides):
    txn = {
        "transaction_id": "TXN999",
        "timestamp": "2026-03-16T09:00:00Z",
        "source_account": "ACC-1001",
        "destination_account": "ACC-2001",
        "amount": "1500.00",
        "currency": "USD",
        "transaction_type": "transfer",
        "status": "approved",
        "metadata": {"country": "US"},
    }
    txn.update(overrides)
    return txn


def test_clean_transaction_passes():
    result = cc.check_transaction(_txn())
    assert result["status"] == "approved"
    assert "rejection_reason" not in result


def test_sanctioned_destination_rejected():
    result = cc.check_transaction(_txn(destination_account="ACC-9999"))
    assert result["status"] == "rejected"
    assert "sanctioned destination" in result["rejection_reason"]


def test_restricted_jurisdiction_rejected():
    result = cc.check_transaction(_txn(metadata={"country": "IR"}))
    assert result["status"] == "rejected"
    assert "restricted jurisdiction" in result["rejection_reason"]


def test_restricted_jurisdiction_kp():
    result = cc.check_transaction(_txn(metadata={"country": "KP"}))
    assert result["status"] == "rejected"
    assert "KP" in result["rejection_reason"]


def test_restricted_jurisdiction_sy():
    result = cc.check_transaction(_txn(metadata={"country": "SY"}))
    assert result["status"] == "rejected"
    assert "SY" in result["rejection_reason"]


def test_already_rejected_passes_through():
    txn = _txn(status="rejected", rejection_reason="bad currency")
    result = cc.check_transaction(txn)
    assert result["status"] == "rejected"
    assert result["rejection_reason"] == "bad currency"


def test_sanctioned_takes_priority_over_jurisdiction():
    """If both sanctions and jurisdiction fire, sanctions wins (checked first)."""
    result = cc.check_transaction(
        _txn(destination_account="ACC-9999", metadata={"country": "IR"})
    )
    assert result["status"] == "rejected"
    assert "sanctioned destination" in result["rejection_reason"]


def test_flagged_review_with_sanctioned_account_rejected():
    result = cc.check_transaction(
        _txn(status="flagged_review", destination_account="ACC-9999")
    )
    assert result["status"] == "rejected"


def test_missing_metadata_passes():
    txn = _txn()
    del txn["metadata"]
    result = cc.check_transaction(txn)
    assert result["status"] == "approved"


def test_check_batch():
    batch = [
        _txn(transaction_id="A"),
        _txn(transaction_id="B", destination_account="ACC-9999"),
        _txn(transaction_id="C", metadata={"country": "KP"}),
    ]
    results = cc.check_batch(batch)
    assert [r["status"] for r in results] == ["approved", "rejected", "rejected"]
