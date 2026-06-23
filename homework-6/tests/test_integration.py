"""Integration test: full pipeline against sample-transactions.json.

Runs in an isolated shared/ dir via tmp_path and asserts the build-plan oracle.
"""

import json
from pathlib import Path

import integrator

SAMPLE = Path(integrator.BASE) / "sample-transactions.json"


def test_full_pipeline_matches_oracle(tmp_path):
    transactions = integrator.load_transactions(SAMPLE)
    shared = tmp_path / "shared"

    outcomes = integrator.run_pipeline(transactions, shared_root=shared, verbose=False)

    # Oracle: the fraud decisions must match exactly.
    integrator.assert_oracle(outcomes)
    assert outcomes == integrator.ORACLE

    # Every transaction lands as a final record in shared/results/.
    results_dir = shared / "results"
    for tid in integrator.ORACLE:
        assert (results_dir / f"{tid}.json").exists()

    # Run summary is written with the expected decision counts.
    summary = json.loads((results_dir / "_run_summary.json").read_text())
    assert summary["total_transactions"] == 8
    assert summary["fraud_decision_counts"] == {
        "approved": 2,
        "flagged_review": 2,
        "rejected": 4,
    }
    assert summary["settlement_status_counts"] == {
        "settled": 2,
        "held": 2,
        "rejected": 4,
    }


def test_results_files_mask_pii(tmp_path):
    """Final records still contain raw accounts (records, not logs), but the
    console log path masks them — assert masking helper is wired via summary."""
    transactions = integrator.load_transactions(SAMPLE)
    shared = tmp_path / "shared"
    integrator.run_pipeline(transactions, shared_root=shared, verbose=True)
    # TXN003 must be flagged (structuring), not waved through.
    record = json.loads((shared / "results" / "TXN003.json").read_text())
    assert record["data"]["fraud_score"] == 50


def test_reset_shared_creates_dirs(tmp_path):
    root = tmp_path / "shared"
    (root / "results").mkdir(parents=True)
    (root / "results" / "stale.json").write_text("{}")
    integrator.reset_shared(root)
    assert (root / "input").exists()
    assert not (root / "results" / "stale.json").exists()
