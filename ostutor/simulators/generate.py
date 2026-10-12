"""Generate simulator-verified OS problems with auditable worked solutions.

Design rules, each of which exists for a MEASURED reason:

  VISIBLE STEPS, NOT <think>. The base model is non-thinking and the worked steps
  ARE the deliverable for a tutor. Hidden reasoning cannot be simulator-verified,
  cannot be shown to a student, and forces non-greedy decoding.

  PROSE DIVERSITY, NOT JUST PARAMETER RANDOMISATION. The first version of this
  module varied only the numbers: same opening sentence, same table, same
  question. Measured pairwise cosine between two "different" FCFS problems was
  0.997 against a 0.93 dedup threshold, and the pipeline collapsed 5,394
  generated rows to 22 - one per topic. Parameter randomisation is not diversity.
  Framing, entity naming, data presentation and the question asked are now varied
  independently (see prose.py), which multiplies out to thousands of genuinely
  distinct surface forms over identical verified computations.

  EVERY ANSWER IS RE-VERIFIED. After rendering, the answer is checked against the
  simulator. A renderer bug that silently corrupts a target is exactly the failure
  this project cannot afford.

  NON-UNIQUE ANSWERS ARE HANDLED. Banker's safe sequences are not unique, so the
  record carries a validator rather than a single string answer key.

  EVERY INTERMEDIATE VALUE IS WRITTEN (v2.1). Error analysis of the first
  fine-tune found that the model followed every step of the procedure but slipped
  on arithmetic the v2.0 solutions did in one jump ("9 x 1024 + 118 = 9334" became
  9374), lost track of long traces (the scheduling trace was also CUT at 22 events),
  and made choices the solution never justified (worst-fit hole, SCAN direction).
  Solutions now show products, differences and running sums, the ready queue or
  policy state at every decision, and the candidate list behind every choice.

  SOLUTIONS RENDER FROM PARAMETERS ALONE. `render_solution(verify)` rebuilds the
  worked solution from the stored parameters, so existing problems can be
  re-rendered without changing a byte of the problem text (and therefore without
  changing fingerprints, decontamination or the evaluation suites).
"""
import random
import re

from . import clarify, formulas, prose, student
from .banker import is_safe, need_matrix, request, verify_sequence
from .memory import (disk_schedule, fit_allocation, page_replacement, translate)
from .scheduling import ALGORITHMS, Proc

FORMULA_KINDS = formulas.KINDS


# ----------------------------------------------------------------- helpers
def _tbl(rows, headers):
    w = [max(len(str(h)), *(len(str(r[i])) for r in rows)) for i, h in enumerate(headers)]
    out = ["| " + " | ".join(str(h).ljust(w[i]) for i, h in enumerate(headers)) + " |",
           "|" + "|".join("-" * (x + 2) for x in w) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c).ljust(w[i]) for i, c in enumerate(r)) + " |")
    return "\n".join(out)


def _gantt(segs):
    top = "".join(f"| {p} " for p, _, _ in segs) + "|"
    marks = [str(segs[0][1])] + [str(e) for _, _, e in segs]
    line = ""
    for i, (p, _, _) in enumerate(segs):
        line += marks[i].ljust(len(f"| {p} "))
    return top + "\n" + line + marks[-1]


# ---------------------------------------------------------------- scheduling
# v3.0: 60% of problems are worded the way students and exam papers write them
# (student.py); the rest keep the template framings. Sizes: normal (exam-sized),
# large, and xl (long traces up to ~10k tokens, so the model has practised answers
# far longer than any exam needs).
STUDENT_P = 0.60
SIZES = dict(
    sched=dict(normal=(4, 6), large=(7, 10), xl=(12, 16)),
    banker=dict(normal=(4, 5), large=(6, 7), xl=(8, 10)),
    paging=dict(normal=(12, 20), large=(24, 32), xl=(40, 60)),
    disk=dict(normal=(6, 9), large=(11, 14), xl=(18, 28)),
    fit_holes=dict(normal=(4, 6), large=(6, 8), xl=(9, 12)),
    fit_reqs=dict(normal=(3, 5), large=(5, 7), xl=(8, 11)),
)


def _size(rng, key, regime):
    lo, hi = SIZES[key][regime]
    return rng.randint(lo, hi)


