"""Side-by-side table: base model vs each fine-tuned version.

    python tools/compare_runs.py

The HEADLINE metric is the hand-written free-form suite (data/eval/os_freeform.jsonl):
questions worded the way students type them, which no generator produced. v2.2
scored 65% on generator-shaped questions and 29% on free wording, and only the
second number predicted how the model behaved in the chat UI.

Also reported: the generator-shaped suites (comparable with v2.x), the hand-written
OS theory benchmark, and the catastrophic-forgetting check (general MMLU + adjacent
CS, with paired flips).

Writes reports/COMPARISON.md.
"""
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1] / "reports"

# label, OS eval report, forgetting report
RUNS = [
    ("base", "eval_baseline_v3.json", "forgetting_base_v3.json"),
    ("v2.2", "eval_finetuned_v2.2_v3suite.json", "forgetting_finetuned_v2.2.json"),
    ("v3.0", "eval_finetuned_v3.json", "forgetting_finetuned_v3.json"),
]
SUITES = [("os_freeform", "free-form (hand-written)"),
          ("os_solve_indist", "generator, standard"),
          ("os_solve_ood", "generator, held-out framings")]
GROUPS = [("os_theory", "OS theory MCQ (hand-written)"),
          ("general", "General MMLU (forgetting)"),
          ("adjacent_cs", "Adjacent-CS MMLU")]


def load(name):
    p = R / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def pct(x):
    return "—" if x is None else f"{100 * x:.1f}%"


def suite(rep, name, key):
    return ((rep or {}).get("suites", {}).get(name) or {}).get(key)


def main():
    runs = [(lab, load(a), load(b)) for lab, a, b in RUNS]
    runs = [r for r in runs if any(r[1:])]
    if not runs:
        print("no reports yet")
        return
    head = "| metric | " + " | ".join(r[0] for r in runs) + " |"
    sep = "|---|" + "---|" * len(runs)
    out = ["# Model comparison", "", head, sep]

    def row(label, vals):
        out.append(f"| {label} | " + " | ".join(vals) + " |")

    for s, name in SUITES:
        n = next((suite(r[1], s, "n") for r in runs if suite(r[1], s, "n")), "?")
        row(f"**{name}** (n={n})", [pct(suite(r[1], s, "final_answer_accuracy")) for r in runs])
        row(f"  answers cut off, {name}", [pct(suite(r[1], s, "truncation_rate")) for r in runs])
    for g, name in GROUPS:
        row(name, [pct(((r[2] or {}).get("summary", {}).get(g) or {}).get("accuracy"))
                   for r in runs])
        row(f"  {name}: right→wrong / wrong→right vs base",
            ["—" if not ((r[2] or {}).get("comparison") or {}).get(g) else
             f"{r[2]['comparison'][g]['right_to_wrong']} / {r[2]['comparison'][g]['wrong_to_right']}"
             for r in runs])

    # per-question-type accuracy on the free-form suite
    kinds = sorted({k for r in runs for k in (suite(r[1], "os_freeform", "by_topic") or {})})
    if kinds:
        out += ["", "| question type, free-form suite | " + " | ".join(r[0] for r in runs) + " |",
                sep]
        for k in kinds:
            cells = []
            for r in runs:
                d = (suite(r[1], "os_freeform", "by_topic") or {}).get(k) or {}
                cells.append(f"{pct(d.get('accuracy'))} ({d.get('n', 0)})" if d else "—")
            row(k, cells)

    text = "\n".join(out)
    print(text)
    (R / "COMPARISON.md").write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
