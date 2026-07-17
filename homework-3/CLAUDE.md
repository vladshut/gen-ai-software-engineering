# CLAUDE.md — Claude Code rules for `card-management-service`

> **This file is for editor-time AI assistance** (Claude Code, autocompletion, in-editor refactors).
> Substantive policy lives in `agents.md`. This file is the *short, fast-feedback layer*: things I want Claude to remember on every keystroke, without re-reading the full spec.

When in doubt, defer to: `specification.md` → `agents.md` → this file.

---

## Project at a glance

- **What it is:** Virtual card lifecycle management service. Owns: card metadata, state machine, limits, transaction read model, audit. Does **not** own: PAN, authorization decisions, funds ledger.
- **Stack:** PHP 8.2, Symfony 6.4 LTS, Doctrine ORM 3, PostgreSQL 15, Redis 7, Kafka, PHPUnit 11.
- **Bounded context:** finance / regulated. Defaults are stricter than usual web-app defaults.

---

## Hard rules — never violate

1. **No PAN, CVV, full magstripe, or PIN** in: code, comments, logs, traces, exceptions, fixtures, dumps, screenshots. Only `last4` and `bin` are acceptable PAN-derived fields.
2. **All money is integer minor units** + ISO-4217 currency. Never `float`. Always via `Money` value object for arithmetic.
3. **All write endpoints require `Idempotency-Key` header.** Validated by middleware. A controller without it is a defect.
4. **State changes go through aggregate methods**, not setters. `$card->freeze($reason, $actor)`, never `$card->setStatus(...)`.
5. **State change + audit event = one DB transaction.** Use the transactional outbox. Never "save then publish".
6. **Authorization: defense in depth.** Controller attribute *and* repository ownership check. Cross-tenant ID guess returns `404`, not `403`.
7. **Compliance lock supersedes user/support actions.** A user/support unfreeze on a `compliance_lock=true` card returns `403 compliance_lock`.
8. **Webhooks must verify HMAC signature.** Never disable, even "temporarily for debugging".

If a refactor or generation would break any of the above, **stop and ask.** Do not produce code with a `// TODO fix later` for these rules.

---

## Code shape defaults

- Service classes: `final class`, all properties `readonly`, dependencies via constructor.
- Value objects: `final readonly class`.
- **No traits** for code reuse.
- **No abstract classes** unless modelling a domain hierarchy.
- Interface naming: no `I` prefix, no `Interface` suffix when there's one production binding. Production binding ends in `Implementation` or describes the technology (e.g., `HttpAmlScreener`, `DoctrineCardRepository`).
- Exceptions: domain / application / infrastructure separation. Never catch `\Throwable` outside the global handler.
- Time: never call `new DateTimeImmutable()` directly in domain services; inject `Psr\Clock\ClockInterface`.

---

## Tests

- Prefer **factories + fakes** over mocks. Mock only at the outermost wire boundary.
- Never mock the system under test.
- Coverage targets (informational; CI enforces critical paths):
  - `src/Domain/`: ≥ 90 % line, mutation score ≥ 70 % on state machine and limit invariants.
  - All controllers: integration test with happy + each error code.
  - All adapters: contract test.
- Test PANs: use canonical PCI test values (e.g., `4111111111111111`). Never make up new sequences.

---

## Naming

- Files: `PascalCase.php` for classes; one class per file.
- Routes: `/cards`, `/cards/{cardId}`, `/cards/{cardId}/freeze`, etc. Resource names plural, actions as POST sub-resources.
- DB tables: `snake_case`, plural (`cards`, `card_limits`, `audit_events`).
- DB columns: `snake_case`. Booleans: `is_*` or `has_*`. Timestamps: `*_at`.
- Doctrine entities: `App\Domain\<Aggregate>\<Entity>`.
- Audit event types: `<aggregate>.<verb>` past tense (e.g., `card.frozen`, `limit.changed`).

---

## When generating new code

- New controller? Apply: `#[Route]`, `#[IsGranted]`, `Idempotency-Key` middleware, `RequestValidator`, mapping exception → RFC 9457 problem detail.
- New aggregate method? Emit a domain event; method should return `void` for state changes, returning data implies a query.
- New webhook handler? Signature check first, idempotency check second, then business logic.
- New limit rule? Check the invariants chain `per_tx ≤ daily ≤ monthly`; check currency match; check regulatory cap.

---

## Style preferences (low-stakes)

- Prefer named arguments at call sites for constructors with > 2 parameters.
- Prefer `match` over `switch`.
- Prefer `enum` over class constants for closed sets (statuses, reason codes).
- Group `use` statements: PHP stdlib, vendor, app — alphabetised within group.
- No comments restating what the code does; comments explain *why* if non-obvious, or reference the spec section.

---

## What to surface, not silently fix

When Claude notices these, **flag** them rather than auto-fixing during an unrelated change:

- A PAN-shaped string in a log call.
- A controller without `Idempotency-Key` middleware.
- A state mutation outside the state machine.
- Mocking a domain class (likely "testing the test").
- Float arithmetic on a money field.
- A `try/catch (\Throwable)` in non-global code.
- A migration that drops or renames an audit-related column.

These are signals of design decay; flag them in the PR/comment so a human decides whether to widen scope.

---

## Reference files (source of truth)

- `specification.md` — what the system does and its invariants.
- `agents.md` — full agent operating manual; refusal rules; PR templates.
- `docs/adr/` — architecture decisions; consult before challenging a long-standing pattern.
- `docs/runbooks/` — operational procedures (incident response, key rotation).

---

## Quick refusal phrases (for when a request would break a hard rule)

- *"I can't add PAN to logs — `agents.md §3.1` and PCI scope. I can add `card_id` and `last4` instead, which gives you the diagnostic value without the scope impact."*
- *"That endpoint mutates state but I see no `Idempotency-Key` plan. Want me to add the middleware now, or are we postponing for a follow-up? I'd rather not ship the controller without it."*
- *"This would create a state-machine transition not in `specification.md §8.2`. Either we update the spec (and ADR) or this is the wrong shape — which one?"*

The aim isn't pedantry. It's that in regulated finance, a 30-second clarification is cheaper than a 30-day audit finding.
