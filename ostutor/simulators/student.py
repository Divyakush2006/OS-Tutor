"""Student-style problem wording (v3.0).

WHY. v2.2 scored 65% on generator-shaped evaluation questions and 4/14 on the same
kinds of problem typed the way a student types them ("P1 arrives at time 0 and
needs 8 ms, ..."). Its 1,031 procedural questions had 204 distinct opening
sentences, all from prose.py templates, and the OOD suite came from the same
generator - so neither training nor evaluation ever saw free wording.

This module states the SAME verified parameters the way exam papers and students
do: sentences, parallel lists, tuples, plain-text tables, hex addresses, "(3,3,2)"
vectors, 1-based partition numbers, and the conventions real papers use that the
generator never did - a Need matrix given instead of Max, TOTAL instances given
instead of Available, and the disk direction implied by the previously served
request. Every builder returns (problem_text, extra_verify_fields); the extra fields
change the worked solution (e.g. "compute Available = Total - column sums first").
"""

NUM_WORDS = {2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven",
             8: "Eight", 9: "Nine", 10: "Ten"}

OPENERS = ["", "", "", "Question: ", "Solve this: ", "Consider the following. ",
           "Here is an exam question. ", "I need help with this problem. ",
           "Can you solve this step by step? ", "Q. "]


def _join(items, rng):
    items = list(map(str, items))
    if len(items) == 1:
        return items[0]
    style = rng.choice(["and", "comma", "comma"])
    if style == "and":
        return ", ".join(items[:-1]) + " and " + items[-1]
    return ", ".join(items)


def _vec(v, rng, style=None):
    style = style or rng.choice(["paren", "paren_sp", "bracket", "angle"])
    if style == "paren":
        return "(" + ",".join(map(str, v)) + ")"
    if style == "paren_sp":
        return "(" + ", ".join(map(str, v)) + ")"
    if style == "angle":
        return "<" + ", ".join(map(str, v)) + ">"
    return "[" + ", ".join(map(str, v)) + "]"


def _plain_table(headers, rows):
    w = [max(len(str(h)), *(len(str(r[i])) for r in rows)) for i, h in enumerate(headers)]
    out = ["  ".join(str(h).ljust(w[i]) for i, h in enumerate(headers))]
    out += ["  ".join(str(c).ljust(w[i]) for i, c in enumerate(r)) for r in rows]
    return "\n".join(out)


def _md_table(headers, rows):
    out = ["| " + " | ".join(map(str, headers)) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(map(str, r)) + " |" for r in rows]
    return "\n".join(out)


# ------------------------------------------------------------------ scheduling
ALGO_NAMES = {
    "FCFS": ["FCFS", "first-come, first-served (FCFS)", "FIFO (first come first serve)"],
    "SJF": ["non-preemptive SJF", "shortest job first (non-preemptive)", "SJF"],
    "SRTF": ["SRTF", "preemptive SJF (SRTF)", "shortest remaining time first",
             "shortest-remaining-time-first (preemptive SJF)"],
    "RR": ["Round Robin with a time quantum of {q} ms", "RR with quantum = {q}",
           "round-robin scheduling (time slice {q})", "Round Robin (q = {q})"],
    "PRIORITY": ["non-preemptive priority scheduling", "priority scheduling (non-preemptive)"],
    "PRIORITY_P": ["preemptive priority scheduling", "priority scheduling with preemption"],
    "HRRN": ["HRRN (highest response ratio next)", "highest response ratio next scheduling"],
}
PRIO_NOTE = ["(a smaller number means a higher priority)", "(priority 1 is the highest)",
             "Lower numbers indicate higher priority.", "(lower value = higher priority)"]
SCHED_ASK = {
    "waiting": ["What is the average waiting time?", "Find the average waiting time.",
                "Calculate the average waiting time."],
    "turnaround": ["What is the average turnaround time?", "Find the average turnaround time."],
    "both": ["Find the average waiting time and the average turnaround time.",
             "Compute the average waiting and turnaround times.",
             "Calculate the average waiting time and average turnaround time."],
    "gantt": ["Draw the Gantt chart.", "Show the Gantt chart and the completion times."],
    "completion": ["Give the completion time of each process.",
                   "When does each process finish?"],
    "last": ["Which process finishes last, and at what time?"],
}


