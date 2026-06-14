export const meta = {
  name: 'fix-bugs',
  description:
    'End-to-end bug-fix pipeline for the Task Tracker app, run against an ISOLATED workspace. Drives the project sub-agents in order: research → verify (gate on quality) → plan → fix (gate on status) → security ∥ tests (parallel). Every path is absolute and rooted at args.runDir, so each sub-agent reads/writes only the run workspace regardless of its working directory — the repo source is never touched. Gates on structured results instead of grepping markdown.',
  phases: [
    { title: 'Research', detail: 'enumerate defects with file:line precision' },
    { title: 'Verify', detail: 'fact-check + rate research quality (gate ≥ L3)' },
    { title: 'Plan', detail: 'concrete before/after change plan' },
    { title: 'Fix', detail: 'apply changes, test after each (gate = PASS)' },
    { title: 'Harden', detail: 'security review ∥ unit-test generation' },
  ],
}

// ---------------------------------------------------------------------------
// Configuration. run-workflow.sh passes ABSOLUTE paths via args so nothing
// here depends on the sub-agents' working directory — the reason an earlier
// CWD-relative version leaked artifacts back into the repo root.
//   args.runDir  — absolute path of the isolated run workspace (seeded buggy)
//   args.rootDir — absolute repo root (source of the canonical agent/skill defs)
// ---------------------------------------------------------------------------
const BUG_ID = (args && args.bugId) || '001'
const RUN_ID = (args && args.runId) || 'in-place'
const RUN_DIR = (args && args.runDir) || '.'
const ROOT_DIR = (args && args.rootDir) || '.'

const SRC = `${RUN_DIR}/src`
const TESTS = `${RUN_DIR}/tests`
const CTX = `${RUN_DIR}/context/bugs/${BUG_ID}`
const RESEARCH = `${CTX}/research`
const AGENTS = `${ROOT_DIR}/agents`
const SKILLS = `${ROOT_DIR}/skills`
const SMOKE_CMD = `ADMIN_API_KEY=test-admin-key pytest ${TESTS}/test_smoke.py -v`
const SUITE_CMD = `ADMIN_API_KEY=test-admin-key pytest ${TESTS}/ -v`

// Each stage runs as a generic sub-agent that *becomes* the project agent by
// reading its definition file. The workspace contract pins every read/write to
// the absolute run workspace so a stray CWD can't redirect an artifact.
function brief({ def, skills = [], task }) {
  const contract = [
    'WORKSPACE CONTRACT — operate ONLY on these absolute paths; never read or',
    'write the same-named files at the repo root:',
    `  • app source dir   : ${SRC}`,
    `  • tests dir        : ${TESTS}`,
    `  • artifacts dir    : ${CTX}   (research under ${RESEARCH})`,
    `  • smoke test cmd   : ${SMOKE_CMD}`,
    'Wherever your agent definition says `src/`, `tests/`, or',
    `\`context/bugs/${BUG_ID}/\`, substitute the absolute paths above.`,
  ].join('\n')
  const skillLine = skills.length
    ? `Read and apply these skills first: ${skills.map((s) => `${SKILLS}/${s}.md`).join(', ')}.`
    : ''
  return [
    `You are the "${def}" sub-agent in the Task Tracker bug-fix pipeline (bug ${BUG_ID}, run "${RUN_ID}").`,
    `Read your full agent definition at ${AGENTS}/${def}.agent.md and follow its Process, Output format, and Protocol guarantees exactly.`,
    skillLine,
    contract,
    task,
    'After writing your artifact file, return the structured result requested by the schema. The structured result is for the orchestrator only; the human-facing deliverable is the artifact file on disk.',
  ]
    .filter(Boolean)
    .join('\n')
}

// ---------------------------------------------------------------------------
// Gate schemas — small, objective signals the orchestrator branches on.
// ---------------------------------------------------------------------------
const RESEARCH_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['emitted', 'findingsCount', 'files'],
  properties: {
    emitted: { type: 'boolean', description: 'codebase-research.md written to the artifacts dir' },
    findingsCount: { type: 'integer' },
    files: { type: 'array', items: { type: 'string' } },
  },
}

const VERIFY_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['status', 'qualityLevel', 'confirmedFindings'],
  properties: {
    status: { type: 'string', enum: ['PASS', 'PASS_WITH_DISCREPANCIES', 'FAIL'] },
    qualityLevel: { type: 'string', enum: ['L1', 'L2', 'L3', 'L4', 'L5'] },
    confirmedFindings: { type: 'integer' },
  },
}

const PLAN_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['emitted', 'changeCount', 'filesTouched'],
  properties: {
    emitted: { type: 'boolean', description: 'implementation-plan.md written to the artifacts dir' },
    changeCount: { type: 'integer' },
    filesTouched: { type: 'array', items: { type: 'string' } },
  },
}

const FIX_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['status', 'changesApplied', 'filesChanged', 'fullSuite'],
  properties: {
    status: { type: 'string', enum: ['PASS', 'FAILED'] },
    changesApplied: { type: 'integer' },
    filesChanged: { type: 'array', items: { type: 'string' } },
    fullSuite: { type: 'string', description: 'e.g. "15 passed, 0 failed"' },
  },
}

const SECURITY_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['gate', 'criticalOpen', 'highOpen'],
  properties: {
    gate: { type: 'string', enum: ['PASS', 'FAIL'] },
    criticalOpen: { type: 'integer' },
    highOpen: { type: 'integer' },
  },
}

