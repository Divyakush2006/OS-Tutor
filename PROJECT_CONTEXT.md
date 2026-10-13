# OS Tutor — Project Context

> **Read this first.** One-file briefing on what this project is, the problem it answers,
> every decision taken so far and why, and exactly where it stands.
> **Status as of 11 October 2026.** No code has changed since 28 September 2026; the system
> described here is the current one.

**One-line summary:** a fine-tuned 4B language model that tutors Operating Systems. It
explains concepts and teaches Socratically, and it hands every calculation to deterministic
simulators. It scores **100% (57/57)** on a hand-written OS problem suite with that delegation,
and **63.2%** without it.

| | |
|---|---|
| **Author** | Divyakush Punjabi (24BCB0126) |
| **Course context** | Case study assessment set by Jagalingam Sir (brief: `Problem Statement LLM.docx.pdf`) |
| **Base model** | Qwen3-4B-Instruct-2507 (Apache-2.0) |
| **Current version** | Dataset v3.0.0 · LoRA adapter v3.0 |
| **State** | Built, trained, deployed locally, evaluated. One open weakness (declarative OS theory). |

---

## Contents

1. [The problem statement](#1-the-problem-statement)
2. [How this project answers the brief](#2-how-this-project-answers-the-brief)
3. [The technical problem and the core decision](#3-the-technical-problem-and-the-core-decision)
4. [System architecture](#4-system-architecture)
5. [Dataset](#5-dataset)
6. [Training](#6-training)
7. [Current status — measured results](#7-current-status--measured-results)
8. [Open issues and limitations](#8-open-issues-and-limitations)
9. [Next steps](#9-next-steps)
10. [Base-model research (September 2026)](#10-base-model-research-september-2026)
11. [Decision log](#11-decision-log)
12. [Hard rules and constraints](#12-hard-rules-and-constraints)
13. [Hardware](#13-hardware)
14. [Repository map and commands](#14-repository-map-and-commands)
15. [Pitfalls already hit](#15-pitfalls-already-hit)
16. [Deliverables produced](#16-deliverables-produced)

---

## 1. The problem statement

The assignment is a **case study on building an LLM specifically for learning and teaching
Operating Systems**. The brief (`Problem Statement LLM.docx.pdf`, 4 pages) contains:

- **A survey of existing LLMs for OS teaching** — ChatGPT, Claude, Gemini, Copilot,
  DeepSeek-R1, Qwen 3, Llama 3.3 — with strengths, limitations, and a per-topic
  recommendation (scheduling, deadlocks, paging, disk scheduling, Banker's algorithm, shell
  scripting, system calls, and so on).
- **A recommended architecture:** student → chat interface → OS LLM, backed by both a
  **RAG database** (OS notes, labs, textbooks, PPTs, question banks) and a **fine-tuned
  model** (teaching style, question generation).
- **Option 1 (recommended): RAG + instruction-tuned LLM.** Suggested bases Llama 3.3
  8B/70B, Qwen 3 14B/32B, Mistral Small 24B, Gemma 3 12B/27B. Embeddings with bge-large /
  e5-large / Instructor-XL, stored in FAISS / ChromaDB / Milvus / Weaviate. Knowledge base
  from Silberschatz, lab manuals, PPTs, past papers, viva questions, man pages.
- **Option 2: fine-tuning**, so the model "behaves like an OS professor", trained on
  instruction/output examples.
- **A suggested research title:** *"OSTutorLLM: A Retrieval-Augmented and Fine-Tuned Large
  Language Model for Personalized Operating Systems Education"*, with five possible
  contributions:
  1. Domain-specific educational fine-tuning for OS
  2. Personalized feedback based on student performance
  3. Automatic generation of labs, MCQs and viva questions
  4. Adaptive difficulty levels for theory and practical exercises
  5. Integration with a RAG knowledge base built from institutional teaching materials

The professor has since asked for two submissions, both of which now exist (Section 16):

- **Theory:** "upload the current status of the LLM project".
- **Case study**, structured as: 1 Introduction · 2 Literature review · 3 Objective ·
  4 Dataset collection · 5 Dataset processing · 6 Model architecture design · 7 Conclusion.

---

## 2. How this project answers the brief

**Be explicit about this when presenting.** The project follows the brief's spirit and
deliberately departs from its recommended architecture in one place.

| Brief item | Our status | Notes |
|---|---|---|
| Domain-specific fine-tuning (contribution 1) | **Done** | QLoRA on 11,760 curated rows; adapter v3.0 |
| Chat interface | **Done** | Open WebUI, six modes, auto-routing |
| Fine-tuned model for teaching style | **Done** | SDFT-distilled explanations, Socratic tutoring data |
| RAG knowledge base (contribution 5, "Option 1") | **Built (G2), off by default; awaiting course notes** | `ostutor/rag/`, CPU hybrid retrieval for explain/analyze only; procedures still go to the simulators (D-006) |
| Personalized feedback (contribution 2) | **Partial** | `tutor` mode responds to the student's own attempt; no per-student history or profile |
| Generate labs, MCQs, viva questions (contribution 3) | **Not started** | Only the internal 70-item MCQ eval set exists |
| Adaptive difficulty (contribution 4) | **Not started** | |
| Base model from the suggested list (Qwen3 14B/32B etc.) | **Different — deliberate** | 4B chosen: the suggested sizes cannot train at 16k tokens on free hardware or serve fast on 8 GB (Section 10) |

**Why no RAG.** Retrieval returns text that *resembles* an answer; it cannot certify that a
Gantt chart for a student's own numbers is correct, because that chart exists in no document.
For procedures, computing the answer is a stronger guarantee than retrieving one.

**But RAG is a real gap for the conceptual side.** The project's one measured weakness is
*declarative* OS knowledge (Section 8). Retrieval grounding is exactly the tool for that, and
it is what the brief recommends. Treat "RAG for concepts, simulators for procedures" as the
natural next architecture, not as a contradiction of the current one.

---

## 3. The technical problem and the core decision

General LLMs fail an OS student in three ways:

1. **They execute procedures unreliably.** They state a rule correctly and still produce the
   wrong schedule. Our own diagnosis: all **7 of 7** scheduling failures on the 57-item suite
   had **perfect arithmetic and a wrong schedule**. Scheduling had the most training rows
   (1,733) and the worst accuracy (42%); disk had 990 rows and 100%. More data did not help,
   because the weakness was never a data problem.
2. **They leak answers** when a student needs guiding.
3. **Fine-tuning can erode general ability** (catastrophic forgetting).

**The evidence that (1) is architectural:**

- *The Illusion of Procedural Reasoning* (arXiv 2511.14777): even Qwen3-235B reaches only
  ~50% on long-horizon finite-state-machine execution.
- *The Deterministic Horizon* (arXiv 2606.00376, Guo, Wu, Yiu): state-tracking capacity of
  decoder-only attention is bounded by **O(H · log(L/H) · √d_h)** — heads and *head*
  dimension, not model width. Horizon **d\* ∈ [19, 31]** steps. Tool-integrated reasoning
  86–94% vs 24–42% for neural chain-of-thought.
- *LLM-Modulo* (Kambhampati et al., ICML 2024): LLMs cannot reliably self-verify; use
  external sound verifiers.

**The core decision: the model explains, simulators compute.** The model is never asked to
carry out a procedure. It reads the question, simulators compute the answer, and the model
(or a renderer in its trained format) explains it. This single change took the suite from
**64.9% → 100%** with no retraining, and cut an evaluation pass from 76 minutes to ~150 s.

---

## 4. System architecture

```
Student question
      │
  Auto router ──── shows an attempt ───────────────► Tutor mode (Socratic; no solver,
      │                                                no fact checker — by design)
      ├── solvable problem ─► Parameter extraction ─ grounded ─► Verified simulator
      │                              │                                 │
      │                        ungrounded                    Rendered solution
      │                              ▼                                 │
      └── concept / analysis ─► Fine-tuned model ─► Fact checker ──────┴─► Answer
```

### Components

| Layer | Component | Port |
|---|---|---|
| Weights | llama.cpp b11050 (CUDA), `qwen3-4b-instruct-2507-Q8_0.gguf` + `ostutor-v3-lora-f16.gguf` applied at runtime | 8081 |
| Logic | `serve/gateway.py` (FastAPI): routing, solver delegation, fact checking, loop guard, trained system prompts, greedy decoding, 16,384-token ceiling | 8090 |
| UI | Open WebUI 0.11.3, local only, no auth, background generations disabled | 3000 |

### Modes exposed to students

| Mode | Behaviour |
|---|---|
| `ostutor` **(default)** | Auto mode — routes each question to one of the modes below |
| `ostutor-solve` | Worked solution; simulator-computed when the question is a solver kind |
| `ostutor-analyze` | Open comparison / reasoning ("why is RR better than FCFS for interactive work?") |
| `ostutor-explain` | Concept explanation, fact-checked |
| `ostutor-tutor` | Socratic guidance on the student's attempt; never reveals the answer |
| `ostutor-shell` | Natural language → bash |

The untuned base is **not** offered as a mode; it is still called internally at LoRA scale 0.

### Key components in detail

- **Router (`route()` → `(mode, reason)`):** a lexical "shown attempt" signal **outranks** the
  LLM classifier. Lexical fallback when the classifier is unavailable. 28/28 on labelled cases.
- **Solver (`ostutor/solver.py`):** three stages.
  1. **Extract** typed JSON parameters (7 solver kinds plus `formula`, `concept`, `analysis`,
     `shell`, `incomplete`, `offtopic`). Runs on the **untuned base** — 84% extraction accuracy
     vs 79% for the adapter, which is biased toward solving rather than reading.
  2. **Ground**: every extracted number must appear in the question. Frames and quantum must
     be *stated*, never invented. Ungrounded → fall back to the model. Missing input → ask.
  3. **Solve and render** in the trained worked-steps format.
- **Fact checker (`fact_checked()` + `CORRECTIONS` in `ostutor/theory_filter.py`):** 10
  canonical corrections for misconceptions observed in real answers (e.g. LRU never suffers
  Belady's anomaly). States the correct fact; does not just drop the answer.
- **Loop guard:** cuts repetition loops in stream and non-stream responses without cutting
  legitimate long traces.

---

## 5. Dataset

**`ostutor-sft` v3.0.0**, built by `python -m ostutor.build` (seed 42, ~6 minutes).
Full record: `reports/manifest.json`; human-readable: `DATASET_CARD.md`.

| | |
|---|---|
| Ingested | **80,732** rows from 31 source files, each with line-level provenance |
| Kept after cleaning | 70,170 |
| Deduplicated | −656 exact (blake2b), −1,133 near (MinHash LSH, Jaccard 0.80) |
| Decontaminated | −643 vs 4,836 eval items (13-grams + parameter fingerprints; 15 reworded leaks caught) |
| Rendered | 12,000 |
| **Split** | **11,760 train · 240 val · 600 OOD holdout** |
| Release gates | **19 / 19 pass** |
| Train file SHA-256 | `f56a7113e4aa5c0e4ccde8dfeb91128f7bc50a78aba39e980ed74283af19477d` |
| Tokens | mean 689 · p50 603 · p99 2,753 · max 11,648 → nothing truncated at 16,384 |

### Composition (train split)

| Category | Share | Rows | What it is |
|---|---|---|---|
| Procedural | 64% | 7,526 | Simulator-verified worked numericals — 39 question types, 8 families |
| Replay | 16% | 1,884 | Tülu 3 (commercial-safe), SmolTalk2 no-think — anti-forgetting anchor |
| Tutoring | 8% | 938 | MathDial teacher moves (375) + own OS dialogues from misconception-generated wrong attempts (563) |
| Shell | 6% | 707 | tldr, NL2Bash (MIT TellinaTool), InterCode, NL2SH-ALFA; every command passes `bash -n` |
| Conceptual | 6% | 705 | Self-distilled (SDFT) answers to a 295-question bank in 4 wordings + hand-written gold, fact-checked |

Procedural families: CPU scheduling 1,733 · formula 1,530 · deadlock/Banker's 1,070 · page
replacement 990 · disk scheduling 990 · contiguous allocation 536 · address translation 382 ·
clarification 295.

### Pipeline (11 stages)

Ingest → **Analyse** (rules tested against data before adoption; some rejected on evidence) →
Clean/scrub/repair (PII redacted, secrets destroyed) → Deduplicate → Decontaminate → Score
(category-specific) → Select gold (quality floor, fingerprint/embedding dedup, k-centre
diversity, weighted family waterfill) → Render (model's own chat template) → Split → **Order**
(rectifier interleaving + spaced replay) → **Gate**.

### Anti-forgetting design

16% replay, **surprise-ranked** (SuRe, arXiv 2511.22367) and **spaced** on a forgetting-curve
schedule (FOREVER, arXiv 2601.03938) — every 4 rows early, every 14 late; **rectifier
ordering** (≤ 4 consecutive rows per category, ≤ 3 per source across 81 sources); **SDFT**
targets for theory and tutoring (Yang et al., ACL 2024); **LoRA** as the drift constraint
(Biderman et al., TMLR 2024); **one epoch**.

### Licensing

Every training row is commercially licensed: MIT 8,991 · ODC-BY-1.0 959 · mixed-permissive
925 · CC-BY-4.0 885. Excluded: **ostep-homework** (no licence — offline test oracle only),
**ceval/ceval-exam** (CC BY-NC-SA — eval only), **AnishJoshi/nl2bash-custom** (no licence).

---

## 6. Training

`train/kaggle_train.py`, run on **Kaggle free tier, 2× T4, DDP** via
`torchrun --nproc_per_node=2`. Dataset mounts at
`/kaggle/input/datasets/<user>/<slug>/` (not the usual `/kaggle/input/<slug>/`).

| Setting | Value | Why |
|---|---|---|
| Method | QLoRA via Unsloth | 4-bit base fits 16k-token sequences in 16 GB |
| LoRA | r=32, α=64, all linear layers, dropout 0.05 | |
| LR / schedule | 1e-4, cosine, **1 epoch** | A second epoch memorised more in v2.2 |
| Sequence length | **16,384**, no packing | No truncation; packing would break the rectifier order |
| Precision / optimiser | **fp16**, adamw_8bit | T4 is Turing — no bf16 |
| Regularisation | NEFTune α=5 | |
| Loss | assistant tokens only (`train_on_responses_only`) | |
| Sampler | **sequential** | Shuffling destroys the engineered order |
| OOM safety | `--longest-first` through the real trainer | Replaced a `memory_probe()` that bypassed Unsloth's checkpointing and false-alarmed |

**Outcome** (`outputs/ostutor-lora-v3/ostutor-lora/train_metrics.json`): validation loss
0.4413 → **0.2713**, falling at every one of 12 evaluations; OOD loss 0.0385 → 0.0139;
training loss **0.1773** averaged over the epoch (last logged batches 0.31–0.33).

> **Correction (2026-10-12).** Earlier text here — and in both PDFs in `docs/` — said
> "final training loss 0.2710 vs validation 0.2754, so no memorisation". No 0.2710 exists
> in any training artifact, and 0.2754 is the step-590 validation loss, not the final one.
> The memorisation claim is withdrawn. OOD loss is low because that split is 100%
> templated procedural text, not because the model generalises: the same model answers
> only ~60% of the 57-item suite correctly on its own. Teacher-forced loss does not
> measure free-running correctness. Adapter: `outputs/ostutor-lora-v3/ostutor-lora` (PEFT) and
`models/gguf/ostutor-v3-lora-f16.gguf` (served).

---

## 7. Current status — measured results

All numbers below are measured. Any number not in this section is an estimate or a target.

### Procedural suite — 57 hand-written items, simulator-exact grading

| Configuration | Score | Source |
|---|---|---|
| v3 alone, transformers (NF4 + PEFT) | 37/57 = 64.9% | `reports/eval_finetuned_v3.json` |
| **v3 alone, served path** (llama.cpp, one adapter, `-np 1`) | **36/57 = 63.2%** | `reports/benchmark_v3_single_np1.json` |
| **v3 + verified solver** | **57/57 = 100%** (38 delegated) | same file; reproduced at `-np 4` |

By type (served path): scheduling 5/12 → **12/12**, paging 5/8 → **8/8**, disk 4/7 → **7/7**,
Banker's safety 3/4 → **4/4**, free space 0/4 → **4/4**, translation 1/3 → **3/3**,
clarification 3/3 → **3/3**, remaining 12 kinds 15/16 → **16/16**.

> **`reports/benchmark_v3.json` is VOID.** It loaded v2.2 and v3 together and switched with
> per-request LoRA scales, which does not isolate them (v3 measured 17/57 there vs 36/57 alone).
> Its base and v2.2 columns are void too. See Section 15.

### Catastrophic forgetting — 770 paired items, logit-scored

| Benchmark | Base | v2.2 | **v3.0** | v3 Δ | Right→wrong | Wrong→right |
|---|---|---|---|---|---|---|
| General MMLU (400) | 80.25% | 79.75% | **79.50%** | −0.75 pp | 13 | 10 |
| Adjacent CS (300) | 64.67% | 63.67% | **67.33%** | **+2.66 pp** | 11 | 19 |
| OS theory MCQ (70) | 90.00% | 88.57% | **85.71%** | **−4.29 pp** | 4 | 1 |

Files: `reports/forgetting_base_v3.json`, `forgetting_v2.2_paired.json`, `forgetting_v3_paired.json`.

**Exact McNemar p-values** (`reports/g0/historical_significance.md`, computed 2026-10-12):
general p = 0.678, adjacent CS p = 0.201, OS theory p = 0.375. **No forgetting effect is
statistically detectable in either direction** — not the OS-theory drop, and not the
adjacent-CS gain. Earlier wording that the flips "confirm genuine transfer" is withdrawn.
The base model scores identically item-for-item in the 2026-09-19 and 2026-09-21 runs, so
the evaluation itself is deterministic.

### RAG over the course corpus (G2, 2026-10-12)

Corpus `data/rag/corpus`: 42 course documents from the owners' `dataset_rag.zip` + 8
Hailperin chapters (CC BY-SA 3.0) + 55 Wikipedia articles (CC BY-SA 4.0) = 105 documents,
2,783 chunks (D-007, `docs/RAG_CORPUS.md`). Off unless `OSTUTOR_RAG` is set.

| Measure | Result | Source |
|---|---|---|
| Retrieval recall@5, 124 labelled questions (hybrid) | **79.0%** (course-material answers 74.7%, online 85.7%) | `reports/rag/corpus_eval.md` |
| Retrieval latency, CPU | p95 **8.3 ms** (brief ≤ 500 ms) | same |
| "Not covered" gate, held-out test half | notes for 59/62 in-scope; withheld for 18/20 off-topic | same |
| Theory MCQ, 200 items, generated letter | base 185 · base+RAG 186 · v3 186 · **v3+RAG 184** (all p ≥ 0.75) | `reports/rag/e2e-20261012-2239/summary.md` |
| Explain answers citing the notes | 50/59, **0 invented citations**, 42.9 tok/s | same |
| Faithfulness of cited sentences | judge (base model) 117/143 = 81.8%; engineer check of 40: **24/40** — judge is lenient | same + `judge_sample_engineer_check.json` |

The MCQ target (v3+RAG ≥ base) is **not met numerically** (92.0% vs 92.5%, 1 item, p = 1.0);
on this 200-item set v3 alone is not below base either. Only 132 of 446 answer sentences
carry a citation. The 130 new MCQ items and the 164 retrieval questions are `unreviewed`.

### RAG over the open corpus (G2, 2026-10-13)

At the owner's request (no course material), corpus `data/rag/open` holds 2,970 documents
and 18,515 chunks. It is compiled from a CC BY-SA pool: Hailperin, CSBU, 1,176 Wikipedia
articles, Wikibooks, and 2,019 Stack Exchange Q&As. Chunks are filtered on quality,
relevance to 40 syllabus topics and near-duplication (D-009,
`reports/rag/open_pool_analysis.md`). It is measured on 144 short-answer questions
(`data/eval_rag/os_short_answer.jsonl`, unreviewed) by answer recall.

| Measure | Result | Source |
|---|---|---|
| Answer recall@5, test half (n = 72) | **83.3%** vs course corpus 73.6% (12 gained / 5 lost, p = 0.143) | `reports/rag/compare_test.md` |
| Answer recall@5, all 144 | 83.3% vs 74.3% (21 / 8, **p = 0.024**) | `reports/rag/compare_all.md` |
| Answer recall@10, test half | 94.4% vs 76.4% | `reports/rag/compare_test.md` |
| "Not covered" gate, test half | notes for 72/72 in-scope; withheld for **14/20** off-topic (course corpus: 18/20) | `reports/rag/open_gate.json` |
| Retrieval latency, CPU | p50 23 ms, p95 26 ms | D-009 |
| End to end (MCQ-200, short answer, faithfulness) | pending: needs a free GPU | `python tools/rag_e2e.py data/rag/open` |

### Other

| Check | Result |
|---|---|
| Router, labelled cases | 28/28, zero misroutes on shown-attempt items (`tools/test_router.py`) |
| Pipeline tests | 89 checks pass (`tools/test_pipeline.py`) |
| Gateway tests | 25 checks pass (`serve/test_gateway.py`) |
| Generation speed | **26.9 tok/s** measured (300 tokens, served stack) |
| Dataset gates | 19/19 |

---

## 8. Open issues and limitations

1. **Declarative OS theory: a dip that is not statistically real** — 85.71% vs 90.00% base
   (4 lost, 1 gained, n=70), exact McNemar **p = 0.375**. It cannot be called a regression
   on this evidence; it also cannot be ruled out. The 70-item set is too small to decide,
   which is why the 200-item set (G3) matters. Conceptual answers remain *ungrounded*
   regardless — that, not this number, is the real gap (G2).
2. ~~Base and v2.2 on the procedural suite are unmeasured~~ — measured in G0 (`reports/g0/20261012-1429/regraded.md`): base 30/57, v2.2 19/57; the adapter's gain without the solver is not significant (p = 0.557).
3. **Conceptual tutoring has no verifier and no measurement** — no rubric eval exists.
4. **Formula kinds (11) are not delegated**; the model answers them with its unaided accuracy.
5. **Fact checker is a finite rule list** (10 corrections); it cannot catch unknown errors.
6. **Brief contributions 2–5 are largely unbuilt** — personalization, lab/MCQ/viva generation,
   adaptive difficulty, RAG (Section 2).
7. **Runtime LoRA may cost speed.** 26.9 tok/s is ~45% of the card's bandwidth for a 4.3 GB
   model; merging the adapter before quantizing is untested but likely 10–30% faster.
8. **Institution / department / course code** are missing from both PDF cover pages.
9. **RAG faithfulness is moderate and citation is sparse** — about 60% of cited sentences
   fully supported on a strict check; most answer sentences cite nothing. Needs a stronger
   citation instruction or answer-side verification (report §6.4). Human check pending
   (`reports/rag/e2e-20261012-2239/judge_sample.md`).
10. **Lab handout `Shell programming - sample excersice.doc`** is not in the corpus — Office
   automation hung on it; open in Word, save as .docx, re-run the import.

---

## 9. Next steps

In priority order:

| # | Step | Serves | Cost |
|---|---|---|---|
| 1 | **Zero-shot probe** of Qwen3.5-4B and Gemma 4 12B (`enable_thinking=False`) on the 70-item theory MCQ, with Qwen3-4B-2507 as control | Decide whether a newer base fixes the theory gap before any retraining | ~2 GPU-h |
| 2 | Expand the theory MCQ from 70 to **200** items | A stable estimate that doesn't hinge on 4 questions | Authoring |
| 3 | Measure **base and v2.2** on the 57-item suite, one adapter per server | Completes the "what did fine-tuning buy" comparison | ~45 min GPU |
| 4 | **Targeted declarative replay** (or a LoRA-scale sweep) for regressed topics | Recover theory accuracy to ≥ base | One rebuild + retrain |
| 5 | Prototype **RAG for concepts** over permissively licensed notes | Brief's recommended architecture; addresses item 1 in Section 8 | Medium |
| 6 | Extend delegation to the 11 formula kinds | Procedural 100% at larger scale | Simulator work only |
| 7 | Rubric-scored conceptual tutoring eval | The one area with no number | Medium |
| 8 | Merge LoRA → re-quantize; then try speculative decoding (Qwen3-0.6B draft) | Speed | Small |
| 9 | Brief contributions: MCQ/viva/lab generation, adaptive difficulty | Course brief | Larger |

If step 1 shows Qwen3.5-4B clearly ahead, the migration path is: switch to **16-bit LoRA**
(Unsloth advises against QLoRA on Qwen3.5), check **transformers v5** runs on the Kaggle image,
and confirm fp16 LoRA at 16,384 tokens fits one T4 (~10 GB + activations).

---

## 10. Base-model research (September 2026)

**Conclusion: keep Qwen3-4B-Instruct-2507 for now; probe two 2026 models (step 1 above).**

Why 4B and not the brief's 14B/32B:

| Candidate | Why not (estimates / vendor figures) |
|---|---|
| Dense 14B (Qwen3-14B, Phi-4, Qwen2.5-14B) | ~16–17 GB for QLoRA at 16k — over one T4; ~5 tok/s served on 8 GB VRAM (spills to single-channel RAM). In-band conceptual gain ≈ +1 pp at best. |
| gpt-oss-20b (MoE, 3.6B active) | ~23 GB to train at 16k; hides reasoning in a separate channel. *Serving* is fine: ~15–25 tok/s with llama.cpp `--n-cpu-moe`. |
| Qwen3.5-9B | 22 GB for bf16 LoRA; vendor advises against 4-bit QLoRA on Qwen3.5 |
| Qwen3-30B-A3B, Gemma 4 26B-A4B | Too large for 15.6 GB RAM at usable quantization |
| AirLLM (layer streaming) | ~1.4 tok/s for 14B — only wins when a model fits in neither VRAM nor RAM |

Facts established:

- Qwen3-4B-Instruct-2507 card: MMLU-Pro 69.6, MMLU-Redux 84.2, GPQA 62.0, IFEval 83.4;
  benchmarked *against* Qwen3-30B-A3B. 2024-era 14Bs do not beat it.
- **Qwen3.5** (Feb–Mar 2026, Apache-2.0): 0.8B, 2B, 4B, 9B, 27B, 35B-A3B, 122B-A10B,
  397B-A17B — **no model between 9B and 27B**. Qwen3.5-4B Intelligence Index 27 vs 18 for
  Qwen3-4B-2507 (an aggregate, not a knowledge benchmark). bf16 LoRA: 4B 10 GB, 9B 22 GB.
- **Gemma 4 12B** (3 June 2026, 11.95B, **Apache-2.0**, 256K context, toggleable thinking):
  MMLU-Pro 77.2, GPQA-Diamond 78.8 — **benchmark mode not stated**; may be thinking-mode.
- Speed is a cliff, not a slope: while weights fit 7.3 GB VRAM, cost tracks size; once they
  spill to RAM (~25 GB/s vs ~115 GB/s effective VRAM), throughput falls ~4–5×. A **second
  16 GB DIMM** (dual-channel, 31 GB) is the single highest-leverage hardware upgrade.

Prompts used for external deep research are in conversation history, not the repo; a
reusable copy could go in `docs/`.

---

## 11. Decision log

| Decision | Reason |
|---|---|
| **Verified-solver delegation** instead of more training | Execution failure is architectural; delegation gave 64.9% → 100% with no retraining |
| **RAG for concepts only, opt-in** (D-006) | Retrieval can't certify a computed answer, so procedures stay with the simulators; prose modes retrieve over owner notes; tutor never retrieves |
| **Qwen3-4B-Instruct-2507**, non-thinking | Visible steps for students; fits 16k QLoRA on T4; strong for size |
| **16,384-token sequences** | Longest row 11,648; long worked traces + rectifier order must stay whole |
| **Extraction on the untuned base** | 84% vs 79% for the adapter |
| **Tutoring has no solver and no fact checker** | No path for a computed answer to reach a student mid-attempt |
| **Lexical attempt signal outranks the classifier** | A shown attempt must never be answered |
| **Base removed from the mode picker** | User request; still used internally at scale 0 |
| **Auto mode is the default** | User request; WebUI `DEFAULT_MODELS=ostutor` |
| **One epoch** | v2.2's second epoch memorised more |
| **Sequential sampler** | Shuffling would destroy the rectifier schedule |
| **Paired flips, not just means**, for forgetting | An unchanged mean can hide cancelling losses |
| **Report measured vs expected separately** | Section 7 of the design doc shows targets beside measured values, never in place of them |
| **Declined to swap the OS-theory numbers** in the design doc | Would have fabricated results; reframed as an "expected ≥ 90%" target instead |
| **Do not use AirLLM** | Wrong tool below ~70B on this hardware |

---

## 12. Hard rules and constraints

- **Training happens on Kaggle free tier only.** No paid compute anywhere.
- **Commercial-licence data only** in training. Non-commercial sources are evaluation-only.
- **OSTEP homework is never redistributed or ingested** — offline test oracle only.
- **The Kaggle API key** (`C:\Users\DK\.kaggle\kaggle.json`) is **never printed** or committed.
- **Never send the user's personal details to external services.**
- **Measured numbers are never altered.** Projections are labelled as targets.
- **Cite only papers verified to exist.** All 16 references in the case study were checked.

---

## 13. Hardware

| | Training | Inference / evaluation |
|---|---|---|
| Where | Kaggle free tier | Local Windows 11 laptop |
| GPU | 2 × Tesla T4, 16 GB each (Turing, fp16 only, no FlashAttention-2) | RTX 4060 Laptop, 8,188 MiB (~7.3 GB usable) |
| Memory | — | 15.6 GB DDR5-5200, **single DIMM** (single-channel, ~25–30 GB/s) |
| Bus / disk | — | PCIe 4.0 ×8 (~13 GB/s); Micron 2400 QLC NVMe 512 GB |
| Limits | 12 h/session, 30 GPU-h/week; DDP adds throughput, not memory | Serving stack uses ~7.5 GB VRAM; little free RAM while it runs |

---

## 14. Repository map and commands

```
ostutor/                 data pipeline + solver (python -m ostutor.build)
  build.py               runs all 11 stages, writes reports/manifest.json
  analysis/ clean.py scrub.py dedup.py quality.py select.py mix.py render.py gates.py
  config.py              categories, weights, system prompts per (mode, domain)
  solver.py              extraction → grounding → simulator → render
  theory_filter.py       misconception rules + CORRECTIONS (fact checker)
  simulators/            scheduling, memory, banker, formulas, clarify, dialogues, theory bank
  evaluation/harness.py  simulator-exact grader
train/kaggle_train.py    QLoRA training (Kaggle, 2×T4)
serve/                   gateway.py, start_tutor.ps1, stop_tutor.ps1, tests, llama.cpp/
  rag/                   G2 retrieval: corpus.py (manifest + chunking), retrieve.py (BM25 + MiniLM, gate, citations)
tools/                   evaluation, benchmarking, generation, packaging scripts
                         (g0_*.py ablation/audit/regrade; rag_eval.py, rag_e2e.py; test_g0.py, test_rag.py)
data/                    raw/, build/, eval/ (57-item suite), eval_theory/ (70 MCQ), eval_general/
models/                  Qwen3-4B-Instruct-2507 (HF), gguf/ (base Q8_0 + v2.2/v3 LoRAs)
outputs/                 trained adapters (v2.0, v2.2 = ostutor-lora, v3) and logs
reports/                 manifest, eval and forgetting results, comparisons
docs/                    design document, case study (HTML sources + PDFs + build script)
_archive/                previous pipeline versions (kept; do not delete datasets)
```

### Commands

```powershell
# Build the dataset (all 11 stages + gates)
python -m ostutor.build

# Tests
python tools/test_pipeline.py
serve/.venv-webui/Scripts/python serve/test_gateway.py
python tools/test_router.py
python tools/test_g0.py
python tools/test_rag.py

# Retrieval: measure on the fixture; serve with the owners' notes
python tools/rag_eval.py data/rag/fixture
$env:OSTUTOR_RAG = "data/rag/corpus"   # before start_tutor.ps1; unset = no retrieval
#   or "data/rag/open" (open corpus, D-009): rebuild it first with
#   python tools/fetch_rag_pool.py; python tools/analyze_rag_pool.py; python -m ostutor.rag.ingest data/rag/open
python tools/rag_compare.py --split test   # corpus comparison by answer recall

# Start / stop the local tutor  (UI at http://localhost:3000)
powershell -ExecutionPolicy Bypass -File serve\start_tutor.ps1
powershell -ExecutionPolicy Bypass -File serve\stop_tutor.ps1

# Procedural benchmark on the served path (server must have ONLY v3 loaded)
python tools/benchmark.py --single --only v3 v3+solver --out reports/<name>.json

# Forgetting check (needs the GPU free — stop the stack first)
python tools/run_forgetting_eval.py --4bit --adapter outputs/ostutor-lora-v3/ostutor-lora `
    --compare reports/forgetting_base_v3.json --out reports/<name>.json

# Rebuild the case-study PDF (contents page numbers + footers computed automatically)
python docs/build_case_study.py
```

---

## 15. Pitfalls already hit

| Pitfall | Lesson |
|---|---|
| Two LoRAs loaded in one llama-server, switched by per-request scale | **Does not isolate them.** One adapter per server, restart between configurations. |
| `busy("benchmark.py")` matched `run_full_benchmark.py` itself | The chain waited an hour polling itself. Match the full path. |
| Polling for a free GPU between chained jobs | A poll in the gap between children started llama-server and crashed the next job (`CUDA error: unknown error`). Require several consecutive clear polls. |
| Bash heredocs with regex escapes | Wrote literal `\x08` bytes instead of `\b`; invisible in `grep`. Use the Write/Edit tools for code with backslashes. |
| Edge `--print-to-pdf` | The launcher returns before the file exists; wait for a stable file size. `--no-pdf-header-footer` removes the date/file-path stamp. |
| Git Bash and Windows flags | `taskkill /F` becomes `F:/`; use PowerShell `Stop-Process`. |
| `SP=... && nohup ... &` | The whole chain is backgrounded, so the variable isn't set in the parent shell. |
| `memory_probe()` before training | Bypassed Unsloth's gradient checkpointing and reported a false OOM. |
| `C-SCAN` vs `CSCAN` | Simulator expects `CSCAN`/`CLOOK`; the normaliser must emit those. |
| `numbers_in()` | Missed numbers followed by "."; grounding wrongly rejected valid extractions. |
| `clean.py` tutoring minimum `< 4` messages | Silently discarded all 1,508 OS tutoring rows; now `< 2`. |
| Decontamination keyed on `category == "procedural"` | Removed 58% of OS tutoring; now keyed on the presence of a fingerprint. |
| pypdf `merge_page` | Inflated the PDF from ~0.3 MB to 3.5 MB; compress content streams afterwards. |

---

## 16. Deliverables produced

| Deliverable | Location | For |
|---|---|---|
| **Case study — current project status** (18 pp, professor's 7-section structure, 16 verified references) | `docs/OS-Tutor-Case-Study.pdf` (source `docs/os-tutor-case-study.html`) | Professor's case-study submission |
| **Design document** (8 pp: problem, aim, architecture, software/hardware requirements, uniqueness, expected outcome) | `docs/OS-Tutor-Design-Document.pdf` (source `docs/os-tutor-design-document.html`) | Review panel |
| Design document, online collaborative copy | online doc "OS Tutor — Design Document" — **out of sync**: lacks the expected-outcome rewrite and author names | — |
| **Project report with RAG** (dataset · preprocessing · code + screenshots · results · what went wrong · improvements) | `docs/OS-Tutor-Project-Report.pdf` (source `docs/os-tutor-rag-report.html`; `python docs/build_code_shots.py` then `python docs/build_rag_report.py`) | Assignment submission; RAG figures are fixture-measured or labelled targets |
| Dataset card | `DATASET_CARD.md` | Dataset documentation |
| Planning research | `OSTutorLLM-Dataset-Pipeline.md`, `OSSolverLLM-Model-Selection.md` | Background (September 2026; parts superseded by Section 10) |
| Anti-forgetting notes | `docs/ANTI_FORGETTING.md` | Background |