def sched_text(rng, names, arrivals, bursts, prios, algo, q):
    n = len(names)
    show_p = algo in ("PRIORITY", "PRIORITY_P")
    all_zero = all(a == 0 for a in arrivals)
    styles = ["sentences", "tuples", "lists", "plain_table", "md_table"]
    if all_zero:
        styles += ["all_zero", "all_zero"]
    style = rng.choice(styles)
    unit = rng.choice([" ms", " ms", "", " units"])
    if style == "sentences":
        parts = []
        for i in range(n):
            pr = f" with priority {prios[i]}" if show_p else ""
            verb = rng.choice(["needs", "has a burst of", "requires"])
            parts.append(f"{names[i]} arrives at {'time ' if i == 0 else ''}{arrivals[i]} "
                         f"and {verb} {bursts[i]}{unit}{pr}")
        data = "; ".join(parts) + "."
    elif style == "tuples":
        hdr = "(arrival, burst, priority)" if show_p else "(arrival, burst)"
        cells = [f"{names[i]} ({arrivals[i]}, {bursts[i]}" + (f", {prios[i]})" if show_p else ")")
                 for i in range(n)]
        data = f"Processes {hdr}: " + ", ".join(cells) + "."
    elif style == "lists":
        data = (f"Processes {_join(names, rng)} have arrival times {_join(arrivals, rng)} "
                f"and burst times {_join(bursts, rng)}{unit}")
        if show_p:
            data += f", with priorities {_join(prios, rng)}"
        data += " respectively."
    elif style == "all_zero":
        data = (f"{NUM_WORDS.get(n, str(n))} processes arrive at time 0 in the order "
                f"{_join(names, rng)} with CPU burst times {_join(bursts, rng)}{unit}")
        if show_p:
            data += f" and priorities {_join(prios, rng)}"
        data += "."
    else:
        hdr = ["Process", "Arrival Time", "Burst Time"] + (["Priority"] if show_p else [])
        rows = [[names[i], arrivals[i], bursts[i]] + ([prios[i]] if show_p else [])
                for i in range(n)]
        data = (_plain_table if style == "plain_table" else _md_table)(hdr, rows)
    aname = rng.choice(ALGO_NAMES[algo]).format(q=q)
    ask_kind = rng.choice(list(SCHED_ASK))
    ask = rng.choice(SCHED_ASK[ask_kind])
    how = rng.choice([f"Using {aname}, ", f"The scheduler uses {aname}. ",
                      f"Apply {aname}. ", f"With {aname}: "])
    note = (" " + rng.choice(PRIO_NOTE)) if show_p else ""
    if algo == "RR" and rng.random() < 0.5:
        note += rng.choice([" If a new process arrives at the moment a slice ends, it "
                            "joins the queue before the preempted process.", ""])
    ask = ask[0].lower() + ask[1:] if how.endswith(", ") else ask
    text = rng.choice(OPENERS) + (data + "\n\n" if "\n" in data else data + " ") + how + ask + note
    return text.strip(), dict(ask=ask_kind)


# ------------------------------------------------------------------ paging
POLICY_NAMES = {
    "FIFO": ["FIFO", "first-in first-out (FIFO)", "FIFO page replacement"],
    "LRU": ["LRU", "least recently used (LRU)", "the LRU algorithm"],
    "OPT": ["optimal (OPT)", "the optimal page replacement algorithm",
            "Belady's optimal algorithm (MIN/OPT)"],
    "CLOCK": ["the clock (second-chance) algorithm", "second-chance (CLOCK)"],
}
PAGING_ASK = {
    "faults": ["How many page faults occur?", "Find the number of page faults.",
               "how many page faults will occur?"],
    "hits": ["How many page hits are there?", "Find the number of hits and the hit ratio."],
    "ratio": ["What is the page fault rate (miss ratio)?", "Find the hit ratio."],
    "frames": ["How many page faults occur, and what is in memory at the end?"],
}


def paging_text(rng, refs, frames, policy):
    sep = rng.choice([" ", ", ", ",", " - "])
    rs = sep.join(map(str, refs))
    ref_intro = rng.choice([f"For the reference string {rs}",
                            f"Consider the page reference string: {rs}.",
                            f"A process references pages in the order {rs}.",
                            f"Page requests arrive in this order: {rs}."])
    fr = rng.choice([f"with {frames} frames", f"with {frames} page frames (initially empty)",
                     f"if memory can hold {frames} pages", f"with a frame count of {frames}",
                     f"given {frames} frames, all empty at the start"])
    pol = rng.choice(POLICY_NAMES[policy])
    ask_kind = rng.choice(list(PAGING_ASK))
    ask = rng.choice(PAGING_ASK[ask_kind])
    if ref_intro.endswith("."):
        text = f"{ref_intro} Using {pol} {fr}, {ask[0].lower() + ask[1:]}"
    else:
        text = f"{ref_intro} {fr}, using {pol}: {ask[0].lower() + ask[1:]}"
    return rng.choice(OPENERS) + text, dict(ask=ask_kind)


