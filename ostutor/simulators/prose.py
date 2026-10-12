"""Prose diversity for generated problems.

WHY THIS EXISTS. The first generator randomised parameters only: same opening
sentence, same table layout, same question, different numbers. Measured pairwise
cosine between two "different" FCFS problems was 0.997, against a semantic-dedup
threshold of 0.93. The pipeline collapsed 5,394 procedural rows to 22 - exactly
the number of topics. One template each.

Parameter randomisation is not diversity. A model trained on that learns the
template, not the procedure, and the collapse proves the examples carry one
training signal between them.

Real variation needs four independent axes:
  1. FRAMING    - how the problem is introduced (scenario, plain, exam-style)
  2. NAMING     - P1..Pn vs job names vs thread ids vs PIDs
  3. PRESENTATION - markdown table vs inline list vs prose
  4. THE ASK    - full solution vs one quantity vs comparison vs verification

Combining them multiplies out to thousands of genuinely distinct surface forms
per topic while the underlying verified computation stays identical.
"""
import random

# ------------------------------------------------------------------ scenarios
SCENARIOS = [
    ("a print server", "print jobs", "job"),
    ("a web server thread pool", "incoming requests", "request"),
    ("an embedded controller", "control tasks", "task"),
    ("a batch processing cluster", "batch jobs", "job"),
    ("a university lab machine", "student programs", "program"),
    ("a video transcoding farm", "encode jobs", "job"),
    ("a database server", "queries", "query"),
    ("a CI build agent", "build jobs", "build"),
    ("an air-traffic display system", "update tasks", "task"),
    ("a point-of-sale terminal", "transactions", "transaction"),
]

# --------------------------------------------------------------- naming schemes
def naming(rng, n):
    style = rng.choice(["P", "J", "T", "pid", "letters", "words"])
    if style == "P":
        return [f"P{i+1}" for i in range(n)]
    if style == "J":
        return [f"J{i+1}" for i in range(n)]
    if style == "T":
        return [f"T{i+1}" for i in range(n)]
    if style == "pid":
        # cumulative steps: v2.x drew base + i * randint(1, 30), which can repeat a PID
        # (6049 twice) - a duplicate process name makes the problem ambiguous
        out, cur = [], rng.randrange(1000, 9000)
        for _ in range(n):
            out.append(str(cur))
            cur += rng.randint(1, 30)
        return out
    if style == "letters":
        return [chr(ord("A") + i) for i in range(n)]
    pool = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta",
            "theta", "iota", "kappa", "lambda", "mu"]
    return pool[:n] if n <= len(pool) else [f"P{i+1}" for i in range(n)]


# ------------------------------------------------------------------ presentation
def present_procs(rng, names, arrivals, bursts, priorities=None):
    """Table, inline list, or prose - three genuinely different surface forms."""
    style = rng.choice(["table", "inline", "prose"])
    show_p = priorities is not None
    if style == "table":
        hdr = ["Process", "Arrival", "Burst"] + (["Priority"] if show_p else [])
        rows = [[names[i], arrivals[i], bursts[i]] + ([priorities[i]] if show_p else [])
                for i in range(len(names))]
        w = [max(len(str(h)), *(len(str(r[i])) for r in rows)) for i, h in enumerate(hdr)]
        out = ["| " + " | ".join(str(h).ljust(w[i]) for i, h in enumerate(hdr)) + " |",
               "|" + "|".join("-" * (x + 2) for x in w) + "|"]
        for r in rows:
            out.append("| " + " | ".join(str(c).ljust(w[i]) for i, c in enumerate(r)) + " |")
        return "\n".join(out)
    if style == "inline":
        parts = []
        for i, nm in enumerate(names):
            p = f", priority {priorities[i]}" if show_p else ""
            parts.append(f"- **{nm}**: arrives at t={arrivals[i]}, needs "
                         f"{bursts[i]} ms of CPU{p}")
        return "\n".join(parts)
    parts = []
    for i, nm in enumerate(names):
        p = f" with priority {priorities[i]}" if show_p else ""
        parts.append(f"{nm} arrives at time {arrivals[i]} and requires "
                     f"{bursts[i]} units of CPU time{p}")
    return "; ".join(parts) + "."