const TESTS_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['testFile', 'testsAdded', 'suiteResult', 'firstCompliant'],
  properties: {
    testFile: { type: 'string', description: 'absolute path of the test file written' },
    testsAdded: { type: 'integer' },
    suiteResult: { type: 'string', enum: ['PASS', 'FAIL'] },
    firstCompliant: { type: 'boolean', description: 'all FIRST principles satisfied' },
  },
}

// ---------------------------------------------------------------------------
// Pipeline.
// ---------------------------------------------------------------------------
log(`Bug ${BUG_ID} — run "${RUN_ID}". Isolated workspace: ${RUN_DIR}`)

// Stage 1 — Research.
phase('Research')
const research = await agent(
  brief({
    def: 'bug-researcher',
    task: `Inspect ${SRC} and ${TESTS} and emit ${RESEARCH}/codebase-research.md per your protocol. Read ONLY the "Purpose" and "Expected Pipeline Outcome" sections of ${CTX}/bug-context.md — stop at the first "Seeded" heading.`,
  }),
  { label: 'research', phase: 'Research', schema: RESEARCH_SCHEMA },
)
log(`Research: ${research.findingsCount} finding(s) → ${RESEARCH}/codebase-research.md`)

// Stage 2 — Verify (gate: refuse to proceed on FAIL or low-quality research).
phase('Verify')
const verified = await agent(
  brief({
    def: 'research-verifier',
    skills: ['research-quality-measurement'],
    task: `Input: ${RESEARCH}/codebase-research.md. Fact-check every reference against ${SRC}, rate quality with the skill, and emit ${RESEARCH}/verified-research.md.`,
  }),
  { label: 'verify', phase: 'Verify', schema: VERIFY_SCHEMA },
)
log(`Verify: status=${verified.status}, quality=${verified.qualityLevel}, confirmed=${verified.confirmedFindings}`)

if (verified.status === 'FAIL' || verified.qualityLevel === 'L1' || verified.qualityLevel === 'L2') {
  log(`✘ Gate FAILED at Verify — research is not actionable (status=${verified.status}, quality=${verified.qualityLevel}). Stopping per protocol.`)
  return { ok: false, stoppedAt: 'verify', runId: RUN_ID, bugId: BUG_ID, research, verified }
}

// Stage 3 — Plan.
phase('Plan')
const plan = await agent(
  brief({
    def: 'bug-planner',
    task: `Input: ${RESEARCH}/verified-research.md. Produce a deterministic before/after change plan and emit ${CTX}/implementation-plan.md. For per-change verification, prescribe exactly this command: \`${SMOKE_CMD}\`. Do not write to ${SRC}.`,
  }),
  { label: 'plan', phase: 'Plan', schema: PLAN_SCHEMA },
)
log(`Plan: ${plan.changeCount} change(s) → ${CTX}/implementation-plan.md`)

// Stage 4 — Fix (gate: a failed fix must not reach security/test stages).
phase('Fix')
const fix = await agent(
  brief({
    def: 'bug-fixer',
    task: `Input: ${CTX}/implementation-plan.md. Apply each change to ${SRC}/app.py, running the prescribed smoke test after each. Stop on the first failing test. After all pass, run the full suite \`${SUITE_CMD}\`. Emit ${CTX}/fix-summary.md.`,
  }),
  { label: 'fix', phase: 'Fix', schema: FIX_SCHEMA },
)
log(`Fix: status=${fix.status}, applied=${fix.changesApplied}, suite=${fix.fullSuite}`)

if (fix.status !== 'PASS') {
  log(`✘ Gate FAILED at Fix — ${fix.status}. Stopping before security/test stages.`)
  return { ok: false, stoppedAt: 'fix', runId: RUN_ID, bugId: BUG_ID, research, verified, plan, fix }
}

// Stage 5 — Harden. Security review and test generation both depend only on
// fix-summary.md and are mutually independent → run them concurrently.
phase('Harden')
const [security, tests] = await parallel([
  () =>
    agent(
      brief({
        def: 'security-verifier',
        task: `Input: ${CTX}/fix-summary.md. Review ONLY the files it lists (under ${SRC}). Emit ${CTX}/security-report.md. Set gate=FAIL if any CRITICAL or HIGH issue is open.`,
      }),
      { label: 'security', phase: 'Harden', schema: SECURITY_SCHEMA },
    ),
  () =>
    agent(
      brief({
        def: 'unit-test-generator',
        skills: ['unit-tests-FIRST'],
        task: `Input: ${CTX}/fix-summary.md. Write regression tests for the changed code only to ${TESTS}/test_app.py, run the suite with \`${SUITE_CMD}\`, and emit ${CTX}/test-report.md.`,
      }),
      { label: 'tests', phase: 'Harden', schema: TESTS_SCHEMA },
    ),
])

if (security) log(`Security: gate=${security.gate}, critical_open=${security.criticalOpen}, high_open=${security.highOpen}`)
else log('Security: stage errored (null result)')
if (tests) log(`Tests: ${tests.testsAdded} added → ${tests.testFile}, suite=${tests.suiteResult}, FIRST=${tests.firstCompliant}`)
else log('Tests: stage errored (null result)')

// Final acceptance gate.
const ok = !!security && security.gate === 'PASS' && !!tests && tests.suiteResult === 'PASS'
log(ok ? '✅ Pipeline complete — all gates passed.' : '⚠️ Pipeline finished with at least one open gate.')

return { ok, runId: RUN_ID, bugId: BUG_ID, research, verified, plan, fix, security, tests }
