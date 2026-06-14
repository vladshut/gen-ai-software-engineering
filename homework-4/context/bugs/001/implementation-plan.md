# Implementation Plan — bug 001

> Produced by: `bug-planner` agent (model: opus)
> Date: 2026-05-23
> Verified-research status: PASS, L4 — proceeding.

## Summary

- **Changes**: 4
- **Files touched**: `src/app.py`, `src/.env.example` (new)
- **Order**: change-1 (env scaffolding) → change-2 (SQLi) → change-3 (pagination) → change-4 (404)
- **Rationale for order**: change-1 is a prerequisite for change-2's
  related hardening but is independent enough to commit first. The
  other three are mutually independent.

---

## Change 1 — Replace hardcoded admin secret with env var

- **Finding ref**: F-004
- **File**: `src/app.py`
- **Lines**: 15–19
- **Before**:
  ```python
  # 🚨 SEEDED SECURITY ISSUE #2: hardcoded admin secret in source.
  # Should be loaded from environment variable.
  ADMIN_API_KEY = "supersecret-admin-key-do-not-commit"
  ```
- **After**:
  ```python
  import os
  ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY")
  if not ADMIN_API_KEY:
      raise RuntimeError(
          "ADMIN_API_KEY environment variable is required. "
          "See .env.example for setup."
      )
  ```
- **Prerequisite**: create `src/.env.example` documenting the variable.
- **Test command** (smoke — comprehensive tests come from Unit Test Generator):
  ```bash
  ADMIN_API_KEY=test-key pytest tests/test_smoke.py -v
  ```

---

## Change 2 — Parameterise `get_task` query and tighten type

- **Finding ref**: F-002
- **File**: `src/app.py`
- **Lines**: 97–104
- **Before**:
  ```python
  @app.get("/tasks/{task_id}", response_model=Task)
  def get_task(task_id: str) -> Task:
      conn = get_db()
      query = f"SELECT * FROM tasks WHERE id = {task_id}"
      row = conn.execute(query).fetchone()
  ```
- **After**:
  ```python
  @app.get("/tasks/{task_id}", response_model=Task)
  def get_task(task_id: int) -> Task:
      conn = get_db()
      row = conn.execute(
          "SELECT * FROM tasks WHERE id = ?", (task_id,)
      ).fetchone()
  ```
- **Test command** (smoke):
  ```bash
  ADMIN_API_KEY=test-key pytest tests/test_smoke.py -v
  ```

---

## Change 3 — Fix off-by-one in pagination

- **Finding ref**: F-001
- **File**: `src/app.py`
- **Lines**: 88–94
- **Before**:
  ```python
  rows = conn.execute(
      "SELECT * FROM tasks ORDER BY id LIMIT ? OFFSET ?",
      (limit - 1, offset),
  ).fetchall()
  ```
- **After**:
  ```python
  rows = conn.execute(
      "SELECT * FROM tasks ORDER BY id LIMIT ? OFFSET ?",
      (limit, offset),
  ).fetchall()
  ```
- **Test command** (smoke):
  ```bash
  ADMIN_API_KEY=test-key pytest tests/test_smoke.py -v
  ```

---

## Change 4 — Return 404 from `complete_task` when row missing

- **Finding ref**: F-003
- **File**: `src/app.py`
- **Lines**: 107–113
- **Before**:
  ```python
  @app.patch("/tasks/{task_id}/complete")
  def complete_task(task_id: int) -> dict:
      conn = get_db()
      conn.execute("UPDATE tasks SET completed = 1 WHERE id = ?", (task_id,))
      conn.commit()
      conn.close()
      return {"status": "completed", "id": task_id}
  ```
- **After**:
  ```python
  @app.patch("/tasks/{task_id}/complete")
  def complete_task(task_id: int) -> dict:
      conn = get_db()
      cur = conn.execute(
          "UPDATE tasks SET completed = 1 WHERE id = ?", (task_id,)
      )
      conn.commit()
      updated = cur.rowcount
      conn.close()
      if updated == 0:
          raise HTTPException(status_code=404, detail="Task not found")
      return {"status": "completed", "id": task_id}
  ```
- **Test command** (smoke):
  ```bash
  ADMIN_API_KEY=test-key pytest tests/test_smoke.py -v
  ```

---

## Notes for the Bug Fixer

- Per-change verification uses the existing smoke test, which checks
  the app still starts and exposes its OpenAPI schema. This catches
  catastrophic regressions (import errors, syntax mistakes) after
  each change.
- Comprehensive regression tests for each finding will be added by the
  Unit Test Generator agent **after** all four changes are applied
  and the Security Verifier has run.
- After all four changes, run the smoke suite one more time:
  `ADMIN_API_KEY=test-key pytest tests/ -v`. Result will be recorded
  in `fix-summary.md`.
