---
name: research-quality-measurement
description: Use this skill whenever you need to assess, label, or report the quality of a bug-research artifact produced by a research agent. Trigger when reading or writing `verified-research.md`, when a Research Verifier is judging a Bug Researcher's findings, or when any task requires assigning a quality level (L1–L5) to a piece of investigative output. Apply even if the user does not explicitly say "research quality" — any time bug research is being audited, fact-checked, or graded, this skill defines the rubric.
---

# Research Quality Measurement

## Purpose

Provide a single, deterministic rubric for grading the output of a Bug
Researcher agent. The Research Verifier **must** apply this rubric when
writing `verified-research.md`. Any other agent that consumes research
output (Bug Planner, Bug Fixer) must respect the assigned level when
deciding how much to trust the findings.

## Quality Levels

Each level is **inclusive** — L4 implies all properties of L1–L3.

### L1 — Surface

- Issue is named at a high level ("there is a SQL injection somewhere
  in the task endpoints").
- No specific file references.
- No code snippets.
- **Trust posture**: not actionable. Planner must re-investigate.

### L2 — Located

- Each finding includes `path/to/file.py` reference.
- No line numbers or no code snippet, or both are imprecise.
- **Trust posture**: minimally actionable. Planner may proceed but
  must read the referenced files in full.

### L3 — Cited

- Each finding includes `path/to/file.py:LINE` (single line or range).
- Includes a verbatim code excerpt of the suspect code (≤10 lines).
- Single source per claim (one file:line per finding is fine).
- **Trust posture**: standard. Planner may write the implementation
  plan directly from the research without re-reading the codebase.

### L4 — Cross-validated

- All of L3, plus:
- For each finding, at least one of:
  - A reproduction step (curl command, test snippet, or input that
    triggers the issue), **or**
  - A second corroborating source (a related test, a related call
    site, a documented spec).
- Impact statement (who/what is affected, blast radius).
- **Trust posture**: high. Planner may also skip part of the planning
  phase when the research already contains the fix shape.

### L5 — Comprehensive

- All of L4, plus:
- Each finding has a proposed remediation approach (not the full code,
  just the strategy).
- Risk/dependency analysis (does fixing this break other things?).
- Coverage statement: which files were inspected, which were skipped
  and why.
- **Trust posture**: maximal. Suitable for fully autonomous downstream
  agents with no human-in-the-loop.

## How the Verifier Applies the Rubric

1. Read `research/codebase-research.md` in full.
2. For each finding in the research:
   - Open the referenced file(s) and confirm the line numbers exist.
   - Confirm any code excerpt matches the actual source byte-for-byte
     (allowing for whitespace normalisation).
   - Note any discrepancies in a `Discrepancies Found` section.
3. Determine the **lowest** level for which all findings satisfy the
   criteria. That is the **overall research quality**.
4. If individual findings vary, list per-finding levels in addition to
   the overall.

## Required Structure of `verified-research.md`

```markdown
# Verified Research — bug 001

## Verification Summary
- Status: PASS | PASS_WITH_DISCREPANCIES | FAIL
- Research Quality: L1 | L2 | L3 | L4 | L5

## Verified Claims
- [finding-id] [path:line] [verdict: confirmed | adjusted | rejected]

## Discrepancies Found
- ...

## Research Quality Assessment
- Overall level: Lx
- Reasoning: ...
- Per-finding levels: ...

## References
- research/codebase-research.md
- src/app.py
```

## Anti-patterns to Reject

- **Vague impact claims** without a reproducer ("this could be
  exploited") → downgrade to L3 even if file:line is present.
- **Speculation framed as fact** ("the bug is on line 91") without an
  open-the-file verification → downgrade and mark in Discrepancies.
- **Multiple findings collapsed into one** → split into separate
  entries before grading.
