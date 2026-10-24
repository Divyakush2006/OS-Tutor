"""Unit tests for correctness-critical pipeline logic.

These cover the places where a silent bug corrupts the dataset without failing
loudly. Every test below pins a bug that was ACTUALLY FOUND during development,
so the suite is a regression record rather than a wish list.

    python tools/test_pipeline.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from ostutor.clean import clean_records, merge_same_role, normalise, trim_dead_tail
from ostutor.evaluation.harness import _answer_number, _sequence_after, grade
from ostutor.mix import allowed_gap, feasible, interleave, verify_invariants
from ostutor.quality import band, count_steps, ttr
from ostutor.schema import validate
from ostutor.scrub import find_secrets, redact_pii
from ostutor.select import achievable_total, farthest_point
from ostutor.simulators.banker import is_safe, verify_sequence
from ostutor.simulators.memory import beladys_anomaly, disk_schedule, page_replacement
from ostutor.simulators.scheduling import ALGORITHMS, Proc

FAILED = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}  {detail}")
        FAILED.append(name)


# ============================================================ simulators
print("\n-- simulators: validated against canonical textbook answers --")
ps = [Proc("P1", 0, 8), Proc("P2", 1, 4), Proc("P3", 2, 9), Proc("P4", 3, 5)]
srtf = ALGORITHMS["SRTF"]([Proc(p.pid, p.arrival, p.burst) for p in ps])
check("SRTF avg waiting = 6.5 (Silberschatz)", srtf.avg_waiting == 6.5,
      f"got {srtf.avg_waiting}")
refs = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]
for pol, exp in (("FIFO", 15), ("LRU", 12), ("OPT", 9)):
    got = page_replacement(refs, 3, pol)["faults"]
    check(f"{pol} page faults = {exp}", got == exp, f"got {got}")
b = beladys_anomaly([1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5], 3, 4)
check("Belady's anomaly reproduced (9 vs 10)",
      (b["faults_small"], b["faults_large"]) == (9, 10) and b["anomaly"])
rq, head = [98, 183, 37, 122, 14, 124, 65, 67], 53
for pol, d, exp in (("FCFS", "up", 640), ("SSTF", "up", 236), ("SCAN", "down", 236),
                    ("LOOK", "down", 208), ("CSCAN", "up", 382), ("CLOOK", "up", 322)):
    got = disk_schedule(rq, head, pol, 200, d)["total_head_movement"]
    check(f"disk {pol} ({d}) = {exp}", got == exp, f"got {got}")

print("\n-- banker: safe sequences are NOT unique --")
alloc = [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]]
maxm = [[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]]
safe, seq, _ = is_safe([3, 3, 2], maxm, alloc)
check("canonical state is SAFE", safe)
check("our sequence validates", verify_sequence(seq, [3, 3, 2], maxm, alloc)[0])
check("textbook's DIFFERENT sequence also validates",
      verify_sequence(["P1", "P3", "P4", "P0", "P2"], [3, 3, 2], maxm, alloc)[0],
      "a grader that string-matches one key would mark correct work wrong")
check("an invalid sequence is rejected",
      not verify_sequence(["P0", "P1", "P2", "P3", "P4"], [3, 3, 2], maxm, alloc)[0])

# ============================================================ scrub
print("\n-- scrub: secrets destroyed, PII redacted, false positives preserved --")
check("aws key detected", find_secrets("AKIAIOSFODNN7EXAMPLE") == ["aws_access_key"])
check("private key detected", "private_key" in find_secrets("-----BEGIN RSA PRIVATE KEY-----"))
check("clean text is clean", find_secrets("how does paging work") == [])
check("real email redacted", redact_pii("mail bob@acme.co.uk", "replay")[0] == "mail <EMAIL>")
check("example.com preserved", redact_pii("mail a@example.com", "replay")[1] == {})
check("phone redacted", "<PHONE>" in redact_pii("call 555-123-4567", "replay")[0])
check("luhn-valid card redacted", "<CARD>" in redact_pii("4532015112830366", "replay")[0])
check("non-card numeral preserved",
      "1234567890123456" in redact_pii("counted 1234567890123456", "replay")[0])
check("page-table numerals preserved", redact_pii("base 4096 offset 1024", "replay")[1] == {})
check("shell args exempt", redact_pii("timeout 300 500 1000", "shell")[1] == {})

# ============================================================ clean
print("\n-- clean: repair before drop --")
msgs = [dict(role="user", content="a"), dict(role="assistant", content="b"),
        dict(role="assistant", content="c")]
check("merges same-role turns", len(merge_same_role(msgs)) == 2)
check("merge preserves content", merge_same_role(msgs)[1]["content"] == "b c")
check("trims dead tail",
      len(trim_dead_tail([dict(role="user", content="q"),
                          dict(role="assistant", content="real answer"),
                          dict(role="user", content="ok"),
                          dict(role="assistant", content="correct")])) == 2)
check("normalise collapses blank runs", normalise("a\n\n\n\nb") == "a\n\nb")
check("normalise PRESERVES code indentation",
      normalise("def f():\n    return 1") == "def f():\n    return 1",
      "a global [ \\t]+ -> ' ' destroys every code block in the corpus")

_rec = dict(id="t1", category="tutoring", subcategory="d", mode="tutor", domain="math",
            source="eth-nlped/mathdial", license="cc-by-4.0", commercial_ok=True,
            lineage={}, n_chars=0, quality=0.0,
            messages=[dict(role="user", content="I think the answer is 12 because I multiplied"),
                      dict(role="assistant", content="What operation did the problem ask for?"),
                      dict(role="user", content="Oh, it was addition not multiplication"),
                      dict(role="assistant", content="Correct"),
                      dict(role="user", content="thanks")])
_out = clean_records([_rec], report={})
check("trailing-user truncation cannot recreate a dead tail",
      not _out or not _out[0]["messages"][-1]["content"].strip().lower().startswith("correct"),
      "tail normalisation must run BEFORE category dispatch")

# ============================================================ quality
print("\n-- quality: scoring matches the real corpus --")
check("band rewards right-sized", band(100, 50, 200) == 1.0 and band(1000, 50, 200) < 1.0)
check("ttr of repeats is low", ttr("a a a a a") < 0.3)
check("counts ** Step N ** headings", count_steps("**Step 1 - build**\n**Step 2 - go**") >= 2)
check("counts bullet traces", count_steps("- one\n- two\n- three") >= 3)
check("counts numbered lists", count_steps("1. one\n2. two") >= 2,
      "a numbered-only pattern matched ZERO of 6,900 generated solutions")

# ============================================================ schema
print("\n-- schema: invariants enforced --")
ok = dict(category="shell", mode="shell", commercial_ok=True,
          messages=[dict(role="user", content="x"), dict(role="assistant", content="y")])
check("valid record passes", validate(ok) == [])
check("non-alternating caught",
      any("non-alternating" in p for p in
          validate(dict(ok, messages=[dict(role="user", content="x"),
                                      dict(role="user", content="y")]))))
check("non-commercial caught",
      any("non-commercial" in p for p in validate(dict(ok, commercial_ok=False))))
check("think block caught",
      any("think" in p for p in
          validate(dict(ok, messages=[dict(role="user", content="x"),
                                      dict(role="assistant", content="<think>hi</think>")]))))

# ============================================================ rectifier
print("\n-- rectifier: ordering invariants on a hostile mix --")
by_cat = {"procedural": [dict(category="procedural", subcategory=f"s{i%3}", id=f"p{i}")
                         for i in range(200)],
          "replay": [dict(category="replay", subcategory="tulu", id=f"r{i}") for i in range(40)],
          "shell": [dict(category="shell", subcategory="tldr", id=f"s{i}") for i in range(30)]}
ordered = interleave(by_cat, seed=42)
ok_inv, stats = verify_invariants(ordered)
check("all rows preserved", len(ordered) == 270, f"got {len(ordered)}")
check("no duplicates", len({r["id"] for r in ordered}) == 270)
check("category run cap respected",
      stats["longest_same_category_run"] <= stats["max_run_allowed"],
      f"run={stats['longest_same_category_run']}")
check("feasibility computed", feasible({"a": 200, "b": 50})[0] and not feasible({"a": 500, "b": 5})[0])
tail = "".join(r["category"][0] for r in ordered[-40:])
check("tail does not degenerate",
      max(len(m.group(0)) for m in re.finditer(r"(.)\1*", tail)) <= stats["max_run_allowed"],
      f"tail={tail} - a rate-matching scheduler leaves no separators in reserve")
_a = interleave({c: [dict(category=c, subcategory=c, id=f"{c}{i}") for i in range(20)]
                 for c in ["alpha", "beta", "gamma"]}, seed=7)
_b = interleave({c: [dict(category=c, subcategory=c, id=f"{c}{i}") for i in range(20)]
                 for c in ["gamma", "alpha", "beta"]}, seed=7)
check("ordering ignores input key order",
      [r["id"] for r in _a] == [r["id"] for r in _b],
      "a dict built from a SET iterates process-dependently -> unreproducible build")

print("\n-- rectifier: Ebbinghaus-spaced replay --")
check("replay gap grows across the epoch", allowed_gap(0.0) < allowed_gap(1.0),
      "FOREVER (arXiv 2601.03938): replay dense early, sparser once stabilised")
check("gap is bounded at both ends", allowed_gap(-1) == allowed_gap(0.0)
      and allowed_gap(2) == allowed_gap(1.0))

# ============================================================ selection
print("\n-- selection: diversity, not top-N --")
rng = np.random.default_rng(0)
a = rng.normal(0, .01, (60, 8)) + np.array([1, 0, 0, 0, 0, 0, 0, 0])
b = rng.normal(0, .01, (6, 8)) + np.array([0, 1, 0, 0, 0, 0, 0, 0])
emb = np.vstack([a, b])
emb /= np.linalg.norm(emb, axis=1, keepdims=True)
q = np.concatenate([np.full(60, 0.9), np.full(6, 0.6)])   # cluster scores HIGHER
picked = farthest_point(emb, q, 8)
minority = sum(1 for i in picked if i >= 60)
check("farthest-point reaches the minority cluster", minority >= 1,
      "top-N by quality would take 8 near-identical rows from the big cluster")
check("does not pick only the minority", minority < 8)

print("\n-- selection: ratio enforcement --")
# Supply is expressed as a multiple of each category's share so the test does not
# depend on the MIX values: every category can support 4,000 rows except
# conceptual, which can support 1,500 - so conceptual must bind at 1,500.
from ostutor.config import MIX as _MIX
pools = {c: ([0] * int(4000 * sh), None) for c, sh in _MIX.items()}
pools["conceptual"] = ([0] * int(1500 * _MIX["conceptual"]), None)
total, binding, limits = achievable_total(pools)
check("total is bound by the scarcest category relative to its share",
      binding == "conceptual", f"binding={binding} limits={limits}")
check("total respects the binding category's share",
      abs(total * 0.20 - 300) < 1.5, f"total={total}")
check("a plentiful category does not raise the total",
      total <= 1500, f"total={total} - quotas are proportions, not ceilings")

print("\n-- selection: subcategory cap never overshoots quota --")
from ostutor.select import _subcat_cap
_rows = [dict(subcategory=f"s{i%5}") for i in range(300)]
_out, _per, _ = _subcat_cap(_rows, list(range(300)), 50)
check("cap returns exactly quota when given 6x candidates", len(_out) == 50,
      f"got {len(_out)} - the SuRe path passes a 3x pool")

print(chr(10) + "-- selection: stratified procedural selection --")
from ostutor.select import waterfill, stratified_pick
from ostutor.dedup import by_fingerprint
check("waterfill splits evenly and redistributes a small key's surplus",
      waterfill(dict(a=100, b=5, c=100), 60) == dict(a=28, b=5, c=27),
      str(waterfill(dict(a=100, b=5, c=100), 60)))
check("waterfill never exceeds supply", waterfill(dict(a=3, b=4), 50) == dict(a=3, b=4))
# A number-blind embedding: every page-replacement row is identical, every CPU row
# is spread out. Global farthest-point would pick almost only CPU rows.
_r = ([dict(subcategory="page_replacement_lru") for _ in range(200)]
      + [dict(subcategory="cpu_scheduling_rr") for _ in range(200)])
_e = np.zeros((400, 8)); _e[:200, 0] = 1
_rng = np.random.default_rng(0); _e[200:] = _rng.normal(size=(200, 8))
_e /= np.linalg.norm(_e, axis=1, keepdims=True)
_pick, _alloc = stratified_pick(_r, _e, np.ones(400), 100)
_n_page = sum(1 for j in _pick if _r[j]["subcategory"].startswith("page"))
# v3.0: families are filled by WEIGHT, so the expected split is the weight ratio
# (page_replacement 0.13 vs cpu_scheduling 0.23 -> ~36 of 100), not 50/50. What the
# test pins is that stratification still prevents topic collapse: global
# farthest-point over this number-blind embedding would pick ~1 page-replacement row.
from ostutor.config import FAMILY_WEIGHTS as _FWT
_want = round(100 * _FWT["page_replacement"] / (_FWT["page_replacement"] + _FWT["cpu_scheduling"]))
check("stratified pick keeps topics balanced under a number-blind embedding",
      len(_pick) == 100 and abs(_n_page - _want) <= 2,
      f"page={_n_page} of {len(_pick)}, expected about {_want}")
_fp = [dict(quality=q, id=str(i), lineage=dict(fingerprint=f))
       for i, (q, f) in enumerate([(0.5, "x"), (0.9, "x"), (0.7, "y"), (0.8, None)])]
check("fingerprint dedup keeps the best row per problem and all unfingerprinted rows",
      by_fingerprint(_fp) == [1, 2, 3], str(by_fingerprint(_fp)))

# ============================================================ leakage
print(chr(10) + "-- leakage: evaluation data is never ingested for training --")
import json as _json, copy as _copy
from ostutor.sources import ingest_procedural, ingest_tutoring, ingest_shell, fingerprint
from ostutor.dedup import decontaminate
_proc = ingest_procedural()
check("OOD holdout is not ingested",
      not any("holdout" in r["lineage"].get("file", "") for r in _proc),
      "the procedural_*.jsonl glob matched the holdout file")
check("MathDial test split is not ingested",
      not any("mathdial_test" in r["lineage"].get("file", "") for r in ingest_tutoring()[0]))
check("NL2SH-ALFA verified test set is not ingested",
      not any(r["subcategory"] == "nl2sh_verified" for r in ingest_shell()))
if _proc:
    _ev = [_json.loads(l) for l in open("data/eval/os_solve_ood.jsonl", encoding="utf-8")][:2]
    _leaks = []
    for _i, _e in enumerate(_ev):
        _r = _copy.deepcopy(_proc[_i]); _r["id"] = f"LEAK{_i}"
        _r["messages"][0]["content"] = "Completely reworded statement of the problem."
        _r["lineage"]["fingerprint"] = fingerprint(_e["verify"]); _leaks.append(_r)
    _kept = decontaminate(_proc[:200] + _leaks, [], {},
                          eval_fingerprints={fingerprint(e["verify"]) for e in _ev})
    check("reworded leak caught by parameter fingerprint",
          not any(r["id"].startswith("LEAK") for r in _kept),
          "n-gram matching cannot see a leak whose wording changed")
    check("no false positives on clean generated rows", len(_kept) == 200,
          f"kept {len(_kept)}/200")
else:
    print("  SKIP  parameter-fingerprint leak check: the procedural pool in data/raw is not "
          "published (tools/generate_procedural.py rebuilds it)")

# ============================================================ harness
print("\n-- eval harness: parsers --")
check("reads the RESULT, not the working",
      _answer_number("Average waiting time = (13 + 13 + 3 + 9) / 4 = **9.5**",
                     "average waiting") == 9.5,
      "reading the first number scores the sum's first term")
check("sequence parser ignores '<= Work [5, 5, 5] ->'",
      _sequence_after("P0: Need [1,2] <= Work [5, 5, 5] -> run it\n"
                      "A safe sequence is **< P1, P3, P0 >**.",
                      "safe sequence") == ["P1", "P3", "P0"])
check("sequence parser handles numeric PIDs",
      _sequence_after("A safe sequence is **< 1543, 1554, 1581 >**.", "safe sequence")
      == ["1543", "1554", "1581"])

print(chr(10) + "-- v2.1 worked solutions: every intermediate value is written --")
from ostutor.simulators.generate import render_solution
_t = render_solution(dict(kind="translate", logical=1142, page_size=1024,
                          table=[27, 9, 30]))
check("translation shows the product and the sum separately",
      "9 x 1024 = 9216" in _t and "9216 + 118 = 9334" in _t, _t)
_procs = [["P%d" % i, i, 3 + i % 4, 1] for i in range(10)]
_s = render_solution(dict(kind="scheduling", algo="RR", quantum=2, procs=_procs))
_slices = sum(1 for l in _s.splitlines() if l.startswith("- t=") and ": run " in l)
_need = sum(-(-(3 + i % 4) // 2) for i in range(10))
check("round-robin trace is complete (v2.0 cut it at 22 events)",
      _slices == _need, f"{_slices} slices shown, {_need} needed")
check("scheduling averages use a running sum",
      "Sum of waiting times: " in _s and " + " in _s.split("Sum of waiting times: ")[1])
_p = render_solution(dict(kind="paging", refs=[7, 0, 1, 2, 0, 3], frames=3, policy="LRU"))
check("LRU trace lists frames least-recently-used first",
      "| 4 | 2 | miss | 7 | frames full; last used 7@#1 < 0@#2 < 1@#3 -> least recent = 7 | 0 1 2 | 4 |" in _p, _p)
_f = render_solution(dict(kind="freespace", holes=[100, 500, 600], reqs=[212],
                          policy="WORST"))
check("worst-fit shows the candidate holes behind the choice",
      "hole 1=100 < 212 no; hole 2=500 >= 212 fits; hole 3=600 >= 212 fits -> largest "
      "fitting: 600 > 500 -> hole 3" in _f, _f)

import re as _re
_multi = _re.compile(r"(?<![\w\[])\d+(?:\.\d+)?\s*[+\-x*/]\s*\d+(?:\.\d+)?\s*[+\-x*/]\s*\d+")
_bad = []
for _kind, _v in [("scheduling", dict(algo="SRTF", quantum=2, procs=_procs)),
                  ("translate", dict(logical=11800, page_size=2048, table=[1, 2, 3, 4, 5, 27])),
                  ("paging", dict(refs=[7, 0, 1, 2, 0, 3, 0, 4], frames=3, policy="OPT")),
                  ("disk", dict(reqs=[98, 183, 37, 122], head=53, policy="SSTF", size=200,
                                direction="up")),
                  ("freespace", dict(holes=[100, 500, 600, 50], reqs=[212, 30], policy="BEST")),
                  ("banker_safety", dict(avail=[3, 3, 2], names=["A", "B", "C"],
                                         maxm=[[7, 5, 3], [3, 2, 2], [2, 2, 2]],
                                         alloc=[[0, 1, 0], [2, 0, 0], [2, 1, 1]]))]:
    for _line in render_solution(dict(kind=_kind, **_v)).splitlines():
        if _multi.search(_line.split("(check:")[0]):
            _bad.append(_line)
_bk = render_solution(dict(kind="banker_safety", avail=[3, 3, 2], names=["A", "B"],
                           maxm=[[1, 2, 2], [4, 3, 3]], alloc=[[1, 0, 0], [0, 0, 2]]))
check("Banker's comparisons are written component by component",
      "Need [0, 2, 2] vs Work [3, 3, 2]: 0<=3, 2<=3, 2<=2 -> all fit" in _bk, _bk[:400])
check("Banker's Need is computed row by row", "- A: [1, 2, 2] - [1, 0, 0] = [0, 2, 2]" in _bk)
check("no worked-solution line chains two operations (one operation per line)",
      not _bad, "; ".join(_bad[:3]))

from ostutor.evaluation.harness import _request_decision
check("request grader reads the concluded decision",
      _request_decision("**Conclusion: the request is DENIED.**") is False
      and _request_decision("Therefore, the request cannot be granted.") is False
      and _request_decision("**Final Answer:** The request is granted.") is True)
check("request grader gives no credit to an unfinished, conditional trace",
      _request_decision("Test 1 passes, so it could be granted if Available allows") is None)

from ostutor.simulators.generate import generate as _generate, missing_inputs
_ho, _ = _generate(210, seed=7, regime="large", holdout=True)
_miss = [(r["verify"]["kind"], missing_inputs(r)) for r in _ho if missing_inputs(r)]
check("OOD reframing keeps every input the question needs (Available, requests)",
      not _miss and all(r.get("holdout_framing") for r in _ho), str(_miss[:3]))
_bad_q = dict(verify=dict(kind="freespace", holes=[100, 200], reqs=[50, 60], policy="FIRST"),
              problem="Free partitions `[100, 200]` KB.\n\nApply FIRST-fit.")
check("missing-input detector catches a question without its requests",
      missing_inputs(_bad_q) == ["reqs"])

print("\n-- v3.0: explicit decisions, student wording, formulas, clarification --")
from ostutor.simulators import generate as _G
import random as _rnd
_sr = render_solution(dict(kind="scheduling", algo="SRTF", quantum=2,
                           procs=[["P1", 0, 8, 1], ["P2", 1, 4, 1], ["P3", 2, 9, 1], ["P4", 3, 5, 1]]))
check("SRTF decisions are written as comparisons",
      "t=1: P2 arrives; ready P2(4) < P1(7) -> PREEMPT P1, run P2" in _sr, _sr[:600])
check("every schedule states its rule", "_Rule: at every arrival and completion" in _sr)
check("HRRN textbook ratios", "P2 waited 8 - 1 = 7, (7 + 4) / 4 = 2.75" in render_solution(
    dict(kind="scheduling", algo="HRRN", quantum=2,
         procs=[["P1", 0, 8, 1], ["P2", 1, 4, 1], ["P3", 2, 9, 1], ["P4", 3, 5, 1]])))
_ss = render_solution(dict(kind="disk", reqs=[98, 183, 37, 122, 14, 124, 65, 67], head=53,
                           policy="SSTF", size=200, direction="up"))
check("SSTF writes the distance comparison", "12 < 16 -> 65" in _ss, _ss[:400])
_bad = [(k, i) for k in _G.FORMULA_KINDS for i in range(60)
        if not grade((r := _G.gen_formula(k, _rnd.Random(i))), r["solution"])["final_correct"]]
check("every formula kind: reference solution grades correct", not _bad, str(_bad[:3]))
_cl = _G.gen_clarify(_rnd.Random(0))
check("clarification asks and gives no answer", grade(_cl, _cl["solution"])["final_correct"]
      and "**Answer:" not in _cl["solution"])
check("clarify grader: a solved answer to an unsolvable question is wrong",
      not grade(_cl, "**Answer: 42**")["final_correct"])
_us = [r for r in (_G.gen_banker(_rnd.Random(i)) for i in range(80)) if not r["answer"]["safe"]]
check("UNSAFE Banker's states are generated and graded", bool(_us) and all(
    grade(r, r["solution"])["final_correct"] for r in _us))
_st = [_G.gen_scheduling(_rnd.Random(i)) for i in range(200)]
check("student-worded problems carry every input",
      all(not missing_inputs(r) for r in _st) and any("ask" in r["verify"] for r in _st))
check("no duplicate process names", all(
    len(set(p[0] for p in r["verify"]["procs"])) == len(r["verify"]["procs"]) for r in _st))
check("grader reads the quantity's own result, not the last number on the line",
      _answer_number("**Answer: average waiting time = 6.5, average turnaround time = 13.0**",
                     "average waiting") == 6.5
      and _answer_number("Average waiting time = 48 / 5 = **9.6**", "average waiting") == 9.6)

from ostutor.select import waterfill_weighted as _wfw
from ostutor.config import FAMILY_WEIGHTS as _FW
_a = _wfw({k: 4000 for k in _FW}, 8000, _FW)
check("weighted family allocation follows the weights",
      all(abs(_a[k] / 8000 - w) < 0.01 for k, w in _FW.items()), str(_a))
check("weighted allocation redistributes what a scarce family cannot supply",
      _wfw({"a": 10, "b": 1000}, 100, {"a": 0.5, "b": 0.5}) == {"a": 10, "b": 90})
check("weighted allocation never exceeds supply",
      _wfw({"a": 10, "b": 20}, 100, {"a": 0.5, "b": 0.5}) == {"a": 10, "b": 20})

from ostutor.gates import run_gates as _rg
_clar = dict(id="c1", category="procedural", subcategory="clarify_fit_reqs", mode="solve",
             domain="os", source="simulators/own", license="mit", commercial_ok=True,
             lineage={}, n_chars=10, quality=0.5, n_tokens=50, text="x",
             messages=[dict(role="system", content="s"), dict(role="user", content="q"),
                       dict(role="assistant", content="Which request sizes are they?")])
_passed, _res, _ = _rg([_clar], dict(ok=True), {}, 1, 1)
check("clarification rows are exempt from the visible-steps defect gate",
      next(r for r in _res if r["gate"] == "defect_rate")["passed"],
      str([r["gate"] for r in _res if not r["passed"]][:3]))

from ostutor.theory_filter import accept_theory as _at, accept_tutor as _atu, sanitise as _san
check("emoji and sycophantic openers are stripped from self-distilled answers",
      _san("Great question! \U0001F600 Paging **works** like this.") == "Paging **works** like this.",
      repr(_san("Great question! \U0001F600 Paging **works** like this.")))
check("an answer asserting a misconception is rejected",
      _at(dict(answer="LRU suffers from Belady's anomaly. " * 12, finish_reason="stop"))[0] is None)
check("a correct answer about the same topic is kept",
      _at(dict(answer="FIFO can suffer from Belady's anomaly; LRU cannot, because it is a "
                      "stack algorithm. " * 4, finish_reason="stop"))[0] is not None)
check("a tutoring reply that reveals the answer is rejected",
      _atu(dict(answer="The average waiting time is 6.5, do you see why?" * 3,
                finish_reason="stop", right=6.5))[0] is None)
check("a tutoring reply that affirms a wrong attempt is rejected",
      _atu(dict(answer="Yes, that looks right. What did you get for the next one? " * 3,
                finish_reason="stop", right=9.0))[0] is None)

# -- v3.0 opener sanitisation: four defects found by auditing 700 real answers -----
_body = "Body text that is definitely long enough to pass the length floor. " * 4
check("stacked openers are all removed",
      _san("Absolutely! Let's break down the difference between X and Y.\n\n### Heading\n\n"
           + _body).startswith("### Heading"),
      repr(_san("Absolutely! Let's break down the difference.\n\n### Heading\n\n" + _body)[:60]))
check("an opener never leaves a dangling dash",
      _san("Great question - **copy-on-write** is the idea. " + _body)
      .startswith("**Copy-on-write** is the idea."),
      repr(_san("Great question - **copy-on-write** is the idea. " + _body)[:60]))
check("a leading horizontal rule and its blank line are removed",
      _san("---\n\n### What is Fragmentation?\n\n" + _body).startswith("### What is"),
      repr(_san("---\n\n### What is Fragmentation?\n\n" + _body)[:40]))
# The colon here INTRODUCES content; cutting at it used to leave "**what read() does**."
_colon = ("Great question! Let's break down system calls and walk through an example: "
          "**what happens when a program calls read()**.\n\n" + _body)
check("an opener whose colon introduces content is left intact",
      _san(_colon).startswith("Let's break down system calls"), repr(_san(_colon)[:60]))
# A mid-sentence opener must not be cut either: "...down **simply**, like you're new"
_mid = "Let's break down\n**what a system call is** and why it matters.\n\n" + _body
check("an opener running onto the next line is left intact",
      _san(_mid).startswith("Let's break down"), repr(_san(_mid)[:40]))
from ostutor.theory_filter import fact_flags as _ff
# A large quantum degenerates RR to FCFS (convoy effect), it does not starve anyone.
# The claim straddles two markdown bullet lines, so a per-sentence scan misses it.
check("a misconception split across two bullet lines is caught",
      [n for n, _ in _ff("- **Large quantum**:\n- Less preemption, but may cause "
                         "starvation of short processes.")] == ["rr_large_q_starves"])
check("a hedge does not excuse that claim",
      bool(_ff("A large quantum may cause starvation.")))
check("the correct convoy-effect statement is not flagged",
      not _ff("A large time quantum makes Round Robin behave like FCFS, so short jobs "
              "wait behind long ones; no process starves, as each is served in bounded time."))
check("starvation attributed to the right algorithm is not flagged",
      not _ff("Priority scheduling can cause starvation of low-priority processes; "
              "aging fixes it."))
# The question template carries a tag saying WHAT it asks for. v3.0.0 discarded it,
# so rows whose wording said only "draw the Gantt chart" still answered with both
# averages - the dataset teaching the model to answer a different question.
import random as _rnd
import re as _re2
from ostutor.simulators.generate import gen_scheduling as _gs
_mismatch = _over = 0
for _i in range(400):
    _r = _gs(_rnd.Random(9_000 + _i), "normal")
    _p = _r["problem"].lower()
    _a = [l for l in _r["solution"].splitlines() if l.strip().startswith("**Answer")][-1].lower()
    _chart_only = bool(_re2.search(r"gantt|execution order", _p)) and not _re2.search(
        r"waiting|turnaround|completion|average", _p)
    if _chart_only and _re2.search(r"waiting|turnaround", _a):
        _mismatch += 1
    if "turnaround" in _a and "turnaround" not in _p and "both" not in _p \
            and "averages" not in _p:
        _over += 1
check("a chart-only question is answered with the chart, not with averages",
      _mismatch == 0, f"{_mismatch}/400 rows answered a different question")
check("no scheduling answer reports a quantity the question never asked for",
      _over == 0, f"{_over}/400 rows over-answered")

# Unweighted farthest-point selection over the whole tutoring pool took 912 MathDial
# rows and 26 OS rows, because the self-distilled OS rows are mutually similar and
# lose on spread. Tutoring is now allocated by domain first.
import numpy as _np2
from ostutor.select import _subcat_cap as _cap, domain_pick as _dp


def _pool(n_math, n_os):
    return ([dict(domain="math", subcategory="mathdial_dialogue")] * n_math
            + [dict(domain="os", subcategory="os_scheduling")] * n_os)


_rows2 = _pool(1000, 700)
_e = _np2.random.RandomState(0).rand(len(_rows2), 8).astype("float32")
_q2 = _np2.ones(len(_rows2), dtype="float32")
_, _alloc = _dp(_rows2, _e, _q2, 960, {"os": 0.60, "math": 0.40})
check("tutoring is allocated by domain, not by embedding spread",
      _alloc == {"math": 384, "os": 576}, str(_alloc))
_rows3 = _pool(1000, 200)
_e3 = _np2.random.RandomState(1).rand(len(_rows3), 8).astype("float32")
_, _alloc3 = _dp(_rows3, _e3, _np2.ones(len(_rows3), dtype="float32"), 960,
                 {"os": 0.60, "math": 0.40})
check("a short domain redistributes its shortfall, still filling the quota",
      _alloc3 == {"math": 760, "os": 200} and sum(_alloc3.values()) == 960, str(_alloc3))
# The cap used to be refilled from the source it had just capped.
_capped, _per, _ = _cap(_pool(900, 100), list(range(1000)), 500)
check("the subcategory cap is not backfilled from the source it capped",
      _per["os_scheduling"] == 100 and _per["mathdial_dialogue"] == 400, str(_per))

# A row's TARGET and the SYSTEM PROMPT it is rendered under must not contradict each
# other. Two measured failures came from exactly that: the tutor prompt said "do not
# reveal the answer UNTIL they have attempted it" when every example was a student who
# had attempted it, and the solve prompt ordered "State the final answer last" while
# 295 clarification rows teach the model to ask instead of answering. The second cost
# 0/3 on the hand-written clarification items until the prompt stated the exception.
from ostutor.config import SYSTEM_PROMPTS as _SP
_solve = _SP[("solve", "os")].lower()
check("the solve prompt states the missing-input exception the clarify rows teach",
      ("missing" in _solve or "not state" in _solve) and "ask" in _solve,
      repr(_SP[("solve", "os")][-120:]))
_tutor = _SP[("tutor", "os")].lower()
check("the tutor prompt does not license revealing the answer after an attempt",
      "until they have attempted" not in _tutor and "never state" in _tutor,
      repr(_SP[("tutor", "os")][-120:]))

# v3.0 OS tutoring is ONE exchange: the student states the problem and their wrong
# attempt, the tutor diagnoses it and asks a question. A "< 4 messages" rule written
# for v2's multi-turn template dialogues discarded all 1,508 of them, leaving an OS
# tutor whose entire tutoring category was maths.
from ostutor.clean import clean_records as _cr


def _tut(msgs):
    return dict(category="tutoring", subcategory="os_scheduling", mode="tutor",
                domain="os", source="simulators/own", license="mit", commercial_ok=True,
                lineage={}, messages=msgs)


_one_exchange = _tut([
    dict(role="user", content="Processes P1 (0, 5), P2 (1, 3) with SRTF. My attempt: I "
                              "used shortest job first and got average waiting time = 2.5. "
                              "Is that right?"),
    dict(role="assistant", content="Your method is the issue rather than the arithmetic. "
                                   "SRTF re-checks the remaining time whenever a process "
                                   "arrives, so what happens at t=1 when P2 arrives and "
                                   "P1 still has 4 ms left?")])
check("a single-exchange tutoring row survives cleaning",
      len(_cr([_one_exchange])) == 1, "the OS tutoring category would be empty")
check("a tutoring row with no teacher turn is still dropped",
      _cr([_tut([dict(role="user", content="Is my answer of 2.5 right for this SRTF "
                                           "problem with P1 and P2?")])]) == [])

# hex(2604) is "0xa2c"; an item may equally write "0x0A2C". Comparing the formatted
# string instead of the value failed the procedural_inputs_complete release gate.
from ostutor.simulators.generate import missing_inputs as _mi
_hexrec = dict(problem="1 KB pages; the page table is [3, 7, 2, 9, 0]. What is the "
                       "physical address for virtual address 0x0A2C?",
               verify=dict(kind="translate", logical=2604, page_size=1024,
                           table=[3, 7, 2, 9, 0], hex=True))
check("a hex address in any letter case counts as stated", _mi(_hexrec) == [],
      str(_mi(_hexrec)))
check("a translate question with no address is still caught",
      "logical" in _mi(dict(problem="1 KB pages; the page table is [3, 7, 2, 9, 0]. "
                                    "What is the physical address?",
                            verify=_hexrec["verify"])))

from ostutor.theory_filter import _reveals as _rev
# A bare digit match discarded good Socratic replies: the correct fault count also
# appeared as a row index in the trace table the tutor drew.
check("a trace-table row index is not read as the revealed answer",
      not _rev("|11 | 1 | [1, 2, 3] | Hit already in frame |", 11))
check("a restated input count is not read as the revealed answer",
      not _rev("There are 3 processes in the table. Which does SRTF pick first?", 3))
check("an asserted final answer is still caught",
      _rev("Average waiting time = 44 / 5 = **8.8**", 8.8))
check("an answer stated with its unit is still caught",
      _rev("Your figure should be 12 ms, not 14.", 12))
check("integer and decimal forms of the answer are both caught",
      _rev("The total comes to **9.0** if you redo it.", 9))
check("sanitise never strips the affirmation the tutor filter checks for",
      _atu(dict(answer="Yes! " + "You have it right, well done. Shall we try another? " * 3,
                finish_reason="stop", right=9.0))[1] == "affirms a wrong answer")

print("\n" + ("ALL TESTS PASSED" if not FAILED else f"{len(FAILED)} FAILED: {FAILED}"))
sys.exit(1 if FAILED else 0)
