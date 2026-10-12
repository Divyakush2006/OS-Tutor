"""Re-grade a saved G0 run with the current grader; the run's own files are not touched.

    python tools/g0_regrade.py reports/g0/<run>

The run directory keeps the verdicts it was graded with. D-003 and D-004 fixed grader
blind spots after 20261012-1429 was graded; this writes regraded.json and regraded.md
next to it with every configuration and paired comparison under the current grader.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ostutor.evaluation.harness import grade  # noqa: E402
from ostutor.evaluation.stats import paired  # noqa: E402

CONFIGS = ["base", "base+solver", "v2.2", "v2.2+solver", "v3", "v3+solver"]
PAIRS = [("adapter, no solver", "base", "v3"), ("adapter, with solver", "base+solver", "v3+solver"),
         ("solver, on the base model", "base", "base+solver"), ("solver, on v3", "v3", "v3+solver"),
         ("v2.2 adapter, no solver", "base", "v2.2"), ("v2.2 -> v3, no solver", "v2.2", "v3")]


def main() -> None:
    run = Path(sys.argv[1]).resolve()
    suite = {json.loads(l)["id"]: json.loads(l)
             for l in open(ROOT / "data/eval/os_freeform.jsonl", encoding="utf-8")}
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                            text=True).stdout.strip()
    res, scores = dict(run=run.name, graded_at_commit=commit, configs={}, paired={}), {}
    for c in CONFIGS:
        items = json.loads((run / f"suite_{c}.json").read_text(encoding="utf-8"))
        items = items["items"] if isinstance(items, dict) else items
        now = {x["id"]: grade(suite[x["id"]], x["output"])["final_correct"] for x in items}
        was = {x["id"]: bool(x["correct"]) for x in items}
        scores[c] = now
        res["configs"][c] = dict(n=len(now), correct_as_run=sum(was.values()),
                                 correct_regraded=sum(now.values()),
                                 changed=sorted(i for i in now if now[i] != was[i]))
    for label, a, b in PAIRS:
        res["paired"][label] = paired(scores[a], scores[b], a, b)
    (run / "regraded.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    md = [f"# {run.name} re-graded with the grader at `{commit[:10]}`", "",
          "| Configuration | As run | Re-graded | Items that changed |", "|---|---|---|---|"]
    md += [f"| {c} | {v['correct_as_run']}/{v['n']} | {v['correct_regraded']}/{v['n']} | "
           f"{', '.join(v['changed']) or '—'} |" for c, v in res["configs"].items()]
    md += ["", "| Question | A → B | Correct A → B | Right→wrong | Wrong→right | exact McNemar p |",
           "|---|---|---|---|---|---|"]
    md += [f"| {k} | {p['a']} → {p['b']} | {p['correct_a']} → {p['correct_b']} | {p['right_to_wrong']} | "
           f"{p['wrong_to_right']} | {p['mcnemar_p']:.4f} |" for k, p in res["paired"].items()]
    (run / "regraded.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
