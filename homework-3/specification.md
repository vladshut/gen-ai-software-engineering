# Specification: Virtual Card Lifecycle Management

| Field            | Value                                                             |
| ---------------- | ----------------------------------------------------------------- |
| Document version | 1.0                                                               |
| Status           | Draft for engineering review                                      |
| Owner            | Card Platform Team                                                |
| Last updated     | 2026-05-08                                                        |
| Service name     | `card-management-service` (CMS)                                   |
| Bounded context  | Card lifecycle, limits, transaction read model — **not** issuance authorization, **not** ledger of funds |

> **Reading guide.** Sections 1–4 are the *intent layer* (why / what / how well). Sections 5–7 are the *guardrails* an implementer or AI agent must respect. Sections 8–11 are *executable*: state machines, low-level tasks with acceptance criteria, edge cases, verification, and SLOs. Each low-level task references a Mid-Level Objective by ID.

---

## 1. High-Level Objective

Provide cardholders and internal operators with a controlled, auditable lifecycle for **virtual debit/credit cards** — issuance, freeze/unfreeze, limit configuration, and transaction visibility — such that every state-changing action is traceable, every sensitive data access is logged, and the system remains within a minimised PCI-DSS scope by delegating PAN custody to a certified issuer processor.

**Scope boundary (one sentence):** This service owns card *metadata, lifecycle state, user-defined limits, and a denormalised transaction read model*; it does **not** own PAN/CVV storage, authorization decisioning, settlement, or the funds ledger.

---

## 2. Stakeholders & Personas

| Persona                       | Primary needs                                                                          | Trust level                      |
| ----------------------------- | -------------------------------------------------------------------------------------- | -------------------------------- |
| **Cardholder** (end-user)     | Issue a card, freeze instantly when lost, set spending caps, see recent transactions   | Authenticated via SCA per PSD2   |
| **Ops / Support agent**       | Look up cardholder's cards, see lifecycle history, freeze on user request, **not** raise limits | Authenticated, role `support`    |
| **Compliance / Fraud officer**| Read-only access to *all* cards & full audit trail; place compliance freeze (overrides user) | Authenticated, role `compliance` |
| **AML / Sanctions sub-system**| Pre-issuance verdict producer (sync API call)                                          | System-to-system, mTLS           |
| **Issuer processor**          | External system holding PAN; receives lifecycle events, sends transaction events       | System-to-system, mTLS + signed webhooks |

---

## 3. Mid-Level Objectives (testable "what")

Each objective is observable: a black-box test or a manual review can determine whether it is met.

| ID    | Objective                                                                                          | Success signal                                                                                                       |
| ----- | -------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| MLO-1 | Cardholder can issue exactly one virtual card per request, with idempotent retry semantics.        | Two requests with same `Idempotency-Key` produce one card and identical responses.                                   |
| MLO-2 | Card lifecycle follows an explicit, enforced state machine (no "any-to-any" transitions).          | Invalid transition (e.g., `closed → active`) is rejected with `409` and never mutates state.                         |
| MLO-3 | Freeze propagates to the issuer processor and is reflected in authorization decisions within budget. | End-to-end freeze-to-decline median ≤ 2 s, P99 ≤ 5 s; reconciliation job catches divergence within 5 min.            |
| MLO-4 | User-defined limits (per-tx, daily, monthly, MCC, geo) are versioned and stamp every authorization request to the processor. | Each authorization callback echoes `limits_version`; replay against historical version produces identical verdict. |
| MLO-5 | Transaction read model is eventually consistent with processor events and exposes no PAN/CVV.       | Sample audit: 100 % of returned objects expose `card_last4` only; PAN/CVV absent from response, logs, traces.        |
| MLO-6 | Every state-changing or sensitive-read operation produces an immutable audit event.                | Append-only audit store; tamper test detects mutation; 100 % of state transitions traceable to actor + reason + correlation id. |
| MLO-7 | Compliance freeze takes precedence over user freeze/unfreeze and cannot be lifted by user or support. | User unfreeze API returns `403 compliance_lock` while compliance lock is active.                                     |
| MLO-8 | Sensitive data flow is bounded: PAN/CVV never enter CMS storage, logs, traces, or backups.         | Threat-model review + automated log scanner finds zero PAN-shaped strings (Luhn-valid 13–19 digit) over 30 days.     |
| MLO-9 | The system degrades safely: if the processor is unreachable, **freeze must still succeed locally** and queue for downstream propagation. | Chaos test (processor down) confirms freeze API returns `202 accepted, propagation_pending`; no silent failures.    |

