#!/usr/bin/env bash
# Workflow Runner — isolated, repeatable bug-fix runs
#
# Each invocation builds a fresh, self-contained run workspace under runs/<id>/
# seeded with the BUGGY app, then drives the multi-agent workflow
# (workflows/fix-bugs.mjs) against that folder using ABSOLUTE paths. The fix,
# the generated tests, and every artifact land in runs/<id>/ — the repo's own
# src/ and context/ are never touched. (Absolute paths matter: a sub-agent's
# working directory is not guaranteed, so the workflow pins every read/write to
# runs/<id>/ explicitly rather than relying on `cd`.)
#
# Run it again → a new folder, seeded buggy again, fixed again. Each run is
# independent and reproducible.
#
#   runs/<id>/
#   ├── src/app.py            # seeded buggy → fixed in place by the run
#   ├── tests/                # test_smoke.py (seed) + test_app.py (generated)
#   ├── context/bugs/<id>/    # research, plan, fix-summary, security, test report
#   └── .last-workflow.json   # returned JSON summary
#
# Usage:
#   ./run-workflow.sh [BUG_ID]              # BUG_ID defaults to 001
#   RUN_ID=my-label ./run-workflow.sh 001   # name the run folder yourself
#
# Requirements:
#   - claude (Claude Code CLI) >= 2.1.154 with Workflows enabled.
#   - ADMIN_API_KEY exported, or src/.env present.
#   - Python deps installed: pip install -r src/requirements.txt

set -euo pipefail

BUG_ID="${1:-001}"
ROOT="$(cd "$(dirname "$0")" && pwd)"

log() { printf '\n\033[1;36m▶ %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31m✘ %s\033[0m\n' "$*" >&2; exit 1; }

# Optional: source .env for ADMIN_API_KEY.
[[ -f "${ROOT}/src/.env" ]] && set -a && source "${ROOT}/src/.env" && set +a
[[ -z "${ADMIN_API_KEY:-}" ]] && die "ADMIN_API_KEY is not set. See src/.env.example."

command -v claude >/dev/null 2>&1 || die "claude (Claude Code CLI) not found on PATH."
[[ -f "${ROOT}/src/app.py.seeded" ]] || die "src/app.py.seeded not found — nothing to seed the run with."
[[ -f "${ROOT}/context/bugs/${BUG_ID}/bug-context.md" ]] || die "context/bugs/${BUG_ID}/bug-context.md not found."

# --- Build the isolated run workspace, seeded with the BUGGY app ----------
RUN_ID="${RUN_ID:-$(date +%Y%m%d-%H%M%S)}"
RUN_DIR="${ROOT}/runs/${RUN_ID}"
[[ -e "${RUN_DIR}" ]] && die "Run folder ${RUN_DIR} already exists. Pick a different RUN_ID."

log "Creating isolated run workspace: runs/${RUN_ID} (seeded buggy)"
mkdir -p "${RUN_DIR}/src" "${RUN_DIR}/tests" "${RUN_DIR}/context/bugs/${BUG_ID}/research"

# The app, seeded to its buggy baseline (this is the code the pipeline fixes).
cp "${ROOT}/src/app.py.seeded" "${RUN_DIR}/src/app.py"
cp "${ROOT}/src/app.py.seeded" "${RUN_DIR}/src/app.py.seeded"
cp "${ROOT}/src/requirements.txt" "${RUN_DIR}/src/" 2>/dev/null || true
cp "${ROOT}/src/.env.example" "${RUN_DIR}/src/" 2>/dev/null || true

# Seed test (self-locates ../src) + the bug context the Researcher reads.
cp "${ROOT}/tests/test_smoke.py" "${RUN_DIR}/tests/"
cp "${ROOT}/context/bugs/${BUG_ID}/bug-context.md" "${RUN_DIR}/context/bugs/${BUG_ID}/"

# --- Generate a per-run copy of the workflow with the run config BAKED IN.
# Passing args through a `claude -p` prompt proved unreliable: the headless
# session runs the script but silently drops the args object, so the workflow's
# paths fall back to the repo root and the run leaks into the source tree.
# Baking absolute paths into a dedicated script removes that dependency — there
# are no args to drop, and every read/write is pinned to this run's folder
# (verified: a one-agent probe with a baked RUN_DIR wrote only inside it).
RUN_SCRIPT="${RUN_DIR}/fix-bugs.run.mjs"
sed -e "s|^const BUG_ID = .*|const BUG_ID = '${BUG_ID}'|" \
    -e "s|^const RUN_ID = .*|const RUN_ID = '${RUN_ID}'|" \
    -e "s|^const RUN_DIR = .*|const RUN_DIR = '${RUN_DIR}'|" \
    -e "s|^const ROOT_DIR = .*|const ROOT_DIR = '${ROOT}'|" \
    "${ROOT}/workflows/fix-bugs.mjs" > "${RUN_SCRIPT}"

PROMPT="Run the workflow script at ${RUN_SCRIPT} verbatim using the Workflow tool (scriptPath=\"${RUN_SCRIPT}\"). \
Do NOT pass any args, and do NOT re-author, rewrite, or inline the script — execute the file as-is. \
When the workflow finishes, report its returned JSON summary (ok, stoppedAt if present, and each stage's structured result)."

log "Triggering workflow → runs/${RUN_ID} (bug ${BUG_ID})"

# bypassPermissions lets the sub-agents edit the run folder's src/, write tests/,
# and run pytest unattended. The run folder is a throwaway sandbox, so this is
# safe. Safer alternative: --permission-mode acceptEdits --allowedTools "Bash,Read,Edit,Write,Grep,Glob,Task"
( cd "${ROOT}" && claude -p "${PROMPT}" \
    --permission-mode bypassPermissions \
    --output-format json ) | tee "${RUN_DIR}/.last-workflow.json"

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