def gen_scheduling(rng, regime="normal"):
    n = _size(rng, "sched", regime)
    algo = rng.choice(["FCFS", "SJF", "SRTF", "RR", "PRIORITY", "PRIORITY_P", "HRRN"])
    spread = rng.choice([0, 1, 2, 3])
    names = prose.naming(rng, n) if rng.random() < 0.5 else [f"P{i + 1}" for i in range(n)]
    arrivals, bursts, prios, t = [], [], [], 0
    for _ in range(n):
        t += rng.randint(0, spread * 2)
        arrivals.append(t)
        bursts.append(rng.randint(1, 12 if regime != "xl" else 15))
        prios.append(rng.randint(1, 5))
    procs = [Proc(names[i], arrivals[i], bursts[i], prios[i]) for i in range(n)]
    q = rng.choice([2, 3, 4, 5])
    res = ALGORITHMS[algo]([Proc(p.pid, p.arrival, p.burst, p.priority) for p in procs],
                           quantum=q)
    verify = dict(kind="scheduling", algo=algo, quantum=q,
                  procs=[[p.pid, p.arrival, p.burst, p.priority] for p in procs])
    if rng.random() < STUDENT_P:
        problem, extra = student.sched_text(rng, names, arrivals, bursts, prios, algo, q)
        verify.update(extra)
    else:
        show_prio = algo.startswith("PRIORITY")
        sc = prose.pick_scenario(rng)
        framing = rng.choice(prose.SCHED_FRAMINGS).format(**sc)
        body = prose.present_procs(rng, names, arrivals, bursts, prios if show_prio else None)
        # The tag says WHAT the wording asks for. Discarding it (as v3.0.0 did) left
        # `ask` unset, so every template-path row answered with both averages - even
        # when the question only said "draw the Gantt chart". Answering a question
        # other than the one asked is precisely the habit this dataset must not teach.
        tag, ask = rng.choice(prose.SCHED_ASKS)
        if tag != "full":
            verify["ask"] = tag
        lead = rng.choice([f"Use **{res.algorithm}**",
                           f"They are scheduled with **{res.algorithm}**",
                           f"The scheduler uses **{res.algorithm}**",
                           f"Assume **{res.algorithm}** scheduling"])
        if algo == "RR":
            lead += f" with a time quantum of {q}"
        if show_prio:
            lead += " (a lower number means higher priority)"
        problem = framing + "\n\n" + body + "\n\n" + lead + ". " + ask
    return dict(topic=f"cpu_scheduling_{algo.lower()}", problem=problem,
                solution=render_solution(verify),
                answer=dict(avg_waiting=res.avg_waiting,
                            avg_turnaround=res.avg_turnaround),
                verify=verify)


# ------------------------------------------------------------------- banker
def _banker_state(rng, regime):
    n = _size(rng, "banker", regime)
    m = rng.randint(3, 4)
    for _ in range(300):
        maxm = [[rng.randint(0, 8) for _ in range(m)] for _ in range(n)]
        alloc = [[rng.randint(0, maxm[i][j]) for j in range(m)] for i in range(n)]
        avail = [rng.randint(1, 6) for _ in range(m)]
        safe, seq, steps = is_safe(avail, maxm, alloc)
        if safe:
            return n, m, maxm, alloc, avail, seq, steps
    return n, m, maxm, alloc, avail, seq, steps


def _banker_state_any(rng, regime, want_safe):
    n = _size(rng, "banker", regime)
    m = rng.randint(3, 4)
    for _ in range(2000):
        maxm = [[rng.randint(0, 8) for _ in range(m)] for _ in range(n)]
        alloc = [[rng.randint(0, maxm[i][j]) for j in range(m)] for i in range(n)]
        avail = [rng.randint(0 if not want_safe else 1, 6) for _ in range(m)]
        safe, seq, steps = is_safe(avail, maxm, alloc)
        if safe == want_safe:
            break
    return n, m, maxm, alloc, avail, seq, steps


def gen_banker(rng, regime="normal"):
    # v3.0: a quarter of safety problems are UNSAFE. Every v2.x safety problem was
    # safe, which teaches "the answer is always SAFE".
    n, m, maxm, alloc, avail, seq, steps = _banker_state_any(rng, regime, rng.random() < 0.75)
    names = prose.naming(rng, n) if rng.random() < 0.5 else [f"P{i}" for i in range(n)]
    verify = dict(kind="banker_safety", avail=avail, maxm=maxm, alloc=alloc, names=names)
    if rng.random() < STUDENT_P:
        problem, extra = student.banker_text(rng, verify)
        verify.update(extra)
    else:
        res = "ABCD"[:m]
        sc = prose.pick_scenario(rng)
        framing = rng.choice(prose.BANKER_FRAMINGS).format(m=m, n=n, res=", ".join(res), **sc)
        ask = rng.choice(prose.BANKER_ASKS)
        avail_txt = rng.choice([f"Available = {avail}.",
                                f"Currently available: {avail}.",
                                f"The system has {avail} instances of each type free."])
        tbl = _tbl([[names[i]] + alloc[i] + maxm[i] for i in range(n)],
                   ["P"] + [f"Alloc {c}" for c in res] + [f"Max {c}" for c in res])
        problem = f"{framing} {avail_txt}\n\n{tbl}\n\n{ask}"
    safe, seq, steps = is_safe(avail, maxm, alloc, names)
    return dict(topic="deadlock_bankers_safety", problem=problem,
                solution=render_solution(verify), answer=dict(safe=safe, sequence=seq),
                verify=verify)


