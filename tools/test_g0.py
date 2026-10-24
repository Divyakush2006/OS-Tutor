"""Tests for the G0 measurement code. Hermetic: no GPU, no model server.

    python tools/test_g0.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Test names contain non-ASCII characters; a legacy Windows console would otherwise crash.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from ostutor.evaluation.extraction import answer_fields, fields_match  # noqa: E402
from ostutor.evaluation.stats import mcnemar_exact, paired  # noqa: E402
from ostutor import solver  # noqa: E402

FAILED: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  -> {detail}" if not ok and detail else ""))
    if not ok:
        FAILED.append(name)


def close(a: float, b: float) -> bool:
    return abs(a - b) < 1e-9


# ---------------------------------------------------------------- McNemar
print("mcnemar_exact")
check("no discordant pairs gives p = 1", mcnemar_exact(0, 0) == 1.0)
check("4 vs 1 gives 0.375 (OS-theory flips)", close(mcnemar_exact(4, 1), 0.375))
check("0 vs 6 gives 2 / 64", close(mcnemar_exact(0, 6), 2 / 64))
check("symmetric in its arguments", mcnemar_exact(11, 19) == mcnemar_exact(19, 11))
check("an even split is p = 1", mcnemar_exact(7, 7) == 1.0)
check("never exceeds 1", mcnemar_exact(10, 13) <= 1.0)
# 13 vs 10: 2 * P(X <= 10 | n=23) = 0.6776...
check("13 vs 10 matches the binomial tail", abs(mcnemar_exact(13, 10) - 0.6776) < 1e-3,
      str(mcnemar_exact(13, 10)))
try:
    mcnemar_exact(-1, 2)
    check("negative counts are rejected", False)
except ValueError:
    check("negative counts are rejected", True)

print("paired")
a = {"q1": True, "q2": True, "q3": False, "q4": False, "x": True}
b = {"q1": True, "q2": False, "q3": True, "q4": True, "y": False}
p = paired(a, b, "A", "B")
check("compares only shared ids", p["n"] == 4 and p["only_in_a"] == 1 and p["only_in_b"] == 1)
check("counts flips in each direction", p["right_to_wrong"] == 1 and p["wrong_to_right"] == 2)
check("reports accuracies and delta", p["accuracy_a"] == 0.5 and p["accuracy_b"] == 0.75
      and p["delta_pp"] == 25.0)
try:
    paired({"a": True}, {"b": True})
    check("disjoint runs are an error, not a silent zero", False)
except ValueError:
    check("disjoint runs are an error, not a silent zero", True)

# ---------------------------------------------------------------- extraction scoring
print("fields_match")
sched = {"kind": "scheduling", "algo": "FCFS", "quantum": 2,
         "procs": [["P1", 0, 5, 1], ["P2", 1, 3, 1]]}
check("identical parameters match", fields_match(dict(sched), sched) == (True, []))
check("the quantum is ignored when the algorithm is not RR",
      fields_match(dict(sched, quantum=9), sched)[0])
check("process names are ignored",
      fields_match(dict(sched, procs=[["A", 0, 5, 1], ["B", 1, 3, 1]]), sched)[0])
check("a wrong burst is caught",
      fields_match(dict(sched, procs=[["P1", 0, 6, 1], ["P2", 1, 3, 1]]), sched) == (False, ["procs"]))
rr = dict(sched, algo="RR")
check("the quantum counts for RR", fields_match(dict(rr, quantum=4), rr) == (False, ["quantum"]))
pri = dict(sched, algo="PRIORITY_P", procs=[["P1", 0, 5, 2], ["P2", 1, 3, 1]])
check("priorities count for priority scheduling",
      not fields_match(dict(pri, procs=[["P1", 0, 5, 1], ["P2", 1, 3, 1]]), pri)[0])
check("priorities are ignored for FCFS",
      fields_match(dict(sched, procs=[["P1", 0, 5, 9], ["P2", 1, 3, 9]]), sched)[0])
disk = {"kind": "disk", "policy": "FCFS", "reqs": [10, 20], "head": 5, "size": 200,
        "direction": "up"}
check("direction and size are ignored for FCFS disk",
      fields_match(dict(disk, direction="down", size=500), disk)[0])
scan = dict(disk, policy="SCAN")
check("direction counts for SCAN", fields_match(dict(scan, direction="down"), scan)[1] == ["direction"])
check("size counts for SCAN", fields_match(dict(scan, size=500), scan)[1] == ["size"])
check("canonical names compare equal (C-SCAN vs CSCAN)",
      fields_match(dict(disk, policy="C-SCAN"), dict(disk, policy="CSCAN"))[0])
check("a wrong kind is a single mismatch",
      fields_match(dict(disk, kind="paging"), disk) == (False, ["kind"]))
check("no extraction at all is a miss", fields_match(None, disk) == (False, ["missing"]))
req = {"kind": "banker_request", "alloc": [[1, 0]], "maxm": [[2, 1]], "avail": [1, 1],
       "req": [1, 0], "pid": 0, "names": ["P0"]}
check("the requesting process counts for banker_request",
      fields_match(dict(req, pid=1), req)[1] == ["pid"])
check("every solver kind has answer fields",
      all(answer_fields(k, {"algo": "RR", "policy": "SCAN"})
          for k in ["scheduling", "paging", "disk", "banker_safety", "banker_request",
                    "freespace", "translate"]))

# ---------------------------------------------------------------- trace instrumentation
print("solver trace")
Q = ("Schedule with FCFS. Processes: P1 arrives at 0 with burst 5; "
     "P2 arrives at 1 with burst 3. Find the average waiting time.")
GOOD = json.dumps({"kind": "scheduling", "algo": "FCFS",
                   "procs": [["P1", 0, 5, 1], ["P2", 1, 3, 1]]})
INVENTED = json.dumps({"kind": "scheduling", "algo": "FCFS",
                       "procs": [["P1", 0, 7, 1], ["P2", 1, 3, 1]]})


def scripted(*replies):
    it = iter(replies)
    return lambda system, user: next(it)


trace: list = []
v, why = solver.extract(Q, scripted("not json at all", GOOD), trace=trace)
check("an invalid reply then a good one is traced in order",
      [e["outcome"] for e in trace] == ["invalid_json", "ok"], str(trace))
check("the accepted parameters are recorded", trace[-1]["params"]["algo"] == "FCFS")

trace = []
v, why = solver.extract(Q, scripted(INVENTED, INVENTED, INVENTED), trace=trace)
check("an invented number is traced as ungrounded, on every attempt",
      [e["outcome"] for e in trace] == ["ungrounded"] * 3 and v is None, str(trace))
check("the ungrounded number is named", 7 in trace[0]["missing"], str(trace[0]))

trace = []
solver.extract("What is a page fault?",
               scripted(json.dumps({"kind": "concept"})), trace=trace)
check("a non-solver question is traced as non_solver",
      [e["outcome"] for e in trace] == ["non_solver"] and trace[0]["kind"] == "concept")

# Disk range (final review): "spans 0-299" is 300 cylinders. Extraction read the top of
# the range as the size in 9 of 9 misread OOD items; normalise() now reads the range.
DQ = ("Disk telemetry reports the arm at **156** (device spans 0-299) and a queue of: "
      "`170, 112, 188, 92, 34, 86`. Using **CSCAN** scheduling, give the total head movement.")
d = solver.normalise({"kind": "disk", "policy": "CSCAN", "head": 156,
                      "reqs": [170, 112, 188, 92, 34, 86], "size": 299}, DQ)
check("a 0-299 range is read as 300 cylinders", d and d["size"] == 300, str(d))
d = solver.normalise({"kind": "disk", "policy": "CSCAN", "head": 156,
                      "reqs": [170, 112, 188, 92, 34, 86], "size": 300}, DQ)
check("a size already read correctly is left alone", d and d["size"] == 300, str(d))
d = solver.normalise({"kind": "disk", "policy": "SSTF", "head": 136, "reqs": [333, 440],
                      "size": 500}, "head at cylinder 136 on a 500-cylinder device, queue 333, 440")
check("a stated size with no range is unchanged", d and d["size"] == 500, str(d))

r1 = solver.solve(Q, scripted("nope", GOOD))
r2 = solver.solve(Q, scripted("nope", GOOD), trace=[])
check("tracing never changes the solver's result", r1 == r2)
check("solve() without a trace still works (callers unchanged)", r1[1]["delegated"] is True)

# ---------------------------------------------------------------- grader
print("grader: reading the final answer")
from ostutor.evaluation.harness import _answer_number  # noqa: E402

W = ("average waiting", "avg waiting", "mean waiting", "AWT")
cases = [
    # the line that exposed the bug (base model, rr_classic): 5.67 is waiting, 15.67 turnaround
    (r"\boxed{\text{Average waiting time} = \dfrac{17}{3} \approx 5.67}, \quad "
     r"\boxed{\text{Average turnaround time} = \dfrac{47}{3} \approx 15.67}", 5.67),
    ("Average waiting time = 6.5, average turnaround time = 13.0", 6.5),
    ("Average waiting time = (13 + 13 + 3 + 9) / 4 = **9.5**", 9.5),
    ("Average waiting time = 48 / 5 = **9.6**", 9.6),
    ("Average waiting time: 4.25; average turnaround time: 9.75", 4.25),
    ("**Answer: average waiting time = 7.0 ms**", 7.0),
    ("Avg waiting = 3.2  and avg turnaround = 8.4", 3.2),
]
for text, want in cases:
    got = _answer_number(text, *W)
    check(f"reads {want} from: {text[:52]}...", got == want, f"got {got}")

print("grader: explicit final-answer markers (D-004)")
from ostutor.evaluation.harness import grade  # noqa: E402

suite = {json.loads(l)["id"]: json.loads(l)
         for l in open(ROOT / "data/eval/os_freeform.jsonl", encoding="utf-8")}
marker_cases = [
    # (item, output tail, should be correct) - the first four are real base-model endings
    ("scan_down", "- Total: 53 + 183 = **236**\n---\n### ✅ Final Answer:\n**236**", True),
    ("fcfs_disk", "- 5461 + 1620 = **7081**\n**Final Answer: 7081**", True),
    ("translate_4k", "= 4096 + 808\n= **4904**\n---\n### ✅ Final Answer:\n**4904**", True),
    ("lru_4f", "Step 18: fault (18)\n✅ Final answer: **10 page faults**", True),
    # the trained v3 format must grade exactly as before
    ("scan_down", "**Answer: total head movement = 236**", True),
    ("scan_down", "**Answer: total head movement = 230**", False),
    # a marker with the WRONG value is still wrong, whatever the working says
    ("scan_down", "Total: 53 + 183 = **236**\n### Final Answer:\n**235**", False),
    # hex in the marker is decoded (expected 4904 = 0x1328)
    ("translate_4k", "**Answer: physical address = 0x1328**", True),
]
for iid, out, want in marker_cases:
    got = grade(suite[iid], out)["final_correct"]
    check(f"{iid}: {out.splitlines()[-1][:44]!r} -> {want}", got == want, f"got {got}")

# ---------------------------------------------------------------- server guard
print("adapter guard")
import g0_ablation as g  # noqa: E402

v3 = [{"id": 0, "path": str(g.LORAS["v3"]), "scale": 1.0}]
try:
    g.check_adapters(v3, "v3")
    check("the expected single adapter is accepted", True)
except SystemExit:
    check("the expected single adapter is accepted", False)
for name, reported, expected in [
        ("two adapters are refused (the void-benchmark layout)",
         v3 + [{"id": 1, "path": str(g.LORAS["v2.2"])}], "v3"),
        ("the wrong adapter is refused", v3, "v2.2"),
        ("an adapter on the base server is refused", v3, None),
        ("a missing adapter is refused", [], "v3")]:
    try:
        g.check_adapters(reported, expected)
        check(name, False)
    except SystemExit:
        check(name, True)
try:
    g.check_adapters([], None)
    check("the base server with no adapter is accepted", True)
except SystemExit:
    check("the base server with no adapter is accepted", False)

print("\nALL G0 TESTS PASSED" if not FAILED else f"\n{len(FAILED)} FAILED: {FAILED}")
sys.exit(1 if FAILED else 0)
