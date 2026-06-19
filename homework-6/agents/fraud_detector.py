"""Agent 2 of the runtime pipeline: Fraud Detector.

Deterministic additive scoring (no LLM). Already-rejected transactions pass
through untouched; validated ones get a fraud score, a per-signal breakdown, and
a decision status.

Scoring table (frozen contract):
    high value          amount >= 10000                  +40
    very high value     amount >= 50000                  +20 (additional)
    structuring         9800 <= amount < 10000           +50
    unusual timing      hour in [00:00, 05:00) UTC        +20
    cross-border        metadata.country != "US"          +15
    high-risk rail      transaction_type == wire_transfer +10

Decision: >= 50 flagged_review ; 25..49 review ; < 25 approved.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from common.constants import (
    DOMESTIC_COUNTRY,
    FLAGGED_THRESHOLD,
    HIGH_RISK_TYPE,
    HIGH_VALUE_THRESHOLD,
    POINTS_CROSS_BORDER,
    POINTS_HIGH_RISK_RAIL,
    POINTS_HIGH_VALUE,
    POINTS_STRUCTURING,
    POINTS_UNUSUAL_TIMING,
    POINTS_VERY_HIGH_VALUE,
    REVIEW_THRESHOLD,
    STATUS_APPROVED,
    STATUS_FLAGGED,
    STATUS_REJECTED,
    STATUS_REVIEW,
    STRUCTURING_HIGH,
    STRUCTURING_LOW,
    UNUSUAL_HOUR_END,
    UNUSUAL_HOUR_START,
    VERY_HIGH_VALUE_THRESHOLD,
)


def _parse_hour_utc(timestamp: str) -> int | None:
    """Return the UTC hour from an ISO-8601 timestamp, or None if unparseable."""
    try:
        ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    return ts.hour


def score_transaction(txn: dict[str, Any]) -> dict[str, Any]:
    """Compute the additive fraud score and per-signal breakdown for a txn."""
    amount = txn["amount"]
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))

    signals: dict[str, int] = {}

    if amount >= HIGH_VALUE_THRESHOLD:
        signals["high_value"] = POINTS_HIGH_VALUE
    if amount >= VERY_HIGH_VALUE_THRESHOLD:
        signals["very_high_value"] = POINTS_VERY_HIGH_VALUE
    if STRUCTURING_LOW <= amount < STRUCTURING_HIGH:
        signals["structuring"] = POINTS_STRUCTURING

    hour = _parse_hour_utc(txn.get("timestamp", ""))
    if hour is not None and UNUSUAL_HOUR_START <= hour < UNUSUAL_HOUR_END:
        signals["unusual_timing"] = POINTS_UNUSUAL_TIMING

    country = (txn.get("metadata") or {}).get("country", DOMESTIC_COUNTRY)
    if country != DOMESTIC_COUNTRY:
        signals["cross_border"] = POINTS_CROSS_BORDER

    if txn.get("transaction_type") == HIGH_RISK_TYPE:
        signals["high_risk_rail"] = POINTS_HIGH_RISK_RAIL

    return {"score": sum(signals.values()), "signals": signals}


def decide(score: int) -> str:
    """Map a fraud score to a decision status."""
    if score >= FLAGGED_THRESHOLD:
        return STATUS_FLAGGED
    if score >= REVIEW_THRESHOLD:
        return STATUS_REVIEW
    return STATUS_APPROVED


def assess_transaction(txn: dict[str, Any]) -> dict[str, Any]:
    """Return the transaction enriched with fraud score, signals and status.

    Already-rejected transactions are passed through unchanged.
    """
    result = dict(txn)
    if result.get("status") == STATUS_REJECTED:
        return result

    scored = score_transaction(result)
    result["fraud_score"] = scored["score"]
    result["fraud_signals"] = scored["signals"]
    result["status"] = decide(scored["score"])
    return result


def assess_batch(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [assess_transaction(txn) for txn in transactions]