---

## 4. Non-Functional Requirements & Policy

> All numeric targets are **assumed targets**, justified per row. They are inputs to capacity planning, not contractually committed SLAs.

### 4.1 Security

| Concern                  | Requirement                                                                                                               | Justification / standard                                  |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| Authentication           | All cardholder write operations require step-up auth (SCA) — biometric or OTP — within last 5 min.                        | PSD2 RTS Art. 4 (strong customer authentication).         |
| Transport                | TLS 1.3 only; mTLS for processor and AML adapters; HSTS preload.                                                          | PCI-DSS v4.0 §4.2.1.                                      |
| Secrets                  | No secrets in env vars in production; Vault / KMS-backed retrieval at boot.                                               | OWASP ASVS L2 §6.4.                                       |
| Authorization            | RBAC: `cardholder`, `support`, `compliance`, `system`. Authorization checked at controller boundary **and** repository.   | Defense in depth.                                         |
| Sensitive data           | PAN, CVV, full magstripe, PIN — **never persisted, never logged, never traced**. Only `card_last4`, `processor_card_id`, BIN. | PCI-DSS scope minimisation (tokenisation pattern).      |
| Rate limiting            | Per-user: 60 limit-change requests / hour; 10 issuance requests / day. Per-IP fallback on unauth endpoints.               | Anti-abuse.                                               |

### 4.2 Privacy & Data Handling

- **Data classification.** Three tiers: `pci-restricted` (must not enter system), `pii` (cardholder name, masked PAN, address — encrypted at rest with envelope encryption), `internal` (limits, lifecycle state, MCC lists).
- **Right to erasure (GDPR Art. 17).** Closed cards are retained for 7 years (financial record-keeping) but cardholder PII is *pseudonymised* on user erasure request; lifecycle and audit records remain with pseudonymous subject ID.
- **Cross-border.** All data resides in EU regions; processor adapter must reject non-EU processor endpoints by allow-list.

### 4.3 Audit & Logging

- **Audit event taxonomy** (mandatory categories):
  `card.issued`, `card.frozen`, `card.unfrozen`, `card.closed`, `card.compliance_locked`, `card.compliance_unlocked`, `limit.changed`, `transaction.viewed`, `card_details.viewed`, `auth.failed`.
- Every audit event carries: `event_id` (UUIDv7), `correlation_id`, `actor_id`, `actor_role`, `subject_card_id`, `reason_code`, `reason_text` (free-form, capped 500 chars), `before_state` snapshot, `after_state` snapshot, `occurred_at` (UTC, ISO-8601).
- **Immutability.** Audit store is append-only; mutation/deletion privilege not granted to any application role; quarterly hash-chain verification.
- **Retention.** Audit: 7 years (PSD2 / national AML retention norms). Application logs: 90 days hot, 1 year cold.

### 4.4 Reliability

| Metric              | Target                                              | Notes                                                              |
| ------------------- | --------------------------------------------------- | ------------------------------------------------------------------ |
| Service availability| 99.95 % monthly                                     | ≈ 21.6 min/month error budget. Justification: card freeze is safety-critical UX; one major outage per month tolerable, two is not. |
| RPO                 | ≤ 1 min for lifecycle / limits; 0 for audit         | Lifecycle replayable from processor events; audit must be synchronously durable. |
| RTO                 | ≤ 30 min                                            | Read replica failover automatable.                                 |

