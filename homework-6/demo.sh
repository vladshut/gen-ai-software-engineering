#!/usr/bin/env bash
# demo.sh — Zero-manual-step demo of the banking pipeline REST API.
#
# What it does:
#   1. Installs dependencies (if needed)
#   2. Starts the FastAPI server (uvicorn)
#   3. Waits for it to be ready
#   4. Submits all sample transactions via the /pipeline endpoint
#   5. Retrieves and displays results via the API
#   6. Shows the pipeline config
#   7. Shuts down the server
#
# Usage:
#   chmod +x demo.sh
#   ./demo.sh

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

PORT=8000
BASE_URL="http://127.0.0.1:$PORT"
SERVER_PID=""

# --- Helpers ------------------------------------------------------------------

cleanup() {
    if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        echo ""
        echo "🛑 Shutting down API server (PID $SERVER_PID)..."
        kill "$SERVER_PID" 2>/dev/null
        wait "$SERVER_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

wait_for_server() {
    local retries=20
    while [ $retries -gt 0 ]; do
        if curl -s "$BASE_URL/config" > /dev/null 2>&1; then
            return 0
        fi
        sleep 0.5
        retries=$((retries - 1))
    done
    echo "❌ Server failed to start on $BASE_URL"
    exit 1
}

# --- Find Python --------------------------------------------------------------

if [ -x "$PROJECT_DIR/.venv/bin/python" ]; then
    PY="$PROJECT_DIR/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PY="python3"
else
    echo "❌ Python 3 not found. Please install Python 3.12+."
    exit 1
fi

echo "================================================================"
echo "  Banking Pipeline — REST API Demo"
echo "  Python: $PY"
echo "================================================================"
echo ""

# --- 1. Install dependencies --------------------------------------------------

echo "📦 Checking dependencies..."
$PY -m pip install --quiet fastapi uvicorn httpx pytest pytest-cov fastmcp 2>/dev/null || true
echo "   ✓ Dependencies ready"
echo ""

# --- 2. Start the API server --------------------------------------------------

echo "🚀 Starting API server on $BASE_URL ..."
$PY -m uvicorn api_server:app --port $PORT --log-level warning &
SERVER_PID=$!
wait_for_server
echo "   ✓ Server running (PID $SERVER_PID)"
echo ""

# --- 3. Show pipeline configuration ------------------------------------------

echo "⚙️  Pipeline configuration:"
curl -s "$BASE_URL/config" | $PY -m json.tool
echo ""

# --- 4. Submit all sample transactions ----------------------------------------

echo "📤 Submitting 8 sample transactions to POST /pipeline ..."
echo "────────────────────────────────────────────────────────────────"
printf "%-8s %-14s %-10s %-8s %s\n" "TXN" "STATUS" "SETTLE" "NET_USD" "REASON"
echo "────────────────────────────────────────────────────────────────"

# Read transactions from sample file and POST each one
$PY -c "
import json, httpx, sys

txns = json.loads(open('sample-transactions.json').read())
results = []

with httpx.Client(timeout=30.0) as client:
    for txn in txns:
        resp = client.post('$BASE_URL/pipeline', json=txn)
        resp.raise_for_status()
        r = resp.json()
        results.append(r)

        tid = r.get('transaction_id', '?')
        status = r.get('status', '?')
        settle = r.get('settlement', '-')
        net = r.get('net_usd', '-')
        reason = r.get('rejection_reason', '')
        print(f'{tid:<8} {status:<14} {settle:<10} {str(net):<8} {reason}')

# Summary
print()
print('Summary:')
from collections import Counter
statuses = Counter(r.get('status') for r in results)
for s, c in sorted(statuses.items()):
    print(f'  {s}: {c}')
settled_total = sum(float(r['net_usd']) for r in results if r.get('settlement') == 'settled')
print(f'  Settled total (USD net): {settled_total:.2f}')
"
echo ""

# --- 5. Query individual transaction status -----------------------------------

echo "🔍 Querying individual results from shared/results/ ..."
echo ""
echo "   GET result for TXN003 (sanctioned):"
$PY -c "
import json
from pathlib import Path
data = json.loads((Path('shared/results/TXN003.json')).read_text())['data']
print(f\"     status={data['status']}, reason={data.get('rejection_reason','')}\")
"

echo "   GET result for TXN001 (settled):"
$PY -c "
import json
from pathlib import Path
data = json.loads((Path('shared/results/TXN001.json')).read_text())['data']
print(f\"     status={data['status']}, settlement={data['settlement']}, net_usd={data['net_usd']}\")
"
echo ""

# --- 6. Run tests with coverage -----------------------------------------------

echo "🧪 Running test suite with coverage..."
$PY -m pytest --cov=agents --cov=common --cov-report=term-missing -q 2>&1 | tail -15
echo ""

# --- Done ---------------------------------------------------------------------

echo "════════════════════════════════════════════════════════════════"
echo "  ✅ Demo complete! All transactions processed via REST API."
echo "  📁 Results in: shared/results/"
echo "  🌐 API was served at: $BASE_URL"
echo "════════════════════════════════════════════════════════════════"
