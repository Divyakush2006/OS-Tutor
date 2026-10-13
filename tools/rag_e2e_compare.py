"""Compare two end-to-end runs' short-answer phases item by item (same questions, same models).

    python tools/rag_e2e_compare.py reports/rag/e2e-short-course reports/rag/e2e-20261013-1339

For base and v3 with retrieval on, run A's corpus against run B's: correct counts and the
paired exact McNemar test, on the test split and on all 144 questions, under the
pre-registered grading and the secondary amended grading (tools/rag_e2e.py). Also checks
that the retrieval-off replies are identical across the two runs (they must be: same
prompt, greedy, prompt cache off). Writes reports/rag/short_<A>_vs_<B>.md and .json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from ostutor.evaluation.stats import mcnemar_exact  # noqa: E402
from rag_e2e import contains_amended  # noqa: E402


def load(run: Path) -> tuple[dict, str]:
    rows = {}
    for l in open(run / "short.partial.jsonl", encoding="utf-8"):
        r = json.loads(l)
        rows[r["key"]] = r
    corpus = json.loads((run / "provenance.json").read_text(encoding="utf-8"))["corpus"]
    return rows, corpus


def main() -> None:
    ra, rb = Path(sys.argv[1]), Path(sys.argv[2])
    a, ca = load(ra)
    b, cb = load(rb)
    off = [k for k in a if "|off|" in k]
    res = dict(a=dict(run=ra.name, corpus=ca), b=dict(run=rb.name, corpus=cb),
               off_replies_identical=sum(a[k]["text"] == b[k]["text"] for k in off), off_replies=len(off), rows=[])
    for grading in ("pre-registered", "amended"):
        ok = (lambda r: r["correct"]) if grading == "pre-registered" else \
            (lambda r: contains_amended(r["id"], r["text"], r["answers"]))
        for split in ("test", "all"):
            for srv in ("v3", "base"):
                ids = [k.split("|")[2] for k in b if k.startswith(f"{srv}|on|")
                       and (split == "all" or b[k]["split"] == split)]
                x = {i: ok(a[f"{srv}|on|{i}"]) for i in ids}
                y = {i: ok(b[f"{srv}|on|{i}"]) for i in ids}
                lost = sum(x[i] and not y[i] for i in ids)
                gained = sum(y[i] and not x[i] for i in ids)
                res["rows"].append(dict(grading=grading, split=split, model=srv, n=len(ids), a=sum(x.values()),
                                        b=sum(y.values()), lost=lost, gained=gained,
                                        p=round(mcnemar_exact(lost, gained), 4)))
    name = f"short_{ra.name}_vs_{rb.name}"
    out = ROOT / "reports" / "rag"
    (out / f"{name}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    md = [f"# Short-answer accuracy with retrieval: `{ca}` (A) vs `{cb}` (B)", "",
          f"Runs `{ra.name}` and `{rb.name}`. Retrieval-off replies identical across the runs: "
          f"{res['off_replies_identical']}/{res['off_replies']}.", "",
          "| Grading | Split | Model + RAG | A correct | B correct | B lost | B gained | exact McNemar p |",
          "|---|---|---|---|---|---|---|---|"]
    md += [f"| {r['grading']} | {r['split']} | {r['model']} | {r['a']}/{r['n']} | {r['b']}/{r['n']} | {r['lost']} | "
           f"{r['gained']} | {r['p']:.4f} |" for r in res["rows"]]
    (out / f"{name}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
