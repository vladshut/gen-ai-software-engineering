# Homework 3 — Specification-Driven Design

**Author:** Vladyslav Shut
**Submission date:** 2026-05-08
**Topic:** Virtual Card Lifecycle Management — specification package for a regulated FinTech context.
**AI Tools Used:** Claude (Opus 4.7 + Adaptive Thinking) + Claude Code (just to commit and push) 

## Task summary

Produce a layered specification package for a finance-oriented application without writing any implementation. Deliverables:

1. `specification.md` — the layered product / feature specification.
2. `agents.md` — operating manual for AI coding agents working in the project.
3. `.claude/CLAUDE.md` — Claude Code editor-time rules (the chosen "editor / AI rules" deliverable).
4. `README.md` — this file: rationale, choices, industry-practice mapping.

The graded artifact is the specification's depth, traceability, and quality of decomposition — not breadth of features.

---

## Feature choice and scope decision

I chose **virtual card lifecycle management** because:

- It has a well-defined state machine (small enough to be exhaustive, large enough to require care).
- It naturally exposes the things this homework cares about: idempotency, audit, async propagation, sensitive-data handling, RBAC, limit invariants, eventual consistency in a read model.
- It has a clear *boundary* against systems we deliberately don't own (issuer processor, ledger, decisioning), which forces the spec to be honest about what it is and isn't responsible for. That boundary discipline is more pedagogically useful than a feature that pretends to do everything.

I rejected broader options ("a banking app", "a wallet") because they would have produced a wider but shallower spec. The grading rubric rewards depth and traceability over breadth.

---

## Rationale — why the spec is shaped this way

### Layering decisions

The spec uses six explicit layers (high-level objective → mid-level objectives → NFRs → implementation notes → context → low-level tasks) because each answers a different question and a different reader needs a different layer:

- **Product / business** reads §1–§3 (what is the outcome, who benefits, how do we know we got there).
- **Compliance / security** reads §4 (NFRs, audit, retention) and §10 (edge cases with compliance impact).
- **Engineering** reads §5–§9 and §11 (guardrails, context, state machine, low-level tasks, verification).
- **AI agents** read §5 (implementation notes) plus `agents.md` and `.claude/CLAUDE.md`.

If any of these audiences had to read the whole spec to find their parts, the spec would be working against its readers. The layering is for *navigability*, not just structure.

### Traceability

Every Mid-Level Objective (MLO-1 to MLO-9) is referenced by:
- The Non-Functional Requirements that constrain it (§4).
- One or more Low-Level Tasks that implement it (§9), with explicit `MLO-x` annotation.
- A Verification entry (§11) describing how its success is observed.

The verification table in §11 is intentionally a *reverse index*: given an objective, find the tests. This means a reviewer checking whether the spec is implementable can check coverage in O(MLO count) rather than searching ad-hoc.

### Why MLOs are testable, not aspirational

I deliberately phrased mid-level objectives as observable signals (e.g., "Two requests with same `Idempotency-Key` produce one card and identical responses") rather than goals ("system should be idempotent"). The latter is unfalsifiable in code review and will be ignored under deadline pressure; the former is a checkbox a reviewer can either tick or not.

### How performance targets were chosen

The targets in §4.5 are **assumed**, not measured. Their justification is:

- **Mobile UX baselines.** "Below 100 ms feels instant; below 1 s feels responsive; above 3 s loses the user." This is broadly consistent with Nielsen Norman / Google RAIL guidance. So freeze and lookup endpoints sit at sub-second P95; issuance, which has a synchronous external call, is allowed up to 1.5 s P99.
- **Card-freeze criticality.** A freeze that takes 5 s when the user thinks their card is stolen is a *trust* failure even if it succeeds. That motivates the local-commit-then-async-propagate design (MLO-9) and the median ≤ 2 s end-to-end target.
- **Throughput.** I sized for ~1 M cardholders. Per-cardholder operation rate is low (mostly views, occasional mutations), so 200 RPS sustained / 800 RPS burst is generous. I would refine these once we had production telemetry; the homework deliberately required reasoning, not measurement.
- **Honesty.** I labelled them "assumed targets" in the spec to make clear these are inputs to capacity planning, not committed SLAs. Pretending these are SLAs without measurement is a common spec failure I wanted to avoid.

### How verification depth was chosen

For each MLO I picked the *cheapest* verification that gives high confidence:

- State machine: exhaustive transition matrix is cheap (O(states²)) and catches almost everything.
- Idempotency: integration test pair is sufficient; property test is cheap insurance.
- Sensitive-data handling: combination of static check (forbidden field list in CI) + runtime canary (synthetic log line) — neither alone is sufficient, the combination is much stronger.
- Compliance / RBAC precedence: integration tests + manual compliance review — the manual step is irreducible because the spec encodes a regulatory expectation, not just a code-level rule.

I avoided "prefix every section with 'comprehensive testing required'" — that's the kind of phrase that signals the spec wasn't actually thought through.

### What the spec deliberately does *not* do

To keep the deliverable honest:

- It doesn't pretend to specify the issuer processor's contract — that's an external dependency I called out as a black box.
- It doesn't enforce regulatory caps numerically (e.g., "5,000 EUR for unverified accounts" is a placeholder); those are jurisdiction-specific and product-decided.
- It explicitly lists open questions in §14 instead of pretending they're solved.

A spec that pretends to resolve every open question is worse than one that flags them — the reader is then surprised at implementation time.

---

## Industry best practices — what's where

