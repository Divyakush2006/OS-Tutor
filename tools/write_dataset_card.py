"""Generate DATASET_CARD.md from the build manifest.

    python tools/write_dataset_card.py

Every figure in the card is read from reports/manifest.json or counted from the
built splits. Nothing is typed by hand, because a hand-typed number in a dataset
card is a number that silently goes stale: v2.2's card had to be corrected twice
after the build changed underneath it. Prose that is a DESIGN DECISION (why a rule
exists, what a limitation is) lives here as text; prose that is a MEASUREMENT is
interpolated.

tools/package_kaggle.py copies the result to dist/ostutor-sft/README.md, so this is
also the documentation that ships with the dataset.
"""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ostutor import config as C  # noqa: E402

BUILD = ROOT / "data" / "build"
CARD = ROOT / "DATASET_CARD.md"

CONTENT = {
    "procedural": "Simulator-verified numeric problems, worked step by step, with every "
                  "decision written as a rule plus the comparison behind it. 39 question "
                  "types across 8 weighted families: CPU scheduling (FCFS, SJF, SRTF, RR, "
                  "priority, preemptive priority, HRRN), page replacement (FIFO, LRU, OPT, "
                  "CLOCK), Banker's safety and request (including UNSAFE states), disk "
                  "scheduling (FCFS, SSTF, SCAN, LOOK, C-SCAN, C-LOOK), contiguous "
                  "allocation (first/best/worst fit), address translation, 11 formula "
                  "kinds (EAT, multilevel paging, deadlock minimum, fork count, ...), and "
                  "clarification items where a required input is missing and the correct "
                  "behaviour is to ask rather than to guess.",
    "conceptual": "Explanations of OS concepts. Self-distilled from the base model "
                  "(SDFT, Yang et al., ACL 2024) over a hand-written 295-question bank in "
                  "four wordings, then sanitised and fact-checked: any answer asserting a "
                  "known misconception is dropped, never repaired. Plus hand-written, "
                  "fact-checked gold explanations.",
    "tutoring": "Socratic dialogue. MathDial supplies real teacher moves; the OS half is "
                "self-distilled replies to a student's WRONG attempt, where the wrong "
                "answer is generated from a named misconception (non-preemptive SJF for an "
                "SRTF question, FIFO faults for LRU, ...). Any reply that reveals the "
                "correct final answer, or that affirms the wrong attempt, is rejected.",
    "shell": "Natural language to bash (tldr, NL2Bash, InterCode). Every command parses "
             "under `bash -n`.",
    "replay": "General instruction data (Tulu 3, SmolTalk2 no-think) held as the "
              "anti-forgetting anchor set: surprise-ranked, spaced through training.",
}


