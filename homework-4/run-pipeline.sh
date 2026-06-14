#!/usr/bin/env bash
# 4-Agent Pipeline Runner
#
# Single-command execution of the bug-fix pipeline. Invokes each
# sub-agent in order via the Claude Code CLI. Each invocation runs in a
# fresh context but reads/writes shared files under context/bugs/$BUG_ID/.
#
# Usage:
#   ./run-pipeline.sh [BUG_ID]
#     BUG_ID defaults to "001".
#
# Requirements:
#   - claude (Claude Code CLI) on PATH
#   - ADMIN_API_KEY exported, or .env loaded
#   - Python deps installed: pip install -r src/requirements.txt

set -euo pipefail

BUG_ID="${1:-001}"
ROOT="$(cd "$(dirname "$0")" && pwd)"
CTX="${ROOT}/context/bugs/${BUG_ID}"
RESEARCH="${CTX}/research"

mkdir -p "${RESEARCH}"

log() { printf '\n\033[1;36m▶ %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31m✘ %s\033[0m\n' "$*" >&2; exit 1; }

# Optional: source .env if it exists
[[ -f "${ROOT}/src/.env" ]] && set -a && source "${ROOT}/src/.env" && set +a

# Prerequisite: ADMIN_API_KEY (post-fix app refuses to import without it)
if [[ -z "${ADMIN_API_KEY:-}" ]]; then
  die "ADMIN_API_KEY is not set. See src/.env.example."
fi

command -v claude >/dev/null 2>&1 || die "claude (Claude Code CLI) not found on PATH."

# Helper: invoke a sub-agent via claude -p. Each agent's behaviour is defined
# by its agents/<name>.agent.md file, which the headless session reads and
# follows. (The CLI has no --agents-dir/--skills-dir flag; agents load by
# reading their definition from disk, and skills are read by path from the
# task.) --permission-mode bypassPermissions lets the agent edit src/, write
# tests/, and run pytest unattended — required for true single-command runs.
run_agent() {
  local agent_name="$1"
  local task="$2"
  local out="${CTX}/.last-${agent_name}.json"
  local prompt="Read the agent definition at ${ROOT}/agents/${agent_name}.agent.md and act exactly as that sub-agent — follow its Process, Output format, and Protocol guarantees. Any skills it requires are under ${ROOT}/skills/. ${task}"
  # Retry on transient API failures. Six sequential cold-start claude -p calls
  # mean any one network blip (529 Overloaded, socket close) would otherwise
  # kill the whole run; retry up to 3 times before giving up.
  local attempt rc
  for attempt in 1 2 3; do
    log "Running agent: ${agent_name} (attempt ${attempt}/3)"
    rc=0
    claude -p "${prompt}" \
      --permission-mode bypassPermissions \
      --output-format json \
      > "${out}" 2>/dev/null || rc=$?
    if [[ ${rc} -eq 0 ]] && ! grep -q '"is_error":[[:space:]]*true' "${out}"; then
      return 0
    fi
    log "  transient failure (rc=${rc}); retrying in 8s…"
    sleep 8
  done
  die "Agent ${agent_name} failed after 3 attempts (last error in ${out})."
}

# --- Automatic baseline reset (in-place) ---------------------------------
# This runner works on the repo's own src/ in place, so before a real run the
# app must be in its BUGGY state — otherwise there is nothing to fix. Restore
# the seeded baseline automatically (the manual `cp src/app.py.seeded src/app.py`
# step is no longer needed). Set RESET=0 to skip — e.g. to re-run only later
# steps against an already-fixed tree.
RESET="${RESET:-1}"
if [[ "${RESET}" == "1" ]]; then
  [[ -f "${ROOT}/src/app.py.seeded" ]] || die "src/app.py.seeded not found — cannot reset to the buggy baseline."
  cp "${ROOT}/src/app.py.seeded" "${ROOT}/src/app.py"
  rm -f "${ROOT}/tasks.db" "${ROOT}/src/tasks.db"
  log "Reset src/app.py to the seeded buggy baseline (RESET=1)."
else
  log "RESET=0 — running against src/ as-is."
