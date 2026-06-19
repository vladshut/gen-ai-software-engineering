# Banking Transaction Pipeline

**Created by Vladyslav Shut**

A deterministic, multi-agent banking pipeline that ingests raw transactions and
runs them through **validation → fraud scoring → settlement**, passing JSON
messages over a file-based `shared/` protocol and producing an auditable final
record for every transaction. A custom **FastMCP** server exposes the results,
and a **coverage gate** blocks pushes below 80%.

## What it does

1. Loads raw transactions from `sample-transactions.json`.
2. **Validates** structure, amount (`Decimal > 0`, ≤ 2 dp), and currency.
3. **Scores fraud** with a fixed additive model and assigns a decision band.
4. **Settles** approved/review transactions (FX → USD + 0.1% fee), holds
   flagged ones, leaves rejected ones rejected.
5. Writes a final record per transaction to `shared/results/` plus a run summary,
   and asserts the run reproduces a known outcome **oracle**.

## Agents

- **Transaction Validator** — enforces required fields, the amount rule, and the
  ISO-4217 currency set; rejects with a reason (e.g. `XYZ`, negative amounts).
- **Fraud Detector** — additive scoring (high value, very high, structuring,
  unusual timing, cross-border, high-risk rail) → `approved`/`review`/`flagged_review`.
- **Settlement Processor** — FX-converts to a USD base with static rates, applies
  a 0.1% fee (ROUND_HALF_UP, min $0.01); `settled` / `held` / `rejected`.

## Pipeline diagram

```
            sample-transactions.json
                      │
                      ▼
        ┌──────────────────────────┐
        │        integrator        │  (orchestrator + PII masking + oracle)
        └──────────────────────────┘
                      │  shared/input/
                      ▼
        ┌──────────────────────────┐
        │   Transaction Validator  │ ──► rejected (bad currency / amount)
        └──────────────────────────┘
                      │  shared/processing/
                      ▼
        ┌──────────────────────────┐
        │      Fraud Detector      │ ──► approved · review · flagged_review
        └──────────────────────────┘
                      │  shared/output/
                      ▼
        ┌──────────────────────────┐
        │   Settlement Processor   │ ──► settled · held · rejected
        └──────────────────────────┘
                      │  shared/results/<txn>.json
                      ▼
        ┌──────────────────────────┐
        │   FastMCP: pipeline-status │  get_transaction_status · list_pipeline_results
        │   resource pipeline://summary │
        └──────────────────────────┘
```

## Outcome oracle (the 8 sample transactions)

| Decision | Transactions |
|---|---|
| `approved` | TXN001, TXN008 |
| `review` | TXN004 |
| `flagged_review` | TXN002, TXN003, TXN005 |
| `rejected` | TXN006 (currency `XYZ`), TXN007 (negative amount) |

After settlement: approved/review → `settled` (3), flagged → `held` (3),
rejected → `rejected` (2).

## Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.12+ (developed on 3.13) |
| Money | `decimal.Decimal` + `ROUND_HALF_UP` (no floats) |
| MCP server | `fastmcp` (2 tools + 1 resource, STDIO transport) |
| Tests | `pytest` + `pytest-cov` (96% coverage) |
| Quality gate | Claude Code PreToolUse hook + `.githooks/pre-push` (≥ 80%) |
| Docs research | `context7` MCP (decimal + fastmcp lookups, see `research-notes.md`) |
| Inter-agent transport | File-based JSON `Message` envelopes in `shared/` |

## Project layout

```
homework-6/
├── common/        constants.py · money.py · messages.py   (frozen contracts)
├── agents/        transaction_validator · fraud_detector · settlement_processor
├── mcp_server/    server.py                                (FastMCP)
├── shared/        input/ processing/ output/ results/      (file-based protocol)
├── tests/         per-agent unit tests + integration test
├── .claude/       commands/ · settings.json · hooks/       (spec + coverage gate)
├── integrator.py  orchestrator
├── mcp.json       context7 + pipeline-status
└── specification.md · agents.md · research-notes.md · HOWTORUN.md
```

> See **HOWTORUN.md** for numbered setup → demo steps.
