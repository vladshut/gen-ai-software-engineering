---
description: Run the full banking pipeline and show the per-transaction outcome + oracle check
---

# /run-pipeline

Run the end-to-end banking pipeline against `sample-transactions.json` (or the
file named in `$ARGUMENTS`) and report results.

Steps:

1. From the project root, run the orchestrator:
   ```bash
   ./.venv/bin/python integrator.py
   ```
2. Read the run summary it writes to `shared/results/_run_summary.json`.
3. Report, as a short table:
   - each transaction's fraud decision and final settlement status,
   - the fraud-decision counts and settlement-status counts,
   - the total settled USD (net of fee).
4. Confirm the **oracle check passed** (the script asserts it). If it failed,
   show which transactions diverged and stop.
5. Remind the user that every final record is in `shared/results/<txn>.json`
   and PII is masked in all logs.
