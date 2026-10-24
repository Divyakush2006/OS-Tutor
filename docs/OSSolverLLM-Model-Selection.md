# OSSolverLLM: Choosing the Best Open Base Model for QLoRA Fine-Tuning on Kaggle Free Tier

*Prepared for: DKP — OS education LLM research project*
*Date: September 2026*

---

## TL;DR

- **Primary recommendation: Qwen3-4B-Instruct-2507** (Apache 2.0, non-thinking) — the sweet spot for auditable step-by-step OS numericals: strong math (MMLU-Pro 69.6, GPQA 62.0, AIME25 47.4), trains comfortably in QLoRA on a single Kaggle T4 (16 GB), first-class Unsloth/GGUF/vLLM/Ollama support, clean license for publishing weights and institutional deployment, and it is the *same model an existing CS-education fine-tuning paper used successfully*.
- **Runner-up: Qwen3-8B (Apache 2.0)** for more capacity while still fitting one-T4 QLoRA.
- **Paper baseline: Llama-3.1-8B-Instruct** (community-standard reference, weaker math) plus the *un-fine-tuned base Qwen3-4B* to isolate your fine-tuning gains.
- **Do not use a thinking/reasoning model as the base** (Qwen3-Thinking, DeepSeek-R1 distills, Phi-4-reasoning, Magistral). Your task wants deterministic, verifiable, fixed-format worked solutions; SFT on non-reasoning-trace data measurably degrades these models and creates `<think>`-tag/decoding complications. Use the instruct/non-thinking variant.

---

## Key Findings

### Kaggle free tier (2026) — confirmed specs