# ---------------------------------------------------------------------- framings
SCHED_FRAMINGS = [
    "Consider the following set of processes:",
    "{scenario_cap} receives the following {items}:",
    "A system must schedule these {items}:",
    "The ready queue of {scenario} contains:",
    "An operating systems exam gives the following process table:",
    "During one scheduling interval the following {items} arrive:",
    "You are analysing the workload of {scenario}. The {items} are:",
    "The scheduler observes these arrivals:",
]

SCHED_ASKS = [
    ("full", "Draw the Gantt chart and compute the average waiting time and "
             "average turnaround time."),
    ("full", "Construct the Gantt chart, then determine the average waiting and "
             "turnaround times."),
    ("waiting", "What is the average waiting time?"),
    ("turnaround", "Compute the average turnaround time."),
    ("gantt", "Draw the Gantt chart showing the execution order."),
    ("full", "Show the schedule step by step and report both averages."),
    ("completion", "Give the completion time of each process."),
    ("waiting", "Work through the schedule and give the average waiting time, "
                "showing all intermediate steps."),
]

PAGING_FRAMINGS = [
    "Given the page reference string",
    "A process generates the following sequence of page references:",
    "{scenario_cap} produces this reference string:",
    "Consider a program whose memory accesses translate to the page sequence",
    "During execution the following pages are referenced in order:",
    "An OS exam provides this reference string:",
]

PAGING_ASKS = [
    "How many page faults occur? Show the frame contents after each reference.",
    "Determine the number of page faults, showing the state of memory at each step.",
    "Count the page faults and trace the contents of the frames.",
    "How many page faults result? Include a step-by-step trace.",
    "Compute the total page faults and the hit ratio.",
]

DISK_FRAMINGS = [
    "A disk has cylinders 0-{max_cyl}. The head is at cylinder **{head}** and "
    "the pending request queue is",
    "{scenario_cap} uses a disk with cylinders 0-{max_cyl}. With the head at "
    "**{head}**, the following requests are pending:",
    "The disk scheduler has these outstanding requests (head currently at "
    "cylinder **{head}**, disk spans 0-{max_cyl}):",
    "Consider a disk of {n_cyl} cylinders. The read/write head sits at **{head}** "
    "and the request queue holds",
    "An I/O subsystem with cylinders 0-{max_cyl} has its head at **{head}**. "
    "Queued requests:",
]

DISK_ASKS = [
    "Give the service order and the total head movement.",
    "What is the total number of cylinders the head traverses? Show the order.",
    "Determine the seek sequence and total head movement.",
    "List the order in which requests are served and compute the total distance moved.",
]

BANKER_FRAMINGS = [
    "A system has {m} resource types ({res}) and {n} processes.",
    "{scenario_cap} manages {m} resource types ({res}) shared by {n} processes.",
    "Consider a system with {n} processes competing for {m} resource classes ({res}).",
    "An operating system tracks {m} kinds of resource ({res}) across {n} processes.",
    "The resource allocation state of a system with {m} resource types ({res}) is:",
]

BANKER_ASKS = [
    "Using Banker's algorithm, determine whether the system is in a safe state. "
    "If it is, give a safe sequence.",
    "Is this state safe? Apply the safety algorithm and show a safe sequence if one exists.",
    "Run the safety algorithm. State whether the system is safe and give the sequence.",
    "Determine safety using Banker's algorithm, showing the Need matrix and each "
    "Work update.",
]

TRANSLATE_FRAMINGS = [
    "A system uses paging with a page size of **{ps} bytes**.",
    "{scenario_cap} runs on a machine with **{ps}-byte** pages.",
    "Consider a paged memory system where each page is **{ps} bytes**.",
    "A processor uses {ps}-byte pages and the following page table:",
]

TRANSLATE_ASKS = [
    "Translate the logical address **{la}** to a physical address.",
    "What physical address does logical address **{la}** map to? Show your working.",
    "Compute the physical address for logical address **{la}**.",
    "Convert logical address **{la}** into its physical equivalent, showing the "
    "page number and offset.",
]