### 4.5 Performance budgets (assumed targets)

| Operation                         | Target P50 / P95 / P99       | Justification                                                                 |
| --------------------------------- | ---------------------------- | ----------------------------------------------------------------------------- |
| `POST /cards` (issue)             | 300 / 800 / 1500 ms          | Synchronous processor call dominates; ≤ 1 s feels instant in mobile UX.       |
| `POST /cards/{id}/freeze`         | 100 / 300 / 700 ms (local commit) | Critical safety action; must feel instant. Processor propagation async.   |
| `PUT /cards/{id}/limits`          | 150 / 400 / 900 ms           |                                                                               |
| `GET /cards/{id}/transactions`    | 100 / 400 / 900 ms (page = 50) | Cursor-paginated; from local read model (no processor call on hot path).    |
| `GET /cards/{id}`                 | 50 / 150 / 400 ms            | High-volume read; should be cache-friendly.                                   |
| Processor event ingestion lag     | P95 ≤ 5 s end-to-end          | Cardholder expects to see a transaction in app within seconds of swipe.       |
| Freeze→processor propagation      | Median ≤ 2 s, P99 ≤ 5 s       | Mirrors MLO-3.                                                                |
| Throughput                        | 200 RPS sustained, 800 RPS burst (1 min) | Estimate: 1 M cardholders × 0.0002 ops/s baseline + headroom.        |

### 4.6 Compliance posture (declared, not built here)

- **PCI-DSS v4.0**: target SAQ-A scope by tokenisation (no SAD or PAN in CMS).
- **PSD2 / SCA**: enforced at API gateway via partnered IdP.
- **AML / Sanctions**: synchronous pre-issuance check via AML adapter; outcome stored as immutable verdict on the card record.
- **DORA (EU 2022/2554)**: incident classification & 4-hour major-incident notification path documented in runbook (not in this spec).

---

## 5. Implementation Notes (guardrails for builders / AI agents)

These are **non-negotiable** conventions. An AI agent or human implementer who violates them is producing wrong code regardless of test outcome.

### 5.1 Money & numeric handling

- All monetary amounts are stored and transmitted as **integer minor units** (e.g., cents) with an explicit ISO-4217 currency code; *never* as floats.
- All comparisons and arithmetic use a `Money` value object (see `agents.md`); raw integer arithmetic on monetary fields is forbidden outside that object.
- Limit currency must match card currency; cross-currency limit configuration is rejected with `422 currency_mismatch`.

### 5.2 Identifiers

- External IDs (returned to clients) are UUIDv7 prefixed with the resource type: `card_01HW…`, `lim_01HW…`, `evt_01HW…`. Sequential integer IDs are forbidden in API responses (information leakage).
- `processor_card_id` is opaque, treated as a string, never parsed.

### 5.3 Idempotency

- Every state-changing endpoint requires an `Idempotency-Key` header (UUID, max 128 chars).
- Idempotency record TTL: 24 hours.
- A retry with the same key + identical body returns the original response. A retry with the same key + *different* body returns `409 idempotency_key_reuse`.

### 5.4 Error semantics

- Errors follow [RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457). Every error has a stable `type` URI (e.g., `https://errors.example.com/card/state-conflict`) and a `code` machine-readable string.
- 4xx errors expose minimum information necessary; never leak whether a card belongs to another user (return `404` not `403` for cross-tenant access).
- Compliance-related rejections expose a generic reason to the user (`card_unavailable`) and the specific reason only in audit logs.

### 5.5 Time

- All timestamps are UTC, ISO-8601, millisecond precision.
- **Daily and monthly limit windows** are evaluated in the **card's home timezone** (set at issuance, default = cardholder's account timezone). This must be explicit because UTC midnight gives surprising behaviour for users in UTC-8 / UTC+9. Window boundary algorithm documented in §8.4.

### 5.6 PII / PCI redaction

