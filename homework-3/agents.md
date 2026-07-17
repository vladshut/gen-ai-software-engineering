# agents.md — AI Coding Partner Guidelines

> This file tells any AI coding agent (Claude Code, Cursor, Copilot, Codex, Aider, etc.) **how to behave** when working in this repository. Rules here are stricter than general best practice because the domain is regulated finance: silent mistakes have audit, compliance, or money-loss consequences.
>
> Editor-time auto-completion rules live in `.claude/CLAUDE.md` (Claude Code) — that file points back here for substantive policy. **This file is the source of truth.**

---

## 1. Mission & operating principles

You are assisting on `card-management-service`, a virtual card lifecycle service. Read `specification.md` before making any non-trivial change.

**Operate by these principles, in priority order:**

1. **Correctness over speed.** A working stub that respects invariants beats a feature that violates the state machine.
2. **Explicit over clever.** Prefer boring, readable code; avoid metaprogramming, magic, or "smart" macros.
3. **Refuse to bypass guardrails.** If a request asks you to log a PAN, persist a CVV, skip an audit event, or weaken a signature check — **stop and surface the concern**, do not silently comply.
4. **Surface uncertainty.** When the spec is ambiguous, propose two options with trade-offs; do not invent a "reasonable default" silently.
5. **Small, traceable changes.** Each change references the Mid-Level Objective ID (MLO-x) and / or low-level task ID (e.g. `B.1 AC-3`).

---

## 2. Tech stack assumptions

| Area                | Choice                                       | Why                                                          |
| ------------------- | -------------------------------------------- | ------------------------------------------------------------ |
| Language            | PHP 8.2+                                     | Existing platform standard.                                  |
| Framework           | Symfony 6.4 LTS                              | Existing platform standard; LTS for compliance stability.    |
| Persistence         | PostgreSQL 15+ via Doctrine ORM 3.x          | Strong transactional guarantees for outbox + state changes.  |
| Async messaging     | Kafka (audit) + Symfony Messenger (outbox)   | Hybrid: Kafka for immutable event log, Messenger for in-process work. |
| Cache               | Redis 7+                                     | Idempotency store, rate limits, SCA freshness window.        |
| HTTP client         | Symfony HttpClient                           | Built-in retry, timeout, mTLS support.                       |
| Tests               | PHPUnit 11, with test doubles + factories    | Per existing internal standards.                             |
| Static analysis     | PHPStan level max + Psalm                    | Two analysers catch different classes of error.              |
| API description     | OpenAPI 3.1, contract-first                  | Generated controllers verified against spec.                 |

If a request would introduce a *new* runtime dependency, surface this as a question — do not silently add it.

---

## 3. Domain rules (banking-specific)

These rules are **invariants**. Violating them is a defect, regardless of test outcome.

### 3.1 Sensitive data

- **Never** include PAN, CVV, full magstripe, PIN, or unmasked card details in:
  - Database columns
  - Log messages (any level)
  - Tracing spans / span attributes
  - Exception messages
  - Backup files, dumps, or fixtures
  - Test fixtures (use synthetic processor IDs only)
- The only PAN-derived data the system stores: `last4` (4-digit suffix) and `bin` (first 6 digits, for routing only).
- If a processor response contains a PAN by accident, the response handler **must** redact before persistence and emit a `security.unexpected_pan_in_payload` audit event.

### 3.2 Money

- All amounts: integer minor units + ISO-4217 currency code.
- Use the `App\Domain\Common\Money` value object for all arithmetic. Never use float, never use `bccomp` directly outside that class.
- Currency mismatch is a runtime error, not a silent rounding.

### 3.3 Time

- All persisted timestamps: UTC, `DATETIMEZ` column type, with millisecond precision.
- Limit windows: card's home timezone (see specification §5.5). Use the `LimitWindowCalculator` service; do not compute window boundaries inline.

### 3.4 Idempotency

- Every state-changing controller action: `Idempotency-Key` header **required**, validated by `IdempotencyMiddleware`. If you write a controller without it, you've made a defect.
- Key + request body hash + response are stored for 24h.
- Outbox processors must be idempotent on `processor_event_id` (incoming) or `outbox_id` (outgoing).

### 3.5 State changes

