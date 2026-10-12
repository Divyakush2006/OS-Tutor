"""Exact McNemar p-values for every historical paired comparison.

    python tools/significance_history.py

Reads the existing reports (never modifies them) and writes
reports/g0/historical_significance.json and .md. Each comparison is between two runs
scored on the same item ids; the p-value tests whether the right->wrong and
wrong->right flips are more lopsided than chance.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ostutor.evaluation.stats import paired  # noqa: E402

R = ROOT / "reports"
OUT = R / "g0"

FORGETTING = [
    # (run A, run B, what the comparison asks)
    ("forgetting_base_v3.json", "forgetting_v2.2_paired.json", "base -> v2.2 (2026-09-21 run)"),
    ("forgetting_base_v3.json", "forgetting_v3_paired.json", "base -> v3.0 (2026-09-21 run)"),
    ("forgetting_v2.2_paired.json", "forgetting_v3_paired.json", "v2.2 -> v3.0 (2026-09-21 run)"),
    ("forgetting_base.json", "forgetting_finetuned_v2.0.json", "base -> v2.0 (2026-09-19 run)"),
    ("forgetting_base.json", "forgetting_finetuned_v2.2.json", "base -> v2.2 (2026-09-19 run)"),
]


def forgetting(a_file: str, b_file: str, question: str) -> list[dict]:
    a = json.loads((R / a_file).read_text(encoding="utf-8"))["items"]
    b = json.loads((R / b_file).read_text(encoding="utf-8"))["items"]
    rows = []
    for group in sorted({x["group"] for x in a}):
        ga = {x["id"]: x["correct"] for x in a if x["group"] == group}
        gb = {x["id"]: x["correct"] for x in b if x["group"] == group}
        if set(ga) & set(gb):
            rows.append(dict(paired(ga, gb, a_file, b_file), group=group, question=question))
    return rows


def procedural() -> list[dict]:
    """v3 alone vs v3 + solver from the one valid served-path run (2026-09-21)."""
    runs = json.loads((R / "benchmark_v3_single_np1.json").read_text(encoding="utf-8"))
    by = {r["label"]: {str(x["index"]): x["final_correct"] for x in r["items"]} for r in runs}
    return [dict(paired(by["v3"], by["v3+solver"], "v3", "v3+solver"), group="57-item suite",
                 question="solver, on v3 (benchmark_v3_single_np1.json)")]


def main() -> None:
    rows = [r for a, b, q in FORGETTING for r in forgetting(a, b, q)] + procedural()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "historical_significance.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    md = ["# Historical paired comparisons — exact McNemar", "",
          "Recomputed from existing reports, which are left unchanged. "
          "p < 0.05 is marked **sig**.", "",
          "| Comparison | Group | n | Accuracy A → B | Right→wrong | Wrong→right | p |",
          "|---|---|---|---|---|---|---|"]
    for r in rows:
        sig = " **sig**" if r["mcnemar_p"] < 0.05 else ""
        md.append(f"| {r['question']} | {r['group']} | {r['n']} | {r['accuracy_a']:.2%} → "
                  f"{r['accuracy_b']:.2%} | {r['right_to_wrong']} | {r['wrong_to_right']} | "
                  f"{r['mcnemar_p']:.4f}{sig} |")
    (OUT / "historical_significance.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
