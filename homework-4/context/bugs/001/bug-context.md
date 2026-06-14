# Bug Context — Task Tracker API

**ID**: 001
**App**: Task Tracker (FastAPI + sqlite3)
**Created**: 2026-05-23
**Status**: seeded, awaiting pipeline run

---

## 🎯 Purpose

This document catalogs the **intentionally seeded** issues planted in
`src/app.py` so the 4-agent pipeline has concrete material to discover,
fix, and verify. Reviewers can use this file to cross-check that the
pipeline's outputs (`verified-research.md`, `fix-summary.md`,
`security-report.md`, `test-report.md`) correctly identify and resolve
every seeded issue.

> **Important**: the Bug Researcher agent must **not** read this file —
> it would defeat the purpose of the homework. The reviewer may consult
> it after the pipeline completes.

---

## 🐛 Seeded Bugs (logic / behavioural)

### Bug #1 — Off-by-one in pagination

- **Location**: `src/app.py`, `list_tasks()` endpoint, line ~91
- **Symptom**: caller requesting `?limit=N` receives `N-1` rows.
- **Root cause**: query parameter is decremented before being bound:
  `(limit - 1, offset)` instead of `(limit, offset)`.
- **Severity**: Medium — silently wrong data; not crash-visible.
- **How to reproduce**:
  ```bash
  # Seed 5 tasks then list with limit=5
  curl 'http://localhost:8000/tasks?limit=5'   # returns 4 tasks
  ```

### Bug #2 — `complete_task` returns 200 for non-existent task

- **Location**: `src/app.py`, `complete_task()` endpoint, line ~108
- **Symptom**: `PATCH /tasks/999/complete` returns `200 {"status":"completed","id":999}`
  even though no task with id=999 exists.
- **Root cause**: SQL `UPDATE` on missing row is a no-op; the handler
  does not inspect `rowcount` and does not raise 404.
- **Severity**: Medium — violates REST semantics, breaks idempotency
  contracts for clients that rely on status codes.

---

## 🚨 Seeded Security Issues

### Security #1 — SQL Injection in `GET /tasks/{task_id}`

- **Location**: `src/app.py`, `get_task()` endpoint, line ~99
- **Vector**: `task_id` is declared as `str` and concatenated into raw
  SQL via f-string: `f"SELECT * FROM tasks WHERE id = {task_id}"`.
- **Severity**: CRITICAL.
- **Exploitation examples**:
  ```bash
  # Bypass row filter — returns all rows
  curl 'http://localhost:8000/tasks/1%20OR%201=1'
  # Destructive — drops table
  curl 'http://localhost:8000/tasks/1%3B%20DROP%20TABLE%20tasks%20--'
  ```
- **Required fix**: change `task_id: str` → `task_id: int`, switch to
  parameterised query `("SELECT ... WHERE id = ?", (task_id,))`.

### Security #2 — Hardcoded admin secret

- **Location**: `src/app.py`, module top, line ~17
- **Issue**: `ADMIN_API_KEY = "supersecret-admin-key-do-not-commit"`
  is committed to source control.
- **Severity**: HIGH.
- **Required fix**: load from environment variable; refuse to start if
  unset; never commit the literal.

---

## 📊 Expected Pipeline Outcome

After running `./run-pipeline.sh`:

| Artifact                 | Should mention                                   |
| ------------------------ | ------------------------------------------------ |
| `verified-research.md`   | All 4 seeded issues, file:line, quality ≥ L3     |
| `implementation-plan.md` | Concrete before/after snippets for all 4         |
| `fix-summary.md`         | 4 applied changes, tests run, status PASS        |
| `security-report.md`     | At minimum Security #1 (CRITICAL) and #2 (HIGH)  |
| `test-report.md`         | Tests covering both bugs + parametrised SQLi probe |

If the pipeline misses an issue, that is a real failure mode worth
documenting in the homework writeup — not something to paper over.