- Logging framework must apply a redaction filter on every log line; PAN-shaped strings (digit sequences passing Luhn check, length 13–19) are replaced with `[REDACTED:PAN]` regardless of field name.
- Stack traces from processor adapter scrubbed before being persisted.
- This is enforced at framework level, not by developer discipline.

### 5.7 Concurrency

- Optimistic locking (`version` column, monotonically increasing) on `card` aggregate. Update with stale version → `409 stale_version`.
- Limit changes use the same mechanism; the `limits_version` exposed to the processor is the post-update value.

### 5.8 Asynchronous propagation

- All processor-bound mutations (lifecycle, limits) are committed locally first, then enqueued. A background outbox processor publishes to the processor adapter with at-least-once delivery; processor adapter must be idempotent.
- Outbox pattern is mandatory; "fire-and-forget" HTTP calls inside the request handler are forbidden.

---

## 6. Beginning Context (what exists before any work starts)

```
repo/
├── docs/
│   ├── architecture/
│   │   └── context-diagram.md        (C4 L1 of platform; CMS shown as future component)
│   └── adr/
│       ├── 0001-tokenisation-strategy.md
│       └── 0002-pii-classification.md
├── platform/
│   ├── auth-gateway/                  (existing service; issues JWTs with role claims)
│   └── audit-bus/                     (existing append-only Kafka topic + sink)
└── homework-3/
    ├── specification.md               (this file)
    ├── agents.md
    ├── README.md
    └── .claude/CLAUDE.md
```

External systems (assumed to exist as black boxes):

- **Issuer Processor** — REST + webhooks, certified PCI-DSS Level 1, exposes: `POST /cards`, `POST /cards/{id}/state`, `POST /cards/{id}/limits`, webhook `transaction.cleared`, `transaction.declined`.
- **AML Adapter** — sync `POST /screen` returning `{verdict: pass|fail|review, case_id?}`.
- **Audit Bus** — Kafka topic `audit.events.v1`, schema-registered Avro.
- **Auth Gateway** — issues JWTs with `sub`, `roles[]`, `auth_time`, `acr` (SCA level).

## 7. Ending Context (artifacts that exist after all tasks complete)

```
homework-3/                            (unchanged — spec only)

future-implementation/                 (out of scope; sketched for traceability)
├── src/
│   ├── Domain/Card/
│   ├── Domain/Limit/
│   ├── Application/Command/
│   ├── Application/Query/
│   ├── Infrastructure/Persistence/
│   ├── Infrastructure/Processor/
│   └── Infrastructure/Audit/
├── tests/
│   ├── Unit/
│   ├── Integration/
│   ├── Contract/processor/
│   └── E2E/
├── migrations/
└── deploy/
```

---

## 8. Domain Model & State Machine

### 8.1 Aggregates

- **Card** (aggregate root): `id, cardholder_id, currency, status, limits_version, home_timezone, processor_card_id, last4, created_at, version, compliance_lock`.
- **Limit** (entity inside Card): `version, per_tx_amount, daily_amount, monthly_amount, allowed_mcc[], blocked_mcc[], allowed_countries[], blocked_countries[]`.
- **AuditEvent** (separate aggregate, append-only): see §4.3.
- **TransactionReadModel** (denormalised, eventually consistent): `id, card_id, amount, currency, mcc, country, merchant_name, status, occurred_at`.

### 8.2 Card state machine

```
        ┌──────────────────┐
        │  PendingIssuance │
        └────────┬─────────┘
                 │ (processor confirms)
                 ▼
        ┌──────────────────┐    user/support freeze    ┌──────────────────┐
        │      Active      │ ────────────────────────▶ │      Frozen      │
        │                  │ ◀──────────────────────── │                  │
        └────────┬─────────┘    user/support unfreeze  └─────────┬────────┘
                 │                                                │
                 │  user close / compliance close                 │
                 └─────────────────┬──────────────────────────────┘
                                   ▼
                          ┌──────────────────┐
                          │      Closed      │  (terminal)
                          └──────────────────┘

Compliance lock is an *orthogonal* flag. While `compliance_lock = true`,
all user/support transitions are rejected; only compliance can clear the lock.
```

