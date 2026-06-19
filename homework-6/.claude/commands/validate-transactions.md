---
description: Validate a transactions file (dry-run) without running the full pipeline
---

# /validate-transactions

Run only the **Transaction Validator** against a transactions file in dry-run
mode — no files are written, just a results table.

Steps:

1. From the project root, run:
   ```bash
   ./.venv/bin/python -m agents.transaction_validator --dry-run ${ARGUMENTS:-sample-transactions.json}
   ```
2. Present the table, highlighting any **rejected** rows and their reason
   (e.g. unsupported currency `XYZ`, negative amount, > 2 decimal places,
   missing required fields).
3. Note that account numbers are masked to last 4 (`****1001`) in the output.
4. If everything is valid, say so; otherwise summarize how many were rejected
   and why.