def gen_banker_request(rng, regime="normal"):
    n, m, maxm, alloc, avail, _, _ = _banker_state(rng, regime)
    names = prose.naming(rng, n) if rng.random() < 0.5 else [f"P{i}" for i in range(n)]
    need = need_matrix(maxm, alloc)
    pid = rng.randrange(n)
    mode = rng.random()
    if mode < 0.15:      # exceeds Need: Test 1 must fail
        req = [need[pid][j] + (1 if j == 0 else 0) for j in range(m)]
    elif mode < 0.30:    # exceeds Available: Test 2 must fail
        req = [min(need[pid][j], avail[j] + 1) for j in range(m)]
        if all(req[j] <= avail[j] for j in range(m)):
            req = [rng.randint(0, max(need[pid][j], 0)) for j in range(m)]
    else:
        req = [rng.randint(0, max(min(need[pid][j], avail[j]), 0)) for j in range(m)]
    if not any(req):
        req[rng.randrange(m)] = 1
    granted, steps = request(avail, maxm, alloc, pid, req, names)
    verify = dict(kind="banker_request", avail=avail, maxm=maxm, alloc=alloc,
                  pid=pid, req=req, names=names)
    if rng.random() < STUDENT_P:
        problem, extra = student.banker_text(rng, verify, request_mode=True)
        verify.update(extra)
    else:
        res = "ABCD"[:m]
        sc = prose.pick_scenario(rng)
        framing = rng.choice(prose.BANKER_FRAMINGS).format(m=m, n=n, res=", ".join(res), **sc)
        tbl = _tbl([[names[i]] + alloc[i] + maxm[i] for i in range(n)],
                   ["P"] + [f"Alloc {c}" for c in res] + [f"Max {c}" for c in res])
        ask = rng.choice([
            f"Process {names[pid]} now requests {req}. Should this request be granted?",
            f"{names[pid]} issues a request for {req}. Apply the resource-request "
            f"algorithm and decide.",
            f"A request of {req} arrives from {names[pid]}. Can it be satisfied safely?",
            f"Using the resource-request algorithm, determine whether {names[pid]}'s "
            f"request for {req} can be granted."])
        problem = f"{framing} Available = {avail}.\n\n{tbl}\n\n{ask}"
    return dict(topic="deadlock_bankers_request", problem=problem,
                solution=render_solution(verify), answer=dict(granted=granted),
                verify=verify)


# ------------------------------------------------------------------ paging
def gen_paging(rng, regime="normal"):
    policy = rng.choice(["FIFO", "LRU", "OPT", "CLOCK"])
    length = _size(rng, "paging", regime)
    refs = [rng.randint(0, rng.randint(5, 9)) for _ in range(length)]
    frames = rng.randint(3, 4) if regime == "normal" else rng.randint(3, 6)
    r = page_replacement(refs, frames, policy)
    verify = dict(kind="paging", refs=refs, frames=frames, policy=policy)
    if rng.random() < STUDENT_P:
        problem, extra = student.paging_text(rng, refs, frames, policy)
        verify.update(extra)
    else:
        sc = prose.pick_scenario(rng)
        framing = rng.choice(prose.PAGING_FRAMINGS).format(**sc)
        ask = rng.choice(prose.PAGING_ASKS)
        refs_txt = rng.choice([f"`{', '.join(map(str, refs))}`",
                               "`" + " ".join(map(str, refs)) + "`"])
        frames_txt = rng.choice([f"with **{frames} frames**",
                                 f"and the process is allocated **{frames} page frames**",
                                 f"given **{frames}** available frames"])
        problem = (f"{framing}\n\n{refs_txt}\n\n{frames_txt}, using the **{policy}** "
                   f"replacement policy. {ask}")
    return dict(topic=f"page_replacement_{policy.lower()}", problem=problem,
                solution=render_solution(verify), answer=dict(faults=r["faults"]),
                verify=verify)


# -------------------------------------------------------------------- disk
def gen_disk(rng, regime="normal"):
    policy = rng.choice(["FCFS", "SSTF", "SCAN", "CSCAN", "LOOK", "CLOOK"])
    k = _size(rng, "disk", regime)
    size = rng.choice([200, 200, 250, 300, 500])
    reqs = rng.sample(range(1, size - 1), k)
    head = rng.randint(20, size - 20)
    while head in reqs:
        head += 1
    direction = rng.choice(["up", "down"]) if policy in ("SCAN", "LOOK", "CSCAN", "CLOOK") else "up"
    r = disk_schedule(reqs, head, policy, size, direction)
    verify = dict(kind="disk", reqs=reqs, head=head, policy=policy, size=size,
                  direction=direction)
    if rng.random() < STUDENT_P:
        problem, extra = student.disk_text(rng, reqs, head, policy, size, direction)
        verify.update(extra)
    else:
        sc = prose.pick_scenario(rng)
        framing = rng.choice(prose.DISK_FRAMINGS).format(
            max_cyl=size - 1, n_cyl=size, head=head, **sc)
        ask = rng.choice(prose.DISK_ASKS)
        dtxt = (f" The head is currently moving toward "
                f"{'higher' if direction == 'up' else 'lower'} cylinder numbers."
                if policy in ("SCAN", "LOOK", "CSCAN", "CLOOK") else "")
        problem = (f"{framing}\n\n`{', '.join(map(str, reqs))}`\n\n"
                   f"Using **{policy}** scheduling.{dtxt} {ask}")
    return dict(topic=f"disk_scheduling_{policy.lower()}", problem=problem,
                solution=render_solution(verify),
                answer=dict(total_head_movement=r["total_head_movement"]),
                verify=verify)


