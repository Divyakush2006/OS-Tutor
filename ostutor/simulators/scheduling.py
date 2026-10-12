"""CPU scheduling simulators with ARRIVAL TIMES.

This is the single largest gap in every available OS teaching resource. The OSTEP
homework scheduler supports FIFO/SJF/RR only and assumes all jobs arrive at t=0
(`grep -c arriv scheduler.py` returns 0), yet essentially every exam question
gives arrival times and asks for a Gantt chart. Preemptive scheduling with
staggered arrivals is also precisely where LLMs fail hardest, because it is a
state machine unrolled over time rather than a formula.

Every algorithm returns an auditable trace: the Gantt segments, the ready queue
at each decision point, and per-process completion/turnaround/waiting times.
The final numbers are derived from the trace, never computed separately, so a
consistent trace and a consistent answer cannot disagree.

v3.0 - EVERY DECISION IS WRITTEN AS A COMPARISON. Testing v2.2 through the chat UI
on free-worded textbook questions, the model wrote "ready P1(7) P2(4) -> keep P1
(7 > 4)": it compared correctly and still chose wrong, because v2.2 traces listed
the ready set pre-sorted and named the choice - the rule "smallest first" was
never written down. Each trace now opens with the algorithm's RULE, and every
decision is an explicit ordered chain ("P2(4) < P1(7) -> PREEMPT P1, run P2"),
so the choice follows from text the model has just written.
"""
from dataclasses import dataclass
from fractions import Fraction


@dataclass
class Proc:
    pid: str
    arrival: int
    burst: int
    priority: int = 0
    # filled in by the simulator
    start: int = -1
    completion: int = -1
    remaining: int = 0

    def __post_init__(self):
        self.remaining = self.burst


@dataclass
class Result:
    algorithm: str
    gantt: list           # [(pid, start, end)]
    events: list          # human-readable decision log (first line: the rule)
    table: list           # per-process dicts
    avg_waiting: float
    avg_turnaround: float
    quantum: int = 0

    def check(self, procs):
        """Internal consistency. A trace that disagrees with its own numbers is a
        bug, and must never reach the dataset."""
        busy = sum(e - s for _, s, e in self.gantt)
        assert busy == sum(p.burst for p in procs), "gantt busy time != total burst"
        for (_, s1, e1), (_, s2, _) in zip(self.gantt, self.gantt[1:]):
            assert e1 <= s2, "overlapping gantt segments"
        seen = [g[0] for g in self.gantt]
        for p in procs:
            assert p.pid in seen, f"{p.pid} never scheduled"
            assert p.completion >= p.arrival + p.burst, f"{p.pid} completed too early"
        return True


RULES = {
    "FCFS": "Rule: run processes in order of ARRIVAL; each runs to completion.",
    "SJF": "Rule: whenever the CPU is free, run the ready process with the SHORTEST "
           "BURST to completion (ties: earlier arrival, then name).",
    "SRTF": "Rule: at every arrival and completion, run the ready process with the "
            "SHORTEST REMAINING time; preempt the running process if a shorter one "
            "is ready (ties: earlier arrival, then name).",
    "RR": "Rule: run the process at the HEAD of the queue for up to q = {q} units; "
          "processes arriving during a slice join the tail BEFORE the preempted "
          "process goes back to the tail.",
    "PRIORITY": "Rule: whenever the CPU is free, run the ready process with the "
                "HIGHEST priority (LOWEST number) to completion (ties: earlier "
                "arrival, then name).",
    "PRIORITY_P": "Rule: at every arrival and completion, run the ready process with "
                  "the HIGHEST priority (LOWEST number); preempt the running process "
                  "if a higher-priority one is ready (ties: earlier arrival, then name).",
    "HRRN": "Rule: whenever the CPU is free, compute each ready process's response "
            "ratio = (waiting + burst) / burst and run the HIGHEST ratio to "
            "completion (ties: earlier arrival, then name).",
}


def _finish(name, procs, gantt, events, quantum=0):
    table, tw, tt = [], 0, 0
    for p in sorted(procs, key=lambda x: x.pid):
        turn = p.completion - p.arrival
        wait = turn - p.burst
        resp = p.start - p.arrival
        tw += wait
        tt += turn
        table.append(dict(pid=p.pid, arrival=p.arrival, burst=p.burst,
                          priority=p.priority, start=p.start,
                          completion=p.completion, turnaround=turn,
                          waiting=wait, response=resp))
    r = Result(name, gantt, events, table,
               round(tw / len(procs), 2), round(tt / len(procs), 2), quantum)
    r.check(procs)
    return r


