# How to run

Numbered setup → demo steps. All commands run from the `homework-6/`
project root.

## 1. Create the virtual environment (Python 3.12+)

```bash
python3.14 -m venv .venv        # or any python >= 3.12
./.venv/bin/python -m pip install --upgrade pip
```

## 2. Install dependencies

```bash
./.venv/bin/python -m pip install pytest pytest-cov fastmcp
# or, using the project metadata:
./.venv/bin/python -m pip install -e ".[dev]"
```

## 3. Validate transactions (dry-run, no files written)

```bash
./.venv/bin/python -m agents.transaction_validator --dry-run sample-transactions.json
```
Expect TXN006 (currency `XYZ`) and TXN007 (negative amount) to be **rejected**;
account numbers are masked to last 4 (`****1001`).

## 4. Run the full pipeline

```bash
./.venv/bin/python integrator.py
```
This resets `shared/`, runs validator → fraud → settlement, masks PII in logs,
writes each final record to `shared/results/<txn>.json`, and asserts the
**oracle** (prints `✅ Oracle check passed`).

## 5. Run the tests with coverage

```bash
./.venv/bin/python -m pytest --cov=agents --cov=common --cov-report=term-missing
```
Expect all tests passing at **≥ 90%** coverage.

## 6. Try the coverage gate (push protection)

Enable the git fallback hook once:
```bash
git config core.hooksPath .githooks
```
- A normal `git push` runs the suite and **allows** the push at ≥ 80%.
- To see it **block**, raise the bar temporarily:
  ```bash
  CLAUDE_PROJECT_DIR="$PWD" COVERAGE_MIN=99 \
    bash .claude/hooks/coverage-gate.sh <<< '{"tool_input":{"command":"git push"}}'
  echo "exit=$?"   # -> 2 (blocked)
  ```
  In Claude Code, the same check runs automatically as a PreToolUse hook
  (`.claude/settings.json`) whenever a `git push` Bash command is attempted.

## 7. Exercise the MCP server

Configured in `mcp.json` (both `context7` and `pipeline-status`). Quick local
check of the custom server:
```bash
./.venv/bin/python -c "
import asyncio
from fastmcp import Client
from mcp_server.server import mcp
async def main():
    async with Client(mcp) as c:
        print([t.name for t in await c.list_tools()])
        r = await c.call_tool('get_transaction_status', {'transaction_id':'TXN005'})
        print('TXN005:', r.data['status'])
asyncio.run(main())
"
```
Or run it directly over STDIO: `./.venv/bin/python -m mcp_server.server`.
```
> Tip: run `python integrator.py` (step 4) before querying the MCP server so
> `shared/results/` is populated.
```
