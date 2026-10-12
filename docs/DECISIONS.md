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

## D-006 — RAG: CPU hybrid retrieval, prose modes only, off by default

**Date:** 2026-10-12 · **Decided by:** engineer (no student-facing change until the
owners set `OSTUTOR_RAG`)

**Decision.** `ostutor/rag/`: notes are chunked by heading (≤ 180 words, 30-word
overlap); BM25 (pure Python) and all-MiniLM-L6-v2 embeddings (Apache-2.0, local cache
only) are fused by reciprocal rank (k = 60); an abstain gate returns nothing when the
notes do not cover the question. The gateway appends the passages to the *trained*
system prompt (kept word for word first) for `explain` and `analyze` only, asks for
`[S1]`-style citations and adds a sources footer. Tutor mode never retrieves; solve mode
keeps the simulator. Off unless `OSTUTOR_RAG` names a corpus directory.

**Alternatives.** (a) A vector database (FAISS / Chroma) as the brief suggests.
(b) A larger embedding model (bge-large, Qwen3-Embedding-0.6B — both cached locally).
(c) Retrieval in tutor mode too. (d) Dense-only retrieval.

**Reason.** At course-notes scale (hundreds to low thousands of chunks) a NumPy dot
product is exact and takes milliseconds, so (a) adds a service and no accuracy. (b)
costs CPU time and RAM next to an 8 GB-VRAM stack that already leaves little free; it is
the first thing to try if real-notes recall is low. (c) would let a passage state the
answer a student is working towards — the tutor's one hard rule. (d) loses exact terms;
on the fixture, BM25 alone was the best single retriever.

**Evidence.** `reports/rag/fixture_eval.md`: hybrid section recall@4 95.6%, p95 latency
5.7 ms on the CPU (brief: ≤ 500 ms). The v1 gate (cosine < 0.35), chosen before any
measurement, abstained on only 6/10 out-of-scope questions, because the classes overlap
(in-scope minimum 0.34, out-of-scope maximum 0.40). The v2 gate (cosine < 0.45 **and**
BM25 < 6.0) abstains 10/10 but was fitted on the same queries and must be refitted on
held-out queries over the owners' notes. 29 checks in `tools/test_rag.py`; 6 new gateway
checks (34/34), every earlier one unchanged with retrieval off.

---

## D-005 — Evaluation requests disable llama-server's prompt cache

**Date:** 2026-10-12 · **Decided by:** engineer (evaluation only; serving unchanged)

**Decision.** Every request from `tools/g0_ablation.py` sends `cache_prompt: false`, and
the run's provenance records it. The student-facing gateway keeps the cache on.

**Alternatives.** (a) Keep the cache and report several runs as a noise band. (b) Fix
the request order so cache states repeat. (c) Disable the cache in serving too.

**Reason.** With the cache on, greedy decoding is not reproducible. The cache reuses the
KV of a shared prefix (the system prompt) left by whatever request came before, which
changes how the prompt is batched and so the logits; a greedy decode then diverges.
v3 alone scored 36/57 on 2026-09-21 and 34/57 on 2026-10-12 with identical weights and
only 23/57 identical outputs — purely because the two runs issued requests in different
orders. (a) makes every number a sample, (b) is brittle, (c) costs students latency for
a reproducibility property they do not need: the cache changes *which* plausible answer
is sampled, not the distribution.

**Evidence.** `tools/g0_diagnostics.py` (results in `reports/g0/20261012-1429/
diagnostics.json`): with the cache off, repeating a request with an unrelated request
in between gave byte-identical output **6/6**; with the cache warmed by a different
prompt, **5/6** differed.

---

## D-004 — Grader: read an explicit final-answer marker first (paging, disk, translate)

**Date:** 2026-10-12 · **Decided by:** engineer (alters no existing measured number — verified)

**Decision.** For the one-quantity kinds, `grade()` first reads the number under the
last explicit final-answer marker ("Final Answer", "**Answer"), on that line or the next;
the keyword search remains the fallback. Hex in the marker is decoded.

**Reason.** The G0 grader audit (`tools/g0_grader_audit.py`) found five base-model
answers that were right and graded wrong. The base model ends with "### ✅ Final
Answer:" and the bare number on the next line ("**236**"), with no keyword, so the
keyword search fell back to a line of working ("Total: 53 + 183 = 236" read as 53).
The fine-tuned model's trained format is unaffected, so the bug again biased base-vs-
adapter comparisons toward the adapter.

**Evidence.** Old vs new grader over every saved output: **0** verdict changes in 799
historical outputs; in the G0 run exactly the **5** hand-audited items flip
(`lru_4f`, `scan_down`, `fcfs_disk`, `sstf_2`, `translate_4k`), nothing else in any
configuration. Eight regression cases in `tools/test_g0.py`, including a marker with a
wrong value (stays wrong) and the unchanged trained format.

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