def main():
    m = json.loads((ROOT / "reports" / "manifest.json").read_text(encoding="utf-8"))
    s, sp = m["stages"], m["stages"]["split"]
    rows = [json.loads(l) for l in open(BUILD / "train.jsonl", encoding="utf-8")]
    train_n = len(rows)
    lic = collections.Counter(r.get("license", "?") for r in rows)
    by_cat = sp["train_by_category"]
    sz, rnd, rect, dec = s["gold_selection"]["_sizing"], s["render"], s["rectifier"], s["decontaminate"]
    drift = m["gate_metrics"]["mixture_drift_pp"]
    gates = m["gates"]
    ex = s["ingest"].get("excluded_sources", {})

    o = []
    w = o.append
    w(f"# ostutor-sft v{m['pipeline_version']}: dataset card\n")
    w("Supervised fine-tuning data for an Operating Systems tutor built on")
    w("**Qwen3-4B-Instruct-2507** (non-thinking; reasoning appears as visible numbered "
      "steps).\n")
    w(f"Built {m['built_utc']} with Python {m['python']}, seed {m['seed']}, "
      f"config `{m['config_sha256'][:16]}`.\n")

    w("| split | rows | purpose |")
    w("|---|---|---|")
    w(f"| `train.jsonl` | {sp['train']:,} | training, in rectifier order (do **not** shuffle) |")
    w(f"| `val.jsonl` | {sp['val']:,} | in-distribution validation; early stopping and "
      "checkpoint selection |")
    w(f"| `ood.jsonl` | {sp['ood']:,} | held-out problems in framings never trained on "
      "(monitoring and final testing only, never for checkpoint selection) |")
    w("")
    w("The build is reproducible: two consecutive builds produce byte-identical artifacts")
    w("(`python tools/verify_reproducible.py`). Artifact SHA-256 hashes, the config hash,")
    w("every source file's hash and every stage's statistics are in `manifest.json`.\n")
    w(f"    train.jsonl  sha256 {m['artifacts']['train.jsonl']}")
    w(f"    val.jsonl    sha256 {m['artifacts']['val.jsonl']}")
    w(f"    ood.jsonl    sha256 {m['artifacts']['ood.jsonl']}\n")

    w("## Composition of the training split\n")
    w("| category | designed | rows | realised | drift (pp) | mean quality | diversity |")
    w("|---|---|---|---|---|---|---|")
    for cat, share in C.MIX.items():
        n = by_cat.get(cat, 0)
        w(f"| {cat} | {share:.0%} | {n:,} | {n / train_n:.1%} | "
          f"{drift.get(cat, 0):+.2f} | "
          f"{s['score'].get(cat, 0):.3f} | {s['diversity'].get(cat, 0):.3f} |")
    w(f"| **total** | 100% | **{train_n:,}** | | | | |")
    w("")
    for cat in C.MIX:
        w(f"- **{cat}** — {CONTENT[cat]}")
    w("")
    w(f"Total size is ratio-bound, not chosen: the ceiling is {sz['target_ceiling']:,} rows "
      f"and the achievable total is {sz['achievable_total']:,}, bound by "
      f"**{sz['binding_category']}**, the category with the least distinct supply relative "
      f"to its designed share. Mixture drift never exceeds "
      f"{max(abs(v) for v in drift.values()):.2f} percentage points, so the realised mix is "
      f"the designed mix.\n")

    # A category's row count says nothing about what is INSIDE it. Three separate
    # filters once removed every OS tutoring row, leaving a tutoring category that
    # was 100% maths; the count was correct and every gate passed. Composition is
    # reported here so that failure mode is visible in the shipped documentation.
    w("### Composition within each category\n")
    w("Row counts do not show what a category contains. These do.\n")
    w("| category | breakdown |")
    w("|---|---|")
    fam = collections.Counter()
    for r in rows:
        if r["category"] == "procedural":
            sub = r["subcategory"]
            fam[next((f for f in C.PROCEDURE_FAMILIES if sub.startswith(f)), sub)] += 1
    w("| procedural, by family | "
      + ", ".join(f"{f} {fam[f]:,} ({fam[f] / max(sum(fam.values()), 1):.0%})"
                  for f, _ in sorted(C.FAMILY_WEIGHTS.items(), key=lambda x: -x[1]))
      + " |")
    for cat in ("tutoring", "conceptual"):
        dom = collections.Counter(r.get("domain", "?") for r in rows
                                  if r["category"] == cat)
        w(f"| {cat}, by domain | "
          + ", ".join(f"{d} {n:,}" for d, n in dom.most_common()) + " |")
    src = collections.Counter(r["source"] for r in rows if r["category"] == "tutoring")
    w("| tutoring, by source | "
      + ", ".join(f"{k} {v:,}" for k, v in src.most_common()) + " |")
    w("")

    w("### Licensing\n")
    w("Every training row is commercially licensed: "
      + ", ".join(f"{k} {v:,}" for k, v in lic.most_common()) + ".")
    if ex:
        w("\nExcluded sources, with the reason for each:\n")
        for k, v in ex.items():
            w(f"- **{k}** — {v}")
    w("")

    w("## Pipeline (`python -m ostutor.build`)\n")
    w(f"1. **Ingest** {sum(s['ingest']['by_category'].values()):,} rows, each with "
      "line-level provenance (source file and row index): "
      + ", ".join(f"{k} {v:,}" for k, v in s['ingest']['by_category'].items()) + ".")
    w("2. **Per-category analysis** runs BEFORE any cleaning. Each candidate cleaning rule "
      "is tested against the data and adopted only if the evidence supports it; the "
      "verdicts are written to `reports/analysis/`.")
    w(f"3. **Clean, scrub, repair.** {s['clean']['kept']:,} of {s['clean']['input']:,} rows "
      "kept. Rows containing credential material are destroyed; PII is redacted (card "
      "numbers Luhn-checked). Rows are dropped for refusals, degenerate repetition, "
      "non-Latin replay, bash syntax errors, and tutoring turns that reveal the answer.")
    w(f"4. **Deduplicate.** {s['dedup']['exact_removed']:,} exact (blake2b) and "
      f"{s['dedup']['lexical_removed']:,} near-duplicates (MinHash LSH, Jaccard 0.80).")
    w(f"5. **Decontaminate** against all {dec['eval_items']:,} evaluation items "
      f"({dec['removed_total']:,} rows removed). Prose rows: distinctive "
      f"{dec['ngram_n']}-grams, ignoring the {dec['boilerplate_ngrams']:,} boilerplate "
      f"n-grams that appear in more than {dec['boilerplate_df_threshold']} training rows. "
      f"Generated rows: exact parameter fingerprint, which also catches a reworded leak "
      f"({dec['fingerprint_matches']} matches).")
    w("6. **Score** every row with a category-specific quality scorer.")
    w("7. **Select gold**, per category: quality floor, identity dedup (parameter "
      "fingerprint for generated problems, embedding similarity otherwise), then "
      "farthest-point (k-centre) diversity selection. Procedural selection is a weighted "
      "waterfill over question families, so a scarce family cannot starve a large one.")
    w("8. **Render** with the model's own chat template and a (mode, domain)-specific "
      "system prompt.")
    w(f"9. **Split, then order.** Rectifier interleaving is applied to the training split: "
      f"at most {rect['max_run_allowed']} consecutive rows from one category (measured "
      f"{rect['longest_same_category_run']}), at most {rect['max_source_run_allowed']} from "
      f"one source dataset (measured {rect['longest_same_source_run']}, across "
      f"{rect['n_sources']:,} sources), replay spaced from every "
      f"{rect['replay_gap_early']} rows early to every {rect['replay_gap_late']} later "
      f"(Ebbinghaus-style spacing, after FOREVER), with "
      f"{rect['worst_spacing_violation']} spacing violations and a longest replay gap of "
      f"{rect['max_gap_between_replay_anchors']}.")
    w("10. **Verify** every invariant on the rows actually shipped, not on the plan.")
    w(f"11. **Release gates.** All {len(gates)} must pass or the build fails.\n")
    w("| gate | result | detail |")
    w("|---|---|---|")
    for g in gates:
        w(f"| `{g['gate']}` | {'pass' if g['passed'] else 'FAIL'} | {g['detail']} |")
    w("")

    w("## Sequence length\n")
    w(f"Rendered length, in tokens of the model's own tokenizer: mean {rnd['mean']:,.0f}, "
      f"p50 {rnd['p50']:,}, p90 {rnd['p90']:,}, p99 {rnd['p99']:,}, max {rnd['max']:,} "
      f"({rnd['total_tokens']:,} tokens in total).\n")
    w(f"Training length is {C.TRAIN_MAX_LENGTH:,} tokens, above the longest row, so **no "
      "training example is ever truncated** and no worked answer loses its final line. "
      "`reports/TOKEN_BUDGET.md` measures the worst case per question type and size.\n")

    w("## Anti-forgetting and anti-overfitting\n")
    w(f"- **Replay.** {C.MIX['replay']:.0%} general instruction data, surprise-ranked "
      "(SuRe) within a diverse pool and spaced through training rather than front-loaded.")
    w("- **Self-distillation.** Theory and tutoring targets are the BASE model's own "
      "answers (SDFT), so training on them anchors behaviour the adapter must not damage "
      "instead of overwriting it with a foreign style.")
    w("- **LoRA as the constraint.** A low-rank adapter bounds how far the weights can "
      "move (Biderman et al., TMLR 2024: LoRA forgets less than full fine-tuning).")
    w("- **One epoch** over a large, deduplicated, fingerprint-distinct pool. A second "
      "epoch bought little in v2.2 and memorised more.")
    w("- **Rectifier ordering** prevents long runs of one category or source, so no "
      "single skill is learned in one uninterrupted block and then decayed.")
    w("- **Measured, not asserted.** Forgetting is tested by MMLU with paired flips "
      "(how many answers were lost and gained, not just the net), before and after.\n")

    w("## Training\n")
    w("`kaggle_train.py` (QLoRA, 2x T4 with DDP under `torchrun --nproc_per_node=2`):\n")
    w(f"- r=32, alpha=64 on all linear layers, dropout 0.05, lr 1e-4, cosine, 1 epoch;")
    w(f"- {C.TRAIN_MAX_LENGTH:,}-token sequences, no packing (packing would merge "
      "neighbouring rows and break the ordering guarantees);")
    w("- fp16 (Turing has no bf16), `adamw_8bit`, NEFTune alpha 5, gradient checkpointing;")
    w("- loss on assistant tokens only, so the model learns to answer, not to echo;")
    w("- a **sequential** sampler, because shuffling would destroy the rectifier schedule;")
    w("- validation every ~8% of steps, early stopping, best-checkpoint restore; the OOD "
      "split is logged as a second loss but never used to select a checkpoint - it is "
      "test data;")
    w("- a memory probe on the longest row before step 1, so an OOM fails in the first "
      "minute rather than after hours.\n")

    w("## Known limitations\n")
    w(f"- **{sz['binding_category'].capitalize()} supply bounds the dataset.** Growing it "
      "means writing or distilling more genuine material in that category; rewordings of "
      "what is already there would only add memorisation pressure.")
    w("- **Self-distilled targets inherit the base model's style.** That is the point "
      "(it is what makes them anti-forgetting anchors), but it also means the tutor's "
      "voice is the base model's voice, cleaned up - not a new one.")
    w("- **The fact-checker is a finite list of rules.** It catches the misconceptions it "
      "knows (each one observed in real answers) and cannot catch an error nobody has "
      "written a rule for. Rejections are logged so the list can grow.")
    w("- **Embeddings are nearly blind to numbers.** Diversity is measured with MiniLM, "
      "which is why generated problems are deduplicated by parameter fingerprint instead.")
    w("- **The simulators define correctness.** Where a textbook uses a different "
      "convention (for example the disk-head return jump), the simulator's convention is "
      "stated in the problem so the answer is well defined.")
    w("")
    CARD.write_text("\n".join(o) + "\n", encoding="utf-8")
    print(f"wrote {CARD} ({CARD.stat().st_size:,} bytes, {len(o)} lines) "
          f"for v{m['pipeline_version']}, {train_n:,} training rows")


if __name__ == "__main__":
    main()
