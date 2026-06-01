# Fix Summary — bug 001

> Produced by: `bug-fixer` agent (model: sonnet)
> Date: 2026-05-23
> Plan ref: `context/bugs/001/implementation-plan.md`

## Changes Made

### Change 1 — Replace hardcoded admin secret with env var

- **File**: `src/app.py`
- **Lines**: 15–19 → 15–24
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
- **Prerequisite applied**: created `src/.env.example` with documented
  variable.
- **Test command**: `ADMIN_API_KEY=test-key pytest tests/test_smoke.py -v`
- **Test result**: ✅ PASS (1 passed in 0.18 s)

---

### Change 2 — Parameterise `get_task` query and tighten type

- **File**: `src/app.py`
- **Lines**: 97–104 → 97–104
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
- **Test command**: `ADMIN_API_KEY=test-key pytest tests/test_smoke.py -v`
- **Test result**: ✅ PASS (1 passed in 0.17 s)

---

### Change 3 — Fix off-by-one in pagination

- **File**: `src/app.py`
- **Lines**: 88–94 → 88–94
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
- **Test command**: `ADMIN_API_KEY=test-key pytest tests/test_smoke.py -v`
- **Test result**: ✅ PASS (1 passed in 0.16 s)

---

### Change 4 — Return 404 from `complete_task` when row missing

- **File**: `src/app.py`
- **Lines**: 107–113 → 107–118
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
- **Test command**: `ADMIN_API_KEY=test-key pytest tests/test_smoke.py -v`
- **Test result**: ✅ PASS (1 passed in 0.17 s)

---

## Overall Status

- **Status**: ✅ PASS
- **Total changes applied**: 4 / 4
- **Files modified**: `src/app.py`
- **Files created**: `src/.env.example`
- **Full suite result**: `ADMIN_API_KEY=test-key pytest tests/ -v` →
  PASS (1 passed in 0.17 s)
- **Duration**: ~5 s wall-clock for all four changes including test runs

## Manual Verification Steps

1. Start the app:
   ```bash
   ADMIN_API_KEY=test-key uvicorn app:app --app-dir src --reload
   ```
2. Verify pagination returns exactly `limit` items:
   ```bash
   # First seed 5 tasks via POST /tasks
   curl 'http://localhost:8000/tasks?limit=5'
   # Expected: array of 5 tasks
   ```
3. Verify SQL injection is blocked:
   ```bash
   curl -i 'http://localhost:8000/tasks/1%20OR%201=1'
   # Expected: 422 Unprocessable Entity (FastAPI type validation)
   ```
4. Verify 404 on missing complete:
   ```bash
   curl -i -X PATCH http://localhost:8000/tasks/9999/complete
   # Expected: HTTP/1.1 404 Not Found
   ```
5. Verify env var is required:
   ```bash
   unset ADMIN_API_KEY
   uvicorn app:app --app-dir src
   # Expected: RuntimeError on startup
   ```

## References

- Implementation plan: `context/bugs/001/implementation-plan.md`
- Verified research: `context/bugs/001/research/verified-research.md`
- Modified files: `src/app.py`, `src/.env.example` (new)
