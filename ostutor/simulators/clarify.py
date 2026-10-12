"""Questions that are missing an input (v3.0).

Measured failure: given "Apply first-fit to holes of 100, 500, 200 and 300 KB.
Which hole serves each request?" (no requests), v2.2 invented fourteen requests
and solved them. A tutor must never compute from numbers the student did not give.

Two behaviours are taught:
  * ASK - an input with no standard default is missing (the requests, Available,
    the frame count, the RR quantum, the page size, the priorities, the request
    vector): say exactly what is given, what is missing and why it is needed, and
    ask for it. No numeric answer is produced.
  * ASSUME - the input has a textbook default (the head direction for SCAN-family
    disk scheduling): state the assumption, solve, and give the other direction's
    total too (implemented in generate.render_solution via verify["assumed"]).
"""
from . import student

MISSING = ("fit_reqs", "banker_avail", "paging_frames", "rr_quantum", "page_size",
           "priorities", "request_vector")


def gen(rng, which=None):
    which = which or rng.choice(MISSING)
    n = rng.randint(3, 5)
    names = [f"P{i + 1}" for i in range(n)]
    if which == "fit_reqs":
        holes = [rng.randint(50, 600) for _ in range(rng.randint(4, 6))]
        pol = rng.choice(["first-fit", "best-fit", "worst-fit"])
        q = rng.choice([f"Apply {pol} to memory holes of {', '.join(f'{h} KB' for h in holes)}. "
                        f"Which hole serves each request?",
                        f"The free partitions are {holes} KB. Using {pol}, where does each "
                        f"process go?"])
        given = f"the hole sizes {holes} KB and the policy ({pol})"
        need = "the sizes of the requests (processes) and the order in which they arrive"
        why = f"{pol} decides placement one request at a time by comparing each request with the holes"
        example = "for example: 212 KB, 417 KB, 112 KB, 426 KB"
        params = dict(holes=holes, policy=pol)
    elif which == "banker_avail":
        m = rng.randint(3, 4)
        alloc = [[rng.randint(0, 3) for _ in range(m)] for _ in range(n)]
        mx = [[a + rng.randint(0, 4) for a in row] for row in alloc]
        q = (f"Allocation: {', '.join(f'{names[i]} {tuple(alloc[i])}' for i in range(n))}. "
             f"Max: {', '.join(f'{names[i]} {tuple(mx[i])}' for i in range(n))}. "
             f"Is the system in a safe state?")
        given = "the Allocation and Max matrices"
        need = ("the Available vector (or the total number of instances of each resource, "
                "from which Available = Total - allocated)")
        why = "the safety algorithm starts with Work = Available and checks each Need against it"
        example = f"for example: Available = {tuple(rng.randint(1, 5) for _ in range(m))}"
        params = dict(alloc=alloc, max=mx)
    elif which == "paging_frames":
        refs = [rng.randint(0, 7) for _ in range(rng.randint(10, 16))]
        pol = rng.choice(["FIFO", "LRU", "optimal"])
        q = f"Reference string: {' '.join(map(str, refs))}. How many page faults occur with {pol}?"
        given = f"the reference string and the policy ({pol})"
        need = "the number of page frames"
        why = "a fault happens only when the page is absent, and that depends on how many pages fit in memory"
        example = "for example: 3 frames, initially empty"
        params = dict(refs=refs, policy=pol)
    elif which == "rr_quantum":
        arr = sorted(rng.randint(0, 6) for _ in range(n))
        bur = [rng.randint(2, 10) for _ in range(n)]
        q = (f"Processes {', '.join(names)} arrive at {', '.join(map(str, arr))} with bursts "
             f"{', '.join(map(str, bur))}. Using Round Robin, find the average waiting time.")
        given = "the arrival and burst times"
        need = "the time quantum (time slice)"
        why = "Round Robin preempts after each quantum, so every slice boundary depends on it"
        example = "for example: q = 2 ms or q = 4 ms"
        params = dict(arrivals=arr, bursts=bur)
    elif which == "page_size":
        table = [rng.randint(0, 30) for _ in range(rng.randint(4, 7))]
        la = rng.randint(1000, 20000)
        q = f"The page table is {table}. What physical address does logical address {la} map to?"
        given = f"the page table {table} and the logical address {la}"
        need = "the page size"
        why = "page number = floor(address / page size) and offset = address mod page size"
        example = "for example: 1 KB or 4 KB pages"
        params = dict(table=table, logical=la)
    elif which == "priorities":
        bur = [rng.randint(2, 10) for _ in range(n)]
        q = (f"Processes {', '.join(names)} all arrive at time 0 with bursts "
             f"{', '.join(map(str, bur))}. Using priority scheduling, find the average waiting time.")
        given = "the burst times (all arrivals at 0)"
        need = "the priority of each process and the convention (is a lower number a higher priority?)"
        why = "priority scheduling orders the processes by priority"
        example = "for example: priorities 3, 1, 2 with 1 the highest"
        params = dict(bursts=bur)
    else:
        m = 3
        avail = tuple(rng.randint(1, 5) for _ in range(m))
        q = (f"Available = {avail}. "
             f"{names[0]} makes a request. Can it be granted immediately?")
        given = "the Available vector"
        need = ("the request vector itself, plus the Allocation and Max (or Need) matrices "
                "for the safety check")
        why = "the resource-request algorithm compares the request with Need and Available, then runs the safety algorithm"
        example = "for example: Request = (1, 0, 2) with the full Allocation and Max tables"
        params = dict(avail=list(avail))
    # `params` carries the problem's ACTUAL DATA. Without it the only
    # parameter-bearing field was `given` - and `given` is excluded from the
    # fingerprint, because for procedural rows it means "Need was given instead of
    # Max", a presentation choice. So all 500 clarification rows collapsed to 68
    # fingerprints, identity dedup kept a handful, and 5 reached the training set
    # out of a designed 384. Identity is the parameters; now they are recorded.
    v = dict(kind="clarify", missing=which, given=given, need=need, why=why,
             example=example, params=params)
    return v, rng.choice(student.OPENERS) + q


TEMPLATES = [
    ("**This question is missing an input, so it cannot be solved yet.**\n\n"
     "- Given: {given}.\n- Missing: **{need}**.\n- Why it matters: {why}.\n\n"
     "Could you tell me {need_short}? ({example})\n\n"
     "Once I have it, I will work the problem step by step."),
    ("I can't give a correct answer from what is stated: **{need}** is not given.\n\n"
     "What the question provides: {given}. The missing value is essential because {why}, "
     "and guessing it would give a meaningless result.\n\n"
     "Please share {need_short} ({example}), and I will solve it fully."),
    ("Before solving, one input is missing.\n\n"
     "| | |\n|---|---|\n| Given | {given} |\n| Missing | {need} |\n| Needed because | {why} |\n\n"
     "What is {need_short}? ({example})"),
]


def render(v):
    need_short = v["need"].split(" (")[0].split(", plus")[0]
    idx = sum(map(ord, v["missing"] + v["given"])) % len(TEMPLATES)
    return TEMPLATES[idx].format(given=v["given"], need=v["need"], why=v["why"],
                                 need_short=need_short, example=v["example"])