# ------------------------------------------------------------------ disk
DISK_NAMES = {"FCFS": ["FCFS", "first-come first-served"],
              "SSTF": ["SSTF", "shortest seek time first (SSTF)"],
              "SCAN": ["SCAN", "SCAN (elevator)", "the elevator algorithm (SCAN)"],
              "CSCAN": ["C-SCAN", "circular SCAN (C-SCAN)"],
              "LOOK": ["LOOK"], "CLOOK": ["C-LOOK", "circular LOOK (C-LOOK)"]}


def disk_text(rng, reqs, head, policy, size, direction):
    extra = {}
    q = rng.choice([", ".join(map(str, reqs)), "{" + ", ".join(map(str, reqs)) + "}",
                    "[" + ", ".join(map(str, reqs)) + "]"])
    qs = rng.choice([f"The request queue is {q}.", f"Pending requests (cylinders): {q}.",
                     f"Requests arrive for cylinders {q}.", f"Queue = {q}."])
    hs = rng.choice([f"The head is at cylinder {head}.",
                     f"The read/write head is currently at {head}.",
                     f"The disk head starts at track {head}.", f"Head position: {head}."])
    needs_edge = policy in ("SCAN", "CSCAN")
    ss = ""
    if needs_edge or rng.random() < 0.6:
        ss = rng.choice([f"The disk has {size} cylinders (0 to {size - 1}).",
                         f"Cylinders are numbered 0-{size - 1}.",
                         f"The disk spans cylinders 0 to {size - 1}."])
    ds = ""
    if policy in ("SCAN", "LOOK", "CSCAN", "CLOOK") and direction == "up" and rng.random() < 0.15:
        extra["assumed"] = True          # exam papers often omit it: state the convention
    elif policy in ("SCAN", "LOOK", "CSCAN", "CLOOK"):
        if rng.random() < 0.3:
            prev = (head - rng.randint(3, 25)) if direction == "up" else (head + rng.randint(3, 25))
            prev = max(0, min(size - 1, prev))
            if prev != head:
                extra["prev"] = prev
                ds = rng.choice([f"The previous request served was at cylinder {prev}.",
                                 f"The head has just finished a request at {prev}."])
        if not ds:
            ds = (rng.choice(["The head is moving towards higher cylinder numbers.",
                              f"The arm is moving towards {size - 1}.",
                              "Direction: increasing cylinder numbers."])
                  if direction == "up" else
                  rng.choice(["The head is moving towards 0.",
                              "The head is moving towards lower cylinder numbers.",
                              "Direction: decreasing cylinder numbers."]))
    ask_kind = rng.choice(["total", "total", "order", "avg"])
    ask = {"total": rng.choice(["What is the total head movement?",
                                "Find the total number of cylinders the head moves.",
                                "Calculate the total seek distance."]),
           "order": "Give the order in which requests are served and the total head movement.",
           "avg": "Find the total head movement and the average seek length."}[ask_kind]
    pol = rng.choice(DISK_NAMES[policy])
    parts = [s for s in (ss, hs, qs, ds) if s]
    body = " ".join(parts)
    text = f"{body} Using {pol} scheduling, {ask[0].lower() + ask[1:]}"
    extra["ask"] = ask_kind
    return rng.choice(OPENERS) + text, extra


# ------------------------------------------------------------------ translation
def translate_text(rng, logical, page_size, table):
    extra = {}
    kb = page_size // 1024
    ps = rng.choice([f"{kb} KB pages", f"a page size of {page_size} bytes",
                     f"pages of {page_size} bytes", f"page size = {kb} KB"])
    style = rng.choice(["arrows", "list", "md"])
    if style == "arrows":
        tb = ", ".join(f"page {i} -> frame {f}" for i, f in enumerate(table))
        tb = f"The page table maps {tb}."
    elif style == "list":
        tb = f"The page table (indexed by page number) is {_vec(table, rng, 'bracket')}."
    else:
        tb = "Page table:\n\n" + _md_table(["Page", "Frame"], [[i, f] for i, f in enumerate(table)])
    if rng.random() < 0.3:
        extra["hex"] = True
        la = hex(logical)
    else:
        la = str(logical)
    ask = rng.choice([f"What physical address does logical address {la} map to?",
                      f"Translate the logical address {la} into a physical address.",
                      f"Find the physical address for virtual address {la}."])
    lead = rng.choice([f"A system uses {ps}.", f"Assume {ps}.", f"Paging is used with {ps}."])
    sep = "\n\n" if style == "md" else " "
    return rng.choice(OPENERS) + f"{lead} {tb}{sep}{ask}", extra


