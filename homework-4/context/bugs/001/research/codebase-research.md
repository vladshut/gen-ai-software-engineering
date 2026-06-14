# Codebase Research — bug 001

> Produced by: `bug-researcher` agent (model: sonnet)
> Inputs read: `src/app.py`, `src/requirements.txt`, `tests/test_smoke.py`
> Date: 2026-05-23

## Coverage

- **Files inspected** (full read):
  - `src/app.py` (140 lines)
  - `src/requirements.txt` (5 lines)
  - `tests/test_smoke.py` (28 lines)
- **Files skipped**: none.
- **Protocol note**: `bug-context.md` was read only up to the
  "Expected Pipeline Outcome" heading, per agent contract.

---

## Findings

### F-001 — Off-by-one in pagination

- **File**: `src/app.py:88-94`
- **Suspected**: `LIMIT ?` is bound with `limit - 1` instead of `limit`,
  so a caller requesting `limit=N` receives `N-1` rows.
- **Severity guess**: medium
- **Excerpt**:
  ```python
  @app.get("/tasks", response_model=List[Task])
  def list_tasks(limit: int = 10, offset: int = 0) -> List[Task]:
      conn = get_db()
      rows = conn.execute(
          "SELECT * FROM tasks ORDER BY id LIMIT ? OFFSET ?",
          (limit - 1, offset),
      ).fetchall()
  ```
- **Reproduction**:
  ```bash
  # seed 5 rows then:
  curl 'http://localhost:8000/tasks?limit=5'   # observes 4 rows
  ```

---

### F-002 — SQL Injection in `GET /tasks/{task_id}`

- **File**: `src/app.py:97-104`
- **Suspected**: `task_id` is typed as `str` and concatenated into a
  raw SQL string via f-string. Both type and parameterisation are
  wrong.
- **Severity guess**: critical
- **Excerpt**:
  ```python
  @app.get("/tasks/{task_id}", response_model=Task)
  def get_task(task_id: str) -> Task:
      conn = get_db()
      query = f"SELECT * FROM tasks WHERE id = {task_id}"
      row = conn.execute(query).fetchone()
  ```
- **Reproduction**:
  ```
  GET /tasks/1 OR 1=1    → returns all rows
  GET /tasks/1; DROP TABLE tasks --   → destructive
  ```

---

### F-003 — `complete_task` returns 200 for non-existent ids

- **File**: `src/app.py:107-113`
- **Suspected**: SQL `UPDATE` on a missing row is a no-op in SQLite.
  The handler does not inspect `rowcount`, so the response is `200`
  for an id that does not exist.
- **Severity guess**: medium
- **Excerpt**:
  ```python
  @app.patch("/tasks/{task_id}/complete")
  def complete_task(task_id: int) -> dict:
      conn = get_db()
      conn.execute("UPDATE tasks SET completed = 1 WHERE id = ?", (task_id,))
      conn.commit()
      conn.close()
      return {"status": "completed", "id": task_id}
  ```
- **Reproduction**:
  ```bash
  curl -X PATCH http://localhost:8000/tasks/9999/complete
  # → 200 {"status":"completed","id":9999}
  ```

---

### F-004 — Hardcoded admin secret

- **File**: `src/app.py:17`
- **Suspected**: `ADMIN_API_KEY` is hardcoded in source. Anyone with
  read access to the repo can call `/admin/stats`.
- **Severity guess**: high
- **Excerpt**:
  ```python
  ADMIN_API_KEY = "supersecret-admin-key-do-not-commit"
  ```
- **Reproduction**:
  ```bash
  curl 'http://localhost:8000/admin/stats?api_key=supersecret-admin-key-do-not-commit'
  # → {"total":..., "completed":...}
  ```

---

## Self-audit

- Every claim has a file and line number from `src/app.py`.
- Every excerpt was copied verbatim from the file.
- Four findings: F-001 (pagination), F-002 (SQLi), F-003 (missing 404),
  F-004 (hardcoded secret).
- No invented findings.