- Per Kaggle's official docs (kaggle.com/docs/efficient-gpu-usage): *"You can use up to a quota limit per week of GPU. The quota resets weekly and is 30 hours or sometimes higher depending on demand and resources."* No credit card required; phone verification is required to enable accelerators.
- Accelerator choices (per Thunder Compute's Sept 2026 Colab-alternatives review and the aicreditmart 2026 Kaggle guide): **1× P100 (16 GB) or dual T4 (T4 ×2 = 32 GB combined)**, plus a TPU option — *"TPU v5e-8 that replaced the older v3-8 in 2025."* **GPU sessions cap at 12 hours** (TPU ~9 hours), with **20 GB persistent storage** and background execution via "Save & Run All (Commit)."
- **T4 has no native bfloat16 and no Flash Attention 2** — only float16 tensor cores. Naive float16 mixed precision can push activations/gradients to infinity (→ NaN loss) on some models. Unsloth documents a three-fold fix (keep activations in bf16/float32, do matmuls in float16 with manual up/down-casting, upcast layernorms to float32). This is a strong reason to train via **Unsloth** on T4.
- **P100 has no tensor cores and no bf16**, so it is generally slower than a T4 for mixed-precision LoRA. Prefer the **2× T4** runtime but plan to train on **one T4**.

### Multi-GPU (2× T4): does it help?

For QLoRA at ≤8B the model fits on a single 16 GB T4, so the second T4 offers **data-parallel throughput at best, not the ability to train a larger model**. Unsloth's free notebooks are single-GPU; going multi-GPU means dropping to plain TRL/Accelerate DDP with added complexity.

**Recommendation: train on one T4 and keep it simple.** Use the second GPU only later if you want ~1.5–2× faster epochs via DDP. Tensor/model parallelism is unnecessary here.

---

## Candidate models — current state (2026)

### Qwen family (Apache 2.0 — best licensing + best small-model math)

All Qwen3 dense models (0.6/1.7/4/8/14/32B) are Apache 2.0. The **2507 refresh split the old hybrid model into separate `-Instruct-2507` (non-thinking) and `-Thinking-2507` variants**, eliminating the messy `/think` toggle — a major practical win for fine-tuning.

- **Qwen3-4B-Instruct-2507** (official model card): MMLU-Pro **69.6**, GPQA **62.0** (Qwen's reported figure, per QwenLM GitHub issue #1462), AIME25 **47.4**, HMMT25 31.0, PolyMATH 31.1, IFEval 83.4. Card states: *"Context Length: 262,144 natively. NOTE: This model supports only non-thinking mode and does not generate `<think></think>` blocks."* Astonishing math for 4B (Qwen claims Qwen3-4B rivals Qwen2.5-72B-Instruct on many tasks). Fits QLoRA on one T4 with room for 4k-token outputs. **This is the primary pick.**
- **Qwen3-8B** (base pre-training numbers, technical report): MMLU 76.9, MMLU-Pro 56.7, GSM8K 89.8, MATH 60.8. QLoRA-trainable on one T4 (~8–10 GB in 4-bit) but tighter at long sequence lengths.
- **Qwen3-14B** (base): MMLU 81.1, MMLU-Pro 61.0, GSM8K 92.5, MATH 62.0. Unsloth says the 14B fits QLoRA in a free 16 GB T4, but throughput will be slow and 4k-token outputs pressure VRAM. Reserve as a stretch goal.
- **Qwen3-4B-Thinking-2507** (for contrast): MMLU-Pro 74.0, GPQA 65.8, AIME25 **81.3** — far higher math, but it is a thinking model (see below). Not a good base for deterministic output.
- **Successors**: Unsloth's 2026 docs document a **Qwen3.5 "Small" series (0.8/2/4/9B)** and a Qwen3.8-27B on the new architecture, with Kaggle notebooks advertising *"30 hours of free GPU usage with 2× Tesla T4 GPUs."* Promising future work, but the 3.5 line has documented `enable_thinking`-toggle quirks; keep as optional, not primary.

### Llama family (Llama Community License — restricts commercial use above 700M MAU)

- **Llama-3.1-8B-Instruct**: the field's standard baseline; weaker math (MATH ~47, GSM8K ~76.6), excellent ecosystem. Best used as your **paper baseline**, not the primary — its license is more restrictive than Apache 2.0 and its math trails Qwen3.
- **Llama 3.2** (1B/3B) weaker; **Llama 3.3 70B** far too big; **Llama 4** (Scout 109B / Maverick 400B MoE) is too large and under the Llama 4 Community License. The open Llama line has effectively stagnated.

### Gemma family (Gemma Terms of Use — custom, not OSI open source)

- **Gemma 3** (1/4/12/27B): 27B-IT reaches MATH ~89, but the license is restrictive (Google reserves a remote-restriction right). **Gemma 2/3 have documented T4 float16 overflow** requiring the Unsloth fix. Workable but a headache.
- **Gemma 4** (2026) reportedly moved to **Apache 2.0** with strong scores (secondary sources); if verified, a small Gemma 4 is a legitimate alternative — but Gemma is heavier to fine-tune on T4 than Qwen.

### Mistral family (mostly Apache 2.0)

- **Mistral Small 3.2 24B** and **Magistral Small 24B** are Apache 2.0 but **too large for comfortable T4 QLoRA at 4k output**.
- **Ministral 3 8B** (Dec 2025, Apache 2.0) is a viable 8B alternative. Mistral 7B is dated. Magistral is a reasoning model (avoid as base).

### DeepSeek-R1 distills (MIT)

DeepSeek-R1-Distill-Qwen-7B/14B and -Llama-8B are MIT-licensed and strong at math, but they are **reasoning models built to emit long `<think>` CoT** — conflicts with your deterministic goal (below).

### Phi-4 (MIT — most permissive frontier-grade)

**Phi-4 14B**: MATH 80.4, MMLU-Pro 56.1, runs ~8.5 GB at Q4. Strong STEM per parameter and a clean MIT license, but 14B on T4 QLoRA is slow, and **Phi-4-reasoning / -mini-reasoning are thinking models** ("designed and tested for math reasoning only"). Non-reasoning Phi-4 14B is a legitimate secondary, especially for the license, but heavier than Qwen3-4B/8B.

### Others

OLMo 2, Granite 3, Nemotron, Falcon, Yi, InternLM, SmolLM: all viable, but none clearly beats Qwen3-4B/8B on the math-per-parameter + Apache-license + ecosystem axis for this task.

---

## Reasoning vs non-reasoning base — decisive evidence

- Unsloth's Qwen3 fine-tuning docs: *"Use 75% reasoning and 25% non-reasoning in your dataset to make the model retain its reasoning capabilities."* Conversely, fine-tuning a thinking model on plain non-CoT SFT data **erases its reasoning** — an Unsloth GitHub issue ("Qwen3 reasoning ability disappears") reports exactly this, even with `enable_thinking=True`.
- Research on self-distillation/aggressive SFT shows reasoning models' out-of-distribution performance can **degrade below the base model** (SDPO under-performs on AIME24); RL is gentler than SFT for reasoning models.
- For your task you actually **want** short, deterministic, template-locked worked solutions from a Python simulator — not stochastic long CoT. A reasoning base fights you on format, inflates output length/VRAM, and needs non-greedy sampling (Qwen: *"do NOT use greedy decoding"* for thinking mode) that undermines determinism.

**Conclusion: use a non-thinking instruct model** and put the step-by-step reasoning *in your training targets*, where your simulator guarantees it is correct.

---

## Instruct vs base as the starting point

Evidence converges: for **narrow SFT with a smallish dataset, the instruct model is the better start** — it follows chat templates, needs less data, and for most domains post-training merely "activates" pre-existing capability (base vs instruct converge). Unsloth explicitly recommends instruct for small datasets. At 5–8k examples either works, but instruct is lower-risk.

**Start from Qwen3-4B-Instruct-2507.**

---

## Synthetic data: is 5–8k enough, and shortcut risk?

Multiple studies show **1k examples already give solid gains and 10k continues to help** for multi-step reasoning/tool-use SFT; a compact, well-curated synthetic set can make a 4B model competitive with far larger models. **5–8k is a reasonable, even generous, size** for a narrow procedural domain.

**Shortcut/memorization is the real risk** with programmatically generated instances. Mitigations:

1. **Wide parameter randomization** — process counts, burst/arrival times, quanta, frame counts, reference strings, disk request orders, resource matrices.
2. **Hold-out generalization tests** on unseen parameter ranges and larger instances.
3. **Supervise intermediate steps** — Gantt slices, ready-queue state, need-matrix updates — not just final numbers, so the loss rewards the procedure.
4. **Simulator-verify every training answer** (you already do this).
5. **OOD size tests** — train on ≤6 processes, test on 8–10.

---

## Catastrophic forgetting & replay ratio

LoRA/QLoRA already mitigates forgetting by freezing base weights, though the active adapter can still shift behavior. The **standard, well-supported replay ratio is 5–15% general data** (some domain-shift cases go up to ~35%). Your planned **10–15% general-instruction mix sits right in the recommended band.** Keep it diverse (instruction-following + light math/code) to preserve conceptual-explanation quality.

---

## LoRA hyperparameters for this scale

Converged best practice for 5–8k-row domain SFT:

- **r=16** (default) to **32**, **alpha = 2r** (32–64)
- **Target ALL linear layers** (q/k/v/o + gate/up/down) — attention-only under-performs
- **Dropout 0.05**, **LR 2e-4** cosine with 3–5% warmup, **2–3 epochs**, AdamW 8-bit
- Monitor validation loss; stop when train-token accuracy saturates
- Move to r=32 if you see underfitting (val loss plateaus above train loss)

---

## Comparison table (QLoRA-on-Kaggle lens)

| Model | Params | License | Math signal | T4 QLoRA fit (4k out) | Reasoning base? | Ecosystem | Role |
|---|---|---|---|---|---|---|---|
| **Qwen3-4B-Instruct-2507** | 4B | Apache 2.0 | MMLU-Pro 69.6, GPQA 62.0, AIME25 47.4 | Comfortable | No | Unsloth/GGUF/vLLM/Ollama, first-class | **Primary** |
| Qwen3-8B | 8B | Apache 2.0 | base MMLU 76.9, GSM8K 89.8, MATH 60.8 | Fits, tighter | No (instruct) | Excellent | **Runner-up** |
| Llama-3.1-8B-Instruct | 8B | Llama Community | MATH ~47, GSM8K ~76.6 | Fits | No | Excellent | **Paper baseline** |
| Qwen3-4B (base, no FT) | 4B | Apache 2.0 | GSM8K 80.2, MATH500 57.4 | n/a | No | — | **Ablation baseline** |
| Phi-4 14B | 14B | MIT | MATH 80.4, MMLU-Pro 56.1 | Slow on T4 | No | Good | Secondary (MIT) |
| Gemma 3 12B | 12B | Gemma ToU | strong | T4 float16 issues | No | Good (needs Unsloth fix) | Alt |
| Ministral 3 8B | 8B | Apache 2.0 | good | Fits | No | Growing | Alt |
| DeepSeek-R1-Distill-Qwen-7B | 7B | MIT | AIME strong | Fits | **Yes** | Good | Avoid as base |
| Qwen3-4B-Thinking-2507 | 4B | Apache 2.0 | AIME25 81.3, MMLU-Pro 74.0 | Fits (long outputs) | **Yes** | Good | Avoid as base |
| Magistral Small / Phi-4-reasoning | 24B/14B | Apache/MIT | very strong | Too big / thinking | **Yes** | Good | Avoid |

---

## Prior art (to position your contribution)

**Most directly relevant:** *"Narrowing the Gap: Supervised Fine-Tuning of Open-Source LLMs as a Viable Alternative to Proprietary Models for Pedagogical Tools"* (arXiv 2507.05305, UNSW Sydney / Aalto, 2025).

Per the abstract, the authors built *"a new dataset of 40,000 C compiler error explanations, derived from real introductory programming (CS1/2) student-generated programming errors, which we used to fine-tune three open-source models: Qwen3-4B, Llama-3.1-8B, and Qwen3-32B,"* evaluated via *"a large-scale automated analysis of 8,000 responses using a validated LLM-as-judge ensemble."* Headline: SFT makes small models nearly match GPT-4.1 (SFT-Qwen-4B within 0.10 of GPT-4.1 on all expert metrics; expert mean-rank 4.12 vs GPT-4.1's 3.09).

This directly validates your recipe (**Qwen3-4B + QLoRA + CS education**) and is your closest related-work/baseline — but it targets *programming-error explanations*, not *simulator-verified OS numericals*.

**Broader CS-education LLM work to cite:**

- Automatic MCQ/exercise generation — Sarsa et al., ICER 2022; Tran et al., FIE 2023
- Programming-exercise instruction tuning — Zeng et al., WISA 2024
- AutoTutor authoring — Pal Chowdhury et al., 2024
- Pedagogical SFT "GuideLM" — arXiv 2502.20527
- Surveys — Maity & Deroy 2024

**No published work targets fine-tuning a small model specifically for step-verified OS numerical solving + generation** — a genuine, defensible gap.

Distinguish from "LLMs *as* schedulers" work (e.g. DynaSchedBench) — a different topic worth a one-line citation to pre-empt confusion.

**Your novelty (state it explicitly):**

1. Step-verified numerical/algorithmic OS problems across scheduling, paging, disk, deadlock, address translation
2. Synthetic, simulator-generated data with guaranteed-correct step traces and answer keys
3. A single model that both **solves** with auditable steps and **generates** new problems with correct keys
4. An automatic, simulator-based step-verified evaluation harness

---

## Kaggle-feasible training configuration (concrete)

| Setting | Value |
|---|---|
| Base model | `unsloth/Qwen3-4B-Instruct-2507` (dynamic 4-bit BnB) |
| Loader | Unsloth `FastLanguageModel`, `load_in_4bit=True`, `dtype=None` (auto → float16 on T4) |
| Hardware | Single T4 (select the 2× T4 accelerator, use device 0) |
| Sequence length | 4096 (drop to 2048 if VRAM-tight) |
| Per-device batch | 2 |
| Gradient accumulation | 8 → effective batch 16 (use 1/16 if OOM at 4k) |
| LoRA rank / alpha | r=16, alpha=32 |
| LoRA dropout | 0.05 |
| Target modules | All linear layers (q, k, v, o, gate, up, down) |
| Gradient checkpointing | `use_gradient_checkpointing="unsloth"` |
| Optimizer | `adamw_8bit` |
| Learning rate | 2e-4, cosine schedule |
| Warmup ratio | 0.03 |
| Weight decay | 0.01 |
| Epochs | 2–3 over ~6–7k examples (5–8k domain + 10–15% general replay) |

**Estimated throughput:** on a single T4 with Unsloth, a 4B QLoRA at 4k seq length runs on the order of hundreds-to-~1k tokens/s; a ~7k-example, ~2.5k-avg-token, 3-epoch run is realistically a **single-digit-hours-per-epoch** job — comfortably inside one 12-hour session and the 30-hour weekly quota. Checkpoint to the 20 GB persistent disk so you can resume across sessions. **Confirm the true step time in the first ~50 steps and extrapolate before committing.**

**Export:** merge to 16-bit, then export **GGUF (Q4_K_M / Q5_K_M)** for Ollama/llama.cpp on modest institution hardware, and/or serve merged weights via vLLM. Q4_K_M of a 4B model runs in ~4 GB VRAM and even on CPU.

---

## Recommendations

1. **Build and train on Qwen3-4B-Instruct-2507 first** with the config above — fastest path to a working, publishable result and the closest match to validated prior art (Narrowing the Gap used exactly this model). Change-trigger: if after 3 epochs your held-out *procedure-generalization* accuracy on the easier algorithms (FCFS / FIFO / FCFS-disk) is below ~85%, escalate.
2. **Escalate to Qwen3-8B** only if 4B plateaus on the hardest procedures (SRTF tie-breaking, Banker's safety sequence, C-SCAN/LOOK). It still fits one T4 in QLoRA; expect slower epochs. Trigger: 4B validation accuracy on Banker's/SRTF stuck below target after tuning (r=32, more epochs).
3. **Baselines for the paper:** report (a) **base Qwen3-4B-Instruct-2507, no fine-tuning** (isolates your contribution), (b) **Llama-3.1-8B-Instruct fine-tuned identically** (model-choice effect + a bigger-but-weaker-math comparator), and optionally (c) a frontier API model zero-shot as an upper reference — the exact structure Narrowing the Gap used.
4. **Data discipline (most important for validity):** randomize instance parameters widely, simulator-verify every answer, supervise intermediate steps, and hold out OOD sizes to prove the model learned the *procedure*, not a shortcut. Mix 10–15% general instruction data against forgetting.
5. **Do NOT start from a thinking/reasoning model.** If you want visible steps, put them in the targets; keep the base non-thinking for deterministic, greedy-decodable, fixed-format output.
6. **Evaluation:** build an automatic checker (your simulator) that parses both final answers AND intermediate steps — exact-match on waiting/turnaround times, Gantt ordering, safety sequences, victim frames, translated addresses. This step-verified auto-eval is itself a paper contribution.

---

## Caveats

- **Throughput estimates are approximate.** No live T4 benchmark was possible; tokens/s and hours/epoch depend on your sequence-length distribution and Unsloth version. Measure the first ~50 steps before a full run.
- **Kaggle specs can change.** The ~30 GPU-hr/week, 12-hr session, 2× T4 / P100 configuration is current per 2026 sources, but verify in-notebook (`nvidia-smi`, quota widget) before planning — Kaggle adjusts quotas with demand.
- **Benchmark apples-to-oranges risk.** The Qwen3-4B-2507 cards report AIME25/MMLU-Pro/GPQA but **not** GSM8K/MATH; the GSM8K/MATH figures cited for Qwen3-8B/14B are *base-model pre-training* numbers from the technical report, not instruct-tuned. Compare across benchmarks cautiously.
- **License nuance for weight release.** Apache 2.0 (Qwen, Mistral, Gemma 4, OLMo) and MIT (Phi-4, DeepSeek) are safe for releasing fine-tuned weights and institutional deployment. Llama and Gemma 2/3 carry custom terms — fine for a university tool but flag them if you publicly release weights.
- **Gemma 4 Apache 2.0 and the Qwen3.5 series** come from 2026 secondary sources not fully cross-verified against primary model cards within budget; treat as promising-but-unconfirmed and verify before relying on them.
- **The "instruct vs base" and "reasoning-model SFT" literature is nuanced** — a few papers find reasoning models a *better* SFT start for code tasks. For your deterministic-numerical task the balance still favors non-thinking instruct, but present it as a justified design choice, not an absolute law.