FIT_FRAMINGS = [
    "Memory contains holes of sizes `{holes}` (in KB, in this order).",
    "{scenario_cap} has free memory partitions of `{holes}` KB.",
    "A memory manager tracks these free blocks (KB, in address order): `{holes}`.",
    "The free list holds partitions of `{holes}` KB.",
]

FIT_ASKS = [
    "Using **{policy}-fit**, show which hole serves each request and the remaining "
    "free space.",
    "Apply **{policy}-fit** allocation. Which partition serves each request?",
    "Allocate these requests with **{policy}-fit** and report the leftover space "
    "in each hole.",
]


def pick_scenario(rng):
    s, items, unit = rng.choice(SCENARIOS)
    return dict(scenario=s, scenario_cap=s[0].upper() + s[1:], items=items, unit=unit)


# ============================================================================
# HELD-OUT FRAMINGS - used ONLY for the out-of-distribution evaluation split.
#
# A same-generator OOD split tests size generalisation and nothing else: if the
# model has learned the TEMPLATE rather than the procedure, larger instances of
# the same template still look familiar. These framings are never used in
# training, so a model that memorised surface form fails here while a model that
# learned the procedure does not. This is the only honest generalisation test the
# pipeline can build for itself.
# ============================================================================

HOLDOUT_SCHED_FRAMINGS = [
    "Your team is reviewing a scheduling trace. The recorded workload was:",
    "Reproduce the following schedule from last term's exam paper:",
    "A colleague sketched this workload on a whiteboard:",
    "Here is a workload captured from a production trace:",
]

HOLDOUT_SCHED_ASKS = [
    "Work it through and report both averages.",
    "Produce the schedule and the two average metrics.",
    "Show the execution timeline and summarise the timing results.",
]

HOLDOUT_PAGING_FRAMINGS = [
    "A memory trace recorded these page accesses:",
    "The following page sequence was captured from a running process:",
    "Here is a reference stream taken from a profiler:",
]

HOLDOUT_DISK_FRAMINGS = [
    "A storage trace shows the head at cylinder **{head}** on a {n_cyl}-cylinder "
    "device, with these outstanding requests:",
    "Disk telemetry reports the arm at **{head}** (device spans 0-{max_cyl}) and a "
    "queue of:",
]

HOLDOUT_BANKER_FRAMINGS = [
    "An allocation snapshot from a {m}-resource system ({res}) with {n} processes:",
    "The following state was dumped by a resource monitor ({m} types: {res}, "
    "{n} processes):",
]

HOLDOUT_TRANSLATE_FRAMINGS = [
    "A memory-management unit is configured with **{ps}-byte** pages.",
    "Address-translation hardware uses {ps}-byte pages and this mapping:",
]

HOLDOUT_FIT_FRAMINGS = [
    "A memory dump shows free partitions of `{holes}` KB.",
    "The allocator's free list currently holds `{holes}` KB blocks.",
]

# The data sentence that shares the first paragraph with the framing. Replacing
# that paragraph must carry these inputs over, or the question is unsolvable
# (v2.2.0 OOD defect: every Banker's question lost Available and every free-space
# question lost its requests). Worded differently from the training phrasings, so
# the OOD split still tests surface-form transfer.
HOLDOUT_AVAIL = [
    "Free instances right now: {avail}.",
    "The monitor reports {avail} units still unallocated.",
]
HOLDOUT_REQS = [
    "Pending requests, in arrival order: `{reqs}` KB.",
    "The queue asks for `{reqs}` KB, served first to last.",
]

HOLDOUT = dict(
    sched_framings=HOLDOUT_SCHED_FRAMINGS, sched_asks=HOLDOUT_SCHED_ASKS,
    paging_framings=HOLDOUT_PAGING_FRAMINGS, disk_framings=HOLDOUT_DISK_FRAMINGS,
    banker_framings=HOLDOUT_BANKER_FRAMINGS,
    translate_framings=HOLDOUT_TRANSLATE_FRAMINGS, fit_framings=HOLDOUT_FIT_FRAMINGS,
)
