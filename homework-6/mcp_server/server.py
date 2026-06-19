"""Custom FastMCP server exposing banking pipeline results.

NOTE: this package is named `mcp_server` (not `mcp`) on purpose — a top-level
package called `mcp` shadows the official MCP SDK that fastmcp imports and breaks
`from fastmcp import FastMCP`.

Exposes (pattern from context7 /prefecthq/fastmcp):
  - tool  get_transaction_status(transaction_id) -> status from shared/results/
  - tool  list_pipeline_results()                -> summary of all processed txns
  - resource pipeline://summary                  -> latest run summary as text

Run (STDIO transport, the fastmcp default):
    python -m mcp_server.server
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running as a bare script (python mcp_server/server.py) by ensuring the
# project root is importable for `common` etc. (not needed for `python -m`).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastmcp import FastMCP  # noqa: E402

RESULTS_DIR = _PROJECT_ROOT / "shared" / "results"
SUMMARY_FILE = RESULTS_DIR / "_run_summary.json"

mcp = FastMCP("pipeline-status")


def _read_result(transaction_id: str) -> dict | None:
    path = RESULTS_DIR / f"{transaction_id}.json"
    if not path.exists():
        return None
    envelope = json.loads(path.read_text(encoding="utf-8"))
    # Final records are stored as message envelopes; unwrap the data payload.
    return envelope.get("data", envelope)


@mcp.tool
def get_transaction_status(transaction_id: str) -> dict:
    """Return the final status of a processed transaction.

    Reads shared/results/<transaction_id>.json. Returns a dict with the status
    and key settlement fields, or an error if the transaction was not processed.
    """
    data = _read_result(transaction_id)
    if data is None:
        return {
            "transaction_id": transaction_id,
            "found": False,
            "error": "no result found — run integrator.py first",
        }
    # Settled records carry converted USD fields (amount_usd/net_usd); held and
    # rejected records only carry the raw amount/currency. Surface the raw value
    # for every record, and fall back amount_usd -> amount only when the currency
    # is USD so we never mislabel a non-USD amount as USD.
    currency = data.get("currency")
    amount = data.get("amount")
    amount_usd = data.get("amount_usd")
    if amount_usd is None and currency == "USD":
        amount_usd = amount

    return {
        "transaction_id": transaction_id,
        "found": True,
        "status": data.get("status"),
        "settlement": data.get("settlement"),
        "fraud_score": data.get("fraud_score"),
        "amount": amount,
        "currency": currency,
        "amount_usd": amount_usd,
        "net_usd": data.get("net_usd"),
        "rejection_reason": data.get("rejection_reason"),
    }


@mcp.tool
def list_pipeline_results() -> dict:
    """Return a summary of every processed transaction from the latest run."""
    if not RESULTS_DIR.exists():
        return {"error": "shared/results/ does not exist — run integrator.py first"}

    results = []
    for path in sorted(RESULTS_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        data = _read_result(path.stem) or {}
        results.append(
            {
                "transaction_id": data.get("transaction_id", path.stem),
                "status": data.get("status"),
                "settlement": data.get("settlement"),
                "fraud_score": data.get("fraud_score"),
            }
        )

    summary = {}
    if SUMMARY_FILE.exists():
        summary = json.loads(SUMMARY_FILE.read_text(encoding="utf-8"))

    return {
        "count": len(results),
        "results": results,
        "fraud_decision_counts": summary.get("fraud_decision_counts", {}),
        "settlement_status_counts": summary.get("settlement_status_counts", {}),
        "settled_total_usd": summary.get("settled_total_usd"),
    }


@mcp.resource("pipeline://summary")
def pipeline_summary() -> str:
    """The latest run summary as human-readable text."""
    if not SUMMARY_FILE.exists():
        return "No run summary yet. Run `python integrator.py` to produce one."
    summary = json.loads(SUMMARY_FILE.read_text(encoding="utf-8"))
    lines = [
        "Banking Pipeline — latest run summary",
        f"Total transactions: {summary.get('total_transactions')}",
        f"Fraud decisions: {summary.get('fraud_decision_counts')}",
        f"Settlement statuses: {summary.get('settlement_status_counts')}",
        f"Settled total (USD net): {summary.get('settled_total_usd')}",
        "",
        "Per-transaction fraud decision:",
    ]
    for tid, status in summary.get("fraud_decisions", {}).items():
        lines.append(f"  {tid}: {status}")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()  # STDIO transport by default