# ------------------------------------------------------------------ free space
FIT_NAMES = {"FIRST": ["first-fit", "first fit"], "BEST": ["best-fit", "best fit"],
             "WORST": ["worst-fit", "worst fit"]}


def fit_text(rng, holes, reqs, policy):
    u = rng.choice([" KB", "K", " KB"])
    hs = rng.choice([f"Memory partitions are {_join([f'{h}{u}' for h in holes], rng)}, in that order.",
                     f"The free holes, in address order, are {_join([f'{h}{u}' for h in holes], rng)}.",
                     f"Free blocks: {', '.join(f'{h}{u}' for h in holes)} (in order)."])
    rs = rng.choice([f"Processes of {_join([f'{r}{u}' for r in reqs], rng)} arrive in that order.",
                     f"Requests of size {', '.join(f'{r}{u}' for r in reqs)} come in sequence.",
                     f"The processes need {_join([f'{r}{u}' for r in reqs], rng)} (in order)."])
    pol = rng.choice(FIT_NAMES[policy])
    ask_kind = rng.choice(["place", "place", "wait", "frag"])
    ask = {"place": rng.choice([f"Where does {pol} place each process?",
                                f"Using {pol}, which partition does each process get?"]),
           "wait": f"Using {pol}, show the allocation. Which processes cannot be allocated?",
           "frag": f"Apply {pol}. How much free memory remains in each hole, and in total?"}[ask_kind]
    return rng.choice(OPENERS) + f"{hs} {rs} {ask}", dict(ask=ask_kind)


# ------------------------------------------------------------------ banker
def _rows_text(rng, label, names, mat, style):
    if style == "tuples":
        return f"{label}: " + ", ".join(f"{names[i]} {_vec(mat[i], rng, 'paren_sp')}"
                                        for i in range(len(names)))
    return f"{label} = " + "[" + ", ".join(_vec(r, rng, "bracket") for r in mat) + "]"


def banker_text(rng, v, request_mode=False):
    """v carries names, avail, maxm, alloc (and pid/req for requests)."""
    extra = {}
    names, alloc, maxm, avail = v["names"], v["alloc"], v["maxm"], v["avail"]
    m = len(avail)
    res = ", ".join("ABCD"[:m])
    need = [[maxm[i][j] - alloc[i][j] for j in range(m)] for i in range(len(names))]
    given = "need" if rng.random() < 0.2 else "max"
    extra["given"] = given
    second, second_label = (need, "Need") if given == "need" else (maxm, "Max")
    if rng.random() < 0.25:
        total = [avail[j] + sum(alloc[i][j] for i in range(len(names))) for j in range(m)]
        extra["total"] = total
        av = rng.choice([f"The total instances of {res} are {_vec(total, rng)}.",
                         f"There are {_join([f'{total[j]} instances of {r}' for j, r in enumerate('ABCD'[:m])], rng)} in total."])
    else:
        av = rng.choice([f"Available = {_vec(avail, rng)}.",
                         f"Currently available: {', '.join(f'{r}={avail[j]}' for j, r in enumerate('ABCD'[:m]))}.",
                         f"The available vector is {_vec(avail, rng)}."])
    style = rng.choice(["tuples", "matrix", "table", "table"])
    if style == "table":
        hdr = ["Process"] + [f"Alloc {r}" for r in "ABCD"[:m]] + [f"{second_label} {r}" for r in "ABCD"[:m]]
        data = _md_table(hdr, [[names[i]] + alloc[i] + second[i] for i in range(len(names))])
        body = f"{av}\n\n{data}"
    else:
        body = (f"{av} {_rows_text(rng, 'Allocation', names, alloc, style)}. "
                f"{_rows_text(rng, second_label, names, second, style)}.")
    intro = rng.choice([f"A system has resource types {res} and processes {_join(names, rng)}.",
                        f"Consider {len(names)} processes and {m} resource types ({res}).",
                        ""])
    if request_mode:
        who, req = names[v["pid"]], v["req"]
        ask = rng.choice([f"{who} requests {_vec(req, rng)}. Can the request be granted immediately?",
                          f"If {who} makes a request {_vec(req, rng)}, should it be granted?",
                          f"Request_{who} = {_vec(req, rng)}. Apply the resource-request algorithm."])
    else:
        ask = rng.choice(["Is the system in a safe state? If so, give a safe sequence.",
                          "Use the Banker's algorithm to check whether the state is safe.",
                          "Find a safe sequence, if one exists."])
    sep = "\n\n" if style == "table" else " "
    text = (intro + " " if intro else "") + body + sep + ask
    return rng.choice(OPENERS) + text.strip(), extra
