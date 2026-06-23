"""Integrator: orchestrate the four pipeline agents over the file-based
shared/ protocol.

Flow per transaction (each hop writes a Message envelope as JSON):

    sample-transactions.json
        -> shared/input/<txn>.json        (raw, ingested)
        -> [validator]   -> shared/processing/<txn>.validated.json
        -> [fraud]       -> shared/output/<txn>.assessed.json
        -> [compliance]  -> shared/output/<txn>.checked.json
        -> [settlement]  -> shared/results/<txn>.json   (final record)

All console logging masks PII (accounts -> ****1234). A run summary is written
to shared/results/_run_summary.json and the outcome is asserted against the
build-plan oracle.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from decimal import Decimal
from pathlib import Path
from typing import Any

from agents.fraud_detector import assess_transaction
from agents.compliance_checker import check_transaction
from agents.settlement_processor import settle_transaction
from agents.transaction_validator import validate_transaction
from common.constants import (
    AGENT_COMPLIANCE,
    AGENT_FRAUD,
    AGENT_INTEGRATOR,
    AGENT_SETTLEMENT,
    AGENT_VALIDATOR,
)
from common.messages import Message, mask_account, safe_log_view

BASE = Path(__file__).resolve().parent
SHARED = BASE / "shared"
DIR_INPUT = SHARED / "input"
DIR_PROCESSING = SHARED / "processing"
DIR_OUTPUT = SHARED / "output"
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


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"not JSON-serializable: {type(value).__name__}")


def reset_shared(root: Path = SHARED) -> None:
    """Recreate the shared/ stage directories empty."""
    if root.exists():
        shutil.rmtree(root)
    for sub in ("input", "processing", "output", "results"):
        (root / sub).mkdir(parents=True, exist_ok=True)


def _write_message(directory: Path, txn_id: str, suffix: str, msg: Message) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{txn_id}{suffix}.json"
    path.write_text(msg.to_json(), encoding="utf-8")


def run_pipeline(
    transactions: list[dict[str, Any]],
    *,
    shared_root: Path = SHARED,
    verbose: bool = True,
) -> dict[str, str]:
    """Run all transactions through the three agents. Returns {txn_id: status}."""
    dir_input = shared_root / "input"
    dir_processing = shared_root / "processing"
    dir_output = shared_root / "output"
    dir_results = shared_root / "results"
    for d in (dir_input, dir_processing, dir_output, dir_results):
        d.mkdir(parents=True, exist_ok=True)

    outcomes: dict[str, str] = {}  # txn_id -> fraud decision (oracle target)
    final_statuses: dict[str, str] = {}  # txn_id -> settlement status
    settled_total_usd = Decimal("0")

    for txn in transactions:
        txn_id = txn.get("transaction_id", "UNKNOWN")

        # Hop 0: ingest raw into shared/input
        ingest = Message(AGENT_INTEGRATOR, AGENT_VALIDATOR, dict(txn))
        _write_message(dir_input, txn_id, ".raw", ingest)

        # Hop 1: validator -> shared/processing
        validated = validate_transaction(txn)
        _write_message(
            dir_processing,
            txn_id,
            ".validated",
            Message(AGENT_VALIDATOR, AGENT_FRAUD, validated),
        )

        # Hop 2: fraud -> shared/output
        assessed = assess_transaction(validated)
        _write_message(
            dir_output,
            txn_id,
            ".assessed",
            Message(AGENT_FRAUD, AGENT_COMPLIANCE, assessed),
        )

        # Hop 3: compliance -> shared/output
        checked = check_transaction(assessed)
        # The status after compliance is the oracle target: approved/review/
        # flagged_review/rejected (compliance may reject sanctioned/restricted).
        outcomes[txn_id] = checked["status"]
        _write_message(
            dir_output,
            txn_id,
            ".checked",
            Message(AGENT_COMPLIANCE, AGENT_SETTLEMENT, checked),
        )

        # Hop 4: settlement -> shared/results (final record)
        settled = settle_transaction(checked)
        _write_message(
            dir_results,
            txn_id,
            "",
            Message(AGENT_SETTLEMENT, AGENT_INTEGRATOR, settled),
        )

        final_statuses[txn_id] = settled["status"]
        if settled.get("settlement") == "settled":
            settled_total_usd += settled["net_usd"]

        if verbose:
            safe = safe_log_view(settled)
            extra = ""
            if "fraud_score" in settled:
                extra += f" score={settled['fraud_score']}"
            if settled.get("settlement") == "settled":
                extra += f" net_usd={settled['net_usd']}"
            if settled.get("rejection_reason"):
                extra += f" reason=({settled['rejection_reason']})"
            print(
                f"  {txn_id}  {settled['status']:<14} "
                f"src={mask_account(safe.get('source_account'))} "
                f"dst={mask_account(safe.get('destination_account'))}{extra}"
            )

    _write_summary(
        dir_results, outcomes, final_statuses, settled_total_usd, len(transactions)
    )
    return outcomes


def _write_summary(
    results_dir: Path,
    fraud_decisions: dict[str, str],
    final_statuses: dict[str, str],
    settled_total_usd: Decimal,
    total: int,
) -> None:
    decision_counts: dict[str, int] = {}
    for status in fraud_decisions.values():
        decision_counts[status] = decision_counts.get(status, 0) + 1
    final_counts: dict[str, int] = {}
    for status in final_statuses.values():
        final_counts[status] = final_counts.get(status, 0) + 1
    summary = {
        "total_transactions": total,
        "fraud_decision_counts": decision_counts,
        "settlement_status_counts": final_counts,
        "settled_total_usd": str(settled_total_usd),
        "fraud_decisions": fraud_decisions,
        "final_statuses": final_statuses,
    }
    (results_dir / "_run_summary.json").write_text(
        json.dumps(summary, indent=2, default=_json_default), encoding="utf-8"
    )


def load_transactions(path: Path) -> list[dict[str, Any]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


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


def _run_graded() -> int:
    """The default, graded run: file-based shared/ protocol + oracle assertion."""
    print("=" * 64)
    print("  Banking Pipeline — validator -> fraud -> compliance -> settlement")
    print("=" * 64)
    reset_shared()
    transactions = load_transactions(BASE / "sample-transactions.json")
    print(f"Loaded {len(transactions)} transactions from sample-transactions.json\n")

    outcomes = run_pipeline(transactions)

    summary = json.loads((DIR_RESULTS / "_run_summary.json").read_text())
    print("\nFraud decision counts:", summary["fraud_decision_counts"])
    print("Settlement status counts:", summary["settlement_status_counts"])
    print("Settled total (USD net):", summary["settled_total_usd"])

    assert_oracle(outcomes)
    print("\n✅ Oracle check passed — all 8 fraud decisions match expected outcome.")
    print(f"   Final records written to: {DIR_RESULTS}")
    return 0


def _run_fast(args: argparse.Namespace) -> int:
    """High-throughput mode: stream JSONL, fan across cores, append JSONL.

    Separate from the graded path — no shared/ files, no oracle. See
    ``fast_pipeline.py`` for the Tier 1 + Tier 2 design.
    """
    from fast_pipeline import run_scaled

    input_path = Path(args.input) if args.input else BASE / "sample-transactions.json"
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = BASE / output_path

    print("=" * 64)
    print("  Banking Pipeline — FAST mode (streaming + multiprocessing)")
    print("=" * 64)
    print(f"Input : {input_path}")

    stats = run_scaled(
        input_path,
        output_path,
        workers=args.workers,
        chunk_size=args.chunk_size,
    )

    print(
        f"\nProcessed {stats['total']:,} transactions in {stats['seconds']}s "
        f"({stats['per_sec']:,}/s) across {stats['workers']} worker(s)"
    )
    print(
        f"  settled={stats['settled']:,}  held={stats['held']:,}  "
        f"rejected={stats['rejected']:,}"
    )
    print(f"  Results -> {output_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Banking pipeline orchestrator")
    parser.add_argument(
        "--fast",
        action="store_true",
        help="high-throughput mode: stream JSONL, run in parallel, no shared/ files",
    )
    parser.add_argument(
        "--input",
        default=None,
        help="input file for --fast (.jsonl streamed, or .json array)",
    )
    parser.add_argument(
        "--output",
        default="shared/results.jsonl",
        help="JSONL results path for --fast (default: shared/results.jsonl)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="worker processes for --fast (default: 1 = single process; "
        "raise only for very large batches — see HOWTORUN.md)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=10_000,
        help="transactions per worker task for --fast (default: 10000)",
    )
    args = parser.parse_args(argv)

    if args.fast:
        return _run_fast(args)
    return _run_graded()


if __name__ == "__main__":
    raise SystemExit(main())
