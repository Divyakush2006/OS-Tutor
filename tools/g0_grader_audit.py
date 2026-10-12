"""Find answers the grader may have marked wrong when they were right.

    python tools/g0_grader_audit.py reports/g0/<run>

D-003 found one grader blind spot that hit only the base model's formatting. This tool
looks for more: for every item graded WRONG, it checks whether the expected value still
appears in the answer's concluding lines. Those items are "suspects" and need a human
read; the rest are clear errors. Writes grader_audit.json and grader_audit.md into the
run directory. It never changes a grade — reviewed verdicts go in a separate file.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ostutor.evaluation.harness import grade  # noqa: E402

TAIL_LINES = 15


def _numbers(text: str) -> list[float]:
    return [float(x.replace(",", "")) for x in re.findall(r"-?\d[\d,]*(?:\.\d+)?", text)]


def _appears(expected, tail: str) -> bool:
    """Does the expected value show up in the tail, in any reasonable form?"""
    if expected is None:
        return False
    if isinstance(expected, (int, float)):
        return any(abs(x - float(expected)) <= max(0.011, 0.005 * abs(float(expected)))
                   for x in _numbers(tail))
    if isinstance(expected, (list, tuple)):
        flat = [str(x) for x in expected]
        # a sequence counts if its items appear in order
        pos = 0
        for item in flat:
            m = re.search(rf"\b{re.escape(item)}\b", tail[pos:])
            if not m:
                return False
            pos += m.end()
        return True
    return str(expected).lower() in tail.lower()


def audit(run: Path) -> dict:
    suite = {json.loads(l)["id"]: json.loads(l)
             for l in open(ROOT / "data/eval/os_freeform.jsonl", encoding="utf-8")}
    out = {}
    for f in sorted(run.glob("suite_*.json")):
        res = json.loads(f.read_text(encoding="utf-8"))
        wrong, suspects = 0, []
        for it in res["items"]:
            if it["correct"]:
                continue
            wrong += 1
            g = grade(suite[it["id"]], it["output"])
            lines = [l for l in it["output"].splitlines() if l.strip()]
            tail = "\n".join(lines[-TAIL_LINES:])
            if _appears(g.get("expected"), tail):
                suspects.append(dict(id=it["id"], kind=it["kind"], expected=g.get("expected"),
                                     got=g.get("got"), finish=it["finish"], tail=tail[-900:]))
        out[res["label"]] = dict(wrong=wrong, suspects=suspects)
    return out


def main() -> None:
    run = Path(sys.argv[1]) if len(sys.argv) > 1 else sorted(
        p for p in (ROOT / "reports/g0").iterdir() if p.is_dir() and not p.name.startswith("smoke"))[-1]
    res = audit(run)
    (run / "grader_audit.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    md = [f"# Grader audit — {run.name}", "",
          "Items graded wrong whose concluding lines still contain the expected value. "
          "Each needs a human read; this file changes no grade.", "",
          "| Configuration | Graded wrong | Suspects |", "|---|---|---|"]
    md += [f"| {k} | {v['wrong']} | {len(v['suspects'])} |" for k, v in res.items()]
    for k, v in res.items():
        for s in v["suspects"]:
            md += ["", f"### {k} · {s['id']} ({s['kind']}) — expected {s['expected']}, "
                       f"grader read {s['got']}, finish={s['finish']}", "", "```", s["tail"], "```"]
    (run / "grader_audit.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md[:6 + len(res)]))


if __name__ == "__main__":
    main()
