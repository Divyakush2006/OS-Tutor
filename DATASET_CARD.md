# ostutor-sft v3.0.0: dataset card

Supervised fine-tuning data for an Operating Systems tutor built on
**Qwen3-4B-Instruct-2507** (non-thinking; reasoning appears as visible numbered steps).

Built 2026-09-20T08:02:07+00:00 with Python 3.13.3, seed 42, config `9911d5b564141e53`.

| split | rows | purpose |
|---|---|---|
| `train.jsonl` | 11,760 | training, in rectifier order (do **not** shuffle) |
| `val.jsonl` | 240 | in-distribution validation; early stopping and checkpoint selection |
| `ood.jsonl` | 600 | held-out problems in framings never trained on (monitoring and final testing only, never for checkpoint selection) |

The build is reproducible: two consecutive builds produce byte-identical artifacts
(`python tools/verify_reproducible.py`). Artifact SHA-256 hashes, the config hash,
every source file's hash and every stage's statistics are in `manifest.json`.

    train.jsonl  sha256 f56a7113e4aa5c0e4ccde8dfeb91128f7bc50a78aba39e980ed74283af19477d
    val.jsonl    sha256 353a02c3195938c837663e40a703372a07543f1332f100aa2add0b14213afeb8
    ood.jsonl    sha256 520d29cf3b7b93212609577fce3bb6d0ac68a200ae67e5116c625948f8e4b5e6

## Composition of the training split

| category | designed | rows | realised | drift (pp) | mean quality | diversity |
|---|---|---|---|---|---|---|
| procedural | 64% | 7,526 | 64.0% | -0.00 | 0.833 | 0.599 |
| conceptual | 6% | 705 | 6.0% | -0.01 | 0.692 | 0.708 |
| tutoring | 8% | 938 | 8.0% | -0.02 | 0.804 | 0.694 |
| shell | 6% | 707 | 6.0% | +0.01 | 0.728 | 0.944 |
| replay | 16% | 1,884 | 16.0% | +0.02 | 0.767 | 0.958 |
| **total** | 100% | **11,760** | | | | |

- **procedural** — Simulator-verified numeric problems, worked step by step, with every decision written as a rule plus the comparison behind it. 39 question types across 8 weighted families: CPU scheduling (FCFS, SJF, SRTF, RR, priority, preemptive priority, HRRN), page replacement (FIFO, LRU, OPT, CLOCK), Banker's safety and request (including UNSAFE states), disk scheduling (FCFS, SSTF, SCAN, LOOK, C-SCAN, C-LOOK), contiguous allocation (first/best/worst fit), address translation, 11 formula kinds (EAT, multilevel paging, deadlock minimum, fork count, ...), and clarification items where a required input is missing and the correct behaviour is to ask rather than to guess.
- **conceptual** — Explanations of OS concepts. Self-distilled from the base model (SDFT, Yang et al., ACL 2024) over a hand-written 295-question bank in four wordings, then sanitised and fact-checked: any answer asserting a known misconception is dropped, never repaired. Plus hand-written, fact-checked gold explanations.
- **tutoring** — Socratic dialogue. MathDial supplies real teacher moves; the OS half is self-distilled replies to a student's WRONG attempt, where the wrong answer is generated from a named misconception (non-preemptive SJF for an SRTF question, FIFO faults for LRU, ...). Any reply that reveals the correct final answer, or that affirms the wrong attempt, is rejected.
- **shell** — Natural language to bash (tldr, NL2Bash, InterCode). Every command parses under `bash -n`.
- **replay** — General instruction data (Tulu 3, SmolTalk2 no-think) held as the anti-forgetting anchor set: surprise-ranked, spaced through training.

Total size is ratio-bound, not chosen: the ceiling is 12,000 rows and the achievable total is 12,000, bound by **tutoring**, the category with the least distinct supply relative to its designed share. Mixture drift never exceeds 0.02 percentage points, so the realised mix is the designed mix.