def _merge(gantt):
    """Collapse adjacent identical-pid slices into one Gantt segment."""
    out = []
    for pid, s, e in gantt:
        if out and out[-1][0] == pid and out[-1][2] == s:
            out[-1] = (pid, out[-1][1], e)
        else:
            out.append((pid, s, e))
    return out


def _chain(items, key, fmt, desc=False):
    """Order candidates by the rule and write the order as explicit comparisons:
    'P2(4) < P4(5) < P1(7)'. Returns (winner, text). Ties are written '=' and
    broken by earlier arrival, then name."""
    sign = -1 if desc else 1
    s = sorted(items, key=lambda x: (sign * key(x), x.arrival, x.pid))
    op = " > " if desc else " < "
    text = fmt(s[0])
    for a, b in zip(s, s[1:]):
        text += (" = " if key(a) == key(b) else op) + fmt(b)
    if len(s) > 1 and key(s[0]) == key(s[1]):
        text += " (tie -> earlier arrival, then name)"
    return s[0], text


def _idle(t, procs):
    nxt = min(p.arrival for p in procs if p.remaining > 0)
    return nxt, f"t={t}: no process has arrived -> CPU idle until t={nxt}"


def fcfs(procs):
    procs = sorted([Proc(p.pid, p.arrival, p.burst, p.priority) for p in procs],
                   key=lambda p: (p.arrival, p.pid))
    t, gantt, ev = 0, [], [RULES["FCFS"],
                           "arrival order: " + ", ".join(f"{p.pid}(t={p.arrival})" for p in procs)]
    for p in procs:
        if t < p.arrival:
            ev.append(f"t={t}: no process has arrived -> CPU idle until t={p.arrival}")
            t = p.arrival
        p.start = t
        ev.append(f"t={t}: {p.pid} runs (arrived t={p.arrival}, burst {p.burst}) "
                  f"-> completes at {t} + {p.burst} = {t + p.burst}")
        t += p.burst
        p.completion = t
        p.remaining = 0
        gantt.append((p.pid, p.start, t))
    return _finish("FCFS", procs, gantt, ev)


def _nonpreemptive(procs, name, rule, key, fmt, desc=False, hrrn=False):
    """SJF, non-preemptive priority and HRRN: choose at each free CPU, run to end."""
    procs = [Proc(p.pid, p.arrival, p.burst, p.priority) for p in procs]
    t, gantt, ev = 0, [], [RULES[rule]]
    while any(p.remaining > 0 for p in procs):
        ready = [p for p in procs if p.arrival <= t and p.remaining > 0]
        if not ready:
            t, line = _idle(t, procs)
            ev.append(line)
            continue
        if hrrn:
            ratio = {p.pid: Fraction(t - p.arrival + p.burst, p.burst) for p in ready}
            calc = ", ".join(f"{p.pid} waited {t} - {p.arrival} = {t - p.arrival}, "
                             f"({t - p.arrival} + {p.burst}) / {p.burst} = "
                             f"{float(ratio[p.pid]):.2f}" for p in
                             sorted(ready, key=lambda x: (x.arrival, x.pid)))
            p, chain = _chain(ready, lambda x: ratio[x.pid],
                              lambda x: f"{x.pid}({float(ratio[x.pid]):.2f})", desc=True)
            head = f"ratios: {calc}; order {chain}" if len(ready) > 1 else \
                f"only {p.pid} is ready"
        else:
            p, chain = _chain(ready, key, fmt, desc)
            head = f"ready {chain}" if len(ready) > 1 else f"only {p.pid} is ready"
        ev.append(f"t={t}: {head} -> run {p.pid}, done at {t} + {p.burst} = {t + p.burst}")
        p.start = t
        gantt.append((p.pid, t, t + p.burst))
        t += p.burst
        p.remaining = 0
        p.completion = t
    return _finish(name, procs, gantt, ev)


def sjf(procs):
    return _nonpreemptive(procs, "SJF (non-preemptive)", "SJF",
                          lambda x: x.burst, lambda x: f"{x.pid}({x.burst})")


def hrrn(procs):
    return _nonpreemptive(procs, "HRRN (highest response ratio next)", "HRRN",
                          None, None, hrrn=True)


