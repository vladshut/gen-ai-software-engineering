# How to Run

Operational runbook for the 4-agent (effectively 6-agent) pipeline.
This document is the **execution-focused** companion to `README.md`,
which covers structure and rationale.

---

## Prerequisites

1. **Claude Code CLI** installed and authenticated:
   ```bash
   claude --version
   ```
   If missing, see https://docs.claude.com/en/docs/claude-code/quickstart.

2. **Python 3.11+** with pip:
   ```bash
   python --version    # ≥ 3.11
   ```

3. **App dependencies** installed:
   ```bash
   pip install -r src/requirements.txt
   # or, if your environment requires it:
   pip install --break-system-packages -r src/requirements.txt
   ```

4. **Environment**: copy `src/.env.example` to `src/.env` and set
   `ADMIN_API_KEY`:
   ```bash
   cp src/.env.example src/.env
   # then edit src/.env, replace the placeholder
   ```

---

## A. Verify the post-fix state (reviewer-friendly, fastest)

The repo ships with `src/app.py` already in its **post-pipeline**
state, so a reviewer can immediately confirm the "Working application"
deliverable without re-running the pipeline.

```bash
# 1. Set env var
export ADMIN_API_KEY=test-admin-key

# 2. Run the full test suite
pytest tests/ -v
# Expected: 15 passed in ~0.6 s

# 3. Boot the app and probe a fix manually
uvicorn app:app --app-dir src &
APP_PID=$!
sleep 1

# Confirm SQLi is blocked (returns 422, not data dump):
curl -i 'http://127.0.0.1:8000/tasks/1%20OR%201=1'

# Confirm 404 on missing complete:
curl -i -X PATCH http://127.0.0.1:8000/tasks/9999/complete

kill $APP_PID
```

---

## B. Re-run the pipeline end-to-end (full reproduction)

This is what a homework reviewer would do to verify that the pipeline
itself works, not just the committed outputs.

```bash
# 1. Restore the buggy baseline so the pipeline has work to do
cp src/app.py.seeded src/app.py

# 2. Confirm the regression suite now fails on the buggy code
export ADMIN_API_KEY=test-admin-key
pytest tests/test_app.py -v
# Expected: 10 failed, 4 passed — proves the tests are not vacuous

# 3. Run the pipeline
./run-pipeline.sh 001
```

What you should see:
- `▶ Running agent: bug-researcher` … (and five more, in order)
- Each step writes its artifact to `context/bugs/001/`
- The final acceptance run shows `15 passed`

Re-running the pipeline overwrites the six artifact files. If you want
to diff against the committed versions, copy them aside first:
```bash
cp -r context/bugs/001 /tmp/baseline-001
./run-pipeline.sh
diff -r /tmp/baseline-001 context/bugs/001
```

---

## B2. Workflow runner (`run-workflow.sh`) — the orchestrated path

`run-pipeline.sh` boots one `claude -p` per agent. `run-workflow.sh` runs the
whole pipeline as a single multi-agent **workflow** (`workflows/fix-bugs.mjs`),
which adds two things the shell script can't do:

- **Structured gating** — stages return typed results (research quality level,
  fix status, security gate) and the workflow branches on real fields instead
  of `grep`-ing markdown.
- **Parallelism** — the Security Verifier and Unit Test Generator both depend
  only on `fix-summary.md`, so they run **concurrently** after the fix.

```bash
export ADMIN_API_KEY=test-admin-key
./run-workflow.sh 001               # BUG_ID defaults to 001
RUN_ID=demo ./run-workflow.sh 001   # name the run folder yourself
```

**Isolated, repeatable runs.** The repo's own `src/` is never touched. Each run
builds a fresh, self-contained workspace under `runs/<id>/` (timestamped by
default), seeds it with the **buggy** app (`src/app.py.seeded`), copies in the
pipeline definition (`agents/`, `skills/`, `workflows/`) plus the seed test and
bug context, then runs the workflow with that folder as its working directory.
The fix, the generated `tests/test_app.py`, and every artifact land in
`runs/<id>/` — and the returned JSON summary in `runs/<id>/.last-workflow.json`.

```
runs/<id>/
├── src/app.py                       # seeded buggy → fixed by the run
├── tests/                           # test_smoke.py (seed) + test_app.py (generated)
├── context/bugs/001/                # research, plan, fix-summary, security, test report
└── .last-workflow.json              # returned summary
```

To fix the bugs again, just run it again — a new `runs/<id>/` is seeded buggy
and fixed independently. `runs/` is git-ignored (the outputs are reproducible).
Inspect a run's result without re-running:

```bash
cat runs/<id>/context/bugs/001/fix-summary.md
ADMIN_API_KEY=test-admin-key pytest runs/<id>/tests/ -v
```

