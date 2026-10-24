# OSTutorLLM: Dataset Strategy & Data Pipeline Plan

**QLoRA Fine-Tuning of Qwen3-4B-Instruct-2507 into an Operating Systems Tutoring Model**

*Prepared for: DKP — OS education LLM research project*
*Date: September 2026*

---

## TL;DR

- **No English OS instruction dataset or OS benchmark exists** — your assumption is correct and now rigorously confirmed. The entire training and evaluation corpus must be built from scratch, primarily via programmatically step-verified synthetic generation (for numeric/algorithmic OS problems), plus a permissively-licensed pedagogical-behavior transfer layer (MathDial-style teacher moves adapted to OS) and a general-skill replay mix (SmolTalk2 / permissive Tulu-3 subsets).
- **Genuine tutoring behavior is only partially teachable by SFT alone.** SFT reliably instills format, hint-before-answer scaffolding and misconception-diagnosis structure, but the one report that directly A/B-tests it (Google LearnLM) states verbatim: *"While SFT seems to improve pedagogical instruction following somewhat, RL is significantly more effective, as preference judgements often contain subtle distinctions in how instructions are interpreted and followed in the context of long conversations."* Plan SFT as the core deliverable and a lightweight DPO pass as a documented Phase 2.
- **Legal posture is favorable if you are disciplined.** Teacher models DeepSeek-R1 / V3.1 / V3.1-Terminus / V3.2 (MIT) and Qwen3 / QwQ (Apache-2.0) are safe for synthetic generation; the original DeepSeek-V3 (Dec-2024 model license) and Claude are prohibited for training-data generation; OSTEP / Silberschatz / Tanenbaum are do-not-touch; xv6, Linux man-pages, tldr and the NL2Bash `data/bash` set are usable with attribution.

---

## 1. The "no OS dataset" claim is TRUE — with important nuances

- **MMLU**: Confirmed — no "operating systems" subject among the 57; only `college_computer_science`, `high_school_computer_science`, `computer_security`, `machine_learning`.
- **C-Eval**: Confirmed the `operating_system` subset exists but is tiny and Chinese. C-Eval has three splits per subject (dev = 5 exemplars, val, test with hidden labels); the entire validation split across all subjects is only 1,346 questions, so the OS val subset is a few dozen items at most. **License: the C-Eval dataset is CC BY-NC-SA 4.0** (code MIT) — non-commercial, so usable for a research eval but not for a commercially-licensed release.
- **CMMLU** (67 topics, Chinese) and **AGIEval** (MIT license; derived from Chinese Gaokao/SAT/LSAT/GRE/GMAT — no OS subject) similarly contain no usable English OS QA. **MMLU-Pro** has a `computer science` bucket (410 samples, Apache-2.0) but it is not OS-specific.
- **The Pedagogy Benchmark / CDPK** (arXiv 2506.18710, Jun 2025) is the closest pedagogy-knowledge eval: 1,143 teacher-exam MCQs (920 CDPK + 223 SEND) sourced from the Chilean Ministry of Education teacher exams; 97 models scored 28%–89%; estimated human accuracy ~50%. It tests pedagogical *knowledge*, not OS content — a model to imitate for eval construction, not a source of OS items.
- **GATE CSE**: Past papers are published by the organizing IITs and each carries an explicit copyright notice (e.g., "Copyright : GATE 2020, IIT Delhi"). They are freely downloadable for practice but are **not released under any open license** — training on them and redistributing derived items is legally risky. At most use privately for internal eval, and even that is contestable; do not redistribute derived items.

---

## 2. Closest prior art — VERIFIED

**arXiv 2507.05305, "Narrowing the Gap: Supervised Fine-Tuning of Open-Source LLMs as a Viable Alternative to Proprietary Models for Pedagogical Tools"** (Lee Solano, Koutcheme, Leinonen, Vassar, Renzella; UNSW + Aalto; submitted 7 Jul 2025).