# -------------------------------------------------------------- translation
def gen_translation(rng, regime="normal"):
    page_size = 1 << rng.choice([9, 10, 11, 12, 13])
    npages = rng.randint(4, 8) if regime == "normal" else rng.randint(8, 16)
    table = [rng.randint(0, 63) for _ in range(npages)]
    la = rng.randrange(0, npages * page_size)
    r = translate(la, page_size, table)
    verify = dict(kind="translate", logical=la, page_size=page_size, table=table)
    if rng.random() < STUDENT_P:
        problem, extra = student.translate_text(rng, la, page_size, table)
        verify.update(extra)
    else:
        sc = prose.pick_scenario(rng)
        framing = rng.choice(prose.TRANSLATE_FRAMINGS).format(ps=page_size, **sc)
        ask = rng.choice(prose.TRANSLATE_ASKS).format(la=la)
        problem = (f"{framing} The page table is:\n\n"
                   f"{_tbl([[i, table[i]] for i in range(npages)], ['Page', 'Frame'])}\n\n{ask}")
    return dict(topic="address_translation", problem=problem,
                solution=render_solution(verify), answer=dict(physical=r["physical"]),
                verify=verify)


# ------------------------------------------------------------- free space
def gen_freespace(rng, regime="normal"):
    policy = rng.choice(["FIRST", "BEST", "WORST"])
    holes = [rng.randint(50, 600) for _ in range(_size(rng, "fit_holes", regime))]
    reqs = [rng.randint(40, 500) for _ in range(_size(rng, "fit_reqs", regime))]
    r = fit_allocation(holes, reqs, policy)
    verify = dict(kind="freespace", holes=holes, reqs=reqs, policy=policy)
    if rng.random() < STUDENT_P:
        problem, extra = student.fit_text(rng, holes, reqs, policy)
        verify.update(extra)
    else:
        sc = prose.pick_scenario(rng)
        framing = rng.choice(prose.FIT_FRAMINGS).format(holes=holes, **sc)
        ask = rng.choice(prose.FIT_ASKS).format(policy=policy)
        req_txt = rng.choice([f"Requests arrive for `{reqs}` KB in order.",
                              f"The following allocations are requested in sequence: `{reqs}` KB.",
                              f"Processes request `{reqs}` KB, in that order."])
        problem = f"{framing} {req_txt}\n\n{ask}"
    return dict(topic=f"contiguous_allocation_{policy.lower()}", problem=problem,
                solution=render_solution(verify), answer=dict(placement=r["placement"]),
                verify=verify)


def _running_sum(vals):
    """'23 + 19 = 42, 42 + 3 = 45, 45 + 4 = 49' - one addition per step."""
    if len(vals) == 1:
        return str(vals[0])
    acc, parts = vals[0], []
    for v in vals[1:]:
        parts.append(f"{acc} + {v} = {acc + v}")
        acc += v
    return ", ".join(parts)


def _hex_steps(value):
    """'0x2328' -> digit products, then one addition per step."""
    digits = hex(value)[2:]
    terms = []
    for i, d in enumerate(digits):
        w = 16 ** (len(digits) - 1 - i)
        terms.append((int(d, 16), w, int(d, 16) * w))
    prods = "; ".join(f"{d} x {w} = {p}" for d, w, p in terms)
    return [f"convert {hex(value)} to decimal: {prods}",
            f"sum: {_running_sum([p for _, _, p in terms])} -> {hex(value)} = {value}"]


def _banker_prep(v, lines):
    """Steps that depend on how the question stated the state (v3.0 student forms):
    TOTAL instances instead of Available, and Need given instead of Max."""
    names, m = v["names"], len(v["avail"])
    res = "ABCD"[:m]
    if v.get("total"):
        lines += ["**Step 0 - Available = Total - (sum of each Allocation column)**", ""]
        for j, r in enumerate(res):
            col = [row[j] for row in v["alloc"]]
            lines.append(f"- {r}: allocated {_running_sum(col)}; available "
                         f"{v['total'][j]} - {sum(col)} = {v['total'][j] - sum(col)}")
        lines += [f"- Available = {v['avail']}", ""]
    need = need_matrix(v["maxm"], v["alloc"])
    if v.get("given") == "need":
        lines += ["**Step 1 - Need is given directly** (Need = Max - Allocation)", ""]
        lines += [f"- {names[i]}: Need {need[i]}" for i in range(len(names))]
    else:
        lines += ["**Step 1 - compute Need = Max - Allocation, row by row** "
                  f"(resources {', '.join(res)})", ""]
        lines += [f"- {names[i]}: {v['maxm'][i]} - {v['alloc'][i]} = {need[i]}"
                  for i in range(len(names))]
    return need


