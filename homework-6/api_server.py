"""FastAPI server exposing each pipeline agent as a REST endpoint.

The pipeline step order is defined in PIPELINE_STEPS config. The orchestrator
POSTs a transaction to /pipeline, which calls the first step; each step
processes the transaction and calls the next step in the chain. If any step
sets status="rejected", the chain stops immediately and the result is written
to shared/results/.

Endpoints:
    POST /pipeline              — entry point: starts the chain for a transaction
    POST /steps/validator       — transaction validator
    POST /steps/fraud           — fraud detector
    POST /steps/compliance      — compliance checker
    POST /steps/settlement      — settlement processor (terminal, writes result)
    GET  /config                — returns current pipeline config

Run:
    uvicorn api_server:app --port 8000
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Request

from agents.compliance_checker import check_transaction
from agents.fraud_detector import assess_transaction
from agents.settlement_processor import settle_transaction
from agents.transaction_validator import validate_transaction
from common.constants import (
    AGENT_INTEGRATOR,
    AGENT_SETTLEMENT,
    STATUS_REJECTED,
)
from common.messages import Message, mask_account, safe_log_view

app = FastAPI(title="Banking Pipeline API")

BASE = Path(__file__).resolve().parent
SHARED = BASE / "shared"
DIR_RESULTS = SHARED / "results"

# --- Pipeline configuration ---------------------------------------------------
# Ordered list of steps. Each entry maps a name to its route path.
# The integrator calls /pipeline which triggers the chain starting at index 0.
# Each step, after processing, calls the next step in the list.
# Settlement is always the terminal step (writes the final record).

PIPELINE_STEPS: list[dict[str, str]] = [
    {"name": "validator", "path": "/steps/validator"},
    {"name": "fraud", "path": "/steps/fraud"},
    {"name": "compliance", "path": "/steps/compliance"},
    {"name": "settlement", "path": "/steps/settlement"},
]


def _get_base_url(request: Request) -> str:
    """Derive the base URL from the incoming request so steps can call each other."""
    return str(request.base_url).rstrip("/")


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"not JSON-serializable: {type(value).__name__}")


def _write_result(txn_id: str, data: dict[str, Any]) -> None:
    """Write final record to shared/results/<txn_id>.json."""
    DIR_RESULTS.mkdir(parents=True, exist_ok=True)
    msg = Message(AGENT_SETTLEMENT, AGENT_INTEGRATOR, data)
    path = DIR_RESULTS / f"{txn_id}.json"
    path.write_text(msg.to_json(), encoding="utf-8")


def _serialize_txn(txn: dict[str, Any]) -> dict[str, Any]:
    """Convert Decimals to strings for JSON transport."""
    return json.loads(json.dumps(txn, default=_json_default))


async def _call_next_step(
    base_url: str, current_index: int, txn: dict[str, Any]
) -> dict[str, Any]:
    """Call the next step in the pipeline chain via HTTP."""
    next_index = current_index + 1
    if next_index >= len(PIPELINE_STEPS):
        # No more steps — shouldn't happen if settlement is terminal
        return txn

    next_path = PIPELINE_STEPS[next_index]["path"]
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base_url}{next_path}",
            json=_serialize_txn(txn),
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()


# --- Endpoints ----------------------------------------------------------------


@app.get("/config")
async def get_config():
    """Return the current pipeline step configuration."""
    return {"pipeline_steps": PIPELINE_STEPS}


@app.post("/pipeline")
async def run_pipeline_entry(txn: dict[str, Any], request: Request):
    """Entry point: starts the pipeline chain for a single transaction.

    The orchestrator POSTs here; this endpoint calls the first step.
    """
    base_url = _get_base_url(request)
    first_path = PIPELINE_STEPS[0]["path"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base_url}{first_path}",
            json=_serialize_txn(txn),
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()


@app.post("/steps/validator")
async def step_validator(txn: dict[str, Any], request: Request):
    """Step 1: validate the transaction."""
    result = validate_transaction(txn)
    txn_id = result.get("transaction_id", "UNKNOWN")

    if result.get("status") == STATUS_REJECTED:
        # Chain stops — write result and return
        settled = settle_transaction(result)
        _write_result(txn_id, settled)
        return _serialize_txn(settled)

    # Call next step
    base_url = _get_base_url(request)
    step_index = 0  # validator is index 0
    return await _call_next_step(base_url, step_index, result)


@app.post("/steps/fraud")
async def step_fraud(txn: dict[str, Any], request: Request):
    """Step 2: fraud scoring."""
    result = assess_transaction(txn)
    # Fraud never rejects on its own — always forwards to next step
    base_url = _get_base_url(request)
    step_index = 1  # fraud is index 1
    return await _call_next_step(base_url, step_index, result)


@app.post("/steps/compliance")
async def step_compliance(txn: dict[str, Any], request: Request):
    """Step 3: compliance screening."""
    result = check_transaction(txn)
    txn_id = result.get("transaction_id", "UNKNOWN")

    if result.get("status") == STATUS_REJECTED:
        # Chain stops — write result and return
        settled = settle_transaction(result)
        _write_result(txn_id, settled)
        return _serialize_txn(settled)

    # Call next step
    base_url = _get_base_url(request)
    step_index = 2  # compliance is index 2
    return await _call_next_step(base_url, step_index, result)


@app.post("/steps/settlement")
async def step_settlement(txn: dict[str, Any], request: Request):
    """Step 4 (terminal): settlement processing. Always writes result."""
    result = settle_transaction(txn)
    txn_id = result.get("transaction_id", "UNKNOWN")
    _write_result(txn_id, result)
    return _serialize_txn(result)
