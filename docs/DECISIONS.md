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
