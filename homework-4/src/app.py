"""
Task Tracker API — Working application (post-pipeline state).

All seeded bugs and security issues catalogued in
context/bugs/001/bug-context.md have been resolved by the 4-agent
pipeline. The buggy baseline is preserved at src/app.py.seeded for
reproducibility — to re-run the pipeline, copy app.py.seeded over
app.py and execute ./run-pipeline.sh.
"""

import os
from typing import List, Optional

import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Task Tracker", version="0.2.0")

# Loaded from environment (fixed Security #2 — formerly hardcoded).
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY")
if not ADMIN_API_KEY:
    raise RuntimeError(
        "ADMIN_API_KEY environment variable is required. "
        "See src/.env.example for setup."
    )

DB_PATH = os.environ.get("TASKS_DB_PATH", "tasks.db")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            completed INTEGER DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None


class Task(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    completed: bool


def _row_to_task(row: sqlite3.Row) -> Task:
    return Task(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        completed=bool(row["completed"]),
    )


@app.post("/tasks", response_model=Task, status_code=201)
def create_task(payload: TaskCreate) -> Task:
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO tasks (title, description) VALUES (?, ?)",
        (payload.title, payload.description),
    )
    conn.commit()
    task_id = cur.lastrowid
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return _row_to_task(row)


@app.get("/tasks", response_model=List[Task])
def list_tasks(limit: int = 10, offset: int = 0) -> List[Task]:
    # Fixed Bug #1 — was `limit - 1`, now correctly bound as `limit`.
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM tasks ORDER BY id LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()
    conn.close()
    return [_row_to_task(r) for r in rows]


@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int) -> Task:
    # Fixed Security #1 — task_id is now int, query is parameterised.
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    return _row_to_task(row)


@app.patch("/tasks/{task_id}/complete")
def complete_task(task_id: int) -> dict:
    # Fixed Bug #2 — now checks rowcount and raises 404 on missing row.
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


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int) -> None:
    conn = get_db()
    cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Task not found")


@app.get("/admin/stats")
def admin_stats(api_key: str) -> dict:
    # Backlog (S-003): switch to hmac.compare_digest for timing-safe
    # comparison. Tracked in security-report.md as LOW severity.
    if api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) AS c FROM tasks").fetchone()["c"]
    completed = conn.execute(
        "SELECT COUNT(*) AS c FROM tasks WHERE completed = 1"
    ).fetchone()["c"]
    conn.close()
    return {"total": total, "completed": completed}