Confirmed details:
- A **new dataset of 40,000 C compiler-error explanations** derived from real CS1/CS2 student errors
- Teacher responses generated with **gpt-4.1-2025-04-14** via OpenAI's batch API at temperature 0, using a three-step prompt (explain causes → actionable hints → guidance) as a CoT scaffold
- Fine-tuned **Qwen3-4B, Llama-3.1-8B, Qwen3-32B**
- Dual evaluation of 8,000 responses with an expert-human + validated LLM-as-judge ensemble
- Result: SFT makes small models pedagogically competitive with much larger ones

**This is your single most important positioning anchor.**

### The precise, defensible gap

2507.05305 covers *C compiler-error explanation* for CS1/2 novices. There is no equivalent for **Operating Systems** — a domain uniquely characterized by *multi-step deterministic numeric procedures* (scheduling, page replacement, address translation, Banker's algorithm) that are machine-verifiable, layered with deep conceptual misconceptions. That combination — programmatically step-verified procedural ground truth + misconception-grounded tutoring, in OS — is an unoccupied niche.

### Other CS-education SFT work

- arXiv 2502.20527 — "Supervised Fine-Tuning LLMs to Behave as Pedagogical Agents in Programming Education"
- Frontiers/PubMed 2026 — "Application-Driven Pedagogical Knowledge Optimization … via RL and SFT" (EduQwen-32B), combines RL then SFT, reports SOTA on the CDPK benchmark

---

## 3. Tutoring behavior — SFT vs RL/DPO evidence

**LearnLM technical report (arXiv 2412.16429, Google, Dec 2024)** is the decisive A/B source.

Verbatim: *"While SFT seems to improve pedagogical instruction following somewhat, RL is significantly more effective, as preference judgements often contain subtle distinctions in how instructions are interpreted and followed in the context of long conversations."*

Expert pedagogical raters (7-point −3 to +3 Likert) preferred LearnLM *"with an average preference strength of 31% over GPT-4o, 11% over Claude 3.5 Sonnet, and 13% over the original Gemini 1.5 Pro."*

Critically, the report documents that pedagogical instruction-following **decays over a long conversation**: its Pedagogical Instruction Following (PIF) metric *"aligns with human instruction following ratings, showing 60 percent correlation,"* and for Gemini 1.5 Pro, GPT-4o and Claude 3.5 Sonnet it *"drops from 0.81 on average at turn 1 … to 0.64 at turn 20"* — a direct warning that multi-turn tutoring is where models leak solutions and lose the plot.

**Supporting evidence:**

| Work | Finding |
|---|---|
| **MathDial** (Macina et al., Findings of EMNLP 2023) | 2,861 semi-synthetic tutoring dialogues; fine-tuning improves tutoring (more hints, fewer premature reveals) — evidence SFT *does* move tutoring behavior. **License: CC BY-SA 4.0** |
| **SocraticLM** (NeurIPS 2024 Spotlight) | SFT of ChatGLM3-6B on 35K "SocraTeach" dialogues improves teaching quality |
| **EULER** (AIxEDU 2024) | DPO on 500–650 Socratic examples brought a small base model near GPT-4o |
| **TeachLM** (2025) | PEFT on ~100,000 hours of tutoring data → ~50% more dialogue turns, more student talk time |
| **Stanford Tutor CoPilot** (arXiv 2410.03017) | RCT, 782 tutors / 1,787 students: students *"are 4 percentage points (p.p.) more likely to master topics (p<0.01)"*, students of lower-rated tutors *"improving mastery by 9 p.p."*, at *"only $20 per-tutor annually"* over 350,000+ messages. Note: inference-time prompting, not a fine-tune |

**Verdict:** SFT alone is sufficient for a strong first result (format, scaffolding, misconception diagnosis, hint-before-answer). Reserve DPO/RL as an explicit, well-motivated Phase 2 for the "withholding solutions" and Socratic-tone dimensions, where preference signal matters most and where LearnLM's turn-20 decay shows SFT is weakest.

---

## 4. Process supervision & procedural generalization

- **Lightman et al., "Let's Verify Step by Step" (arXiv 2305.20050, OpenAI)**: the best process-supervised reward model *"achieved 78.2% accuracy on the MATH test set"* via best-of-N search *"compared to 72.4% for the best ORM"*, and generalized OOD to STEM tests; the authors released PRM800K, *"the complete dataset of 800,000 step-level human feedback labels."* Implication: **step-level, auditable solution targets are strongly preferred over answer-only targets**, especially for multi-step OS procedures.
- **FOVER (arXiv 2505.15960)**: formally-verified tools (Z3, Isabelle) can auto-generate accurate step-level labels — the conceptual blueprint for using an OS simulator as the "formal verifier" of each solution step.
- **Model collapse / synthetic ratio**: pure recursive synthetic training collapses (Shumailov et al.), but *accumulating* real+synthetic avoids it (arXiv 2404.01413); empirical work (arXiv 2510.05133) shows mixed training with modest synthetic proportions (10–20%) over 1–3 iterations maintains performance, degrading at 50%→100%. "Golden Ratio Weighting" (arXiv 2502.18049) formalizes an optimal real-data weight. Your synthetic content is *step-verified against ground truth*, which sharply mitigates collapse risk — but still cap purely-synthetic procedural data and interleave human-authored/real items.

---

## 5. Dataset size & mixture (small-model, narrow-domain SFT)

- **LIMA (arXiv 2305.11206)**: 1,000 curated examples produced strong alignment on a 65B model — but the Databricks LIMIT study showed the "less is more" effect is *evaluation-paradigm-dependent*: small high-quality sets win on LLM-judge-style evals but underperform on knowledge benchmarks (MMLU/BIG-bench) unless the finetuning data matches the eval paradigm. For a 4B model targeting *both* solving accuracy and tutoring style, you need more than 1K and a deliberate multi-bucket mix.
- **Catastrophic forgetting under LoRA**: LoRA reduces but does not eliminate forgetting; replay is the single most effective mitigation (a representative domain study used 50% replay from a pretraining-proxy corpus). A multi-seed study (Capacity-Gated Forgetting in LoRA) warns forgetting measurements are highly seed-sensitive — so measure forgetting explicitly on held-out general benchmarks rather than assuming a fixed replay ratio works.
- **IFD / Cherry LLM (Li et al., arXiv 2308.12032, NAACL 2024)**: the Instruction-Following Difficulty metric selects "cherry" samples; with only ~10% of data, cherry-selected models beat full-data models, and beat random selection consistently from 5%→15% data fractions. Use IFD to prune your synthetic pile to the most instructive examples.

---

## 6. Licensing resolution (primary sources)

- **neulab/tldr**: HF card says MIT (applies to the loader/harvest code). Underlying **tldr-pages content is CC BY 4.0** (scripts MIT) — confirmed from `tldr-pages/tldr` LICENSE.md. NL→bash pairs derived from tldr pages are **CC BY 4.0 (attribution required)**; safe to train and release with attribution.
- **NL2Bash / TellinaTool**: repo **code is GPL-3.0**, but the **dataset `data/bash` is separately MIT-licensed** (README changelog, 24 Apr 2020). The trainable NL–bash pairs are MIT → safe to train and release. This resolves the empty `_LICENSE` field on the `jiacheng-ye/nl2bash` HF loader (→ MIT for the data content).
- **MathDial**: **CC BY-SA 4.0** — usable and redistributable; derived datasets must be ShareAlike.
- **xv6**: source MIT (© 2006–2022 Kaashoek, Morris, Cox); the xv6 book and MIT OCW 6.1810/6.S081 are CC BY-NC-SA — **you can train on them, but a *commercial* release of derived data is blocked; a *non-commercial research* dataset release is acceptable under ShareAlike + attribution**.
- **Linux man-pages**: mixed (Linux-man-pages-copyleft "verbatim," GPL-2.0+, BSD, MIT) — all permit redistribution/modification; retain per-page license metadata.
- **Stack Exchange**: the April-2024 Internet Archive dump was CC BY-SA 4.0 and largely unrestricted; use that snapshot, not post-July-2024 logged-in dumps whose terms purport to bar LLM training.
- **SmolTalk2** (`HuggingFaceTB/smoltalk2`): modern replay set (SFT/Mid/Preference subsets built from OpenHermes-2.5, Tulu-3 Personas IF, Mixture-of-Thoughts, OpenThoughts3, etc.), decontaminated against common benchmarks — good replay source (verify per-subset licenses).
- **Tulu-3 SFT mixture** (`allenai/tulu-3-sft-mixture`): 939,344 samples, **ODC-BY-1.0 overall, but subsets carry different licenses and some are non-commercial** (e.g., No Robots CC BY-NC-4.0) — filter to permissive subsets if you need commercial release.
- **Teacher models for synthetic generation**: **DeepSeek-R1 (MIT), DeepSeek-V3.1 & V3.1-Terminus & V3.2 (MIT, all model-weights included), QwQ-32B (Apache-2.0), Qwen3 family incl. Qwen3-235B thinking (Apache-2.0)** = PERMITTED. **The original DeepSeek-V3 (Dec-2024 model license)** defines "Derivatives of the Model" to explicitly include *"methods based on the generation of synthetic data by the Model for training the other model"* = PROHIBITED for training-data generation. **Claude (Anthropic ToS)** = PROHIBITED.

> **Key nuance:** the original V3 used the restrictive DeepSeek model license, but **V3.1 / V3.1-Terminus / V3.2 moved to MIT** — so use a V3.1+ checkpoint, never the original V3, for a DeepSeek-V3-lineage teacher.

---

## 7. Recommended dataset mixture

**Target: ~25,000–35,000 SFT examples**

| # | Bucket | Rows (target) | Concrete source / how built | HF ID (if exists) | License | Release status |
|---|--------|--------------|------------------------------|-------------------|---------|----------------|
| 1 | **Procedural OS problems, step-verified** (CPU scheduling, page replacement, disk scheduling, Banker's, address translation, page-table math, disk/RAID sizing) | 9,000–12,000 | **Build from scratch**: write your own deterministic Python simulators; randomize parameters; emit auditable step-by-step solution templates; teacher model (DeepSeek-R1 / Qwen3) writes prose *constrained by* verified steps | none | your own (MIT/CC-BY) | Safe to release |
| 2 | **Conceptual OS Q&A + explanations** (processes, threads, scheduling theory, virtual memory, file systems, synchronization, deadlock, I/O) | 6,000–8,000 | Teacher-generated (Qwen3-235B / DeepSeek-R1) grounded in OpenStax / xv6 book / Linux man-pages / OS Wikipedia; human spot-check | none | CC-BY / mixed | Safe (non-commercial if xv6-book-grounded) |
| 3 | **Tutoring/Socratic dialogues** (hint-before-answer, misconception diagnosis, scaffolding) | 3,000–4,000 | Adapt **MathDial** teacher-move taxonomy (Focus/Probing/Telling/Generic) to OS; semi-synthetic teacher-student dialogues | `eth-nlped/mathdial` (seed) | CC BY-SA 4.0 | Safe, ShareAlike |
| 4 | **Shell/bash NL→command** | 2,000–3,000 | **neulab/tldr** (6,414 train) + **NL2Bash `data/bash`** (~8k pairs) reformatted to instruction style | `neulab/tldr`; `jiacheng-ye/nl2bash` | CC BY 4.0 / MIT | Safe w/ attribution |
| 5 | **Assessment generation** (MCQ w/ misconception distractors, viva/short-answer, lab tasks) | 2,000–3,000 | Teacher-generated, misconception-grounded distractors; auto-validated (single-correct, solvability) | none | your own | Safe |
| 6 | **General-skill replay (anti-forgetting)** | ~15–25% of total (≈5,000–8,000) | **SmolTalk2** SFT subset + permissive Tulu-3 subsets, sampled | `HuggingFaceTB/smoltalk2`; `allenai/tulu-3-sft-mixture` | mixed / ODC-BY | Safe (filter subsets) |

**Rationale for ratios:** procedural + conceptual OS content is the differentiator and should dominate (~60%); tutoring dialogues teach *behavior* and need only be a strong minority (MathDial itself is ~2.9K and moved behavior); replay at 15–25% follows the LoRA-forgetting evidence (measure and adjust). Do not let any single bucket exceed ~40% or behavior will skew.

---

## 8. Common OS misconceptions to design training around

The computing-education literature (Koli Calling, SIGCSE, ITiCSE) documents persistent OS misconceptions to explicitly diagnose and correct in bucket 3:

- Six alternative conceptions around **interrupts, I/O operations, context switches/system calls, concurrent computing, deadlock and semaphores** (Koli Calling 2013 online-course study; ACM DL 10.1145/2526968.2526977)
- Student misunderstandings of **concurrency and synchronization** (Koli Calling 2019, 10.1145/3364510.3366166)
- **Virtual-memory** misconceptions (four-year online case study)

There is **no established "OS Concept Inventory"** analogous to the Force Concept Inventory — building one is itself a publishable contribution. Ground each tutoring example in a named misconception → diagnostic question → targeted correction.

---

## 9. Pipeline architecture (raw → split)

1. **Source ingestion** — pull OpenStax / xv6-book / man-pages / tldr / NL2Bash; store per-item license metadata.
2. **Procedural generation** — parameterized simulators (FCFS/SJF/SRTF/RR/Priority; FIFO/LRU/Optimal/Clock; SCAN/C-SCAN/LOOK; Banker's safety; multi-level page tables/TLB) emit `(problem, ground-truth trace, final answer)`.
3. **Solution templating** — convert each verified trace into a structured, auditable step target (numbered steps, intermediate state tables, then final answer) — process-supervision style.
4. **Teacher narration** — MIT/Apache teacher model (DeepSeek-R1 / Qwen3-235B) writes the pedagogical prose *conditioned on and constrained by* the verified steps; reject any narration whose final answer ≠ ground truth.
5. **Verification gate** — re-parse the model's stated final answer and key intermediate values; discard mismatches. This is your anti-hallucination and anti-collapse safeguard.
6. **Cleaning** — strip teacher-model self-references, fix formatting, normalize LaTeX/tables.
7. **Deduplication** — exact (hash) → MinHash/LSH fuzzy (128 permutations, Jaccard threshold ~0.7–0.9) via `datasketch` / `text-dedup` / distilabel `MinHashDedup`, optionally semantic dedup via NVIDIA NeMo Curator.
8. **Quality filtering** — IFD/Cherry-LLM scoring to keep the most instructive examples; optional LLM-as-judge pass to drop low-quality tutoring turns.
9. **Decontamination** — n-gram overlap against your held-out eval set (report the exact n; 8-gram and 13-gram are both standard — pick one and state it); drop any train item overlapping an eval item.
10. **Formatting** — Qwen3 ChatML (`<|im_start|>role … <|im_end|>`), system prompt per mode, EOS = `<|im_end|>` (id 151645), pad = 151654; **no `<think>` blocks** (2507 is non-thinking).
11. **Splitting** — standard random split **plus** OOD/generalization splits: (a) larger problem sizes than seen in train (length generalization), (b) entire parameter regimes held out, (c) for bash, hold out commands by name (as `neulab/tldr` does).

---

## 10. Assessment-generation evidence (bucket 5)

- **Sarsa et al., ICER 2022** (Codex): of 120 generated exercises, 75% were sensible, 81.8% novel, 76.7% had a matching sample solution; code-explanation accuracy ~67%; a weakness is that fewer than a third of exercises with tests pass.
- **Tran et al., FIE 2023**: GPT-4 substantially outperforms GPT-3 at generating distractors and correct answers for a given stem.
- **Doughty et al., ACE 2024**: GPT-4 MCQs are comparable in quality to human-crafted ones.
- **Misconception-grounded distractors**: Bitew et al. 2023 (~53% of generated distractors rated high-quality, immediately usable); DiVERT (arXiv 2406.19356) represents the underlying error as text; 2025 work predicts which distractor students actually pick.

Build distractors from your named OS misconceptions and auto-validate solvability + single-correct-answer.

---

## 11. Engineering specifics

**Chat template / Unsloth.** Use `get_chat_template` for Qwen3 and `train_on_responses_only` with instruction part `<|im_start|>user\n` and response part `<|im_start|>assistant\n`.

> **Known pitfall:** mis-specifying these parts masks *all* labels → the `"All labels in your dataset are -100 … are you sure you used train_on_responses_only correctly?"` ZeroDivisionError seen in Unsloth issues #2734 / #2771.

On T4 you must disable bf16/FA2 (use fp16); Unsloth handles this.

**Completion-only loss masking.** Evidence leans toward masking prompt tokens for instruction SFT (train on responses only) — it concentrates gradient on the behavior you want. For procedural targets the model must *generate* the derivation, so masking the prompt is correct.

**System-prompt / mode design.** Use a small number (3–4) of fixed natural-language system prompts for `solve` / `tutor` / `explain` / `generate` modes rather than special mode tokens — natural-language modes generalize better and survive GGUF/Ollama export. Keep the strings identical between training and inference.

**Sequence budget.** 4,096 tokens is tight for long worked solutions with state tables; truncate/paginate the longest scheduling traces, or raise to 6,144 if T4 memory allows with batch 1 + grad-accum 16.

---

## 12. Evaluation harness (build from scratch)

| Eval | Items | Method |
|---|---|---|
| **OS-Solve** (numeric/algorithmic) | 400–600 | Programmatic step + final-answer checking across algorithm families; report exact-match on final answer AND step accuracy; include OOD-size items |
| **OS-Concept** (explanation quality) | 200–300 | LLM-as-judge with a strong MIT/Apache model; randomize answer order to mitigate position bias; report agreement with a small human-rated subset |
| **OS-Tutor** (tutoring quality) | 150–200 dialogues | BEA-2025 dimensions (mistake identification, mistake location, guidance, actionability) + a solution-leakage / "telling@k" metric |
| **Bash-exec** (execution-based) | — | Reuse **InterCode / IC-Bash** (MIT license, NeurIPS 2023; IC-Bash is built on NL2Bash data) in Docker for execution-based success rate |

**Statistical rigor:** report bootstrap 95% CIs (as the Pedagogy Benchmark does); ~300+ items per sub-benchmark gives usable CIs. Fix decoding (temp 0) for the solve eval.

---

## 13. Recommendations

1. **Phase 0 — build the eval FIRST.** Construct OS-Solve / Concept / Tutor / Bash-exec before generating any training data, so decontamination and honest measurement are possible. Benchmark base Qwen3-4B-Instruct-2507 to establish the baseline.
2. **Phase 1 — procedural core.** Write and unit-test the simulators; generate bucket 1 (9–12K step-verified items). Highest-value, lowest-legal-risk, most novel component — ship it first.
3. **Phase 2 — conceptual + bash + assessment.** Buckets 2/4/5 with permissive teachers (DeepSeek-R1 / V3.1+, Qwen3).
4. **Phase 3 — tutoring behavior.** Adapt the MathDial taxonomy to OS (bucket 3), SFT, then measure OS-Tutor. If solution-leakage and Socratic dimensions lag (they will, per LearnLM's turn-20 decay), run a **small DPO pass** as a documented extension.
5. **Replay & forgetting.** Start at 20% replay; if general-benchmark drop >5%, raise replay; if OS metrics stall, lower it. Report the seed-sensitivity caveat.
6. **Data selection.** Over-generate, then IFD-prune to the most instructive ~50–70%.
7. **Positioning.** Frame the paper as "the OS analogue of *Narrowing the Gap* (2507.05305), extended with programmatically step-verified procedural ground truth and misconception-grounded tutoring" — cite it as the anchor and claim the OS + verified-procedure niche.

**Thresholds that change the plan:**
- If base Qwen3-4B already scores >85% on OS-Solve → shift effort to tutoring/DPO
- If forgetting >10% on MMLU-CS after SFT → increase replay to 30–40% or freeze lower LoRA layers
- If synthetic-only procedural data shows shortcut-learning on OOD-size items → inject counterfactual/real items and expand size randomization

---

## 14. LoRA/training implications of this composition

- The mix is heterogeneous (numeric procedures + prose + dialogue + bash), which argues for **keeping r=16 / alpha=32 on all linear layers** (your existing plan) — do not drop rank; heterogeneous multi-capability SFT benefits from more adapter capacity.
- With long procedural targets, **per-device batch 2 × grad-accum 8 (eff. 16)** at seq-len 4096 is reasonable on T4; if you extend to 6,144, drop to batch 1 × accum 16.
- **2–3 epochs** is right for ~30K examples. Watch for overfitting on the templated procedural set — its low surface diversity can memorize. Use the OOD-size split as your early-stopping signal, not train loss.
- Because 2507 is non-thinking, **do not** train `<think>` traces; put the step-by-step derivation directly in the answer body.

---

## 15. Legal / licensing risk summary

| Source | Train? | Release derived data? | Bucket |
|--------|--------|-----------------------|--------|
| **SAFE — train & release** | | | |
| Your own simulator output | ✅ | ✅ (choose MIT/CC-BY) | 1, 5 |
| neulab/tldr (CC BY 4.0) | ✅ | ✅ with attribution | 4 |
| NL2Bash `data/bash` (MIT) | ✅ | ✅ with attribution | 4 |
| MathDial (CC BY-SA 4.0) | ✅ | ✅ ShareAlike + attribution | 3 |
| Linux man-pages (permissive/copyleft mix) | ✅ | ✅ retain per-page license | 2 |
| Stack Exchange **April-2024 dump** (CC BY-SA 4.0) | ✅ | ✅ ShareAlike | 2 |
| SmolTalk2 / permissive Tulu-3 subsets | ✅ | ✅ (filter subsets) | 6 |
| DeepSeek-R1 / V3.1+ / QwQ / Qwen3 as *teachers* | ✅ | ✅ | all synthetic |
| **SAFE to train, RISKY/NC to release** | | | |
| xv6 book, MIT OCW 6.1810 (CC BY-NC-SA) | ✅ | ⚠️ non-commercial research release only | 2 |
| C-Eval `operating_system` (CC BY-NC-SA) | ✅ (eval) | ⚠️ non-commercial only | eval |
| Tulu-3 NC subsets (e.g., No Robots CC BY-NC) | ✅ | ⚠️ non-commercial only | 6 |
| **DO NOT TOUCH** | | | |
| OSTEP, Silberschatz, Tanenbaum, Stallings | ❌ | ❌ proprietary "all rights reserved" | — |
| GATE/UGC-NET past papers (IIT copyright) | ❌ redistribute | ❌ | — |
| Original DeepSeek-V3 (Dec-2024 license) as teacher | ❌ | ❌ synthetic-data clause | — |
| Claude models as teacher | ❌ | ❌ Anthropic ToS | — |
| Stack Exchange post-July-2024 dumps | ❌ | ❌ terms bar LLM training | — |

---

## 16. Caveats

**Thin or contested evidence:**
- The SFT-vs-RL question for tutoring rests heavily on one report (LearnLM); treat the DPO recommendation as evidence-informed, not settled.
- Optimal replay ratio for QLoRA specifically is not pinned to a single number — the 50% figure is from a full-FT domain study; the multi-seed forgetting study warns measurements are seed-sensitive.
- IFD's "pre-experienced phase" is awkward to deploy at scale.
- Some sub-questions were not fully resolved: Tran et al.'s exact percentages are paywalled, and a named "TerminalBench" successor to InterCode is unconfirmed. Verify before citing precise numbers.

**Legal gray zones:**
- Stack Exchange post-July-2024 terms vs CC BY-SA is genuinely unresolved — use the April-2024 dump only.
- GATE papers are copyrighted; do not redistribute derived items.
- The xv6-book/OCW NC clause blocks commercial release of derived data.

**Simulator licensing:** most GitHub OS-simulator repos have no explicit license (default "all rights reserved"); `pyscheduling` (PyPI, MIT) exists but is optimization-oriented, not classic OS-course simulation. **Write your own deterministic simulators** — the algorithms are simple, and this removes all licensing doubt while giving you exact ground truth.

**Where NO dataset exists at all (must build from scratch):** procedural OS problems (bucket 1), conceptual OS Q&A (2), OS tutoring dialogues (3), OS assessment items (5), and the entire OS evaluation suite. Only bash (4) and general replay (6) have off-the-shelf sources. There is also no OS Concept Inventory — building one is a bonus contribution.

**Model-collapse risk** is real but well-mitigated here because every procedural item is verified against deterministic ground truth. Still: cap purely-synthetic content, interleave human-authored items, and monitor OOD-size generalization as the collapse/shortcut early-warning signal.
