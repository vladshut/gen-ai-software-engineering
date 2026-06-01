# Homework 4 — 4-Agent Bug-Fix Pipeline

**Author**: Vladyslav Shut
**Submission date**: 2026-06-01
**Course**: Gen AI Software Engineering — [Alexey-Popov/gen-ai-software-engineering](https://github.com/Alexey-Popov/gen-ai-software-engineering)

---

## Overview

This homework delivers a Claude Code-based agentic pipeline that
operates on a small FastAPI application:

```
flowchart LR
  R[Bug Researcher] --> V[Research Verifier]
  V --> P[Bug Planner]
  P --> F[Bug Fixer]
  F --> S[Security Verifier]
  F --> T[Unit Test Generator]
```

Although the homework headline mentions "4 agents", the full run order
specified in `TASKS.md` requires six agents (Researcher and Planner in
addition to the four named in the task list). Both stub agents are
included as first-class members of the pipeline — see
`agents/bug-researcher.agent.md` and `agents/bug-planner.agent.md` for
the rationale.

The pipeline operates on a small **Task Tracker** FastAPI app with two
seeded bugs and two seeded security issues. It discovers, fixes,
security-reviews, and regression-tests them in a single command. Two
runners are provided:

Three runners, three orchestration styles — **same six agents, same
artifacts**:

- **`./run-pipeline.sh`** — a **shell loop**: boots one `claude -p` per
  agent, sequentially, gating with `grep`. Portable; no special CLI
  features.
- **`./run-workflow.sh`** — a **deterministic Workflow script**
  (`workflows/fix-bugs.mjs`): one session, structured-schema gating, and
  Security∥Tests in parallel. Needs Claude Code ≥ 2.1.154 with Workflows.
- **`./run-orchestrator.sh`** — **model-driven orchestration**: one prompt
  hands control to the `bug-fix-orchestrator` **agent**, which runs in the
  main session and dispatches the six specialists via the Task tool.

`run-pipeline.sh` writes its artifacts under `context/bugs/001/`;
`run-workflow.sh` and `run-orchestrator.sh` each isolate a run under
`runs/<id>/` (seeded with the buggy app, fixed there, results kept there)
so you can re-fix the bugs repeatedly without touching the repo's `src/`.

### Why the orchestrator is an *agent*, not a *skill*

Two Claude Code constraints force the choice: **sub-agents cannot spawn
sub-agents** (so the orchestrator can't be a dispatched sub-agent), and
**skills don't load in headless `claude -p`** (so a skill wouldn't trigger
from a single command). The fit is an **agent run as the main thread** —
the only context with the Task tool — which reads each specialist's
`.agent.md` and dispatches it. See `agents/bug-fix-orchestrator.agent.md`.

## Repository layout

```
homework-4/
├── README.md                    # this file
├── HOWTORUN.md                  # operational runbook
├── run-pipeline.sh              # runner 1: shell loop, one claude -p per agent
├── run-workflow.sh              # runner 2: one Workflow script (gated + parallel)
├── run-orchestrator.sh          # runner 3: one prompt → orchestrator agent
├── workflows/
│   └── fix-bugs.mjs             # multi-agent workflow: gated + parallel stages
├── agents/                      # 6 specialists + 1 orchestrator (Claude Code format)
│   ├── bug-fix-orchestrator.agent.md    # main-session orchestrator (runner 3)
│   ├── bug-researcher.agent.md
│   ├── research-verifier.agent.md       (Task 1)
│   ├── bug-planner.agent.md
│   ├── bug-fixer.agent.md               (Task 2)
│   ├── security-verifier.agent.md       (Task 3)
│   └── unit-test-generator.agent.md     (Task 4)
├── skills/
│   ├── research-quality-measurement.md  (Task 1.2)
│   └── unit-tests-FIRST.md              (Task 4.2)
├── context/bugs/001/
│   ├── bug-context.md                   # seeded-issue catalog
│   ├── research/
│   │   ├── codebase-research.md         # Researcher output
│   │   └── verified-research.md         # Verifier output
│   ├── implementation-plan.md           # Planner output
│   ├── fix-summary.md                   # Fixer output
│   ├── security-report.md               # Security output
│   └── test-report.md                   # Test gen output
├── src/                                  # Task 5: sample app
│   ├── app.py                            # FIXED state (Working app)
│   ├── app.py.seeded                     # buggy baseline (for replay)
│   ├── requirements.txt
│   └── .env.example
├── tests/
│   ├── test_smoke.py                     # pre-existing smoke test
│   └── test_app.py                       # regression tests (Test gen)
└── docs/screenshots/                     # see Submission section
```

## Model selection per agent

Each agent declares an explicit model in its frontmatter. Justifications
in full live in the agent files; summary table:

| Agent                | Model  | Why                                       |
|----------------------|--------|-------------------------------------------|
| Bug Researcher       | sonnet | Broad inspection, low hallucination cost  |
| Research Verifier    | opus   | Hallucination-resistant fact-checking     |
| Bug Planner          | opus   | Reasoning-heavy planning                  |
| Bug Fixer            | sonnet | Structured, deterministic execution       |
| Security Verifier    | opus   | Adversarial reasoning, low false-negative tolerance |
| Unit Test Generator  | sonnet | Pattern-driven test scaffolding           |

Two Opus calls + four Sonnet calls per run is the deliberate cost
profile: pay for reasoning where errors compound downstream (verifier,
planner, security); use Sonnet where the work is structured execution.

## What the pipeline produces

Running `./run-pipeline.sh` on a fresh checkout where `src/app.py` is
the seeded buggy version produces:

1. `context/bugs/001/research/codebase-research.md` — 4 findings.
2. `context/bugs/001/research/verified-research.md` — quality L4, all
   confirmed.
3. `context/bugs/001/implementation-plan.md` — 4 ordered changes.
4. `context/bugs/001/fix-summary.md` — 4 applied, smoke tests green.
5. `context/bugs/001/security-report.md` — pipeline gate PASS, no
   open CRITICAL/HIGH.
6. `context/bugs/001/test-report.md` — 14 regression tests added, full
   suite 15/15 passing in 0.60 s.

All six output files are committed alongside this README for review.

## Submission

- Pull request to the course repository with summary commit message.
- Screenshots in `docs/screenshots/` — see `docs/screenshots/README.md`
  for what to capture.
- Author/student information at the top of this file (please fill in
  before submitting).

## Critical notes (transparency)

A senior architect's review of the homework spec uncovered three real
issues that the submitter handled explicitly rather than glossing over:

1. **6 agents vs "4-agent" headline.** The run order in TASKS.md
   requires Bug Researcher and Bug Planner agents that are not in the
   four required Task headers. This submission treats them as
   first-class agents (see `agents/`).
2. **Folder name discrepancy** in TASKS.md ("Expected Project Structure"
   says `homework-5/` but the file lives under `homework-4/`). This
   submission uses `homework-4/` to match the file location.
3. **Test ordering**. TASKS.md specifies Bug Fixer → Security → Tests,
   so per-change tests in the implementation plan use the pre-existing
   smoke test rather than not-yet-written named tests. Comprehensive
   regression tests are added by Unit Test Generator after the Fixer
   completes.

These deviations are documented here for the reviewer rather than
hidden.