**Requirements specific to this path:**
- Claude Code CLI **≥ 2.1.154** on a plan with **Workflows enabled**
  (Pro/Max/Team/Enterprise, or Bedrock/Vertex/Foundry). Workflows are a paid
  feature; if yours doesn't have them, use `run-pipeline.sh` instead — same
  agents, same artifacts.
- The script runs with `--permission-mode bypassPermissions` so the sub-agents
  can edit `src/`, write `tests/`, and run `pytest` unattended. Use it only on
  a trusted local checkout. A safer (still unattended) alternative is commented
  in the script: `--permission-mode acceptEdits` + an explicit `--allowedTools`
  list.

Both runners produce the same six artifacts under `context/bugs/001/`.

---

## B3. Orchestrator runner (`run-orchestrator.sh`) — one prompt, one agent

The third runner hands the whole pipeline to a single **agent** in one
`claude -p` call. The `bug-fix-orchestrator` agent runs in the main session
and dispatches the six specialists via the Task tool (research → verify →
plan → fix → security ∥ tests), gating between phases.

```bash
export ADMIN_API_KEY=test-admin-key
./run-orchestrator.sh 001               # BUG_ID defaults to 001
RUN_ID=demo ./run-orchestrator.sh 001   # name the run folder
```

Like `run-workflow.sh`, each run is isolated under `runs/<id>/` (seeded
buggy, fixed there, results kept there). Absolute workspace paths are passed
in the prompt so every dispatched sub-agent stays inside the run folder.

**Why an agent, not a skill:** sub-agents can't spawn sub-agents (so the
orchestrator must be the main thread), and skills don't load in headless
`-p`. An agent read into the main session is the only reliable fit — see
`agents/bug-fix-orchestrator.agent.md` and the README.

## B4. Why three runners? (comparison + pros/cons)

