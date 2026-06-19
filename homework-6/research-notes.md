# Research Notes — context7 lookups

Two documentation lookups performed via the **context7** MCP server before
writing `common/money.py` and `mcp_server/server.py`.

---

## Query 1 — Python `decimal` module (ROUND_HALF_UP, quantize)

- **Search term:** "Python decimal module ROUND_HALF_UP quantize for currency rounding"
- **resolve-library-id →** selected `/python/cpython` (High reputation,
  benchmark 81.6, 46k snippets) over `/arqawa/cpython`.
- **query-docs term:** "decimal module: Decimal quantize with ROUND_HALF_UP to
  2 decimal places for currency, parsing strings, getcontext rounding"

**Returned patterns applied:**

```python
TWOPLACES = Decimal(10) ** -2          # -> Decimal('0.01')
Decimal('3.214').quantize(TWOPLACES)   # round to 2 dp
# ROUND_HALF_UP = "round to nearest, ties going away from zero"
```

**Where applied:** `common/money.py`
- `TWOPLACES = Decimal(10) ** -MAX_DECIMAL_PLACES` (the doc's exact idiom).
- `to_usd()` and `apply_fee()` call `.quantize(TWOPLACES, rounding=ROUND_HALF_UP)`
  so settlement money rounds bankers-away-from-zero, never via float.
- `parse_amount()` inspects `value.as_tuple().exponent` to enforce the
  "≤ 2 decimal places" frozen rule, learned from the `as_tuple()` usage in the
  doc's `moneyfmt` example.

---

## Query 2 — `fastmcp` server API (tools + resources)

- **Search term:** "FastMCP server defining tools and resources in Python"
- **resolve-library-id →** selected `/prefecthq/fastmcp` (High reputation,
  benchmark 77, official repo) over the lower-reputation mirrors.
- **query-docs term:** "FastMCP server: define tool and resource with
  decorators, run with stdio transport, @mcp.tool and @mcp.resource examples"

**Returned patterns applied:**

```python
from fastmcp import FastMCP
mcp = FastMCP("MyServer")

@mcp.tool
def hello(name: str) -> str:
    return f"Hello, {name}!"

@mcp.resource("system://status")
def get_system_status() -> dict:
    return {"status": "all systems normal"}

if __name__ == "__main__":
    mcp.run()   # STDIO transport by default
```

**Where applied:** `mcp_server/server.py`
- `mcp = FastMCP("pipeline-status")` then `@mcp.tool` on
  `get_transaction_status` and `list_pipeline_results`.
- `@mcp.resource("pipeline://summary")` returning the latest run summary as text
  (the decorator-with-URI pattern from the docs).
- `mcp.run()` at the bottom for the default STDIO transport, matching how
  `mcp.json` launches it (`python -m mcp_server.server`).