### Composition within each category

Row counts do not show what a category contains. These do.

| category | breakdown |
|---|---|
| procedural, by family | cpu_scheduling 1,733 (23%), formula 1,530 (20%), deadlock_bankers 1,070 (14%), page_replacement 990 (13%), disk_scheduling 990 (13%), contiguous_allocation 536 (7%), address_translation 382 (5%), clarify 295 (4%) |
| tutoring, by domain | os 563, math 375 |
| conceptual, by domain | os 705 |
| tutoring, by source | simulators/own 563, eth-nlped/mathdial 375 |

### Licensing

Every training row is commercially licensed: mit 8,991, odc-by-1.0 959, mixed-permissive 925, cc-by-4.0 885.

Excluded sources, with the reason for each:

- **AnishJoshi/nl2bash-custom** — no declared licence; superseded by MIT TellinaTool data/bash
- **ostep-homework** — no declared licence; offline test oracle only, never ingested
- **ceval/ceval-exam** — CC BY-NC-SA: evaluation only, never training

## Pipeline (`python -m ostutor.build`)

1. **Ingest** 80,732 rows, each with line-level provenance (source file and row index): procedural 16,720, conceptual 1,485, tutoring 3,633, shell 21,066, replay 37,828.
2. **Per-category analysis** runs BEFORE any cleaning. Each candidate cleaning rule is tested against the data and adopted only if the evidence supports it; the verdicts are written to `reports/analysis/`.
3. **Clean, scrub, repair.** 70,170 of 80,732 rows kept. Rows containing credential material are destroyed; PII is redacted (card numbers Luhn-checked). Rows are dropped for refusals, degenerate repetition, non-Latin replay, bash syntax errors, and tutoring turns that reveal the answer.
4. **Deduplicate.** 656 exact (blake2b) and 1,133 near-duplicates (MinHash LSH, Jaccard 0.80).
5. **Decontaminate** against all 4,836 evaluation items (643 rows removed). Prose rows: distinctive 13-grams, ignoring the 93 boilerplate n-grams that appear in more than 5 training rows. Generated rows: exact parameter fingerprint, which also catches a reworded leak (15 matches).
6. **Score** every row with a category-specific quality scorer.
7. **Select gold**, per category: quality floor, identity dedup (parameter fingerprint for generated problems, embedding similarity otherwise), then farthest-point (k-centre) diversity selection. Procedural selection is a weighted waterfill over question families, so a scarce family cannot starve a large one.
8. **Render** with the model's own chat template and a (mode, domain)-specific system prompt.
9. **Split, then order.** Rectifier interleaving is applied to the training split: at most 4 consecutive rows from one category (measured 4), at most 3 from one source dataset (measured 1, across 81 sources), replay spaced from every 4 rows early to every 14 later (Ebbinghaus-style spacing, after FOREVER), with 0 spacing violations and a longest replay gap of 11.
10. **Verify** every invariant on the rows actually shipped, not on the plan.
11. **Release gates.** All 19 must pass or the build fails.