**Allowed transitions** (anything else → `409 invalid_transition`):

| From              | To       | Allowed actors                          |
| ----------------- | -------- | --------------------------------------- |
| PendingIssuance   | Active   | `system` (processor confirmation only)  |
| PendingIssuance   | Closed   | `system` (issuance failure)             |
| Active            | Frozen   | `cardholder`, `support`, `compliance`   |
| Frozen            | Active   | `cardholder`, `support` (only if no compliance lock) |
| Active / Frozen   | Closed   | `cardholder`, `compliance`              |

### 8.3 Limit windows

Daily window = `[00:00 home_tz, 24:00 home_tz)` of card's home timezone; monthly window = `[1st 00:00, 1st of next month 00:00)` same tz. Spent-to-date counters are evaluated **by the processor** at authorization time using `limits_version` snapshot; CMS only stores the limit config and version history.

---

## 9. Low-Level Tasks

> Each task references its parent Mid-Level Objective. Acceptance criteria use *Given / When / Then* where they describe externally observable behaviour, and bullet checkboxes for review-style criteria.

### Capability A — Issuance

#### A.1 Implement `POST /cards` (issue virtual card) — *MLO-1, MLO-8, MLO-9*

- **AC-1.** Given a valid cardholder with passing AML verdict, when `POST /cards` is called with `Idempotency-Key: K`, then a card is created in `PendingIssuance`, processor is called, and on success the card transitions to `Active`. Response includes `card_id`, `last4`, `currency`, `status`, `limits.version`.
- **AC-2.** Given the same `Idempotency-Key: K` and identical body within 24h, the second call returns the same response and creates **no** additional card.
- **AC-3.** Given the same `Idempotency-Key: K` and a different body, the second call returns `409 idempotency_key_reuse`.
- **AC-4.** Given AML verdict = `fail`, no card is created; response is `422 issuance_rejected` with generic message; audit event `card.issuance.rejected` records the actual AML reason.
- **AC-5.** Given the processor returns 5xx, the card remains in `PendingIssuance`, the outbox retries with exponential backoff, and after 24h still-pending is auto-closed with reason `processor_unreachable`.
- **Edge cases to cover:** AML verdict = `review` (→ `202 issuance_pending_review`); cardholder over per-day issuance rate limit; concurrent issuance with same idempotency key from two pods (DB-level uniqueness on `idempotency_key`).

#### A.2 AML adapter integration — *MLO-1, MLO-8*