| Practice                                                                | Where it appears                                                                              | Why it matters here                                                                                       |
| ----------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| **PCI scope minimisation via tokenisation**                             | spec §1, §4.1, §4.6, §13; agents.md §3.1; CLAUDE.md hard-rule #1                              | Holding only `last4` + `processor_card_id` aims for SAQ-A scope rather than SAQ-D; a 100x reduction in audit overhead. |
| **Strong Customer Authentication (PSD2)**                               | spec §4.1, §10 (E5)                                                                           | Required for cardholder write actions in EU regulated context.                                            |
| **Defense in depth on authorization** (controller + repository)         | spec §5.1 of agents.md (§3.6); spec §9 F.1                                                    | Single-layer authz fails open under refactor; defense in depth localises errors.                          |
| **Idempotency keys (Stripe-style)**                                     | spec §5.3, §9 A.1, F.2; agents.md §3.4                                                        | Mobile clients retry on poor networks; without idempotency every retry is a money-loss risk.              |
| **Transactional outbox pattern** for state + event consistency          | spec §5.8, §9 E.1; agents.md §3.5; CLAUDE.md hard-rule #5                                     | Avoids the dual-write problem (state saved, event lost on crash). This is the single most-violated pattern in event-driven systems. |
| **Immutable, hash-chained audit log**                                   | spec §4.3, §9 E.1                                                                             | Tamper evidence is a regulator expectation under DORA/PSD2 even if not always required by name.           |
| **RFC 9457 Problem Details for HTTP API errors**                        | spec §5.4                                                                                     | Standardised error shape for clients; also reduces ad-hoc message drift.                                  |
| **Optimistic concurrency control on aggregates**                        | spec §5.7, §9 C.1                                                                             | Pessimistic locks don't compose with HTTP retries; optimistic locks force the design to admit conflicts.  |
| **Bounded context discipline** (CMS vs ledger vs processor)             | spec §1, §6, §7, §12                                                                          | Without this, a card service grows into a ledger; auditing and PCI scoping then become impossible.        |
| **Fail-closed on AML timeout**                                          | spec §9 A.2 AC-1                                                                              | Conservative default in a regulated domain; documented as ADR, not silent.                                |
| **Cardholder timezone for limit windows**                               | spec §5.5, §8.3, §10 (E9)                                                                     | A common oversight; UTC midnight makes "daily limit" surprising for users in distant zones.               |
| **Generic error message to user, specific reason in audit**             | spec §5.4, §10 (E7)                                                                           | Avoids leaking compliance signals (sanctions hits, fraud heuristics) to potential adversaries.            |
| **Webhook signature + replay window**                                   | spec §9 D.1; CLAUDE.md hard-rule #8                                                           | Signed webhooks alone don't prevent replay; the timestamp + window pair does.                             |
| **Reconciliation between local intent and external enforcement state**  | spec §9 E.3                                                                                   | The freeze-propagation pattern is *only* safe with a reconciliation job; without it, divergence is silent. |
| **PII redaction at framework level, not developer discipline**          | spec §5.6; agents.md §3.1, §4.4                                                               | Treating sensitive-data handling as an enforced runtime concern survives staff turnover; comments don't.  |
| **GDPR Article 17 with audit retention exception**                      | spec §4.2                                                                                     | Pseudonymisation rather than deletion preserves the audit chain while honouring the user's right.         |
| **Threat modelling baked into PR template**                             | agents.md §6.2                                                                                | STRIDE-on-a-line is cheap and catches most regressions on new endpoints.                                  |

---

## Critical self-assessment — what could be argued against

I'd rather flag the weaknesses than have a reviewer find them:

1. **The spec is processor-aware but not processor-specific.** A real spec would name the processor (Marqeta, Galileo, Stripe Issuing) and inherit constraints (e.g., Marqeta's rate limits, Stripe's webhook retry behaviour). I made it abstract because the homework asked for a feature spec, not a vendor integration design — but that abstraction is a real cost in production.
2. **NFR numbers are not benchmarked.** They're justified by UX heuristics, not measured. In production I'd want to refine after a load test.
3. **The state machine is small.** Real card lifecycles include reissuance, expiry, replacement, suspension-pending-review, hot-list, etc. I deliberately scoped down to keep the spec focused; a production spec would expand §8.2.
4. **The audit event taxonomy is illustrative, not exhaustive.** A real audit schema would also cover read-side actions like "card details viewed by support agent" with finer granularity (which fields were viewed). I included one example (`card_details.viewed`) as a placeholder.
5. **No data residency variation.** The spec states "EU only"; a multi-region service has subtler routing rules (e.g., card belongs to a region; processor adapter routes per region). Out of scope here, but real.
6. **Cardholder authentication is delegated to "auth gateway" without specifying.** This is correct decomposition but means the spec relies on a service it doesn't define. A reader has to trust that gateway exists and behaves correctly.
7. **`agents.md` overlaps `specification.md` in places.** The redundancy is intentional (agents.md is the operating manual; spec is the source of truth) but it does mean two places to update.

---

## How to navigate the deliverables

Read in this order if you want to evaluate the design quickly:

1. `README.md` (this file) — context and rationale.
2. `specification.md` §1–§4 — what / why / how-well.
3. `specification.md` §8 — the state machine; this is where the core design lives.
4. `specification.md` §9.B — lifecycle low-level tasks; representative of decomposition style.
5. `specification.md` §10 — edge cases as a single concentrated table.
6. `agents.md` — how I'd want an AI agent to behave in this codebase.
7. `.claude/CLAUDE.md` — short, fast-feedback editor rules.

Total reading time, end-to-end: ≈ 30 minutes. Spot-check time, top to §8: ≈ 8 minutes.