def render_solution(v):
    """The worked solution for a problem, from its stored parameters alone."""
    k = v["kind"]
    if k in FORMULA_KINDS:
        return formulas.render(v)
    if k == "clarify":
        return clarify.render(v)
    ask = v.get("ask")
    if k == "scheduling":
        procs = [Proc(p, a, b, pr) for p, a, b, pr in v["procs"]]
        res = ALGORITHMS[v["algo"]](procs, quantum=v["quantum"])
        n = len(res.table)
        waits = [r["waiting"] for r in res.table]
        turns = [r["turnaround"] for r in res.table]
        lines = [f"**Algorithm: {res.algorithm}**", "", "**Step 1 - build the schedule**", "",
                 f"_{res.events[0]}_", ""]
        lines += [f"- {e}" for e in res.events[1:]]
        gantt = " ".join(f"{p}[{s}-{e}]" for p, s, e in res.gantt)
        lines += ["", f"**Step 2 - Gantt chart:** {gantt}", "",
                  "**Step 3 - per-process times** (Turnaround = Completion - Arrival; "
                  "Waiting = Turnaround - Burst)", "",
                  _tbl([[r["pid"], r["arrival"], r["burst"], r["completion"],
                         f"{r['completion']} - {r['arrival']} = {r['turnaround']}",
                         f"{r['turnaround']} - {r['burst']} = {r['waiting']}"]
                        for r in res.table],
                       ["Process", "Arrival", "Burst", "Completion", "Turnaround",
                        "Waiting"]),
                  "", "**Step 4 - averages**", "",
                  f"- Sum of waiting times: {_running_sum(waits)}",
                  f"- Average waiting time = {sum(waits)} / {n} = **{res.avg_waiting}**",
                  f"- Sum of turnaround times: {_running_sum(turns)}",
                  f"- Average turnaround time = {sum(turns)} / {n} = "
                  f"**{res.avg_turnaround}**", ""]
        last = max(res.table, key=lambda r: (r["completion"], r["pid"]))
        answer = {
            "waiting": f"average waiting time = {res.avg_waiting}",
            "turnaround": f"average turnaround time = {res.avg_turnaround}",
            "gantt": f"Gantt chart {gantt}",
            "completion": "completion times " + ", ".join(
                f"{r['pid']} = {r['completion']}" for r in res.table),
            "last": f"{last['pid']} finishes last, at t = {last['completion']}",
        }.get(ask, f"average waiting time = {res.avg_waiting}, average turnaround "
                   f"time = {res.avg_turnaround}")
        lines.append(f"**Answer: {answer}**")
        return "\n".join(lines)
    if k == "banker_safety":
        names = v["names"]
        lines = []
        _banker_prep(v, lines)
        safe, seq, steps = is_safe(v["avail"], v["maxm"], v["alloc"], names)
        lines += ["", "**Step 2 - run the safety algorithm** (scan the processes in "
                      "order; run the first one whose Need fits in Work, then add its "
                      "Allocation to Work and scan again)", "",
                  f"- Work = Available = {v['avail']}"]
        lines += [f"- {s['text']}" for s in steps if s["kind"] in ("grant", "skip")]
        if not safe:
            stuck = [nm for nm in names if nm not in seq]
            lines += ["", "**Step 3 - conclusion**", "",
                      f"No remaining process ({', '.join(stuck)}) has a Need that fits in "
                      f"Work {steps[-2]['work'] if steps[-2]['kind'] == 'skip' else ''}, so "
                      f"they can never all finish: the system is **NOT in a safe state "
                      f"(UNSAFE)**." + (f" Processes {', '.join(seq)} could finish, but "
                                        f"{', '.join(stuck)} cannot." if seq else ""),
                      "", "_Unsafe does not mean deadlocked yet: it means a deadlock is "
                          "possible if the processes request their maximum._",
                      "", "**Answer: UNSAFE, no safe sequence exists**"]
            return "\n".join(lines)
        lines += ["", "**Step 3 - conclusion**", "",
                  f"All {len(names)} processes can complete, so the system is in a "
                  f"**SAFE state**.", f"A safe sequence is **< {', '.join(seq)} >**.", "",
                  "_Safe sequences are not unique: any ordering in which each "
                  "process's Need is met by the running Work vector is equally correct._",
                  "", f"**Answer: SAFE, safe sequence < {', '.join(seq)} >**"]
        return "\n".join(lines)
    if k == "banker_request":
        lines = []
        _banker_prep(v, lines)
        granted, steps = request(v["avail"], v["maxm"], v["alloc"], v["pid"], v["req"],
                                 v.get("names"))
        lines += ["", "**Step 2 - apply the three tests of the resource-request "
                      "algorithm**", ""]
        lines += [f"- {s['text']}" for s in steps if s["kind"] != "need"]
        lines += ["", f"**Conclusion: the request is "
                      f"{'GRANTED' if granted else 'DENIED'}.**", "",
                  f"**Answer: {'GRANTED' if granted else 'DENIED'}**"]
        return "\n".join(lines)
    if k == "paging":
        r = page_replacement(v["refs"], v["frames"], v["policy"])
        order = dict(FIFO="oldest first", LRU="least recently used first",
                     OPT="frame order", CLOCK="reference bit in brackets")[r["policy"]]
        rule = dict(FIFO="on a fault with all frames full, evict the page loaded EARLIEST",
                    LRU="on a fault with all frames full, evict the page used LEAST RECENTLY",
                    OPT="on a fault with all frames full, evict the page whose NEXT USE is "
                        "FARTHEST in the future (never used again = farthest)",
                    CLOCK="on a fault with all frames full, advance the hand: a page with "
                          "bit 1 gets a second chance (bit cleared), the first page with "
                          "bit 0 is evicted; a hit sets the bit to 1")[r["policy"]]
        lines = [f"**Policy: {r['policy']}, {v['frames']} frames** (all empty at the start)",
                 "", f"_Rule: {rule}._", "",
                 f"| # | Ref | Result | Evicted | Why | Frames ({order}) | Faults |",
                 "|---|-----|--------|---------|-----|--------|--------|"]
        for st in r["steps"]:
            lines.append(f"| {st['t'] + 1} | {st['page']} | "
                         f"{'hit' if st['hit'] else 'miss'} | "
                         f"{st['victim'] if st['victim'] is not None else '-'} | "
                         f"{st['why']} | {st['state']} | {st['faults_so_far']} |")
        n = len(v["refs"])
        lines += ["", f"**Total page faults = {r['faults']}** "
                      f"(hits = {n} - {r['faults']} = {r['hits']}, "
                      f"hit ratio = {r['hits']} / {n} = {r['hit_ratio']}, "
                      f"fault ratio = {r['faults']} / {n} = {round(r['faults'] / n, 4)})"]
        final = " ".join(map(str, r["steps"][-1]["frames"]))
        answer = {"hits": f"hits = {r['hits']}, hit ratio = {r['hit_ratio']}",
                  "ratio": f"hit ratio = {r['hit_ratio']}, fault ratio = "
                           f"{round(r['faults'] / n, 4)}",
                  "frames": f"page faults = {r['faults']}; final frames: {final}"}.get(
            ask, f"page faults = {r['faults']}")
        lines += ["", f"**Answer: {answer}**"]
        return "\n".join(lines)
    if k == "disk":
        r = disk_schedule(v["reqs"], v["head"], v["policy"], v["size"], v["direction"])
        lines = [f"**Policy: {r['policy']}**", ""]
        if v.get("assumed"):
            lines.append("- direction: not given in the question -> assume the head moves UP, "
                         "towards higher cylinder numbers (the usual textbook convention)")
        if v.get("prev") is not None:
            p, h = v["prev"], v["head"]
            lines.append(f"- direction: previous request {p} {'<' if p < h else '>'} head {h}, "
                         f"so the head is moving {'UP' if p < h else 'DOWN'}")
        lines += [f"- {s}" for s in r["steps"]]
        total, k_req = r["total_head_movement"], len(v["reqs"])
        lines += ["", f"**Service order:** {' -> '.join(map(str, r['order']))}",
                  f"**Total head movement = {total} cylinders**",
                  f"- Average seek length = {total} / {k_req} = {round(total / k_req, 2)}"]
        if r["policy"] in ("CSCAN", "CLOOK"):
            path = [v["head"]] + r["order"]
            jump = next((abs(b - a) for a, b in zip(path, path[1:])
                         if (b < a) == (v["direction"] == "up") and abs(b - a) > 0), 0)
            if jump:
                lines.append(f"- _Convention: this total counts the return jump of {jump} "
                             f"cylinders. If your course excludes the jump, the total is "
                             f"{total} - {jump} = {total - jump}._")
        if v.get("assumed"):
            alt = disk_schedule(v["reqs"], v["head"], v["policy"], v["size"], "down")
            lines.append(f"- _If the head were moving DOWN instead: order "
                         f"{' -> '.join(map(str, alt['order']))}, total "
                         f"{alt['total_head_movement']} cylinders._")
        answer = f"total head movement = {total} cylinders"
        if ask == "avg":
            answer += f", average seek length = {round(total / k_req, 2)}"
        if ask == "order":
            answer = f"order {' -> '.join(map(str, r['order']))}; " + answer
        lines += ["", f"**Answer: {answer}**"]
        return "\n".join(lines)
    if k == "translate":
        r = translate(v["logical"], v["page_size"], v["table"])
        lines = ["**Step-by-step translation**", ""]
        if v.get("hex"):
            lines += [f"- {s}" for s in _hex_steps(v["logical"])]
        lines += [f"- {s}" for s in r["steps"]]
        phys = r["physical"]
        lines += ["", f"**Physical address = {phys}**"]
        if v.get("hex") and phys is not None:
            lines.append(f"- in hexadecimal: {phys} = {hex(phys)}")
        lines += ["", f"**Answer: physical address = {phys}"
                      + (f" ({hex(phys)})" if v.get("hex") and phys is not None else "") + "**"]
        return "\n".join(lines)
    if k == "freespace":
        r = fit_allocation(v["holes"], v["reqs"], v["policy"])
        rule = dict(FIRST="scan holes in order and take the FIRST that is large enough",
                    BEST="take the SMALLEST hole that is large enough",
                    WORST="take the LARGEST hole that is large enough")[v["policy"]]
        lines = [f"**Policy: {v['policy']}-fit**", "", f"_Rule: {rule}; the leftover "
                 f"stays as a smaller hole. A request that fits nowhere must wait._", "",
                 "- holes (free KB, numbered in order): "
                 + ", ".join(f"hole {i + 1}={h}" for i, h in enumerate(v["holes"]))]
        lines += [f"- {s}" for s in r["steps"]]
        place = "; ".join(f"{q} KB -> {'WAIT' if h is None else f'hole {h}'}"
                          for q, h in zip(v["reqs"], r["placement"]))
        waits = [q for q, h in zip(v["reqs"], r["placement"]) if h is None]
        lines += ["", f"**Placement:** {place}",
                  f"**Remaining free space per hole:** {r['remaining']}",
                  f"- Sum of free space: {_running_sum(r['remaining'])}",
                  f"**Total external fragmentation = {r['external_fragmentation']} KB**"]
        answer = {"wait": ("cannot be allocated: " + ", ".join(f"{q} KB" for q in waits))
                          if waits else "every process is allocated",
                  "frag": f"remaining {r['remaining']}, total free "
                          f"{r['external_fragmentation']} KB"}.get(ask, place)
        lines += ["", f"**Answer: {answer}**"]
        return "\n".join(lines)
    raise ValueError(k)