| gate | result | detail |
|---|---|---|
| `secrets_zero` | pass | 0 rows with credential material (limit 0) |
| `no_think_blocks` | pass | 0 rows contain <think> |
| `licence_commercial` | pass | 0 non-commercial rows |
| `schema_valid` | pass | 0 rows fail schema |
| `defect_rate` | pass | 0 known defects = 0.000% (limit 0.000%) |
| `non_latin_rate` | pass | 0 non-Latin-script rows |
| `token_p99` | pass | p99 token length 2753 (limit 16384) |
| `rectifier_invariants` | pass | category run 4/4, worst spacing violation 0 |
| `source_run_bounded` | pass | longest single-dataset run 1 across 81 sources (max 3) |
| `mixture_drift` | pass | worst drift +0.02pp (limit 2.0pp) {'procedural': -0.0, 'conceptual': -0.01, 'tutoring': -0.02, 'shell': 0.01, 'replay': 0.02} |
| `distinct_answers` | pass | lowest distinct-answer ratio 0.988 in "procedural" (min 0.9) |
| `template_share` | pass | largest template share 0.099 in "conceptual" (max 0.25) |
| `pairwise_diversity` | pass | lowest diversity 0.599 in "procedural" (min 0.3) |
| `min_rows_per_category` | pass | smallest category 705 rows (min 50) |
| `min_total_rows` | pass | 11760 train rows (min 2000) |
| `ood_holdout_present` | pass | 600 genuinely out-of-distribution rows in the holdout (600 total ood) |
| `procedural_inputs_complete` | pass | 0 procedural questions omit an input they need (train sources, OOD holdout, eval suites) |
| `os_tutoring_present` | pass | 563 OS-domain tutoring rows (min 300, 938 tutoring rows in total) |
| `family_weights_honoured` | pass | 0 procedural families below half their designed share  |

## Sequence length

Rendered length, in tokens of the model's own tokenizer: mean 689, p50 603, p90 1,397, p99 2,753, max 11,648 (8,270,468 tokens in total).

Training length is 16,384 tokens, above the longest row, so **no training example is ever truncated** and no worked answer loses its final line. `reports/TOKEN_BUDGET.md` measures the worst case per question type and size.

## Anti-forgetting and anti-overfitting

- **Replay.** 16% general instruction data, surprise-ranked (SuRe) within a diverse pool and spaced through training rather than front-loaded.
- **Self-distillation.** Theory and tutoring targets are the BASE model's own answers (SDFT), so training on them anchors behaviour the adapter must not damage instead of overwriting it with a foreign style.
- **LoRA as the constraint.** A low-rank adapter bounds how far the weights can move (Biderman et al., TMLR 2024: LoRA forgets less than full fine-tuning).
- **One epoch** over a large, deduplicated, fingerprint-distinct pool. A second epoch bought little in v2.2 and memorised more.
- **Rectifier ordering** prevents long runs of one category or source, so no single skill is learned in one uninterrupted block and then decayed.
- **Measured, not asserted.** Forgetting is tested by MMLU with paired flips (how many answers were lost and gained, not just the net), before and after.

## Training

`kaggle_train.py` (QLoRA, 2x T4 with DDP under `torchrun --nproc_per_node=2`):

- r=32, alpha=64 on all linear layers, dropout 0.05, lr 1e-4, cosine, 1 epoch;
- 16,384-token sequences, no packing (packing would merge neighbouring rows and break the ordering guarantees);
- fp16 (Turing has no bf16), `adamw_8bit`, NEFTune alpha 5, gradient checkpointing;
- loss on assistant tokens only, so the model learns to answer, not to echo;
- a **sequential** sampler, because shuffling would destroy the rectifier schedule;
- validation every ~8% of steps, early stopping, best-checkpoint restore; the OOD split is logged as a second loss but never used to select a checkpoint - it is test data;
- a memory probe on the longest row before step 1, so an OOM fails in the first minute rather than after hours.

## Known limitations

- **Tutoring supply bounds the dataset.** Growing it means writing or distilling more genuine material in that category; rewordings of what is already there would only add memorisation pressure.
- **Self-distilled targets inherit the base model's style.** That is the point (it is what makes them anti-forgetting anchors), but it also means the tutor's voice is the base model's voice, cleaned up - not a new one.
- **The fact-checker is a finite list of rules.** It catches the misconceptions it knows (each one observed in real answers) and cannot catch an error nobody has written a rule for. Rejections are logged so the list can grow.
- **Embeddings are nearly blind to numbers.** Diversity is measured with MiniLM, which is why generated problems are deduplicated by parameter fingerprint instead.
- **The simulators define correctness.** Where a textbook uses a different convention (for example the disk-head return jump), the simulator's convention is stated in the problem so the answer is well defined.

