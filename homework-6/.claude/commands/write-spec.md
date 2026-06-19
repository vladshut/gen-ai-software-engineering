---
description: Generate specification.md for a multi-agent pipeline using the IndyDevDan spec template
---

# /write-spec

Generate a `specification.md` for this project following the five-section spec
template. Use the frozen contracts in `TASKS.md` / `HW6-build-plan.md` as the
source of truth. If `$ARGUMENTS` names a focus area, scope the spec to it.

Produce `specification.md` with EXACTLY these five sections:

1. **High-Level Objective** — one sentence describing the end goal of the system.
2. **Mid-Level Objectives** — 4–5 bullet points, each a concrete, testable
   capability the system must have.
3. **Implementation Notes** — technical guidance: language/version, libraries,
   coding standards, the file-based `shared/` protocol, the coverage gate
   (≥80% required, ≥90% target), determinism (no LLM calls inside agents),
   PII masking, and money handling (Decimal + ROUND_HALF_UP).
4. **Context** — beginning context (files that exist now) and ending context
   (files that will exist after implementation).
5. **Low-Level Tasks** — an ordered list with **one task per agent**
   (transaction_validator, fraud_detector, settlement_processor) plus the
   integrator, the MCP server, and the test suite. Each task states the
   prompt/instruction, the file it creates, and its acceptance check.

Rules:
- Keep it faithful to the frozen contracts (currency set, fraud weights,
  decision bands, FX rates, fee, oracle outcome).
- Each low-level task must be independently verifiable.
- Write the result to `specification.md` at the project root.
