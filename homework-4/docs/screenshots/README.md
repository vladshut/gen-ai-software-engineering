# Screenshots

This folder is the home for the screenshots requested in the homework
deliverables table. Per `TASKS.md`:

> **Screenshots**: pipeline runs (bugs found → fixes → security → tests)
> + the fixed app demonstrating correct behaviour.

The student capturing the screenshots should produce the following
PNGs in this folder. File names are suggestions, not strict
requirements; what matters is that each numbered item below is
covered.

---

## 01-pipeline-run.png

A terminal showing `./run-pipeline.sh 001` executing end-to-end.
Either the full scroll or a representative pair of frames (start +
end) is acceptable. The "Pipeline complete for bug 001" line at the
bottom should be visible.

## 02-research-and-verification.png

Side-by-side or two-screen capture of:
- `context/bugs/001/research/codebase-research.md` — at least the four
  findings header
- `context/bugs/001/research/verified-research.md` — the
  `Status: PASS` and `Research Quality: L4` lines

## 03-fix-and-security.png

Side-by-side or two-screen capture of:
- `context/bugs/001/fix-summary.md` — at least the `Overall Status: PASS`
- `context/bugs/001/security-report.md` — at least the Summary Table
  and `Pipeline gate: PASS`

## 04-test-suite-green.png

Terminal output of `ADMIN_API_KEY=test-admin-key pytest tests/ -v`
showing `15 passed` against the **fixed** `src/app.py`.

## 05-test-suite-detects-bugs.png

Terminal output of the same pytest invocation against the **buggy**
baseline (`cp src/app.py.seeded src/app.py` first), showing `10 failed,
4 passed`. This is the proof that the regression tests are not
vacuous.

## 06-app-running.png

A `curl` session against a running `uvicorn` showing:
- A `GET /tasks?limit=5` returning exactly 5 items
- A `GET /tasks/1 OR 1=1` returning `422`
- A `PATCH /tasks/9999/complete` returning `404`

---

## Capture tips

- Use a 100 % zoom terminal so text is legible at standard PR-review
  resolution.
- Crop tightly — the reviewer should not need to hunt for the
  relevant line in a sea of shell prompt.
- For diff-style captures, two side-by-side files (split view in
  VS Code, or `code -d before.md after.md`) photograph well.

After capturing, delete this README or replace it with a short
caption file mapping each PNG to its corresponding deliverable.
