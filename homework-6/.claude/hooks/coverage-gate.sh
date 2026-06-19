#!/usr/bin/env bash
# PreToolUse hook: block `git push` unless test coverage is >= 80%.
#
# Claude Code passes the tool call as JSON on stdin. We only gate Bash calls
# whose command contains "git push"; everything else is allowed through.
set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
PY="$PROJECT_DIR/.venv/bin/python"
[ -x "$PY" ] || PY="python3"

# Read the hook payload and pull out the command being run.
payload="$(cat)"
command="$(printf '%s' "$payload" | "$PY" -c 'import sys,json;d=json.load(sys.stdin);print(d.get("tool_input",{}).get("command",""))' 2>/dev/null)"

# Not a push -> allow.
case "$command" in
  *"git push"*) ;;
  *) exit 0 ;;
esac

# Threshold defaults to 80; override with COVERAGE_MIN to demo a block.
COVERAGE_MIN="${COVERAGE_MIN:-80}"
echo "🔒 coverage-gate: 'git push' detected — running coverage check (>= ${COVERAGE_MIN}%)..." >&2

cov_output="$(cd "$PROJECT_DIR" && "$PY" -m pytest \
  --cov=agents --cov=common --cov-report=term-missing --cov-fail-under="$COVERAGE_MIN" 2>&1)"
status=$?

if [ $status -ne 0 ]; then
  echo "$cov_output" >&2
  echo "" >&2
  echo "❌ coverage-gate: push BLOCKED — coverage below ${COVERAGE_MIN}% (or tests failed)." >&2
  exit 2   # exit code 2 tells Claude Code to block the tool call
fi

echo "$cov_output" | tail -5 >&2
echo "✅ coverage-gate: coverage OK — push allowed." >&2
exit 0
