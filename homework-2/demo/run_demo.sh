#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# Customer Support System — Demo & Functionality Check
# ============================================================================
# This script:
#   1. Sets up a virtual environment and installs dependencies
#   2. Starts the FastAPI server
#   3. Runs functionality checks against all endpoints
#   4. Runs the test suite with coverage
#   5. Cleans up
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
BASE_URL="http://localhost:8000"
SERVER_PID=""
PASS=0
FAIL=0
TOTAL=0

# --- Colors ----------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# --- Helpers ---------------------------------------------------------------
log()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()   { echo -e "  ${GREEN}✅ PASS${NC} — $*"; PASS=$((PASS+1)); TOTAL=$((TOTAL+1)); }
fail() { echo -e "  ${RED}❌ FAIL${NC} — $*"; FAIL=$((FAIL+1)); TOTAL=$((TOTAL+1)); }
section() { echo -e "\n${BOLD}${YELLOW}━━━ $* ━━━${NC}"; }

cleanup() {
    if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        log "Stopping server (PID $SERVER_PID)..."
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
    rm -f "$PROJECT_DIR/demo_tickets.db"
    log "Cleanup complete."
}
trap cleanup EXIT

# --- 1. Setup --------------------------------------------------------------
section "1. Environment Setup"
cd "$PROJECT_DIR"

if [ ! -d "$VENV_DIR" ]; then
    log "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

log "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

log "Installing dependencies..."
"$VENV_DIR/bin/pip" install -q -r requirements.txt -r requirements-dev.txt 2>&1 | grep -v "^\[notice\]" || true

# --- 2. Start Server -------------------------------------------------------
section "2. Starting Server"

# Kill any stale process on port 8000
STALE_PID=$(lsof -ti :8000 2>/dev/null || true)
if [ -n "$STALE_PID" ]; then
    log "Killing stale process on port 8000 (PID $STALE_PID)..."
    kill "$STALE_PID" 2>/dev/null || true
    sleep 1
fi

export DATABASE_URL="demo_tickets.db"
log "Starting FastAPI server on port 8000..."
"$VENV_DIR/bin/uvicorn" src.main:app --host 127.0.0.1 --port 8000 --log-level warning &
SERVER_PID=$!

# Wait for server to be ready
log "Waiting for server..."
for i in $(seq 1 30); do
    if curl -s "$BASE_URL/" > /dev/null 2>&1; then
        log "Server is ready (PID $SERVER_PID)"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo -e "${RED}Server failed to start within 30 seconds${NC}"
        exit 1
    fi
    sleep 1
done

# --- 3. Health Check -------------------------------------------------------
section "3. Health Check"

RESP=$(curl -s "$BASE_URL/")
if echo "$RESP" | grep -q '"status":"ok"'; then
    ok "GET / returns status ok"
else
    fail "GET / health check — got: $RESP"
fi

# --- 4. Ticket CRUD -------------------------------------------------------
section "4. Ticket CRUD"

# Create
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/tickets" \
    -H "Content-Type: application/json" \
    -d '{
        "customer_id": "CUST-001",
        "customer_email": "john@example.com",
        "customer_name": "John Doe",
        "subject": "Cannot access my account",
        "description": "Getting error 403 when trying to access my dashboard since yesterday"
    }')
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
TICKET_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")

if [ "$HTTP_CODE" = "201" ] && [ -n "$TICKET_ID" ]; then
    ok "POST /tickets — created ticket $TICKET_ID"
else
    fail "POST /tickets — HTTP $HTTP_CODE"
fi

# Get by ID
RESP=$(curl -s -w "\n%{http_code}" "$BASE_URL/tickets/$TICKET_ID")
HTTP_CODE=$(echo "$RESP" | tail -1)
if [ "$HTTP_CODE" = "200" ]; then
    ok "GET /tickets/$TICKET_ID — retrieved"
else
    fail "GET /tickets/$TICKET_ID — HTTP $HTTP_CODE"
fi

# List
RESP=$(curl -s -w "\n%{http_code}" "$BASE_URL/tickets")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
TOTAL_COUNT=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['total'])" 2>/dev/null || echo "0")
if [ "$HTTP_CODE" = "200" ] && [ "$TOTAL_COUNT" -ge 1 ]; then
    ok "GET /tickets — listed $TOTAL_COUNT ticket(s)"
else
    fail "GET /tickets — HTTP $HTTP_CODE, total=$TOTAL_COUNT"
