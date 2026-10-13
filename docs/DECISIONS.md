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

## D-009 — Open OS corpus: openly licensed sources only, compiled by measured filters

**Date:** 2026-10-13 · **Requested by:** owner ("ignore my faculty's notes … the best
dataset") · **Decided by:** engineer (sources, filters, choice rule)

**Decision.** A second corpus, `data/rag/open` (corpus `f16f42d89331`; 2,970 documents,
18,515 chunks), built only from openly licensed OS text, with no course material:
Hailperin's *Operating Systems and Middleware* (CC BY-SA 3.0, pinned commit), Wienand's
*Computer Science from the Bottom Up* (CC BY-SA 3.0, DocBook at a pinned commit),
1,176 Wikipedia articles from 24 OS categories at recorded revisions (CC BY-SA 4.0),
Wikibooks *Operating System Design* (CC BY-SA 4.0), and 2,019 Stack Exchange questions
from cs and unix under OS tags with question score ≥ 3 and up to two answers scoring ≥ 3
(CC BY-SA 2.5/3.0/4.0 by post date; authors named per document). It is fetched by
`tools/fetch_rag_pool.py` and compiled by `tools/analyze_rag_pool.py`. Every chunk is
measured for letter share, code share, relevance (MiniLM cosine to the nearest of 40
syllabus topics, ACM CS2013 OS area) and near-duplication (MinHash LSH, Jaccard ≥ 0.7,
book > Wikipedia > Wikibooks > Stack Exchange). A chunk is dropped if its letter share is
< 0.60, its code share is > 0.50, its relevance is below the floor, or it is a duplicate.
Documents under 120 words are dropped whole. The relevance floor is **0.307**, the 5th
percentile of the two textbooks' chunks. The rules and the choice rule were fixed before
any measurement. The choice rule: change the compiled corpus only if a variant beats it
on dev with p < 0.05. The gate is refitted for this corpus (cosine ≥ 0.52 or BM25 ≥ 24.0).

**Alternatives.** (a) The unfiltered pool (`data/rag/open_all`, the control). (b) Any
single-source corpus. (c) The variant without Hailperin, best on dev. (d) Keep the course
corpus. (e) MMLU-Pro or other benchmark text: only about 14 genuine OS items. Excluded on
licence: OSDev wiki (mixed), LibreTexts (unverified per page), the xv6 book (unverified),
OSTEP (not openly licensed), and every NC-licensed text.

**Evidence.** Pool analysis is in `reports/rag/open_pool_analysis.md`; comparisons are
in `reports/rag/compare_{dev,test,all}.md`. The question set is 144 short-answer
questions with aliases (`data/eval_rag/os_short_answer.jsonl`, unreviewed). Recall is
answer recall: a top-k chunk contains an accepted answer.

- **Coverage.** Kept chunks contain an answer to 71/72 dev questions; the course corpus
  covers 65/72.
- **Test split (n = 72, never used for a choice).** Recall@5 is **83.3%** for open
  against 73.6% for course (12 gained, 5 lost, p = 0.143, not significant at this size).
  Recall@10 is 94.4% against 76.4%.
- **All 144 questions.** Recall@5 is 83.3% against 74.3% (21 gained, 8 lost,
  **p = 0.024**). Dev was used only to apply the fixed rule; nothing was tuned on it.
- **Filters.** They remove 15% of chunks (21,715 → 18,515) at no recall cost: open_all
  scores 83.3% on dev and 81.9% on test.
- **Ablations.**
  - Without Wikipedia, test recall@5 falls to 65.3% (p = 0.002); Wikipedia is the
    source that matters.
  - (c) Without Hailperin, dev scores 87.5% against open's 83.3%, but p = 0.25, and on
    test it scores 81.9%. Keeping Hailperin is the right call.
  - Without Stack Exchange, test scores 84.7% (p = 1.0) and dev 79.2%; it stays.
- **Gate.** On test, notes are given for 72/72 in-scope questions and withheld for
  **14/20** out-of-scope ones, against 18/20 on the course corpus. The leaks are
  near-topic questions the wider corpus partly covers: JVM garbage collection, B-trees,
  ACID/CAP, HTTP/2, monads and polymorphism.
- **Latency.** CPU retrieval latency is p50 23 ms and p95 26 ms (course corpus: 8 ms).
- **A defect found by the analysis.** The first build kept Wikipedia "See also",
  "External links" and reference lists: 1,137 of 19,674 chunks. A heading-level
  off-by-one in `wikitext_to_md` caused it; it is fixed and covered by tests. The
  rebuilt corpus has 39 such chunks. Recall@5 did not change, recall@10 on test rose
  from 93.1% to 94.4%, and the gate thresholds were refitted and came out the same.
- **Labelling.** Passages from this corpus are presented to the model as "reference
  passages". The student sees "Sources (openly licensed references, not your course
  notes)", or "Not found in the reference corpus". The wording comes from the
  manifest's `label`; the course corpus wording is unchanged and tested word for word.

**Trade-offs.**
- The course corpus cites the students' own slides, which the open corpus cannot.
- The open corpus abstains less often off-topic.
- `docs/`, `extracted/` and `index/` are not committed (about 70 MB, rebuildable).
  The committed manifest holds each document's checksum, revision URL and attribution,
  so a rebuild that drifts is refused.

**End to end** (`reports/rag/e2e-20261013-1339/summary.md`, course run
`reports/rag/e2e-short-course/`, comparison `reports/rag/short_e2e-short-course_vs_e2e-20261013-1339.md`;
greedy, prompt cache off; all 288 retrieval-off replies identical across the two runs):

- **Short answers, v3, test half (n = 72; pre-registered grading).** Without retrieval:
  49 correct (68.1%). With the open corpus: **62 (86.1%)**, 17 gained and 4 lost,
  **p = 0.0072**. On all 144: 102 → 123 (p = 0.0011). Base behaves the same (48 → 62).
- **Open vs course, end to end.** With the course corpus v3 scores 59/72 on test and
  124/144 overall; with the open corpus 62/72 (p = 0.55) and 123/144 (p = 1.0).
  **The better retrieval does not show up as better answers.**
  - v3 already answers 102/144 without retrieval. Retrieval helps only when the passages
    hold an answer the model lacks: 25 items with the course corpus, 26 with the open one.
  - Most of the open corpus's extra hits are on questions the model already gets right.
  - Off-target passages turned a right answer wrong 7 times with the open corpus and
    3 times with the course corpus.
- **MCQ-200.** base 185, base + open 184, v3 186, v3 + open 186 (p = 1.0 throughout;
  course run 184). The MCQ set is at ceiling for every configuration.
- **Explain (72 test questions, v3 + open).**
  - **69/72** answers cite at least one passage (target ≥ 90%: met; the course run's
    rate was 50/59, on a different question set).
  - 0 invented citations, 0 truncated.
  - Decode speed: median 42 tok/s, slowest 39 tok/s (brief: ≥ 20).
- **Faithfulness.** The judge marks 110/138 cited sentences supported (79.7%). My strict
  check of 40 (`judge_sample_engineer_check.json`, not the human check): **25/38** claims
  fully supported, with 2 "Reference:" lines not counted. The course run scored 24/40.
  The judge is again lenient (8 vs 1 disagreements); the usual fault is a detail the
  passage does not contain.
- **Secondary grading.** Hyphen = space, an exact number reply counts, and four aliases;
  fixed from the base model's misses before v3 was read. It adds 2–4 items per arm and
  changes no conclusion.

**Recommendation.** Both corpora raise short-answer accuracy by about 15 points, and
neither is measurably better end to end. Serve the open corpus where students need wide
coverage and a working citation rate. Serve the course corpus where answers should
point to the course's own slides and say "not covered" more often (18/20 vs 14/20).
Either way, a citation check on the answer side (§6.4 of the report), not more data,
is what would move faithfulness.

---

## D-008 — Course corpus: ingestion, embedding model and a calibrated "not covered" gate

**Date:** 2026-10-12 · **Decided by:** engineer (G2 success criteria)

**Decision.** `python -m ostutor.rag.ingest data/rag/corpus` is the single ingest command.
It refuses the whole corpus if any document lacks source, owner, date, checksum or a
licence/permission, if a file changed after it was recorded, or if any supported file has
no manifest entry. Extraction (`ostutor/rag/extract.py`) keeps slide titles ("Slide 4:
…"), Word headings and PDF pages plus large-font headings as citation anchors; it drops
PDF running headers (a line on ≥ ⅓ of pages) and folds ligatures (NFKC). Retrieval stays
BM25 + all-MiniLM-L6-v2 with rank fusion. The abstain gate's two thresholds are fitted
per corpus on the dev half of the labelled questions and stored in `gate.json`; when it
abstains, the answer carries "Not found in the course materials".

**Alternatives.** (a) multilingual-e5-base (278M) as the embedder. (b) Keep the fixture's
thresholds. (c) Answer silently from general knowledge when nothing is found.

**Reason / evidence** (`reports/rag/corpus_eval.md`, `corpus_multilingual-e5-base_eval.md`,
124 in-scope + 40 out-of-scope questions over 2,783 chunks). MiniLM hybrid recall@5
**79.0%**, e5-base 81.5%: 11 vs 8 unique misses, exact McNemar **p = 0.65**, not a real
difference, at 3× the query latency (p95 25 ms vs 8 ms), a 5.5-minute index build and
~1 GB more RAM next to a stack that leaves little free. (b) BM25 scores scale with the
corpus: the fixture threshold (6.0) would have kept notes for nearly every off-topic
question here; the calibrated gate is cosine ≥ 0.59 or BM25 ≥ 18.5. On the held-out test
half it gave notes for **59/62** in-scope questions and withheld them for **18/20**
out-of-scope ones. (c) violates the brief ("says so explicitly").

---

## D-007 — RAG corpus sources: the owners' course material plus openly licensed texts

**Date:** 2026-10-12 · **Approved by:** owner (instruction of 2026-10-12: "you can get more
online … add these with those found online")

**Decision.** The corpus holds (1) the professor's material from `dataset_rag.zip`
(42 documents kept, permission recorded as "supplied by the project owners for use in this
tutor; not for redistribution"; not committed to git), and (2) only openly licensed online
text: Max Hailperin, *Operating Systems and Middleware*, rev. 1.3.1 — 8 OS chapters,
**CC BY-SA 3.0** (licence stated in the book source and README), pinned to commit
`3567f8f8`; and 55 English Wikipedia OS articles, **CC BY-SA 4.0**, pinned to revision ids.
12 files are excluded with reasons in the manifest (duplicates, images without text, the
assignment brief, one legacy .doc Office would not convert, two PDF copies of Word handouts).

**Alternatives.** (a) The owners' material only. (b) Free-to-read textbooks (OSTEP, Galvin
slides found online). (c) Non-commercial texts (Little Book of Semaphores, Think OS:
CC BY-NC-SA).

**Reason.** The brief's rule was "never add copyrighted textbook text the owners did not
supply"; the owner has now asked for online material to supplement theirs. (a) leaves
gaps: no file systems, disk scheduling or deadlock theory beyond one problem sheet.
(b) OSTEP is free to read but not openly licensed, so only the chapters the professor
supplied are included. (c) would contradict the project's commercial-licence rule.
Attribution for every online document is in its manifest entry and is shown in citations.

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
