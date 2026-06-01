# Security Report — bug 001

> Produced by: `security-verifier` agent (model: opus)
> Date: 2026-05-23

## Scope

- **Files reviewed** (full, post-fix state): `src/app.py`,
  `src/.env.example`
- **Source of scope**: `context/bugs/001/fix-summary.md`
- **Out of scope**: `src/requirements.txt` (dependency CVE scan is a
  separate concern for a dedicated agent / tool), `tests/`.

---

## Findings

### S-001 — SQL Injection via f-string interpolation in `get_task`

- **Severity**: CRITICAL
- **File**: `src/app.py:97` (pre-fix line range)
- **Class**: Injection / SQL
- **Status in this run**: fixed-by-bug-fixer
- **Pre-fix evidence**:
  ```python
  def get_task(task_id: str) -> Task:
      query = f"SELECT * FROM tasks WHERE id = {task_id}"
      row = conn.execute(query).fetchone()
  ```
- **Post-fix evidence** (confirms fix is correct):
  ```python
  def get_task(task_id: int) -> Task:
      row = conn.execute(
          "SELECT * FROM tasks WHERE id = ?", (task_id,)
      ).fetchone()
  ```
- **Exploitation (pre-fix)**:
  ```
  GET /tasks/1%20OR%201=1   → returns all rows
  GET /tasks/1%3B%20DROP%20TABLE%20tasks%20--   → destructive
  ```
- **Remediation applied**: type coerced to `int` (FastAPI validates,
  rejects non-integer with 422); query parameterised via `?`
  placeholder. Defence-in-depth holds even if one layer is bypassed.

---

### S-002 — Hardcoded admin secret in source

- **Severity**: HIGH
- **File**: `src/app.py:17` (pre-fix)
- **Class**: Authentication & secrets
- **Status in this run**: fixed-by-bug-fixer
- **Pre-fix evidence**:
  ```python
  ADMIN_API_KEY = "supersecret-admin-key-do-not-commit"
  ```
- **Post-fix evidence**:
  ```python
  ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY")
  if not ADMIN_API_KEY:
      raise RuntimeError(...)
  ```
- **Remediation applied**: loaded from environment, fail-fast on
  missing variable.
- **Residual concern (LOW)**: `compare_digest` should be used for the
  comparison `api_key != ADMIN_API_KEY` to prevent timing attacks. Not
  addressed in this fix scope. Recommend adding to backlog.

---

### S-003 — Timing-attack-vulnerable secret comparison

- **Severity**: LOW
- **File**: `src/app.py:127` (post-fix)
- **Class**: Authentication & secrets
- **Status in this run**: new-finding (out of scope of original
  research; surfaced during security review of changed code)
- **Evidence**:
  ```python
  if api_key != ADMIN_API_KEY:
      raise HTTPException(status_code=403, detail="Forbidden")
  ```
- **Exploitation**: a network-adjacent attacker with precise timing
  measurements could in theory leak the key one byte at a time. In
  practice extremely difficult to exploit over HTTP, but mechanically
  correct to use a constant-time comparator.
- **Remediation (recommended, not applied)**:
  ```python
  import hmac
  if not hmac.compare_digest(api_key or "", ADMIN_API_KEY):
      raise HTTPException(status_code=403, detail="Forbidden")
  ```
- **Decision**: documented as backlog item; does not block this
  pipeline run.

---

### S-004 — No rate limiting on `/admin/stats`

- **Severity**: INFO
- **File**: `src/app.py:124` (post-fix)
- **Class**: Defence-in-depth / brute force
- **Status in this run**: new-finding (advisory)
- **Evidence**: no decorator or middleware limits request rate.
- **Remediation (recommended)**: add `slowapi` or framework-level rate
  limit at 10 req/min/IP. Out of scope for this fix.

---

## Summary Table

| ID    | Severity | File:line         | Status              |
|-------|----------|-------------------|---------------------|
| S-001 | CRITICAL | src/app.py:97     | fixed-by-bug-fixer  |
| S-002 | HIGH     | src/app.py:17     | fixed-by-bug-fixer  |
| S-003 | LOW      | src/app.py:127    | open (backlog)      |
| S-004 | INFO     | src/app.py:124    | advisory            |

---

## Overall Posture

- **CRITICAL open**: 0
- **HIGH open**: 0
- **MEDIUM open**: 0
- **LOW open**: 1 (S-003, documented)
- **INFO**: 1 (S-004, advisory)
- **Pipeline gate**: ✅ **PASS**

The "Working application" deliverable is satisfied: no CRITICAL or
HIGH severity findings remain open after the Bug Fixer's changes.
