"""Agent 1 of the runtime pipeline: Transaction Validator.

Deterministic function (no LLM). Validates required fields, the amount rule, and
the currency set. Rejected transactions get status `rejected` with a reason;
valid ones pass through unchanged for the fraud detector.

CLI:
    python -m agents.transaction_validator --dry-run [path-to-transactions.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from typing import Any

from common.constants import ACCEPTED_CURRENCIES, STATUS_REJECTED
from common.messages import mask_account
from common.money import AmountError, parse_amount

REQUIRED_FIELDS = (
    "transaction_id",
    "timestamp",
    "source_account",
    "destination_account",
    "amount",
    "currency",
    "transaction_type",
)


def validate_transaction(txn: dict[str, Any]) -> dict[str, Any]:
    """Return a result dict: the original transaction plus validation outcome.

    On success: {..., "status": "validated", "amount": Decimal}
    On failure: {..., "status": "rejected", "rejection_reason": "..."}
    """
    result = dict(txn)

    missing = [f for f in REQUIRED_FIELDS if not txn.get(f)]
    if missing:
        result["status"] = STATUS_REJECTED
        result["rejection_reason"] = f"missing required fields: {', '.join(missing)}"
        return result

    currency = txn["currency"]
    if currency not in ACCEPTED_CURRENCIES:
        result["status"] = STATUS_REJECTED
        result["rejection_reason"] = f"unsupported currency: {currency}"
        return result

    try:
        amount = parse_amount(txn["amount"])
    except AmountError as exc:
        result["status"] = STATUS_REJECTED
        result["rejection_reason"] = f"invalid amount: {exc}"
        return result

    result["amount"] = amount
    result["status"] = "validated"
    return result


def validate_batch(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [validate_transaction(txn) for txn in transactions]


def _print_dry_run_table(results: list[dict[str, Any]]) -> None:
    """Print a results table without writing any files (masking PII)."""
    header = f"{'TXN':<10} {'STATUS':<10} {'AMOUNT':>12} {'CUR':<4} {'SRC':<8} REASON"
    print(header)
    print("-" * len(header))
    for r in results:
        amount = r.get("amount", r.get("amount", ""))
        amount_str = f"{amount}" if isinstance(amount, Decimal) else str(amount)
        print(
            f"{r.get('transaction_id', '?'):<10} "
            f"{r.get('status', '?'):<10} "
            f"{amount_str:>12} "
            f"{r.get('currency', ''):<4} "
            f"{mask_account(r.get('source_account')):<8} "
            f"{r.get('rejection_reason', '')}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Transaction Validator agent")
    parser.add_argument(
        "source",
        nargs="?",
        default="sample-transactions.json",
        help="path to a transactions JSON array",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print a results table without writing files",
    )
    args = parser.parse_args(argv)

    with open(args.source, encoding="utf-8") as fh:
        transactions = json.load(fh)

    results = validate_batch(transactions)

    if args.dry_run:
        _print_dry_run_table(results)
    else:
        rejected = sum(1 for r in results if r["status"] == STATUS_REJECTED)
        print(f"validated {len(results) - rejected}, rejected {rejected}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
