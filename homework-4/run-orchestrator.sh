#!/usr/bin/env bash
# Orchestrator Runner — one prompt, model-driven multi-agent orchestration
#
# A single `claude -p` invocation hands control to the bug-fix-orchestrator
# AGENT (agents/bug-fix-orchestrator.agent.md), which runs in the MAIN session
# and dispatches the six pipeline specialists via the Task tool:
#   research → verify (gate) → plan → fix (gate) → security ∥ tests.
#
# Why an agent (not a skill): sub-agents cannot spawn sub-agents, so the
# orchestrator must run in the main thread; and skills don't load in headless
# `-p`. An agent read into the main session is the reliable fit. (See README
# "Three runners".)
#
# Like run-workflow.sh, each run is ISOLATED in runs/<id>/ seeded with the
# buggy app. Absolute workspace paths are passed in the prompt (the `-p`
# argument is delivered reliably, unlike a Workflow args object), so every
# dispatched sub-agent reads/writes only the run folder — the repo src/ is
# never touched.
#
# Usage:
#   ./run-orchestrator.sh [BUG_ID]              # BUG_ID defaults to 001
#   RUN_ID=my-label ./run-orchestrator.sh 001   # name the run folder
#
# Requirements:
#   - claude (Claude Code CLI) on PATH.
#   - ADMIN_API_KEY exported, or src/.env present.
#   - Python deps installed: pip install -r src/requirements.txt

set -euo pipefail

BUG_ID="${1:-001}"
ROOT="$(cd "$(dirname "$0")" && pwd)"

log() { printf '\n\033[1;36m▶ %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31m✘ %s\033[0m\n' "$*" >&2; exit 1; }

[[ -f "${ROOT}/src/.env" ]] && set -a && source "${ROOT}/src/.env" && set +a
[[ -z "${ADMIN_API_KEY:-}" ]] && die "ADMIN_API_KEY is not set. See src/.env.example."
command -v claude >/dev/null 2>&1 || die "claude (Claude Code CLI) not found on PATH."
[[ -f "${ROOT}/src/app.py.seeded" ]] || die "src/app.py.seeded not found."
[[ -f "${ROOT}/agents/bug-fix-orchestrator.agent.md" ]] || die "orchestrator agent not found."
[[ -f "${ROOT}/context/bugs/${BUG_ID}/bug-context.md" ]] || die "bug-context.md not found for ${BUG_ID}."

# --- Build the isolated run workspace, seeded with the BUGGY app ----------
RUN_ID="${RUN_ID:-$(date +%Y%m%d-%H%M%S)}"
RUN_DIR="${ROOT}/runs/${RUN_ID}"
[[ -e "${RUN_DIR}" ]] && die "Run folder ${RUN_DIR} already exists. Pick a different RUN_ID."

log "Creating isolated run workspace: runs/${RUN_ID} (seeded buggy)"
mkdir -p "${RUN_DIR}/src" "${RUN_DIR}/tests" "${RUN_DIR}/context/bugs/${BUG_ID}/research"
cp "${ROOT}/src/app.py.seeded" "${RUN_DIR}/src/app.py"
cp "${ROOT}/src/app.py.seeded" "${RUN_DIR}/src/app.py.seeded"
cp "${ROOT}/src/requirements.txt" "${RUN_DIR}/src/" 2>/dev/null || true
cp "${ROOT}/src/.env.example" "${RUN_DIR}/src/" 2>/dev/null || true
cp "${ROOT}/tests/test_smoke.py" "${RUN_DIR}/tests/"
cp "${ROOT}/context/bugs/${BUG_ID}/bug-context.md" "${RUN_DIR}/context/bugs/${BUG_ID}/"

# --- One prompt → the orchestrator agent drives everything ----------------
SRC="${RUN_DIR}/src"
TESTS="${RUN_DIR}/tests"
ARTIFACTS="${RUN_DIR}/context/bugs/${BUG_ID}"

PROMPT="Read ${ROOT}/agents/bug-fix-orchestrator.agent.md and act as that orchestrator to fix bug ${BUG_ID}. \
Run entirely from this one session: dispatch the six pipeline specialists via the Task tool per the playbook. \
WORKSPACE CONTRACT — use these ABSOLUTE paths and operate ONLY here: \
SRC=${SRC} ; TESTS=${TESTS} ; ARTIFACTS=${ARTIFACTS} (research under ${ARTIFACTS}/research) ; \
AGENTS=${ROOT}/agents ; SKILLS=${ROOT}/skills . \
The bug context is at ${ARTIFACTS}/bug-context.md (the researcher reads only its Purpose/Expected sections). \
Pipeline: research → verify (STOP if status FAIL or quality L1/L2) → plan → fix (STOP if not PASS) → then security-verifier and unit-test-generator IN PARALLEL (two Task calls in one turn). \
Per-change + final test command: ADMIN_API_KEY=test-admin-key pytest ${TESTS}/... -v . \
When done, print the compact summary block defined in the orchestrator playbook (ok, stoppedAt, per-stage status, files)."

log "Triggering orchestrator → runs/${RUN_ID} (bug ${BUG_ID})"

# bypassPermissions so the dispatched sub-agents can edit SRC, write TESTS, and
# run pytest unattended. The run folder is a throwaway sandbox.
( cd "${ROOT}" && claude -p "${PROMPT}" \
    --permission-mode bypassPermissions \
    --output-format json ) | tee "${RUN_DIR}/.last-orchestrator.json"

log "Run complete. Workspace: runs/${RUN_ID}"
echo
echo "Results in runs/${RUN_ID}/:"
echo "  src/app.py                          # fixed app"
echo "  tests/test_app.py                   # generated regression tests"
echo "  context/bugs/${BUG_ID}/research/codebase-research.md"
echo "  context/bugs/${BUG_ID}/research/verified-research.md"
echo "  context/bugs/${BUG_ID}/implementation-plan.md"
echo "  context/bugs/${BUG_ID}/fix-summary.md"
echo "  context/bugs/${BUG_ID}/security-report.md"
echo "  context/bugs/${BUG_ID}/test-report.md"
