"""Error audit: classify every wrong answer of a fine-tuned model.

    python tools/error_audit.py reports/eval_finetuned_v2.0.json [more reports...]

For each graded item that is wrong, find WHY, using the simulators as ground truth:

  arithmetic   an explicit "a op b = c" the model wrote is false (by operator)
  procedure    the trace first diverges from the simulator's (wrong choice/state),
               with every arithmetic line in it correct
  format       the model's final answer is right but the grader could not read it
  truncated    the answer ran out of tokens
  other        none of the above could be established

Writes reports/error_audit.json and prints a summary table.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ostutor.evaluation.harness import grade  # noqa: E402
from ostutor.simulators.memory import (disk_schedule, fit_allocation,  # noqa: E402
                                        page_replacement, translate)
from ostutor.simulators.scheduling import ALGORITHMS, Proc  # noqa: E402

NUM = r"-?\d+(?:\.\d+)?"
BIN = re.compile(rf"(?<![\w.\]])({NUM})\s*([+\-x*/×])\s*({NUM})\s*=\s*\**\s*({NUM})(?![\d.])")
MOD = re.compile(rf"({NUM})\s*mod\s*({NUM})\s*=\s*({NUM})")
FLOOR = re.compile(rf"floor\(\s*({NUM})\s*/\s*({NUM})\s*\)\s*=\s*({NUM})")


def arithmetic_errors(text):
    """Every explicit binary operation the model wrote, checked."""
    errs, n = [], 0
    for line in text.splitlines():
        for m in BIN.finditer(line):
            a, op, b, c = float(m.group(1)), m.group(2), float(m.group(3)), float(m.group(4))
            n += 1
            if op == "+":
                ok = abs(a + b - c) < 1e-6
            elif op == "-":
                ok = abs(a - b - c) < 1e-6 or abs(abs(a - b) - c) < 1e-6
            elif op in "x*×":
                ok = abs(a * b - c) < 1e-6
            else:
                ok = b != 0 and abs(a / b - c) < 0.006
            if not ok:
                errs.append(dict(op={"x": "*", "×": "*"}.get(op, op), expr=m.group(0).strip()))
        for m in MOD.finditer(line):
            n += 1
            a, b, c = int(float(m.group(1))), int(float(m.group(2))), int(float(m.group(3)))
            if b and a % b != c:
                errs.append(dict(op="mod", expr=m.group(0)))
        for m in FLOOR.finditer(line):
            n += 1
            a, b, c = float(m.group(1)), float(m.group(2)), float(m.group(3))
            if b and int(a // b) != c:
                errs.append(dict(op="floor-div", expr=m.group(0)))
    return errs, n


VEC = r"\[\s*-?\d+(?:\s*,\s*-?\d+)*\s*\]"
VADD = re.compile(rf"({VEC})\s*([+\-])\s*(?:Allocation\s*|Alloc\s*|Request\s*)?({VEC})\s*=\s*({VEC})")
VCMP = re.compile(rf"(?:Need|Request)\s*({VEC})\s*(<=|≤|>|exceeds)\s*(?:Work|Need|Available)\s*({VEC})")
PAIR = re.compile(r"(?<![\d.])(\d+)\s*(<=|>)\s*(\d+)(?![\d.])")
SUMAVG = re.compile(rf"\(\s*({NUM}(?:\s*\+\s*{NUM})+)\s*\)\s*/\s*({NUM})\s*=\s*\**\s*({NUM})")
NSUM = re.compile(rf"(?<![\w.(])({NUM}(?:\s*\+\s*{NUM}){{2,}})\s*=\s*\**\s*({NUM})")


def _vec(s):
    return [int(x) for x in re.findall(r"-?\d+", s)]


def structured_errors(text):
    """Arithmetic the binary-expression check cannot see: vector sums and
    differences, Need <= Work comparisons, and multi-term sums and averages."""
    errs, n = [], 0
    for line in text.splitlines():
        for m in VADD.finditer(line):
            a, op, b, c = _vec(m.group(1)), m.group(2), _vec(m.group(3)), _vec(m.group(4))
            if len(a) == len(b) == len(c):
                n += 1
                want = [x + y if op == "+" else x - y for x, y in zip(a, b)]
                if want != c:
                    errs.append(dict(op=f"vector{op}", expr=m.group(0)))
        for m in VCMP.finditer(line):
            a, rel, b = _vec(m.group(1)), m.group(2), _vec(m.group(3))
            if len(a) == len(b):
                n += 1
                le = all(x <= y for x, y in zip(a, b))
                if (rel in ("<=", "≤")) != le and not (rel == "exceeds" and not le):
                    errs.append(dict(op="vector-compare", expr=m.group(0)))
        if " vs " in line:                     # v2.1+ component-wise comparisons
            for m in PAIR.finditer(line.split("->")[0]):
                n += 1
                x, rel, y = int(m.group(1)), m.group(2), int(m.group(3))
                if (x <= y) != (rel == "<="):
                    errs.append(dict(op="component-compare", expr=m.group(0)))
        for m in SUMAVG.finditer(line):
            n += 1
            terms = [float(x) for x in re.findall(NUM, m.group(1))]
            if abs(sum(terms) / float(m.group(2)) - float(m.group(3))) > 0.006:
                errs.append(dict(op="multi-term sum/avg", expr=m.group(0)))
        for m in NSUM.finditer(line):
            n += 1
            terms = [float(x) for x in re.findall(NUM, m.group(1))]
            if abs(sum(terms) - float(m.group(2))) > 1e-6:
                errs.append(dict(op="multi-term sum", expr=m.group(0)))
    return errs, n


def counting_error(v, text):
    """Paging: the fault total the model states vs the misses in its own table."""
    if v["kind"] != "paging":
        return None
    misses = len(re.findall(r"^\|\s*\d+\s*\|\s*\d+\s*\|\s*(?:FAULT|miss)\s*\|", text, re.M))
    m = re.findall(r"faults?\s*=\s*\**\s*(\d+)", text, re.I)
    if misses and m and int(m[-1]) != misses:
        return f"count: table shows {misses} faults, stated total {m[-1]}"
    return None


def procedure_divergence(v, text):
    """Where the model's trace first departs from the simulator's, if detectable."""
    k = v["kind"]
    if k == "paging":
        r = page_replacement(v["refs"], v["frames"], v["policy"])
        rows = re.findall(r"^\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(HIT|FAULT|hit|miss)\s*\|\s*([\d-]+)",
                          text, re.M)
        for t, page, res, ev in rows:
            i = int(t) - 1
            if i >= len(r["steps"]):
                return f"extra reference row #{t}"
            s = r["steps"][i]
            if int(page) != s["page"]:
                return f"copy: reference #{t} read as {page}, actual {s['page']}"
            if (res.upper() in ("HIT",)) != s["hit"]:
                return f"state: reference #{t} ({page}) marked {res}, actually {'hit' if s['hit'] else 'miss'}"
            want = "-" if s["victim"] is None else str(s["victim"])
            if ev != want:
                return f"choice: reference #{t} evicted {ev}, correct {want}"
        return None
    if k == "disk":
        r = disk_schedule(v["reqs"], v["head"], v["policy"], v["size"], v["direction"])
        m = re.search(r"Service order:\**\s*([\d\s\->]+)", text)
        if m:
            got = [int(x) for x in re.findall(r"\d+", m.group(1))]
            for i, (g, w) in enumerate(zip(got, r["order"])):
                if g != w:
                    return f"choice: service step {i + 1} went to {g}, correct {w}"
            if len(got) != len(r["order"]):
                return f"order length {len(got)} vs {len(r['order'])}"
        return None
    if k == "freespace":
        r = fit_allocation(v["holes"], v["reqs"], v["policy"])
        got = re.findall(r"request\s+(\d+):[^\n]*?(?:hole\s+(\d+)[;\s(]|WAIT)", text)
        for i, (req, hole) in enumerate(got[:len(r["placement"])]):
            want = r["placement"][i]
            if (int(hole) if hole else None) != want:
                return f"choice: request {req} placed in hole {hole or 'WAIT'}, correct {want}"
        return None
    if k == "scheduling":
        procs = [Proc(p, a, b, pr) for p, a, b, pr in v["procs"]]
        r = ALGORITHMS[v["algo"]](procs, quantum=v["quantum"])
        for row in r.table:
            m = re.search(rf"^\|\s*{re.escape(row['pid'])}\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)",
                          text, re.M)
            if m:
                arr, burst, comp = map(int, m.groups())
                if arr != row["arrival"] or burst != row["burst"]:
                    return f"copy: {row['pid']} arrival/burst {arr}/{burst}, actual {row['arrival']}/{row['burst']}"
                if comp != row["completion"]:
                    return f"state: {row['pid']} completion {comp}, correct {row['completion']}"
        return None
    if k == "translate":
        r = translate(v["logical"], v["page_size"], v["table"])
        m = re.search(r"page table\[(\d+)\]\s*=\s*frame\s*(\d+)", text)
        if m and (int(m.group(1)) != r["page"] or int(m.group(2)) != r["frame"]):
            return f"lookup: page table[{m.group(1)}] = {m.group(2)}, correct [{r['page']}] = {r['frame']}"
        return None
    return None


def audit(report_path):
    rep = json.loads(Path(report_path).read_text(encoding="utf-8"))
    rows = []
    for sname, s in rep["suites"].items():
        suite = [json.loads(l) for l in open(ROOT / "data" / "eval" / f"{sname}.jsonl",
                                             encoding="utf-8")]
        for it in s.get("items", []):
            if it["final_correct"]:
                continue
            rec, out = suite[it["index"]], it["output"]
            errs, n_ops = arithmetic_errors(out)
            e2, n2 = structured_errors(out)
            errs, n_ops = errs + e2, n_ops + n2
            cnt = counting_error(rec["verify"], out)
            div = procedure_divergence(rec["verify"], out)
            if it.get("truncated"):
                cause = "truncated"
            elif errs:
                cause = "arithmetic"
            elif cnt:
                cause, div = "counting", cnt
            elif div and div.startswith("copy"):
                cause = "copy"
            elif div:
                cause = "procedure"
            else:
                cause = "other"
            rows.append(dict(report=Path(report_path).name, suite=sname, index=it["index"],
                             kind=it["kind"], cause=cause, arithmetic=errs, ops_checked=n_ops,
                             divergence=div))
    return rows


def main():
    reports = sys.argv[1:] or [str(ROOT / "reports" / "eval_finetuned_v2.0.json")]
    rows = [r for p in reports for r in audit(p)]
    by_cause = Counter(r["cause"] for r in rows)
    by_kind = defaultdict(Counter)
    for r in rows:
        by_kind[r["kind"]][r["cause"]] += 1
    ops = Counter(e["op"] for r in rows for e in r["arithmetic"])
    print(f"wrong answers audited: {len(rows)}")
    print("by root cause:", dict(by_cause.most_common()))
    print("arithmetic slips by operator:", dict(ops.most_common()))
    for k, c in sorted(by_kind.items()):
        print(f"  {k:15s} {dict(c.most_common())}")
    print("\nexamples:")
    seen = set()
    for r in rows:
        key = (r["kind"], r["cause"])
        if key in seen:
            continue
        seen.add(key)
        detail = r["arithmetic"][0]["expr"] if r["arithmetic"] else r["divergence"]
        print(f"  [{r['kind']}/{r['cause']}] {detail}")
    (ROOT / "reports" / "error_audit.json").write_text(
        json.dumps(dict(summary=dict(by_cause=by_cause, operators=ops,
                                     by_kind={k: dict(v) for k, v in by_kind.items()}),
                        items=rows), indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