GENERATORS = [gen_scheduling, gen_banker, gen_banker_request, gen_paging,
              gen_disk, gen_translation, gen_freespace]


def holdout_data_sentence(v, rng):
    """Inputs that live in the first paragraph (which the reframing replaces)."""
    if v["kind"] in ("banker_safety", "banker_request"):
        return " " + rng.choice(prose.HOLDOUT_AVAIL).format(avail=v["avail"])
    if v["kind"] == "freespace":
        return " " + rng.choice(prose.HOLDOUT_REQS).format(reqs=v["reqs"])
    return ""


def missing_inputs(rec):
    """Input values of a procedural problem that its question text never states.
    A non-empty result means the question is unsolvable as written.

    v3.0: checks every NUMBER as a standalone token, so the student wordings
    ("100 KB, 500 KB", "(3,3,2)", "A=3, B=3") are recognised; accepts TOTAL
    instances in place of Available, and a hex logical address."""
    v, p = rec["verify"], rec["problem"]
    toks = set(re.findall(r"(?<![\d.])\d+(?![\d])", p))
    # Hex literals, as VALUES. Comparing hex(v["logical"]) as a string required the
    # exact formatting hex() produces: a hand-written item writing the same address
    # as 0x0A2C instead of 0xa2c was reported as missing its logical address, and
    # failed the release gate.
    hexes = {int(h, 16) for h in re.findall(r"0[xX]([0-9a-fA-F]+)", p)}

    def has(val):
        vals = val if isinstance(val, list) else [val]
        return all(str(x) in toks for x in vals)

    need = {"freespace": ["holes", "reqs"], "banker_safety": ["avail"],
            "banker_request": ["avail", "req"], "paging": ["frames", "refs"],
            "translate": ["logical", "page_size"], "disk": ["head", "reqs"]}
    out = []
    for key in need.get(v["kind"], []):
        if key == "avail" and v.get("total") and has(v["total"]):
            continue
        if key == "logical" and v["logical"] in hexes:
            continue
        if key == "page_size" and not has(v[key]) and \
                re.search(rf"(?<!\d){v[key] // 1024}\s*KB", p):
            continue
        if not has(v[key]):
            out.append(key)
    if v["kind"] == "scheduling" and v.get("algo") == "RR" and str(v["quantum"]) not in toks:
        out.append("quantum")
    return out


