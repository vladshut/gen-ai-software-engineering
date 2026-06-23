"""API-based integrator: sends transactions to the FastAPI pipeline server.

This replaces the direct function-call integrator with HTTP calls.
The server (api_server.py) handles the chain logic — each step calls the next.

Usage:
    # Terminal 1: start the server
    uvicorn api_server:app --port 8000

    # Terminal 2: run the integrator
    python integrator_api.py [--base-url http://localhost:8000]
"""

from __future__ import annotations

import argparse
import json
import shutil
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from common.messages import mask_account, safe_log_view

BASE = Path(__file__).resolve().parent
SHARED = BASE / "shared"
DIR_RESULTS = SHARED / "results"

# Expected outcome oracle (build plan).
ORACLE = {
    "TXN001": "approved",
    "TXN002": "flagged_review",
    "TXN003": "rejected",
    "TXN004": "rejected",
    "TXN005": "flagged_review",
    "TXN006": "rejected",
    "TXN007": "rejected",
    "TXN008": "approved",
}

# Map final settlement statuses back to the oracle decision.
# Settlement remaps: approved/review -> settled, flagged_review -> held,
# rejected -> rejected. We need to recover the pre-settlement decision.
STATUS_TO_ORACLE = {
    "settled": None,  # need prior_decision field
    "held": "flagged_review",
    "rejected": "rejected",
}


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"not JSON-serializable: {type(value).__name__}")


def reset_shared(root: Path = SHARED) -> None:
    """Recreate the shared/ results directory empty."""
    if root.exists():
        shutil.rmtree(root)
    (root / "results").mkdir(parents=True, exist_ok=True)


def load_transactions(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_oracle_decision(result: dict[str, Any]) -> str:
    """Extract the oracle-comparable decision from a settled result."""
    status = result.get("status")
    if status == "settled":
        return result.get("prior_decision", "approved")
    if status == "held":
        return "flagged_review"
    return "rejected"


def assert_oracle(outcomes: dict[str, str]) -> None:
    """Raise AssertionError if outcomes diverge from the build-plan oracle."""
    mismatches = {
        tid: (outcomes.get(tid), expected)
        for tid, expected in ORACLE.items()
        if outcomes.get(tid) != expected
    }
    if mismatches:
        lines = [f"{t}: got {got!r}, expected {exp!r}" for t, (got, exp) in mismatches.items()]
        raise AssertionError("oracle mismatch:\n  " + "\n  ".join(lines))


def run(base_url: str, transactions: list[dict[str, Any]], verbose: bool = True) -> dict[str, str]:
    """Send each transaction to the pipeline API. Returns {txn_id: oracle_decision}."""
    outcomes: dict[str, str] = {}
    final_statuses: dict[str, str] = {}
    settled_total_usd = Decimal("0")

    with httpx.Client(timeout=30.0) as client:
        for txn in transactions:
            txn_id = txn.get("transaction_id", "UNKNOWN")

            resp = client.post(f"{base_url}/pipeline", json=txn)
            resp.raise_for_status()
            result = resp.json()

            decision = _extract_oracle_decision(result)
            outcomes[txn_id] = decision
            final_statuses[txn_id] = result.get("status", "unknown")

            net_usd = result.get("net_usd")
            if result.get("settlement") == "settled" and net_usd:
                settled_total_usd += Decimal(str(net_usd))

            if verbose:
                safe = safe_log_view(result)
                extra = ""
                if "fraud_score" in result:
                    extra += f" score={result['fraud_score']}"
                if result.get("settlement") == "settled" and net_usd:
                    extra += f" net_usd={net_usd}"
                if result.get("rejection_reason"):
                    extra += f" reason=({result['rejection_reason']})"
                print(
                    f"  {txn_id}  {result['status']:<14} "
                    f"src={mask_account(safe.get('source_account'))} "
                    f"dst={mask_account(safe.get('destination_account'))}{extra}"
                )

    # Write run summary
    _write_summary(DIR_RESULTS, outcomes, final_statuses, settled_total_usd, len(transactions))
    return outcomes


def _write_summary(
    results_dir: Path,
    decisions: dict[str, str],
    final_statuses: dict[str, str],
    settled_total_usd: Decimal,
    total: int,
) -> None:
    decision_counts: dict[str, int] = {}
    for status in decisions.values():
        decision_counts[status] = decision_counts.get(status, 0) + 1
    final_counts: dict[str, int] = {}
    for status in final_statuses.values():
        final_counts[status] = final_counts.get(status, 0) + 1
    summary = {
        "total_transactions": total,
        "fraud_decision_counts": decision_counts,
        "settlement_status_counts": final_counts,
        "settled_total_usd": str(settled_total_usd),
        "fraud_decisions": decisions,
        "final_statuses": final_statuses,
    }
    (results_dir / "_run_summary.json").write_text(
        json.dumps(summary, indent=2, default=_json_default), encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="API-based pipeline orchestrator")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the pipeline API server (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--input",
        default=None,
        help="Path to transactions JSON (default: sample-transactions.json)",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input) if args.input else BASE / "sample-transactions.json"

    print("=" * 64)
    print("  Banking Pipeline (API mode) — validator -> fraud -> compliance -> settlement")
    print("=" * 64)
    reset_shared()
    transactions = load_transactions(input_path)
    print(f"Loaded {len(transactions)} transactions\n")

    outcomes = run(args.base_url, transactions)

    summary = json.loads((DIR_RESULTS / "_run_summary.json").read_text())
    print("\nFraud decision counts:", summary["fraud_decision_counts"])
    print("Settlement status counts:", summary["settlement_status_counts"])
    print("Settled total (USD net):", summary["settled_total_usd"])

    assert_oracle(outcomes)
    print("\n✅ Oracle check passed — all 8 decisions match expected outcome.")
    print(f"   Final records written to: {DIR_RESULTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