fi

# Step 1 — Bug Researcher
run_agent "bug-researcher" \
  "Inspect the app under ${ROOT}/src and ${ROOT}/tests. Bug context lives at ${CTX}/bug-context.md (read only the Purpose/Expected sections per protocol). Emit ${RESEARCH}/codebase-research.md."

[[ -f "${RESEARCH}/codebase-research.md" ]] || die "Researcher did not emit codebase-research.md"

# Step 2 — Research Verifier
run_agent "research-verifier" \
  "Run the research-verifier agent. Input: ${RESEARCH}/codebase-research.md. Apply the research-quality-measurement skill. Emit ${RESEARCH}/verified-research.md."

[[ -f "${RESEARCH}/verified-research.md" ]] || die "Verifier did not emit verified-research.md"
# Lenient match: tolerate markdown bold / emoji between the label and PASS
# (e.g. "Status: **PASS**", "Status: ✅ PASS"). Also accepts PASS_WITH_DISCREPANCIES.
grep -qiE "status:[^[:alpha:]]*PASS" "${RESEARCH}/verified-research.md" \
  || die "Verifier reported FAIL. Inspect ${RESEARCH}/verified-research.md and re-run from step 1."

# Step 3 — Bug Planner
run_agent "bug-planner" \
  "Run the bug-planner agent. Input: ${RESEARCH}/verified-research.md. Emit ${CTX}/implementation-plan.md."

[[ -f "${CTX}/implementation-plan.md" ]] || die "Planner did not emit implementation-plan.md"

# Step 4 — Bug Fixer
run_agent "bug-fixer" \
  "Input: ${CTX}/implementation-plan.md. Apply changes to ${ROOT}/src/app.py, running 'ADMIN_API_KEY=test-admin-key pytest ${ROOT}/tests/test_smoke.py -v' after each change. After all pass, run 'ADMIN_API_KEY=test-admin-key pytest ${ROOT}/tests/ -v'. Emit ${CTX}/fix-summary.md."

[[ -f "${CTX}/fix-summary.md" ]] || die "Fixer did not emit fix-summary.md"
grep -qiE "status:[^[:alpha:]]*PASS" "${CTX}/fix-summary.md" \
  || die "Fixer reported failure. Inspect ${CTX}/fix-summary.md."

# Step 5 — Security Verifier
run_agent "security-verifier" \
  "Run the security-verifier agent. Input: ${CTX}/fix-summary.md. Review modified files only. Emit ${CTX}/security-report.md."

[[ -f "${CTX}/security-report.md" ]] || die "Security verifier did not emit security-report.md"
grep -qiE "pipeline gate:[^[:alpha:]]*PASS" "${CTX}/security-report.md" \
  || die "Security gate FAIL. Inspect ${CTX}/security-report.md for open CRITICAL/HIGH issues."

# Step 6 — Unit Test Generator
run_agent "unit-test-generator" \
  "Input: ${CTX}/fix-summary.md. Apply the unit-tests-FIRST skill (skills/unit-tests-FIRST.md). Write regression tests for the changed code to ${ROOT}/tests/test_app.py, run 'ADMIN_API_KEY=test-admin-key pytest ${ROOT}/tests/ -v', emit ${CTX}/test-report.md."

[[ -f "${CTX}/test-report.md" ]] || die "Test generator did not emit test-report.md"

# Final acceptance — run the whole test suite once more
log "Final acceptance: full suite"
PY="$(command -v python3 || command -v python || true)"
[[ -z "${PY}" ]] && die "python3/python not found on PATH."
ADMIN_API_KEY="${ADMIN_API_KEY}" "${PY}" -m pytest "${ROOT}/tests/" -v

log "Pipeline complete for bug ${BUG_ID}"
echo
echo "Artifacts:"
echo "  ${RESEARCH}/codebase-research.md"
echo "  ${RESEARCH}/verified-research.md"
echo "  ${CTX}/implementation-plan.md"
echo "  ${CTX}/fix-summary.md"
echo "  ${CTX}/security-report.md"
echo "  ${CTX}/test-report.md"