def _reframe_holdout(rec, rng):
    """Re-render the PROBLEM with framings reserved for the OOD split.

    The computation, the solution and the verified answer are untouched - only the
    surface form changes. A model that learned the procedure is unaffected; a model
    that memorised the training templates is not."""
    body = rec["problem"].split("\n\n", 1)
    if len(body) < 2:
        return rec
    kind = rec["verify"]["kind"]
    bank = dict(scheduling="sched_framings", paging="paging_framings",
                disk="disk_framings", banker_safety="banker_framings",
                banker_request="banker_framings", translate="translate_framings",
                freespace="fit_framings").get(kind)
    if not bank:
        return rec
    tmpl = rng.choice(prose.HOLDOUT[bank])
    try:
        sc = prose.pick_scenario(rng)
        head = rec["verify"].get("head", 0); size = rec["verify"].get("size", 200)
        lead = tmpl.format(head=head, n_cyl=size, max_cyl=size - 1,
                           m=len(rec["verify"].get("avail", []) or [1]),
                           n=len(rec["verify"].get("alloc", []) or [1]),
                           res=", ".join("ABCD"[:len(rec["verify"].get("avail", []) or [1])]),
                           ps=rec["verify"].get("page_size", 4096),
                           holes=rec["verify"].get("holes", []), **sc)
    except Exception:
        return rec
    rec = dict(rec)
    rec["problem"] = lead + holdout_data_sentence(rec["verify"], rng) + "\n\n" + body[1]
    rec["holdout_framing"] = True
    return rec


