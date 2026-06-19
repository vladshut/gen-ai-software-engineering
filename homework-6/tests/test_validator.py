"""Unit tests for the transaction validator and money/message helpers."""

from decimal import Decimal

import pytest

from agents import transaction_validator as tv
from common.messages import Message, mask_account, safe_log_view
from common.money import AmountError, apply_fee, net_after_fee, parse_amount, to_usd


def _base_txn(**overrides):
    txn = {
        "transaction_id": "TXN999",
        "timestamp": "2026-03-16T09:00:00Z",
        "source_account": "ACC-1001",
        "destination_account": "ACC-2001",
        "amount": "1500.00",
        "currency": "USD",
        "transaction_type": "transfer",
    }
    txn.update(overrides)
    return txn


# --- validator --------------------------------------------------------------

def test_valid_transaction_passes():
    result = tv.validate_transaction(_base_txn())
    assert result["status"] == "validated"
    assert result["amount"] == Decimal("1500.00")


def test_bad_currency_rejected():
    result = tv.validate_transaction(_base_txn(currency="XYZ"))
    assert result["status"] == "rejected"
    assert "unsupported currency" in result["rejection_reason"]


def test_negative_amount_rejected():
    result = tv.validate_transaction(_base_txn(amount="-100.00", currency="GBP"))
    assert result["status"] == "rejected"
    assert "invalid amount" in result["rejection_reason"]


def test_zero_amount_rejected():
    result = tv.validate_transaction(_base_txn(amount="0.00"))
    assert result["status"] == "rejected"


def test_missing_required_field_rejected():
    txn = _base_txn()
    del txn["currency"]
    result = tv.validate_transaction(txn)
    assert result["status"] == "rejected"
    assert "missing required fields" in result["rejection_reason"]


def test_too_many_decimal_places_rejected():
    result = tv.validate_transaction(_base_txn(amount="10.123"))
    assert result["status"] == "rejected"


def test_validate_batch_counts():
    batch = [_base_txn(transaction_id="A"), _base_txn(transaction_id="B", currency="XYZ")]
    results = tv.validate_batch(batch)
    assert [r["status"] for r in results] == ["validated", "rejected"]


def test_dry_run_main_prints_table(tmp_path, capsys):
    src = tmp_path / "txns.json"
    src.write_text(
        '[{"transaction_id":"TXN001","timestamp":"2026-03-16T09:00:00Z",'
        '"source_account":"ACC-1001","destination_account":"ACC-2001",'
        '"amount":"1500.00","currency":"USD","transaction_type":"transfer"}]'
    )
    rc = tv.main(["--dry-run", str(src)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "TXN001" in out and "validated" in out
    # PII must be masked in the table output.
    assert "ACC-1001" not in out
    assert "****1001" in out


def test_main_non_dry_run_summary(tmp_path, capsys):
    src = tmp_path / "txns.json"
    src.write_text(
        '[{"transaction_id":"TXN006","timestamp":"2026-03-16T10:05:00Z",'
        '"source_account":"ACC-1006","destination_account":"ACC-7700",'
        '"amount":"200.00","currency":"XYZ","transaction_type":"transfer"}]'
    )
    rc = tv.main([str(src)])
    assert rc == 0
    assert "rejected 1" in capsys.readouterr().out


# --- money ------------------------------------------------------------------

def test_parse_amount_valid():
    assert parse_amount("1500.00") == Decimal("1500.00")
    assert parse_amount(42) == Decimal("42")


def test_parse_amount_unparseable():
    with pytest.raises(AmountError):
        parse_amount("not-a-number")


def test_parse_amount_too_many_places():
    with pytest.raises(AmountError):
        parse_amount("1.234")


def test_parse_amount_negative_rejected():
    with pytest.raises(AmountError):
        parse_amount("-5.00")


def test_parse_amount_nan_rejected():
    with pytest.raises(AmountError):
        parse_amount(Decimal("NaN"))


def test_message_to_json_rejects_unserializable():
    import pytest as _pytest

    msg = Message("a", "b", {"bad": {1, 2, 3}})  # a set is not JSON-serializable
    with _pytest.raises(TypeError):
        msg.to_json()


def test_to_usd_eur_rounding():
    # 500 EUR * 1.08 = 540.00
    assert to_usd(Decimal("500.00"), "EUR") == Decimal("540.00")


def test_to_usd_half_up_rounding():
    # 0.0067 * 1499 = 10.0433 -> 10.04 ; pick a value that lands on a .xx5 tie.
    # 1.27 * 12.5 = 15.875 -> ROUND_HALF_UP -> 15.88
    assert to_usd(Decimal("12.50"), "GBP") == Decimal("15.88")


def test_to_usd_unknown_currency():
    with pytest.raises(AmountError):
        to_usd(Decimal("10"), "XYZ")


def test_apply_fee_min_floor():
    # 0.1% of 1.00 = 0.001 -> below min, floored at 0.01
    assert apply_fee(Decimal("1.00")) == Decimal("0.01")


def test_apply_fee_normal():
    # 0.1% of 1500 = 1.50
    assert apply_fee(Decimal("1500.00")) == Decimal("1.50")


def test_net_after_fee():
    assert net_after_fee(Decimal("1500.00")) == Decimal("1498.50")


# --- messages ---------------------------------------------------------------

def test_mask_account():
    assert mask_account("ACC-1001") == "****1001"
    assert mask_account("") == "****"
    assert mask_account(None) == "****"


def test_message_roundtrip_with_decimal():
    msg = Message("a", "b", {"transaction_id": "T1", "amount": Decimal("12.34")})
    restored = Message.from_json(msg.to_json())
    assert restored.data["transaction_id"] == "T1"
    assert restored.message_id == msg.message_id


def test_safe_log_view_masks_pii():
    txn = {
        "transaction_id": "T1",
        "source_account": "ACC-1001",
        "destination_account": "ACC-2001",
        "name": "Jane Doe",
    }
    safe = safe_log_view(txn)
    assert safe["source_account"] == "****1001"
    assert safe["destination_account"] == "****2001"
    assert safe["name"] == "****"
    # Original is untouched.
    assert txn["source_account"] == "ACC-1001"
