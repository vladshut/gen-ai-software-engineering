"""Agent 3 of the runtime pipeline: Settlement Processor.

Deterministic (no LLM). Decides settlement based on the fraud decision:

    rejected        -> stays rejected (not settled)
    flagged_review  -> held (not settled)
    approved/review -> settled: FX-convert to USD, apply 0.1% fee
                       (ROUND_HALF_UP, min $0.01), write final record

Final settled record carries: amount_usd, fee_usd, net_usd, fx_rate.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from common.constants import (
    FX_RATES_TO_USD,
    STATUS_APPROVED,
    STATUS_FLAGGED,
    STATUS_HELD,
    STATUS_REJECTED,
    STATUS_REVIEW,
    STATUS_SETTLED,
)
from common.money import apply_fee, net_after_fee, to_usd

SETTLE_STATUSES = frozenset({STATUS_APPROVED, STATUS_REVIEW})


def settle_transaction(txn: dict[str, Any]) -> dict[str, Any]:
    """Return the transaction with a final settlement outcome."""
    result = dict(txn)
    status = result.get("status")

    if status == STATUS_REJECTED:
        result["settlement"] = "not_settled"
        return result

    if status == STATUS_FLAGGED:
        result["status"] = STATUS_HELD
        result["settlement"] = "not_settled"
        return result

    if status in SETTLE_STATUSES:
        amount = result["amount"]
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        currency = result["currency"]

        amount_usd = to_usd(amount, currency)
        fee_usd = apply_fee(amount_usd)
        net_usd = net_after_fee(amount_usd)

        result["prior_decision"] = status
        result["status"] = STATUS_SETTLED
        result["settlement"] = "settled"
        result["fx_rate"] = FX_RATES_TO_USD[currency]
        result["amount_usd"] = amount_usd
        result["fee_usd"] = fee_usd
        result["net_usd"] = net_usd
        return result

    # Defensive: unknown status -> leave untouched but mark not settled.
    result["settlement"] = "not_settled"
    return result


def settle_batch(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [settle_transaction(txn) for txn in transactions]
