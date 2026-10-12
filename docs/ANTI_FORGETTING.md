# Catastrophic forgetting and overfitting: methods considered and chosen

Target: Qwen3-4B-Instruct-2507, QLoRA on two Kaggle T4s (16 GB each, fp16, DDP,
≤12 h sessions), v3.0 training rows at up to 16,384 tokens. Methods were chosen on
three criteria:
- the evidence behind them;
- whether they fit that hardware;
- whether their effect can be **measured** here.

## Applied

| method | where | what it does |
|---|---|---|
| Experience replay (Rolnick et al., NeurIPS 2019) | data: 16% of rows | Mixes general instruction data (Tulu 3, SmolTalk2 no-think) into every stretch of training, so general-ability gradients are never absent. |
| Spaced replay, Ebbinghaus schedule (after FOREVER, arXiv 2601.03938) | data: rectifier order | Replay is dense early, where drift is fastest (gap ≤ 4 rows), and spaced out later (gap ≤ 14). Verified on the shipped rows: 0 spacing violations. |
| Surprise-ranked replay (after SuRe, arXiv 2511.22367) | data: replay selection | Among a diverse replay pool, keeps rows with the highest base-model NLL. Those carry the knowledge most at risk of being overwritten. |
| Interleaving, the "rectifier" (a project term, not a published method) | data: ordering | At most 4 consecutive rows from one category and at most 3 from one source dataset (measured: 1). There are no long single-domain blocks for the model to specialise on. The trainer's sampler is sequential so the order survives training. |
| Low-rank, parameter-efficient update (Biderman et al., "LoRA Learns Less and Forgets Less", TMLR 2024) | training | LoRA r=32 trains about 1.6% of parameters. The frozen base limits how far general behaviour can drift. |
| Quality over quantity (Zhou et al., LIMA, 2023) | data: gold selection | Applies to KNOWLEDGE rows (theory, tutoring, shell, replay): a deduplicated, diversity-selected set rather than a large noisy one. **v3.0 stopped applying it to procedural rows**: v2.2 kept ~1,000 of 10,500 verified problems, leaving ~30 examples per algorithm, and the model learned the answer format without learning the decisions. Skills need repetition; knowledge does not. |
| Self-distillation fine-tuning (SDFT, Yang et al., ACL 2024) | data: theory + OS tutoring | v3.0 trains explanation and tutoring behaviour on the **base model's own answers** (sanitised, and rejected if they assert a known misconception). Targets drawn from the model's own distribution keep the shift small, which is the strongest data-side protection for a capability the base model already has. v2.2's template-generated explanations measurably damaged that capability. |
| NEFTune (Jain et al., 2023) | training | Noise on the embeddings reduces overfitting to exact surface forms. |
| Early stopping on held-out validation loss | training | The best checkpoint is restored. The OOD loss is monitored but never used for selection, so it remains a fair test. |
| Conservative optimisation | training | lr 1e-4, cosine schedule, weight decay 0.01, LoRA dropout 0.05. **v3.0 trains ONE epoch** over a much larger pool: more unique examples instead of repeated passes, which is both better for skills and safer for forgetting. |
| Loss on assistant tokens only | training | The model is not trained to reproduce prompts, which removes a source of memorisation. |

## Considered, not applied (and why)

| method | reason |
|---|---|
| EWC (Kirkpatrick et al., PNAS 2017) | Needs Fisher-information estimates over the base weights, with the associated memory and compute. That is impractical on a T4 with a 4-bit base, and replay achieves the same aim through the data. |
| O-LoRA (Wang et al., 2023) / OPLoRA (AAAI) | Orthogonal-subspace constraints are designed for sequences of tasks. This is a single fine-tune, so there is no earlier adapter subspace to protect. OPLoRA is the upgrade path if later OS modules are trained as further stages. |
| Self-distillation for PROCEDURAL rows (Yang et al., ACL 2024) | Applied to theory and tutoring in v3.0 (see above), but never to worked solutions: a rewrite could corrupt simulator-verified numbers. Procedural targets stay simulator-rendered and re-verified. |
| Self-synthesized rehearsal (Huang et al., ACL 2024) | Generates replay from the base model itself. Real commercially licensed replay data (Tulu 3, SmolTalk2) is available, so synthetic rehearsal adds risk without clear benefit here. |

## Measured, not assumed

| check | tool | baseline recorded |
|---|---|---|
| General-knowledge retention: MMLU history, biology, philosophy, nutrition (400 items) | `tools/run_forgetting_eval.py` | 80.25% |
| Adjacent CS retention: MMLU college CS, security, ML (300 items) | same | 64.67% |
| Paired flips (right→wrong vs wrong→right, item by item) | same, `--compare` | produced on the fine-tuned run |
| OS procedure accuracy, in-distribution and generator-OOD | `tools/run_eval.py` | v2.2: 65% / 50% (the OOD suite was repaired in v2.2.1) |
| **OS accuracy on hand-written free-form questions** (57 items, no generator involved) | `tools/run_eval.py --suites os_freeform` | v2.2 measured 29% through the chat UI: the number that predicted real behaviour |
| **OS theory accuracy** (70 hand-written MCQs, logit-scored) | `tools/run_forgetting_eval.py` (group `os_theory`) | recorded for base and for v2.2 |
| Explanation quality regression | reading answers side by side vs the base model | v2.2's explanations were WORSE than the untuned base (template collapse, factual slips), which is why v3.0 rebuilt the theory data |
| Train vs validation vs OOD loss during training | `train/kaggle_train.py` | falling together through step 120 |

Contamination is ruled out for the general-knowledge set: 0 of 1,164 items share a
13-gram with the shipped `train.jsonl`.

**Pass criteria for the fine-tuned adapter**
- General MMLU accuracy is within 2 points of the base.
- Right→wrong flips do not substantially exceed wrong→right flips.
- OS accuracy improves on **both** the in-distribution and OOD suites. An improvement
  only in-distribution would indicate template learning.
