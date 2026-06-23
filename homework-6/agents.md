# Agents

The pipeline has **four runtime agents**, each a deterministic function (no LLM
calls). They communicate only by reading/writing JSON `Message` envelopes in
`shared/`. The `integrator` is the orchestrator that wires them together.

## Message contract (every hop)

```json
{
  "message_id": "uuid4",
  "timestamp": "ISO-8601Z",
  "source_agent": "...",
  "target_agent": "...",
  "message_type": "transaction",
  "data": { "transaction_id": "...", "status": "...", "...": "..." }
}
```

`Decimal` money values are serialized as strings to preserve exact precision.

---

## 1. Transaction Validator (`agents/transaction_validator.py`)

- **Responsibility:** enforce the structural + amount + currency contract.
- **Input:** raw transaction dict (from `shared/input/`).
- **Output:** same dict with `status = "validated"` and a parsed `Decimal`
  `amount`, **or** `status = "rejected"` with a `rejection_reason`.
- **Rejects:** missing required fields, currency outside the ISO-4217 set
  (e.g. `XYZ`), amount that is unparseable / `≤ 0` / `> 2` decimal places.
- **Writes to:** `shared/processing/<txn>.validated.json`
  (`source_agent = transaction_validator`, `target_agent = fraud_detector`).

## 2. Fraud Detector (`agents/fraud_detector.py`)

- **Responsibility:** additive fraud scoring + decision band.
- **Input:** validated transaction (rejected ones pass through untouched).
- **Output:** adds `fraud_score`, `fraud_signals` (per-signal breakdown), and
  sets `status` to `approved` / `review` / `flagged_review`.
- **Scoring:** high value `+40`, very high `+20`, structuring `+50`, unusual
  timing `+20`, cross-border `+15`, wire `+10`. Bands: `≥50` flagged,
  `25–49` review, `<25` approved.
- **Writes to:** `shared/output/<txn>.assessed.json`
  (`source_agent = fraud_detector`, `target_agent = compliance_checker`).

## 3. Compliance Checker (`agents/compliance_checker.py`)

- **Responsibility:** regulatory screening — sanctions list + restricted
  jurisdictions. Deterministic, no LLM.
- **Input:** assessed transaction (from `shared/output/`). Already-rejected
  transactions pass through untouched.
- **Checks (frozen contract):**
  1. **Sanctions screening** — if `destination_account` is in the configured
     sanctioned accounts set → `status = "rejected"`, adds
     `rejection_reason = "sanctioned destination"`.
  2. **Restricted jurisdiction** — if `metadata.country` is in the restricted
     countries set (e.g. `{"KP", "IR", "SY"}`) → `status = "rejected"`, adds
     `rejection_reason = "restricted jurisdiction"`.
- **Output:**
  - If any check fires: `status = "rejected"`, `rejection_reason` string.
    Forwarded to settlement as non-settleable.
  - If all checks pass: status unchanged, forwarded to settlement.
- **Writes to:** `shared/output/<txn>.checked.json`
  (`source_agent = compliance_checker`, `target_agent = settlement_processor`).

## 4. Settlement Processor (`agents/settlement_processor.py`)

- **Responsibility:** final settlement decision + money math.
- **Input:** compliance-checked transaction.
- **Output:**
  - `rejected` → stays `rejected`, `settlement = not_settled`.
  - `flagged_review` → `status = held`, `settlement = not_settled`.
  - `approved` / `review` → `status = settled`, `settlement = settled`, with
    `fx_rate`, `amount_usd`, `fee_usd` (0.1%, ROUND_HALF_UP, min $0.01),
    `net_usd`, and the `prior_decision`.
- **Writes to:** `shared/results/<txn>.json` — the final auditable record
  (`source_agent = settlement_processor`, `target_agent = integrator`).

---

## Integrator (`integrator.py`)

- Resets `shared/`, loads `sample-transactions.json`, and runs each transaction
  through validator → fraud → compliance → settlement, writing a message at
  every hop.
- Masks PII (`****1234`) in all console logging via `safe_log_view` /
  `mask_account`.
- Writes `shared/results/_run_summary.json` (fraud-decision counts, compliance
  outcomes, settlement counts, settled USD total, per-transaction outcomes).
- Asserts the run reproduces the build-plan **oracle**.

---

## REST API Gateway (`api_server.py`)

The pipeline is also exposed as a **FastAPI REST service**. Each agent is an
HTTP endpoint; a configurable step list defines execution order.

### Pipeline step config

```python
PIPELINE_STEPS = [
    {"name": "validator",  "path": "/steps/validator"},
    {"name": "fraud",      "path": "/steps/fraud"},
    {"name": "compliance", "path": "/steps/compliance"},
    {"name": "settlement", "path": "/steps/settlement"},
]
```

To reorder or add steps, edit this list. Settlement must remain the terminal
step (it writes the final record).

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/config` | Returns the current pipeline step order |
| `POST` | `/pipeline` | Entry point — starts the chain at step 0 |
| `POST` | `/steps/validator` | Transaction validation |
| `POST` | `/steps/fraud` | Fraud scoring |
| `POST` | `/steps/compliance` | Compliance screening |
| `POST` | `/steps/settlement` | Settlement (terminal, writes result) |

### Chain behaviour

1. `POST /pipeline` receives a transaction and calls step 0 (`/steps/validator`).
2. Each step processes the transaction. If `status = "rejected"`, the chain
   **stops immediately** — settlement produces the final record, which is
   written to `shared/results/`, and the response flows back.
3. If the step does not reject, it calls the **next step** in `PIPELINE_STEPS`
   via HTTP.
4. Settlement (the terminal step) always writes the final record to
   `shared/results/<txn>.json`.

### API-mode integrator (`integrator_api.py`)

- POSTs each transaction to `POST /pipeline` via HTTP.
- Collects results, masks PII in logs, writes the run summary, and asserts the
  oracle — same as the direct-call integrator but over the network.

### Demo script (`demo.sh`)

A single `./demo.sh` runs the full demo with zero manual steps: starts the
server, submits transactions, displays results, runs tests, shuts down.
