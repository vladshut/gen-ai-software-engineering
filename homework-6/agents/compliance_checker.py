"""Agent 3 of the runtime pipeline: Compliance Checker.

Deterministic function (no LLM). Screens transactions against:
  1. Sanctioned accounts — destination_account in the frozen set.
  2. Restricted jurisdictions — metadata.country in the frozen set.

Already-rejected transactions pass through untouched. If any check fires the
transaction is rejected with a reason; otherwise it passes through unchanged.
"""

from __future__ import annotations

from typing import Any

from common.constants import (
    RESTRICTED_COUNTRIES,
    SANCTIONED_ACCOUNTS,
    STATUS_REJECTED,
)


def check_transaction(txn: dict[str, Any]) -> dict[str, Any]:
    """Return the transaction with compliance screening applied.

    If already rejected, pass through. Otherwise check sanctions and
    jurisdiction; reject with reason if either fires.
    """
    result = dict(txn)

    if result.get("status") == STATUS_REJECTED:
        return result

    destination = result.get("destination_account", "")
    if destination in SANCTIONED_ACCOUNTS:
        result["status"] = STATUS_REJECTED
        result["rejection_reason"] = f"sanctioned destination: {destination}"
        return result

    country = (result.get("metadata") or {}).get("country", "")
    if country in RESTRICTED_COUNTRIES:
        result["status"] = STATUS_REJECTED
        result["rejection_reason"] = f"restricted jurisdiction: {country}"
        return result

    return result


def check_batch(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [check_transaction(txn) for txn in transactions]
