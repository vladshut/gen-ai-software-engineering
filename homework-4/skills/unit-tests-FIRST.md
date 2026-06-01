---
name: unit-tests-FIRST
description: Use this skill whenever generating, reviewing, or critiquing unit tests. Trigger on requests like "write tests", "add coverage", "generate unit tests", or whenever a Unit Test Generator agent must produce a `test-report.md`. Apply even when tests already exist — use FIRST as the audit rubric. The skill defines the five FIRST principles (Fast, Independent, Repeatable, Self-validating, Timely) and how to verify each.
---

# FIRST Principles for Unit Tests

## Purpose

Define the FIRST contract that **every** unit test produced by the Unit
Test Generator must satisfy, and provide a deterministic checklist a
reviewer can apply.

The Unit Test Generator agent must reference this skill in its agent
file and apply the checklist below before emitting `test-report.md`.

## The Five Principles

### F — Fast

Tests must run in milliseconds, not seconds.

**Guidance**

- No real network calls. Use `TestClient`, `httpx.MockTransport`, or
  equivalent in-process fakes.
- No real database. Use in-memory SQLite (`:memory:`) or per-test
  temp file.
- No `time.sleep`. If timing matters, inject a clock.
- Target: full unit suite under 5 seconds for this homework's scope.

**Verification**

```bash
pytest --durations=10
```
Any test over 200 ms is suspect; over 1 s is a violation.

### I — Independent

Tests must not depend on order, shared state, or each other's outputs.

**Guidance**

- Fresh DB per test (fixture with `scope="function"`).
- Do not store state in module-level variables.
- Do not assume a fixture from an earlier test "set things up".
- If two tests need the same setup, extract to a fixture.

**Verification**

```bash
pytest -p no:randomly --tb=no -q                # deterministic order
pytest --random-order --tb=no -q                # randomised order
diff <(pytest --tb=no -q) <(pytest --random-order --tb=no -q)
```
Both runs must pass; failure under randomisation = ordering coupling.

### R — Repeatable

Same input → same result, every run, every machine.

**Guidance**

- No reliance on real `datetime.now()`. Inject a clock or use freezegun.
- No reliance on uuid randomness in assertions. Either inject a uuid
  factory or assert on shape rather than value.
- No reliance on filesystem layout outside the test's own tempdir.
- No reliance on environment variables that are not set by the test
  itself.

**Verification**

Run the suite three times consecutively. Failure rate must be 0/3.

### S — Self-validating

Pass or fail must be unambiguous from exit code. No "look at the logs".

**Guidance**

- Every test ends with at least one `assert`.
- Avoid bare `print()` for verification.
- Avoid catching exceptions broadly (`except Exception: pass`).
- Use `pytest.raises` to assert on expected exceptions, not try/except.

**Verification**

Search the test file for `print(`, bare `except`, missing `assert` —
any hit is a violation.

### T — Timely

Tests are written close to (ideally just before) the production code
under test. For this pipeline, "timely" means the Unit Test Generator
writes tests **as part of the same pipeline run** that applied the fix,
not later.

**Guidance**

- Tests cover **only the changed code** identified in `fix-summary.md`.
- Tests are committed in the same change-set as the fix.
- For regression tests of the seeded bugs, the assertion must demonstrate
  the failure mode (e.g. "limit=5 returns 5 items, not 4").

**Verification**

Cross-reference every test against `fix-summary.md`. Tests that touch
unchanged code are out of scope for this agent and should be flagged,
not produced.

## Required Structure of `test-report.md`

```markdown
# Test Report — bug 001

## Scope
- Files under test: ...
- Source of scope: fix-summary.md

## FIRST Compliance Checklist
| Principle | Status | Evidence |
|-----------|--------|----------|
| Fast       | ✅/❌  | `pytest --durations` output |
| Independent| ✅/❌  | ordered vs randomised run diff |
| Repeatable | ✅/❌  | 3 consecutive runs all green |
| Self-validating | ✅/❌  | grep for forbidden patterns |
| Timely     | ✅/❌  | every test maps to fix-summary entry |

## Tests Added
- path/to/test_file.py::test_name — covers [bug-id / security-id]

## Run Output
```
pytest -v
... raw output ...
```

## Coverage Notes
- Lines covered for changed files: X / Y
- Anything intentionally not covered: ...
```

## Anti-patterns to Reject

- **Tautological tests** (`assert response.status_code == response.status_code`).
- **Snapshot-only tests** that assert against generated golden files
  with no semantic check.
- **Tests that pass on buggy code** because the assertion is too weak.
- **Tests with mocks of the code under test** — mock collaborators, not
  the thing you are testing.