- All state mutations on the `Card` aggregate go through the state machine (`App\Domain\Card\StateMachine`). Direct `$card->setStatus(...)` is a defect; use `$card->freeze($reason, $actor)` etc.
- Audit event creation lives **inside** the same DB transaction as the state change, via the `TransactionalOutbox` pattern. Two-phase "save then publish" is forbidden — it loses events on crash.

### 3.6 Authorization

- Every controller method has an authorization attribute (`#[IsGranted(...)]` or `#[RequiresRole(...)]`). CI pipeline fails if a controller method without one is added.
- Repository / query layer re-checks ownership: `findCardForUser(string $cardId, string $userId)` not `findCard(string $cardId)`. Cross-tenant ID guess returns null → controller returns 404, never 403 (don't leak existence).

---

## 4. Code style & conventions

### 4.1 Class shape (per existing internal standards)

- Service classes: `final class`, all dependencies through constructor, all properties `readonly`.
- Value objects: `final readonly class` with named constructor (`Money::of(...)`) — never raw `new` with positional arguments for non-trivial VOs.
- Aggregates: `final class`, internal mutability via private setters; protocol changes go through methods that emit domain events.
- **No traits** for code reuse (per existing standards). Composition or inheritance from a single base when truly shared.
- **No abstract classes** unless modelling a domain hierarchy. Prefer interfaces + final implementations.

### 4.2 Interfaces

- One concrete implementation per interface in `src/`; multiple in `tests/` is fine (fakes, spies).
- Interface names do *not* use the `I` prefix or `Interface` suffix when there is one production implementation; use the unprefixed name and call the implementation `*Implementation` or describe the binding.
  - Example: `AmlScreener` interface, `HttpAmlScreener` production binding, `InMemoryAmlScreener` test fake.

### 4.3 Exceptions

- Three categories, mapped at the controller boundary by an `ExceptionListener`:
  1. **Domain exceptions** (`App\Domain\Exception\*`): expected business outcomes (e.g. `InvalidStateTransition`). Map to `4xx`.
  2. **Application exceptions** (`App\Application\Exception\*`): orchestration failures (e.g. `IdempotencyKeyReused`). Map to `4xx`.
  3. **Infrastructure exceptions** (`App\Infrastructure\Exception\*`): adapter failures (DB unreachable, processor 5xx). Map to `5xx` after retry.
- Never catch `\Throwable` except in the global handler; never swallow exceptions silently.

### 4.4 Logging

- Channels: `card`, `audit`, `processor`, `aml`, `security`.
- Levels: `INFO` for state changes; `WARNING` for handled retries; `ERROR` for unrecoverable; `CRITICAL` for security/integrity events.
- The `RedactProcessor` is registered globally; **do not** add fields that bypass it.
- Structured logging: every record has `correlation_id`, `card_id` (if applicable), `actor_id` (if applicable). Use Monolog context, not string interpolation.

---

## 5. Testing & verification expectations

### 5.1 What to write per change

| Change type                       | Required tests                                                                          |
| --------------------------------- | --------------------------------------------------------------------------------------- |
| New domain rule / invariant       | Unit test on the aggregate; property test on the invariant if numeric or set-theoretic. |
| New controller endpoint           | Integration test: happy path + each documented error code.                              |
| New processor or AML adapter call | Contract test (recorded fixtures, schema-validated).                                    |
| New webhook handler               | Integration test for valid, replayed, and tampered signatures.                          |
| New audit event                   | Integration test asserting both DB outbox row and Kafka emission.                       |
| New state machine transition      | Update full transition matrix test; assert all *other* transitions still throw.         |

### 5.2 Test doubles

- Per internal standards: prefer **factories + fakes** over mocks. A fake AML adapter is more honest than a mocked HTTP client.
- Mocks acceptable only at the outermost adapter boundary (HTTP, Kafka client) and only when a fake would need to reimplement the wire protocol.
- **Never** test by mocking the system under test.

### 5.3 Sensitive data in tests

- All test PANs must be the canonical Visa/MasterCard test PANs from PCI-DSS test suite (e.g., `4111111111111111`). They are still treated as redacted by the redaction processor — the test asserting redaction must use one of these values, *not* an obviously-fake `1234567890123456`.

---

## 6. Security & compliance constraints

### 6.1 What to refuse

If a user request asks you to:

- Skip the `Idempotency-Key` requirement on a write endpoint
- Log or persist PAN/CVV/SAD even "for debugging"
- Mutate audit events
- Issue a card without an AML verdict
- Open a state-machine transition that's not in `specification.md` §8.2
- Allow `cardholder` or `support` role to bypass `compliance_lock`
- Disable signature verification on processor webhooks "temporarily"

→ **Stop**, explain the policy reference, and propose a compliant alternative. Do not produce the code that violates the rule, even with comments saying "TODO fix this".

### 6.2 Threat-model awareness

When introducing a new endpoint or data flow, briefly reason about:

- **Spoofing**: who calls this, how is identity verified?
- **Tampering**: what integrity guarantee on the payload?
- **Repudiation**: is there an audit event with actor + reason?
- **Information disclosure**: any sensitive field returned, logged, traced?
- **Denial of service**: rate limit? auth required?
- **Elevation of privilege**: cross-tenant ID exposure? mass-assignment risk?

A one-line note in the PR description per dimension is sufficient; the absence of this note for a security-relevant change is a CI warning.

### 6.3 Dependencies

- New runtime dependency requires:
  - License check (MIT/BSD/Apache-2.0 acceptable; GPL/AGPL requires legal review)
  - SCA / known-CVE check (`composer audit` clean)
  - Maintenance signal (last release < 12 months for non-stdlib packages)
- Do not add a dependency to do something the standard library or framework already does adequately.

---

## 7. How to handle ambiguity

When the user request is underspecified:

1. **Re-read the spec** for the relevant Mid-Level Objective and Low-Level Task.
2. If still ambiguous, **list the assumptions** you would otherwise make silently.
3. Propose 2 (or 3) options with trade-offs in 2–4 lines each.
4. Wait for confirmation. Do not pick "the most reasonable" silently in regulated-domain code.

Bad agent behaviour example:

> User: "Add a way to bulk-freeze cards"
> ❌ Agent silently adds `POST /cards/bulk-freeze` accepting an array of IDs and emitting one audit event for the batch.
>
> Correct: surface the questions: "Per-card audit events or batch event? RBAC: support role allowed, or compliance only? Idempotency key per request or per card? Partial-success semantics: 207 multi-status or all-or-nothing?"

---

## 8. Anti-patterns specific to this project

| Anti-pattern                                                              | Why it's wrong here                                          |
| ------------------------------------------------------------------------- | ------------------------------------------------------------ |
| `setStatus()` on `Card`                                                   | Bypasses state machine (§3.5).                               |
| `$logger->info("Card $pan frozen")`                                       | PAN in logs (§3.1) — even if redactor would catch it, the developer must not write code that depends on the redactor as a safety net. |
| `dispatch($command); $this->updateState();`                               | Two-write problem; use transactional outbox.                 |
| `if ($user->id === $card->ownerId)` in controller, no repository check    | Single-layer authz; spec requires defense in depth.          |
| `try { processor->call(); } catch (\Throwable $e) { /* swallow */ }`      | Silent failure on processor side breaks reconciliation.      |
| `'amount' => 12.50` in any persisted/serialised form                      | Float for money (§3.2).                                      |
| Using `DateTime::now()` inside a domain service                           | Untestable; inject `Clock` interface.                        |
| Adding a new field to `transactions` response without OpenAPI schema update | Breaks contract-first; PCI exposure risk if field reveals PAN-adjacent data. |

---

## 9. PR / change description template

When the AI proposes a change, the description should answer:

1. **Which MLO / low-level task does this address?** (e.g., `MLO-3 / B.1 AC-4`)
2. **What invariants did I check?** (state machine, money rules, sensitive data)
3. **What tests did I add or update?** (categories + names)
4. **What did I deliberately *not* do?** (out-of-scope items, deferred refactors)
5. **What ambiguity did I resolve, and how?** (assumption log)

---

## 10. When to escalate to a human

- Any change touching: PAN/CVV handling, audit event schema, state machine transitions, RBAC matrix, retention period, encryption keys.
- Any change that would alter PCI scope (e.g., adding a field that *might* be cardholder data).
- Any change that would break backward compatibility on a published contract (OpenAPI, Kafka schema).
- Any apparent conflict between the spec and a stakeholder request.

In these cases, the AI prepares a written analysis (impact, options, risks) and waits for human sign-off before producing code.