All three drive the **same six agents** and the **same two skills**, and they
produce the **same artifacts** — they differ only in *how* the agents are
orchestrated. Each is a useful answer to a different question ("what if I have
no special features?", "what if I want determinism?", "what if I want the
orchestrator to adapt?"). Verified head-to-head, all three fix the four seeded
issues, clear the security gate, and pass the suite (counts vary slightly
because an LLM writes the tests).

| | `run-pipeline.sh` | `run-workflow.sh` | `run-orchestrator.sh` |
|---|---|---|---|
| **Mechanism** | shell loop: one `claude -p` per agent | one **Workflow** script (`workflows/fix-bugs.mjs`) | one prompt → **orchestrator agent** dispatches via Task |
| **Who orchestrates** | bash + the script author | the Workflow runtime (deterministic JS) | an Opus agent reasoning over the playbook |
| **Gating** | `grep` on markdown | **structured schemas** (typed fields) | model decides from each stage's result |
| **Parallelism** | none (strictly sequential) | yes — security ∥ tests | yes — security ∥ tests |
| **Special requirements** | none | Workflows enabled (CLI ≥ 2.1.154, paid plan) | none |
| **Determinism of control flow** | high (but fragile parsing) | **highest** | lowest (model-driven) |

### `run-pipeline.sh` — the portable shell loop
- **Pros:** runs anywhere `claude` is installed (no special feature/plan);
  fully transparent plain bash you can read and step through; trivial to run
  or re-run a single agent.
- **Cons:** slowest (six cold-start sessions, strictly sequential, no
  parallelism); gating is `grep` over markdown, which is brittle — bold
  `**PASS**` once caused a false gate FAIL, so the patterns had to be made
  tolerant; one transient API error would kill the whole run, so it needs an
  explicit retry loop; runs **in place** (see idempotency below).

### `run-workflow.sh` — the built-in Workflow
- **Pros:** uses Claude Code's **built-in Workflows** primitive; deterministic
  control flow with **schema-validated gates** (no markdown parsing); real
  parallel fan-out (security ∥ tests); one session, so it's robust to
  per-call hiccups; the whole orchestration lives in one readable script.
- **Cons:** needs the Workflows feature (CLI ≥ 2.1.154, paid plan); scripts
  are plain JS, not TS; per-run config is **baked into a copy** of the script
  because a Workflow `args` object passed through `claude -p` is unreliable;
  the control flow is fixed — it won't adapt if a stage does something
  unexpected.

### `run-orchestrator.sh` — the smart agent orchestrator
- **Pros:** most **flexible / adaptive** — the orchestrator agent reasons
  about each gate and can adjust; one prompt, **no special feature** required
  (it's just an agent); parallel dispatch; the orchestration "playbook" is
  plain English in `agents/bug-fix-orchestrator.agent.md`, easy to evolve.
- **Cons:** gating is **model-driven**, so less guaranteed than schemas; adds
  an extra Opus reasoning layer (more tokens); correctness depends on the
  model following the playbook faithfully; exact behavior is the least
  reproducible of the three.

### Which to use
- **No special features / maximum portability** → `run-pipeline.sh`
- **Determinism, speed, robustness** → `run-workflow.sh`
- **Adaptive orchestration, or Workflows unavailable** → `run-orchestrator.sh`

---

## B5. How isolation & idempotency work

A bug-fix run *changes* the app — once fixed, a second run would find nothing
to do. To make runs **repeatable and independent**, `run-workflow.sh` and
`run-orchestrator.sh` never touch the repo's own `src/`. Instead each run is a
throwaway, self-contained workspace:

1. **Immutable baseline.** `src/app.py.seeded` is the buggy app, kept read-only
   and never edited. It is the single source of truth for "the input".
2. **Fresh workspace per run.** The script creates `runs/<id>/` (timestamped by
   default, or `RUN_ID=<name>`), then **copies the seeded buggy app** into
   `runs/<id>/src/app.py` and seeds `tests/test_smoke.py` + the bug context.
3. **Run pointed at that folder.** The pipeline reads/writes only inside
   `runs/<id>/`. The fixed app, generated `tests/test_app.py`, and all six
   artifacts land there; the repo's `src/` and `context/` stay byte-identical.
4. **Re-run = new folder.** Running again seeds another `runs/<id>/` from the
   same baseline and fixes it independently. N runs ≡ N reproducible results;
   no run depends on or corrupts another. `runs/` is git-ignored.

**Why absolute paths matter (the subtle part).** A dispatched sub-agent does
not reliably inherit a working directory, so simply `cd`-ing into the run
folder is not enough — early attempts leaked artifacts back into the repo
root. The fix is to hand every sub-agent the run folder's **absolute** paths:

- `run-workflow.sh` **bakes** the absolute `runDir`/`rootDir` into a per-run
  copy of the workflow script (passing them as a Workflow `args` object proved
  unreliable — the headless session silently dropped it, and paths fell back
  to the repo root).
- `run-orchestrator.sh` puts the absolute paths in the **prompt** (the `-p`
  argument is delivered reliably) and the orchestrator passes them to each
  sub-agent it dispatches.

This is what guarantees a clean repo after any number of runs (verified: root
checksums unchanged across all test runs).

**`run-pipeline.sh` is the exception — it runs in place.** That matches the
homework's classic single-command design, so it mutates the repo's `src/` and
`context/`. To make *it* idempotent, restore the baseline before each run:

```bash
cp src/app.py.seeded src/app.py    # reset to buggy input
./run-pipeline.sh 001
```

(For a fully isolated `run-pipeline.sh` run, copy the project into a scratch
folder and run it there — that is how it was tested without touching the repo.)

---

## C. Run a single agent (debugging / partial re-runs)

Each agent's behaviour lives in its `agents/<name>.agent.md` file. To run one
agent manually, point a headless session at that definition (there is no
`--agents-dir` flag — the agent loads by being read from disk):

```bash
export ADMIN_API_KEY=test-admin-key
claude -p "Read agents/bug-fixer.agent.md and act as that sub-agent. \
Input: context/bugs/001/implementation-plan.md. Apply the changes to src/app.py, \
run the smoke test after each, and emit context/bugs/001/fix-summary.md." \
  --permission-mode bypassPermissions
```

This is useful when:
- A downstream agent fails and you want to re-run only it
- You want to inspect agent output without rewriting committed files
- You are iterating on an agent's instructions

---

## D. Troubleshooting

**`RuntimeError: ADMIN_API_KEY environment variable is required`**
You haven't exported `ADMIN_API_KEY`. The post-fix app refuses to start
without it (this is intentional — see fix Change 1 in
`context/bugs/001/fix-summary.md`).

**`pytest: command not found`**
Dependencies not installed. Re-run `pip install -r src/requirements.txt`.

**Pipeline gate FAIL in security-report.md**
A CRITICAL or HIGH finding is open. Inspect the report, hand off to a
human reviewer. Do not declare the deliverable complete.

**Verifier reports `Status: FAIL`**
Research quality is L1 or L2 — too imprecise to act on. The pipeline
script will stop here. Re-run the Bug Researcher (likely needs a
better prompt or a different model) and re-verify.

**`claude: command not found`**
Claude Code CLI not installed or not on PATH. See Prerequisites.

---

## E. Cost estimate (per pipeline run)

Rough order-of-magnitude only, based on the 4-finding workload in this
homework:

| Agent                | Model  | Input tokens (est.) | Output tokens (est.) |
|----------------------|--------|---------------------|----------------------|
| Bug Researcher       | sonnet | ~5k                 | ~2k                  |
| Research Verifier    | opus   | ~7k                 | ~2k                  |
| Bug Planner          | opus   | ~6k                 | ~3k                  |
| Bug Fixer            | sonnet | ~6k                 | ~2k                  |
| Security Verifier    | opus   | ~5k                 | ~2k                  |
| Unit Test Generator  | sonnet | ~6k                 | ~3k                  |

Two Opus + four Sonnet calls per run. Treat this as a budgeting
sanity-check, not a guarantee — model pricing is in
`docs.claude.com/en/docs/about-claude/pricing` and changes
periodically.