def _preemptive(procs, name, rule, key, fmt):
    """SRTF and preemptive priority: decide at every arrival and completion."""
    procs = [Proc(p.pid, p.arrival, p.burst, p.priority) for p in procs]
    t, gantt, ev = 0, [], [RULES[rule]]
    last, just_done = None, None
    while any(p.remaining > 0 for p in procs):
        ready = [p for p in procs if p.arrival <= t and p.remaining > 0]
        if not ready:
            nxt, line = _idle(t, procs)
            if just_done:
                line = f"t={t}: {just_done} completes; no process ready -> CPU idle until t={nxt}"
                just_done = None
            ev.append(line)
            t, last = nxt, None
            continue
        arrivals = [p.pid for p in procs if p.arrival == t]
        p, chain = _chain(ready, key, fmt)
        if last is None or arrivals or just_done:
            why = []
            if just_done:
                why.append(f"{just_done} completes")
            if arrivals:
                why.append(f"{', '.join(arrivals)} arrive{'s' if len(arrivals) == 1 else ''}")
            if last is None and p.pid != just_done and not why:
                why.append("CPU free")
            if last is None:
                act = f"run {p.pid}"
            elif p.pid != last:
                act = f"PREEMPT {last}, run {p.pid}"
            else:
                act = f"keep running {p.pid}"
            ev.append(f"t={t}: {'; '.join(why)}; "
                      f"{'ready ' + chain if len(ready) > 1 else 'only ' + p.pid + ' is ready'}"
                      f" -> {act}")
        if p.start < 0:
            p.start = t
        gantt.append((p.pid, t, t + 1))
        p.remaining -= 1
        t += 1
        just_done = None
        if p.remaining == 0:
            p.completion = t
            just_done = p.pid
            last = None
        else:
            last = p.pid
    if just_done:
        ev.append(f"t={t}: {just_done} completes; all processes done")
    return _finish(name, procs, _merge(gantt), ev)


def srtf(procs):
    return _preemptive(procs, "SRTF (preemptive SJF)", "SRTF",
                       lambda x: x.remaining, lambda x: f"{x.pid}({x.remaining})")


def round_robin(procs, quantum):
    procs = [Proc(p.pid, p.arrival, p.burst, p.priority) for p in procs]
    order = sorted(procs, key=lambda p: (p.arrival, p.pid))
    q, t, gantt, i = [], 0, [], 0
    ev = [RULES["RR"].format(q=quantum)]
    while i < len(order) and order[i].arrival <= t:
        q.append(order[i]); i += 1
    done = 0
    while done < len(procs):
        if not q:
            if i < len(order):
                nxt = order[i].arrival
                ev.append(f"t={t}: queue empty -> CPU idle until t={nxt}")
                t = max(t, nxt)
                while i < len(order) and order[i].arrival <= t:
                    q.append(order[i]); i += 1
                continue
            break
        before_q = [x.pid for x in q]
        p = q.pop(0)
        if p.start < 0:
            p.start = t
        run = min(quantum, p.remaining)
        before = p.remaining
        gantt.append((p.pid, t, t + run))
        t0, t = t, t + run
        p.remaining -= run
        arrived = []
        # arrivals during this slice enter the queue BEFORE the preempted process
        while i < len(order) and order[i].arrival <= t:
            q.append(order[i]); arrived.append(f"{order[i].pid}(t={order[i].arrival})"); i += 1
        line = (f"t={t0}-{t}: run {p.pid} (head of [{', '.join(before_q)}]) for {run}; "
                f"{before} - {run} = {p.remaining} left")
        if arrived:
            line += f"; arrived {', '.join(arrived)} -> tail"
        if p.remaining > 0:
            q.append(p)
            line += f"; {p.pid} back to tail -> queue [{', '.join(x.pid for x in q)}]"
        else:
            p.completion = t
            done += 1
            line += f"; {p.pid} DONE at {t} -> queue [{', '.join(x.pid for x in q)}]"
        # One line per slice: who ran, the remaining-time arithmetic, and the queue
        # AFTER arrivals and re-queueing. Without the queue, RR traces are where
        # the fine-tuned model lost track (two processes "completing" at t=35).
        ev.append(line)
    return _finish(f"Round Robin (q={quantum})", procs, _merge(gantt), ev, quantum)


def priority(procs, preemptive=False):
    """Lower number = higher priority (the usual textbook convention)."""
    fmt = lambda x: f"{x.pid}(p{x.priority})"  # noqa: E731
    if preemptive:
        return _preemptive(procs, "Priority (preemptive)", "PRIORITY_P",
                           lambda x: x.priority, fmt)
    return _nonpreemptive(procs, "Priority (non-preemptive)", "PRIORITY",
                          lambda x: x.priority, fmt)


ALGORITHMS = {
    "FCFS": lambda ps, **k: fcfs(ps),
    "SJF": lambda ps, **k: sjf(ps),
    "SRTF": lambda ps, **k: srtf(ps),
    "RR": lambda ps, quantum=2, **k: round_robin(ps, quantum),
    "PRIORITY": lambda ps, **k: priority(ps, preemptive=False),
    "PRIORITY_P": lambda ps, **k: priority(ps, preemptive=True),
    "HRRN": lambda ps, **k: hrrn(ps),
}