fi

# Update
RESP=$(curl -s -w "\n%{http_code}" -X PUT "$BASE_URL/tickets/$TICKET_ID" \
    -H "Content-Type: application/json" \
    -d '{"status": "in_progress", "assigned_to": "agent-smith"}')
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
NEW_STATUS=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "")
if [ "$HTTP_CODE" = "200" ] && [ "$NEW_STATUS" = "in_progress" ]; then
    ok "PUT /tickets/$TICKET_ID — updated to in_progress"
else
    fail "PUT /tickets/$TICKET_ID — HTTP $HTTP_CODE, status=$NEW_STATUS"
fi

# Get not found
RESP=$(curl -s -w "\n%{http_code}" "$BASE_URL/tickets/00000000-0000-0000-0000-000000000000")
HTTP_CODE=$(echo "$RESP" | tail -1)
if [ "$HTTP_CODE" = "404" ]; then
    ok "GET /tickets/nonexistent — returns 404"
else
    fail "GET /tickets/nonexistent — expected 404, got $HTTP_CODE"
fi

# Validation error
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/tickets" \
    -H "Content-Type: application/json" \
    -d '{"customer_id": "X", "customer_email": "bad", "customer_name": "X", "subject": "X", "description": "short"}')
HTTP_CODE=$(echo "$RESP" | tail -1)
if [ "$HTTP_CODE" = "422" ]; then
    ok "POST /tickets with invalid data — returns 422"
else
    fail "POST /tickets with invalid data — expected 422, got $HTTP_CODE"
fi

# --- 5. Bulk Import --------------------------------------------------------
section "5. Bulk Import"

# CSV import
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/tickets/import" \
    -F "file=@tests/fixtures/sample_tickets.csv")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
SUCCESSFUL=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['successful'])" 2>/dev/null || echo "0")
if [ "$HTTP_CODE" = "200" ] && [ "$SUCCESSFUL" -ge 1 ]; then
    ok "POST /tickets/import (CSV) — imported $SUCCESSFUL tickets"
else
    fail "POST /tickets/import (CSV) — HTTP $HTTP_CODE, successful=$SUCCESSFUL"
fi

# JSON import
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/tickets/import" \
    -F "file=@tests/fixtures/sample_tickets.json")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
SUCCESSFUL=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['successful'])" 2>/dev/null || echo "0")
if [ "$HTTP_CODE" = "200" ] && [ "$SUCCESSFUL" -ge 1 ]; then
    ok "POST /tickets/import (JSON) — imported $SUCCESSFUL tickets"
else
    fail "POST /tickets/import (JSON) — HTTP $HTTP_CODE, successful=$SUCCESSFUL"
fi

# XML import
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/tickets/import" \
    -F "file=@tests/fixtures/sample_tickets.xml")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
SUCCESSFUL=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['successful'])" 2>/dev/null || echo "0")
if [ "$HTTP_CODE" = "200" ] && [ "$SUCCESSFUL" -ge 1 ]; then
    ok "POST /tickets/import (XML) — imported $SUCCESSFUL tickets"
else
    fail "POST /tickets/import (XML) — HTTP $HTTP_CODE, successful=$SUCCESSFUL"
fi

# Invalid file
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/tickets/import" \
    -F "file=@tests/fixtures/invalid_tickets.csv")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
FAILED_COUNT=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['failed'])" 2>/dev/null || echo "0")
if [ "$HTTP_CODE" = "200" ] && [ "$FAILED_COUNT" -ge 1 ]; then
    ok "POST /tickets/import (invalid CSV) — $FAILED_COUNT validation errors reported"
else
    fail "POST /tickets/import (invalid CSV) — HTTP $HTTP_CODE, failed=$FAILED_COUNT"
fi

# --- 6. Auto-Classification -----------------------------------------------
section "6. Auto-Classification"

# Create a ticket with clear keywords
RESP=$(curl -s -X POST "$BASE_URL/tickets" \
    -H "Content-Type: application/json" \
    -d '{
        "customer_id": "CUST-DEMO",
        "customer_email": "demo@example.com",
        "customer_name": "Demo User",
        "subject": "Production down",
        "description": "CRITICAL: I cannot access my account, the login page shows a security error and production is completely down"
    }')
CL_TICKET_ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")

RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/tickets/$CL_TICKET_ID/auto-classify")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
CATEGORY=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['category'])" 2>/dev/null || echo "")
PRIORITY=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['priority'])" 2>/dev/null || echo "")
CONFIDENCE=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['confidence'])" 2>/dev/null || echo "")
KEYWORDS=$(echo "$BODY" | python3 -c "import sys,json; print(', '.join(json.load(sys.stdin)['keywords_found']))" 2>/dev/null || echo "")

if [ "$HTTP_CODE" = "200" ] && [ -n "$CATEGORY" ]; then
    ok "POST /tickets/{id}/auto-classify — category=$CATEGORY, priority=$PRIORITY, confidence=$CONFIDENCE"
    echo -e "     Keywords: $KEYWORDS"
else
    fail "POST /tickets/{id}/auto-classify — HTTP $HTTP_CODE"
fi

# Auto-classify on creation
RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/tickets" \
    -H "Content-Type: application/json" \
    -d '{
        "customer_id": "CUST-AUTO",
        "customer_email": "auto@example.com",
        "customer_name": "Auto User",
        "subject": "Refund request",
        "description": "I need a refund for the last invoice, I was overcharged on my billing statement",
        "auto_classify": true
    }')
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
AUTO_CAT=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['category'])" 2>/dev/null || echo "null")
if [ "$HTTP_CODE" = "201" ] && [ "$AUTO_CAT" != "null" ] && [ -n "$AUTO_CAT" ]; then
    ok "POST /tickets with auto_classify=true — auto-categorized as $AUTO_CAT"
else
    fail "POST /tickets with auto_classify=true — HTTP $HTTP_CODE, category=$AUTO_CAT"
fi

# --- 7. Filtering & Pagination ---------------------------------------------
section "7. Filtering & Pagination"

RESP=$(curl -s -w "\n%{http_code}" "$BASE_URL/tickets?page=1&page_size=5")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
PAGE=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'page={d[\"page\"]}, page_size={d[\"page_size\"]}, total={d[\"total\"]}, items={len(d[\"items\"])}')" 2>/dev/null || echo "")
if [ "$HTTP_CODE" = "200" ]; then
    ok "GET /tickets?page=1&page_size=5 — $PAGE"
else
    fail "GET /tickets?page=1&page_size=5 — HTTP $HTTP_CODE"
fi

RESP=$(curl -s -w "\n%{http_code}" "$BASE_URL/tickets?status=in_progress")
HTTP_CODE=$(echo "$RESP" | tail -1)
if [ "$HTTP_CODE" = "200" ]; then
    ok "GET /tickets?status=in_progress — filter works"
else
    fail "GET /tickets?status=in_progress — HTTP $HTTP_CODE"
fi

# --- 8. Delete -------------------------------------------------------------
section "8. Delete"

RESP=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/tickets/$TICKET_ID")
HTTP_CODE=$(echo "$RESP" | tail -1)
if [ "$HTTP_CODE" = "200" ]; then
    ok "DELETE /tickets/$TICKET_ID — deleted"
else
    fail "DELETE /tickets/$TICKET_ID — HTTP $HTTP_CODE"
fi

# Verify deleted
RESP=$(curl -s -w "\n%{http_code}" "$BASE_URL/tickets/$TICKET_ID")
HTTP_CODE=$(echo "$RESP" | tail -1)
if [ "$HTTP_CODE" = "404" ]; then
    ok "GET /tickets/$TICKET_ID after delete — returns 404"
else
    fail "GET /tickets/$TICKET_ID after delete — expected 404, got $HTTP_CODE"
fi

# --- 9. Stop Server & Run Tests -------------------------------------------
section "9. Stopping Server"
log "Stopping server..."
kill "$SERVER_PID" 2>/dev/null || true
wait "$SERVER_PID" 2>/dev/null || true
SERVER_PID=""

section "10. Running Test Suite"
echo ""
"$VENV_DIR/bin/python" -m pytest tests/ -v --cov=src --cov-report=term 2>&1 | tail -30

# --- Summary ---------------------------------------------------------------
section "RESULTS"
echo ""
echo -e "${BOLD}Functionality checks: $PASS passed, $FAIL failed (out of $TOTAL)${NC}"
echo ""
if [ "$FAIL" -eq 0 ]; then
    echo -e "${GREEN}${BOLD}🎉 All checks passed!${NC}"
    exit 0
else
    echo -e "${RED}${BOLD}⚠️  $FAIL check(s) failed.${NC}"
    exit 1
fi
