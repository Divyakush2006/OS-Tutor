# Decision record

Non-obvious engineering decisions for OS Tutor v3.1 onward. Each entry: the decision, the
alternatives considered, the reason, and the evidence. Earlier decisions (v1–v3.0) are
summarised in `PROJECT_CONTEXT.md` Section 11.

---

## D-001 — Version control: git, code only, byte-exact

**Date:** 2026-10-12 · **Approved by:** owners

**Decision.** Initialise a local git repository tracking code, docs, reports and evaluation
sets (~7 MB, 135 files at baseline `f6f554e`). Disable line-ending conversion
(`core.autocrlf=false`, `.gitattributes: * -text`).

**Alternatives.** (a) No git, record per-file SHA-256 in reports instead. (b) Track
everything including model weights.

**Reason.** The v3.1 brief requires small reviewable commits and a commit hash in every
report; (a) cannot give either. (b) would put 12 GB of weights, a 920 MB llama.cpp build,
licence-restricted OSTEP material and `.webui_secret_key` under version control.

Line-ending conversion is disabled because the dataset build manifest records SHA-256
hashes of source files: a CRLF rewrite on checkout would change those bytes silently and
break the reproducibility check.

**Evidence.** Staged-file audit at init: no secrets, no `oracle/`, no weights, largest file
1.07 MB. Nothing is pushed to any remote.

**Correction (same day).** The baseline `f6f554e` was staged *before* `core.autocrlf` was
turned off, so git normalised 57 CRLF files to LF in the repository — the opposite of
this decision. Found when edits to `solver.py` showed as whole-file diffs. Fixed in
`3d9f654`, which stores those files as they are on disk (whitespace-only; `git diff -w`
is empty). A check that every tracked file's HEAD blob equals its disk bytes now passes.
One knock-on effect: while chasing the symptom, `serve/gateway.py` was converted from
CRLF to LF on disk in `b7521be`; it stays LF (Python is indifferent to line endings).

---

## D-003 — Grader: a quantity's answer ends at a LaTeX separator or the next quantity

**Date:** 2026-10-12 · **Decided by:** engineer (alters no existing measured number — verified)

**Decision.** In `ostutor/evaluation/harness.py::_answer_number`, a quantity's segment
now also ends at `\quad`, `\qquad`, `;`, or the next "average / avg / mean" quantity.

**Alternatives.** (a) Leave it and hand-audit base outputs. (b) Strip all LaTeX before
grading. (c) Ask an LLM judge to read the final answer.

**Reason.** The base model writes LaTeX: `\boxed{Average waiting time = 17/3 \approx 5.67},
\quad \boxed{Average turnaround time = 47/3 \approx 15.67}`. The old segment ended only at
`, <letter>`, so it ran past `, \quad` and read the *turnaround* time (15.67) as the
waiting time — marking a correct answer wrong. The fine-tuned adapter writes the trained
`**Answer:**` format and is not affected, so the bug biases every base-vs-adapter
comparison in the adapter's favour: exactly what G0 is meant to measure. (b) would also
remove structure other grading depends on; (c) adds a non-deterministic grader.

**Evidence.** Found in the G0 smoke run (`rr_classic`, base). Re-grading all **805**
saved outputs in `reports/` with old and new code changes exactly **1** verdict (that
item, wrong → right); no historical reported number moves. Seven regression cases in
`tools/test_g0.py`, including that line and every format the old code already handled.
Because one blind spot was found, base-alone wrong answers in the G0 run are additionally
hand-audited and the audit is reported separately.

---

## D-002 — Fact checker attaches the correction when its redraft is unavailable

**Date:** 2026-10-12 · **Approved by:** owners (student-facing change, failure path only)

**Decision.** In `serve/gateway.py::fact_checked`, when the redraft call to the model
server fails (server down, timeout), return the canonical correction prepended to the
draft — the same output the existing "redraft still wrong" branch produces — instead of
returning the draft unchanged.

**Alternatives.** (a) Keep behaviour; fix only the test. (b) Drop the answer entirely and
return only the correction.

**Reason.** The previous code returned the original draft on any redraft error, so a
student received a known misconception ("Yes, LRU suffers from Belady's anomaly.") with
no warning — contradicting the function's own stated rule ("state the fact plainly
rather than ship the misconception"). (b) discards the rest of a possibly useful answer;
attaching the correction matches an existing, reviewed behaviour, so it adds no new
output shape.

**Evidence.** Found during the v3.1 baseline run: `serve/test_gateway.py` failed with the
model server down (`-> Yes, LRU suffers from Belady's anomaly.`) and passed with it up.
The test was non-hermetic — it exercised the real `_upstream` call. It now stubs
`_upstream` and covers all three branches (clean redraft, still-wrong redraft, redraft
unavailable): 28/28 pass with the server down. Run against the old `gateway.py`, the new
"redraft unavailable" test fails with exactly the defect, so it guards the regression.
Happy path unchanged.