- **AC-1.** AML call has 2 s timeout; on timeout, treat as `review` (fail-closed for stricter posture) — **explicitly call this out in ADR**.
- **AC-2.** AML adapter is a port (interface); the production binding is HTTP, but tests use an in-memory fake.
- **AC-3.** AML response is persisted as immutable verdict tied to issuance attempt id (not card id, since failed attempts don't get cards).

### Capability B — Lifecycle transitions

#### B.1 `POST /cards/{id}/freeze` — *MLO-2, MLO-3, MLO-9*

- **AC-1.** Given card in `Active`, when freeze is called by cardholder/support, then status becomes `Frozen` locally **before** the response returns; outbox event `card.freeze.requested` is enqueued; response is `200 OK` with `propagation_status: pending|complete`.
- **AC-2.** Given card already `Frozen` and same idempotency key + same `reason`, response is `200 OK` (idempotent).
- **AC-3.** Given card in `Closed`, response is `409 invalid_transition`.
- **AC-4.** Given the processor is unreachable, the local freeze still commits (MLO-9); the outbox retries; the response indicates `propagation_status: pending`.
- **AC-5.** Audit event `card.frozen` includes `actor_id`, `actor_role`, `reason_code` ∈ `{lost, stolen, suspicious, user_choice, compliance, support_request}`, `correlation_id`.

#### B.2 `POST /cards/{id}/unfreeze` — *MLO-2, MLO-7*

- **AC-1.** Mirror of freeze.
- **AC-2.** Given `compliance_lock = true`, response is `403 compliance_lock`; no state change; audit event `auth.failed` with reason `compliance_lock_blocks_unfreeze`.

#### B.3 `POST /cards/{id}/close` — *MLO-2*

- **AC-1.** Closure is **terminal**; subsequent reads must show `Closed` and reject any state-changing call with `409 invalid_transition`.
- **AC-2.** Closure triggers processor close call via outbox; failures retry indefinitely (closed cards must not reappear as charged).
- **AC-3.** Closed cards retain their `processor_card_id` for reconciliation.

#### B.4 Compliance lock / unlock (internal API) — *MLO-7*

- **AC-1.** Only role `compliance` can call these endpoints.
- **AC-2.** Compliance lock can be applied regardless of current status (Active or Frozen); closed cards cannot be locked (no-op).
- **AC-3.** While locked, freeze/unfreeze by cardholder/support returns `403 compliance_lock`.

### Capability C — Limits

#### C.1 `PUT /cards/{id}/limits` — *MLO-4*

- **AC-1.** Given valid limits within regulatory caps, then a new `limits_version` is created (immutable history kept) and propagated to processor via outbox.
- **AC-2.** Given a daily limit > monthly limit, response is `422 limit_invariant_violation`.
- **AC-3.** Given a per-tx limit > regulatory cap (e.g., 5,000 EUR for unverified accounts), response is `422 limit_above_cap`.
- **AC-4.** Concurrent updates: optimistic lock on `card.version`; stale → `409 stale_version`.
- **AC-5.** Limit history is queryable: `GET /cards/{id}/limits/history` returns versions with `valid_from`/`valid_to`.

#### C.2 Limit validation rules

- Per-tx ≤ daily ≤ monthly.
- Currency = card currency.
- MCC lists: allowed and blocked are mutually exclusive (presence in both → 422).
- Countries: ISO-3166-1 alpha-2; sanctioned-country presence in `allowed_countries` is rejected.

### Capability D — Transactions read model

#### D.1 Ingest processor webhook `transaction.cleared` / `transaction.declined` — *MLO-5*

- **AC-1.** Webhook is verified by signature (HMAC-SHA256 over canonical body + timestamp; replay window 5 min).
- **AC-2.** Idempotent on `processor_event_id`.
- **AC-3.** Persists to read-model with PCI-redacted fields only; PAN field from webhook (if present in error) is logged as `[REDACTED:PAN]`.
- **AC-4.** Lag from processor event to read-model visibility: P95 ≤ 5 s (MLO-5 / §4.5).

#### D.2 `GET /cards/{id}/transactions` — *MLO-5, MLO-8*

- **AC-1.** Cursor-pagination with default page size 50, max 200.
- **AC-2.** Returned objects expose `card_last4` only; PAN field absent from schema (compile-time guarantee in code; documented in OpenAPI).
- **AC-3.** Date range filter; default last 90 days.
- **AC-4.** Each call emits audit event `transaction.viewed` with `range`, `count_returned`.

### Capability E — Audit & observability

#### E.1 Append-only audit writer — *MLO-6, MLO-8*

- **AC-1.** All state mutations go through a transactional outbox that includes the audit event in the same DB transaction as the state change. Either both commit or neither.
- **AC-2.** Audit events flushed to `audit.events.v1` Kafka topic by the outbox processor.
- **AC-3.** Audit consumer writes to immutable store (hash-chained, S3 Object Lock or equivalent).
- **AC-4.** Hash-chain verification job runs nightly; alerts on break.

#### E.2 PII/PCI log redaction — *MLO-8*

- **AC-1.** Logging framework registers a Monolog processor that redacts PAN-shaped strings on every record before it leaves the process.
- **AC-2.** Redaction is unit-tested against a corpus including: bare PAN, PAN in JSON, PAN with spaces, PAN with dashes.
- **AC-3.** Synthetic canary log line emitted hourly; log-pipeline alarm fires if canary appears un-redacted.

#### E.3 Reconciliation job — *MLO-3*

- **AC-1.** Every 5 min, job fetches list of cards in `Frozen` from CMS and compares to processor; divergence emits alert and writes audit event `reconciliation.divergence_detected`.
- **AC-2.** Divergence resolution policy: CMS state is authoritative for *intent*; processor state is authoritative for *enforcement*. Mismatch = retry propagation, not state correction.

### Capability F — Cross-cutting infrastructure

#### F.1 RBAC enforcement — *MLO-7*

- **AC-1.** Authorization decorator on every controller; missing decorator → CI fails (static check).
- **AC-2.** Repository layer re-checks tenant ownership; cross-tenant ID guess returns `404` (not `403`).

#### F.2 Idempotency middleware — *MLO-1*

- **AC-1.** Storage: dedicated table with `(idempotency_key, request_hash, response_body, status_code, expires_at)`; PK = `idempotency_key`.
- **AC-2.** Cleanup job purges expired entries daily.

---

## 10. Edge Cases & Failure Modes (consolidated)

| #   | Scenario                                                            | Expected behaviour                                                                                          | Audit / compliance impact                          |
| --- | ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| E1  | User freezes card; before processor confirms, transaction arrives.  | Processor authoritative at decision time. If processor still has Active limits version, decision proceeds. | Logged divergence; reconciliation closes window.   |
| E2  | User changes limits; in-flight authorization is using old version.  | Processor stamps `limits_version` per call; old version honoured for that authorization.                   | No issue; audit shows version trail.                |
| E3  | Double-freeze (idempotent) with same reason.                         | `200 OK`, no state change, no new audit event.                                                              | Single audit event (the original).                 |
| E4  | Double-freeze with different reason.                                 | `200 OK`, no state change; audit event `card.freeze.reason_updated` recorded.                               | Reason history preserved.                          |
| E5  | Compliance lock applied while user holds the freeze toggle.          | Compliance lock supersedes; user unfreeze blocked.                                                          | Audit captures both events.                        |
| E6  | Limit set above regulatory cap.                                      | `422 limit_above_cap`; nothing persisted.                                                                   | Audit event `limit.changed.rejected`.              |
| E7  | Sanctions hit at issuance.                                           | `422 issuance_rejected` with generic message; specific reason in audit only.                                | Compliance case opened (out of CMS scope).         |
| E8  | Closed card resurrection attempt (any state-change API).             | `409 invalid_transition`.                                                                                   | Audit event `auth.failed`.                         |
| E9  | Timezone edge: cardholder in UTC-10 spends at 23:30 local; window?  | Daily window = card home tz; spend counts toward "today" in cardholder's tz, not UTC.                       | Documented in §5.5 and §8.3.                       |
| E10 | Webhook replay (same `processor_event_id`).                          | Idempotent; no duplicate read-model entry.                                                                  | No audit event for replays (noise).                |
| E11 | Webhook with invalid signature.                                      | `401`; no state change; security alert raised.                                                              | Audit event `webhook.signature_invalid`.            |
| E12 | Processor returns success but local DB commit fails after.           | Transactional outbox prevents this: state + outbox row in single tx; processor call only after tx commit.   | N/A by design.                                     |
| E13 | Two pods racing to apply same idempotency key.                       | DB unique constraint on `idempotency_key`; loser sees `23505` and re-reads winner's response.               | N/A.                                               |
| E14 | Cardholder PII deletion request after card closed.                   | PII pseudonymised on card and audit (subject_id replaced with `pseudo:<hash>`); lifecycle data retained.    | Documented in §4.2.                                |
| E15 | Processor unreachable for ≥ 1 h.                                     | Freezes accepted locally with `propagation_status: pending`; issuance returns `503 issuance_unavailable`.   | Incident: DORA major if exceeds threshold.         |

---

## 11. Verification Strategy

| Mid-Level Objective | Primary verification                                                                                  | Secondary                              |
| ------------------- | ----------------------------------------------------------------------------------------------------- | -------------------------------------- |
| MLO-1 (idempotency) | Integration test: same key twice, different body twice; assert single card and `409` respectively.    | Property test on idempotency middleware. |
| MLO-2 (state machine)| Unit tests on state machine: exhaustive transition matrix; every illegal transition asserted to throw.| Mutation testing on state machine class.|
| MLO-3 (freeze propagation) | Contract test against processor sandbox; chaos test (processor down) for MLO-9 overlap.        | Reconciliation job's own integration test.|
| MLO-4 (limits versioning)| Integration test: change limits, verify `limits_version` increment and history endpoint.         | Property test: `per_tx ≤ daily ≤ monthly` invariant. |
| MLO-5 (read model)  | E2E: post webhook, poll read endpoint, assert lag ≤ budget.                                          | OpenAPI schema validates absence of PAN.|
| MLO-6 (audit)       | Integration test: each state-changing endpoint asserts audit row + Kafka emission.                   | Hash-chain verification job in CI on seed dataset. |
| MLO-7 (compliance lock)| Integration tests on RBAC and lock precedence.                                                    | Manual compliance review checklist.    |
| MLO-8 (sensitive data)| Static check: forbidden-field list in CI; runtime: log-scanner canary.                             | Threat model review (sign-off artifact).|
| MLO-9 (degraded mode)| Chaos test: processor down → freeze succeeds locally; RTO/RPO verification.                        | Game day exercise quarterly.           |

**Test category targets** (documentation, not enforced here):

- Unit: ≥ 90 % line coverage on `src/Domain/`; mutation score ≥ 70 % on state machine and limit invariants.
- Integration: every controller, every outbox path, every webhook handler.
- Contract tests: processor adapter; AML adapter; signed-webhook verification.
- Manual compliance review: PCI scope mapping signed off before each release that touches sensitive flows.

---

## 12. Out of Scope (explicit)

- Funds ledger / balance computation (separate `ledger-service`).
- Authorization decisioning (issuer processor responsibility).
- Card-not-present 3-D Secure flow (gateway responsibility).
- Disputes & chargebacks (`dispute-service`).
- Physical card issuance.
- Multi-currency conversion.

---

## 13. Glossary

| Term            | Definition                                                                                          |
| --------------- | --------------------------------------------------------------------------------------------------- |
| PAN             | Primary Account Number — full card number. **Never stored in CMS.**                                 |
| SAD             | Sensitive Authentication Data (CVV, full magstripe, PIN). **Never stored in CMS.**                  |
| MCC             | Merchant Category Code (ISO 18245).                                                                 |
| SCA             | Strong Customer Authentication (PSD2 RTS).                                                          |
| Tokenisation    | Replacement of PAN with a non-sensitive surrogate; PAN custody delegated to certified processor.    |
| `limits_version`| Monotonically increasing version of a card's limit configuration; stamped on processor calls.       |
| Outbox pattern  | Local transactional queue ensuring at-least-once delivery to async downstreams.                     |

---

## 14. Open questions (deliberately unresolved — not failures of the spec)

1. **Per-card vs per-cardholder daily caps.** This spec scopes daily limits per card. If a cardholder holds N cards, aggregate daily cap is not enforced — by design or by oversight? Decision deferred to product.
2. **Cool-down on unfreeze→freeze cycling.** Should there be an anti-abuse minimum interval? Threat model open question.
3. **Closure grace period for pending authorizations.** Currently closure is immediate; some processors keep a 7-day "credentials retired" window. Reconciliation policy may need a tri-state (`Closing`).

These are flagged because pretending they're solved would be worse than declaring them open.