# ------------------------------------------------------------------ verify
def reverify(rec):
    """Re-run the simulator and confirm the rendered answer still matches."""
    v, a = rec["verify"], rec["answer"]
    k = v["kind"]
    if k == "scheduling":
        procs = [Proc(p, ar, b, pr) for p, ar, b, pr in v["procs"]]
        r = ALGORITHMS[v["algo"]](procs, quantum=v["quantum"])
        return r.avg_waiting == a["avg_waiting"] and r.avg_turnaround == a["avg_turnaround"]
    if k == "banker_safety":
        safe, _, _ = is_safe(v["avail"], v["maxm"], v["alloc"], v.get("names"))
        if not a.get("safe", True):
            return not safe
        ok, _ = verify_sequence(a["sequence"], v["avail"], v["maxm"], v["alloc"],
                                v.get("names"))
        return ok and safe
    if k == "banker_request":
        g, _ = request(v["avail"], v["maxm"], v["alloc"], v["pid"], v["req"], v.get("names"))
        return g == a["granted"]
    if k == "paging":
        return page_replacement(v["refs"], v["frames"], v["policy"])["faults"] == a["faults"]
    if k == "disk":
        return disk_schedule(v["reqs"], v["head"], v["policy"], v["size"],
                             v["direction"])["total_head_movement"] == a["total_head_movement"]
    if k == "translate":
        return translate(v["logical"], v["page_size"], v["table"])["physical"] == a["physical"]
    if k == "freespace":
        return fit_allocation(v["holes"], v["reqs"], v["policy"])["placement"] == a["placement"]
    if k in FORMULA_KINDS:
        # answers are exact Fractions; stored as strings so the file is JSON and
        # the value is not rounded
        return {kk: str(x) for kk, x in formulas.expected(v).items()} == a
    if k == "clarify":
        return "**Answer:" not in rec["solution"] and v["need"] in rec["solution"]
    return False


def gen_formula(kind, rng):
    v, problem = formulas.gen(kind, rng)
    return dict(topic=f"formula_{kind}", problem=problem, solution=render_solution(v),
                answer={kk: str(x) for kk, x in formulas.expected(v).items()}, verify=v)


def gen_clarify(rng):
    v, problem = clarify.gen(rng)
    return dict(topic=f"clarify_{v['missing']}", problem=problem,
                solution=render_solution(v), answer={}, verify=v)


def generate(n, seed=42, regime="normal", holdout=False):
    """holdout=True reframes TEMPLATE-worded problems with held-out framings. Student
    wordings keep their data in the first paragraph, which the reframing replaces,
    so holdout generation uses template wording only."""
    global STUDENT_P
    saved = STUDENT_P
    if holdout:
        STUDENT_P = 0.0
    try:
        return _generate(n, seed, regime, holdout)
    finally:
        STUDENT_P = saved


def _generate(n, seed, regime, holdout):
    rng = random.Random(seed)
    out, rejected = [], 0
    while len(out) < n:
        g = rng.choice(GENERATORS)
        s = rng.randrange(1 << 30)
        rec = g(random.Random(s), regime)
        if holdout:
            rec = _reframe_holdout(rec, random.Random(s ^ 0x5EED))
        rec.update(seed=s, regime=regime)
        if not reverify(rec):
            rejected += 1
            continue
        rec["verified"] = True
        out.append(rec)
    return out, rejected
