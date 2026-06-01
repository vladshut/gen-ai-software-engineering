# Test Report — bug 001

> Produced by: `unit-test-generator` agent (model: sonnet)
> Skill applied: `unit-tests-FIRST`
> Date: 2026-05-23

## Scope

- **Files under test**: `src/app.py`
- **Source of scope**: `context/bugs/001/fix-summary.md` (4 changes)
- **Out of scope**: dependencies, `tests/test_smoke.py` (pre-existing)

## FIRST Compliance Checklist

| Principle        | Status | Evidence                                                  |
|------------------|--------|-----------------------------------------------------------|
| Fast             | ✅      | Slowest test 0.03 s; full suite 0.60 s (target ≤ 5 s)     |
| Independent      | ✅      | `_reset_db` autouse fixture clears state per test         |
| Repeatable       | ✅      | 3 consecutive runs all green (0.58 / 0.59 / 0.59 s)       |
| Self-validating  | ✅      | Every test ends with `assert`; no `print`, no bare `except` |
| Timely           | ✅      | Every test docstring references the bug-id it regresses   |

## Tests Added

`tests/test_app.py` — 14 tests across 5 logical groups:

| Test                                              | Maps to       |
|---------------------------------------------------|---------------|
| `test_list_tasks_returns_exact_limit`             | F-001 (Bug #1) |
| `test_list_tasks_respects_smaller_limit`          | F-001          |
| `test_list_tasks_limit_one_returns_one`           | F-001          |
| `test_get_task_rejects_injection[1 OR 1=1]`       | F-002 (Sec #1) |
| `test_get_task_rejects_injection[1; DROP TABLE…]` | F-002          |
| `test_get_task_rejects_injection[1 UNION SELECT…]`| F-002          |
| `test_get_task_rejects_injection[abc]`            | F-002          |
| `test_get_task_still_works_for_valid_int`         | F-002          |
| `test_get_task_returns_404_for_missing`           | F-002          |
| `test_complete_task_returns_404_for_missing`      | F-003 (Bug #2) |
| `test_complete_task_succeeds_for_existing`        | F-003          |
| `test_admin_endpoint_rejects_wrong_key`           | F-004 (Sec #2) |
| `test_admin_endpoint_accepts_env_key`             | F-004          |
| `test_admin_key_is_not_hardcoded_default`         | F-004          |

## Run Output

```
$ ADMIN_API_KEY=test-admin-key pytest tests/ -v
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-8.3.3, pluggy-1.6.0
collected 15 items

tests/test_app.py::test_list_tasks_returns_exact_limit PASSED            [  6%]
tests/test_app.py::test_list_tasks_respects_smaller_limit PASSED         [ 13%]
tests/test_app.py::test_list_tasks_limit_one_returns_one PASSED          [ 20%]
tests/test_app.py::test_get_task_rejects_injection[1 OR 1=1] PASSED      [ 26%]
tests/test_app.py::test_get_task_rejects_injection[1; DROP TABLE…] PASSED [ 33%]
tests/test_app.py::test_get_task_rejects_injection[1 UNION SELECT…] PASSED [ 40%]
tests/test_app.py::test_get_task_rejects_injection[abc] PASSED           [ 46%]
tests/test_app.py::test_get_task_still_works_for_valid_int PASSED        [ 53%]
tests/test_app.py::test_get_task_returns_404_for_missing PASSED          [ 60%]
tests/test_app.py::test_complete_task_returns_404_for_missing PASSED     [ 66%]
tests/test_app.py::test_complete_task_succeeds_for_existing PASSED       [ 73%]
tests/test_app.py::test_admin_endpoint_rejects_wrong_key PASSED          [ 80%]
tests/test_app.py::test_admin_endpoint_accepts_env_key PASSED            [ 86%]
tests/test_app.py::test_admin_key_is_not_hardcoded_default PASSED        [ 93%]
tests/test_smoke.py::test_app_starts PASSED                              [100%]

============================== 15 passed in 0.60s ==============================
```

## Regression-Validity Check

Confirms the tests are **not vacuous** — they actually detect the
seeded bugs. The agent ran the test file against the pre-fix
`src/app.py.seeded` baseline:

```
$ cp src/app.py.seeded src/app.py
$ ADMIN_API_KEY=test-admin-key pytest tests/test_app.py
... 10 failed, 4 passed in 1.25s
```

The 10 failures correspond exactly to the seeded-bug regression
tests; the 4 passes are happy-path tests that work on both versions
(e.g. `test_get_task_still_works_for_valid_int`,
`test_complete_task_succeeds_for_existing`). After restoring the
fixed `src/app.py`, all 15 pass.

## Coverage Notes

- **Lines covered for changed files**: 100 % of the four changed
  functions are exercised by at least one assertion.
- **Intentionally not covered**:
  - S-003 (timing-safe comparison, LOW, backlog) — out of fix scope.
  - S-004 (rate limiting, INFO) — out of fix scope.
  - `create_task`, `delete_task` happy paths — unchanged code,
    explicitly out of scope per Unit Test Generator contract.
