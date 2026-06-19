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

## 8. Fast mode — high-volume throughput (optional)

The graded path (steps 4–5) uses the file-based `shared/` protocol — one JSON
file per hop, ideal for auditing a handful of transactions. For large volumes,
`--fast` keeps the same three deterministic agents but streams JSONL in/out and
fans the work across CPU cores (see `fast_pipeline.py`). It does **not** touch
the graded path, the oracle, or the `shared/` files.

Generate a synthetic load file and run it:
```bash
./.venv/bin/python generate_load.py -n 1000000 -o load.jsonl
./.venv/bin/python integrator.py --fast --input load.jsonl --output results.jsonl
```
The output is one final record per line in `results.jsonl`.

**Where the speed comes from.** Almost all of it is *Tier 1* — streaming JSONL
and dropping the four-files-per-transaction I/O of the graded path. Measured on a
laptop (1 transaction = a few comparisons + a Decimal op):

| Mode | Throughput | vs file-based |
|---|---|---|
| File-based, sequential (graded path) | ~2,300/s | 1× |
| `--fast` (single process, **default**) | ~115,000/s | **~40–50×** |
| `--fast --workers 7` | ~140,000/s | ~50–60× |

`--fast` runs **single-process by default**, which is the right choice here: once
the file I/O is gone the per-transaction work is tiny, so the process-pool
overhead is a net loss on small inputs and only a ~1.2× win at ~1M rows. Use
`--workers N` only for genuinely huge batches; `--chunk-size N` (default 10000)
tunes the per-task batch.

Because the agents are pure functions and every transaction is independent, the
output is byte-identical regardless of `--workers` — worker count never changes a
decision.
