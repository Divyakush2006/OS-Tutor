"""Verified-solver delegation: let the model READ, let the simulator COMPUTE.

WHY THIS EXISTS. v3.0 scored 64.9% on the hand-written suite, and every one of the
seven scheduling failures had a perfect table - turnaround minus burst, sums,
divisions all correct - built from a WRONG SCHEDULE. The model knows the rules and
cannot execute them over a long trace. Measured on this corpus:

    decisions needed   1-3    4-9   10-19   20+
    accuracy           64%    74%    62%    25%

    training rows      scheduling 1,733 -> 42%     disk 990 -> 100%

More data makes it no better; the family with the most rows is the worst. This is the
"deterministic horizon" (arXiv 2606.00376): unaided chain-of-thought crosses 50% at
19-31 sequential steps, the limit is architectural, fine-tuning on better traces
recovers 0.9pp, and delegating to an exact solver restores 76-94%. Qwen3-235B manages
only ~50% on the same class of task, so a bigger model is not the answer either.

WHAT THIS DOES. The model extracts the problem's PARAMETERS, the simulators compute
the answer, and render_solution() writes the worked solution in exactly the format the
model was fine-tuned to produce. The fine-tune still supplies the teaching voice, the
step format and the Socratic behaviour; it simply stops doing arithmetic it cannot do
reliably.

WHY EXTRACTION IS SAFE TO RELY ON. Measured on the same 57 items, extraction scores
84% with the untuned base and 79% with the adapter - the adapter is biased toward
solving rather than reading, so extraction uses the base (llama-server takes a
per-request LoRA scale). More importantly, extraction errors are DETECTABLE in a way
execution errors are not: every number in the extracted parameters must appear in the
question text. Most observed failures were not misreadings at all but shape and unit
deviations - (size, index) pairs instead of a flat list, KB expanded to bytes, "SRPF"
for "SRTF" - all of which normalise in code.
"""
import json
import re

from .simulators.generate import render_solution

SOLVER_KINDS = ("scheduling", "paging", "disk", "banker_safety", "banker_request",
                "freespace", "translate")

EXTRACT_PROMPT = """Read the problem and output ONLY a JSON object of its parameters. No prose, no working.

scheduling: {"kind":"scheduling","algo":"FCFS|SJF|SRTF|RR|PRIORITY|PRIORITY_P|HRRN","quantum":<int>,"procs":[["name",arrival,burst,priority],...]}
paging:     {"kind":"paging","policy":"FIFO|LRU|OPT|CLOCK","frames":<int>,"refs":[<int>,...]}
disk:       {"kind":"disk","policy":"FCFS|SSTF|SCAN|LOOK|CSCAN|CLOOK","head":<int>,"reqs":[<int>,...],"size":<int>,"direction":"up|down"}
banker_safety:  {"kind":"banker_safety","names":[...],"alloc":[[<int>,...],...],"maxm":[[<int>,...],...],"avail":[<int>,...]}
banker_request: {"kind":"banker_request","names":[...],"alloc":[[...],...],"maxm":[[...],...],"avail":[...],"req_proc":"name","req":[<int>,...]}
freespace:  {"kind":"freespace","policy":"FIRST|BEST|WORST","holes":[<int>,...],"reqs":[<int>,...]}
translate:  {"kind":"translate","logical":<int>,"page_size":<int>,"table":[<int>,...]}

Other kinds:
  a formula question (EAT, page-table bits, fork count, semaphore, CPU utilisation,
  internal fragmentation, minimum resources for deadlock, disk access time, cache
  access time) -> {"kind":"formula"}
  a concept or explanation question about operating systems -> {"kind":"concept"}
  an open question that needs judgement rather than a single answer - which approach is
  better, why something behaves as it does, a design or diagnosis question
  -> {"kind":"analysis"}
  a question asking for a Linux/shell command -> {"kind":"shell"}
  an input the answer needs is NOT stated -> {"kind":"incomplete","missing":"<what>"}
  a question that is not about operating systems at all -> {"kind":"offtopic"}

Rules:
- Copy numbers EXACTLY as the problem states them. Do not convert units.
- "holes" and "table" are FLAT lists of numbers, not pairs.
- priority is 1 when not stated; quantum is 2 unless Round Robin gives one.
- Output the JSON object and nothing else."""

_ALGO = {"FCFS": "FCFS", "FIFO": "FCFS", "FIRSTCOMEFIRSTSERVED": "FCFS",
         "SJF": "SJF", "SHORTESTJOBFIRST": "SJF", "SJN": "SJF",
         "SRTF": "SRTF", "SRPF": "SRTF", "SRT": "SRTF", "PREEMPTIVESJF": "SRTF",
         "SHORTESTREMAININGTIMEFIRST": "SRTF",
         "RR": "RR", "ROUNDROBIN": "RR",
         "PRIORITY": "PRIORITY", "PRIORITYNONPREEMPTIVE": "PRIORITY",
         "PRIORITYP": "PRIORITY_P", "PREEMPTIVEPRIORITY": "PRIORITY_P",
         "PRIORITYPREEMPTIVE": "PRIORITY_P",
         "HRRN": "HRRN", "HIGHESTRESPONSERATIONEXT": "HRRN"}
_PAGE = {"FIFO": "FIFO", "LRU": "LRU", "OPT": "OPT", "OPTIMAL": "OPT",
         "MIN": "OPT", "CLOCK": "CLOCK", "SECONDCHANCE": "CLOCK"}
# disk_schedule() matches on "CSCAN"/"CLOOK" internally, even though it documents
# them as C-SCAN/C-LOOK. Emitting the hyphenated form raised ValueError and cost
# two delegations.
_DISK = {"FCFS": "FCFS", "FIFO": "FCFS", "SSTF": "SSTF", "SCAN": "SCAN",
         "ELEVATOR": "SCAN", "LOOK": "LOOK", "CSCAN": "CSCAN", "CLOOK": "CLOOK",
         "CIRCULARSCAN": "CSCAN", "CIRCULARLOOK": "CLOOK"}
_FIT = {"FIRST": "FIRST", "FIRSTFIT": "FIRST", "BEST": "BEST", "BESTFIT": "BEST",
        "WORST": "WORST", "WORSTFIT": "WORST"}


# "all three arrive at time zero" states an arrival of 0 without writing a digit.
_WORD_NUM = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
             "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
             "eleven": 11, "twelve": 12}


def _quantum_stated(q, question):
    """Does the question actually NAME the time quantum?

    Round Robin is undefined without it, and defaulting to 2 answers a question the
    student did not ask: "P1, P2, P3 arrive at 0 with bursts 5, 3, 8 - average waiting
    time under round robin?" has no quantum, so the honest reply asks for one. The
    dataset's own missing_inputs() applies the same rule; without it here, extraction
    grounded on the arrivals and bursts and delegated with an invented quantum."""
    n = re.escape(str(q))
    for pat in (rf"\b{n}\b[^.\n]{{0,26}}(?:quantum|time slice|timeslice)",
                rf"(?:quantum|time slice|timeslice)[^.\n]{{0,20}}\b{n}\b",
                rf"\bq\s*=\s*{n}\b"):
        if re.search(pat, question, re.I):
            return True
    return False


def _frames_stated(f, question):
    """Does the question actually NAME this many page frames?

    A number merely appearing in the text is not enough. "How many page faults does
    LRU give for 1 2 3 4 1 2 5 1 2 3 4 5?" states no frame count, but a 3 occurs in
    the reference string - so extraction invented frames=3 and the grounding check
    waved it through, turning a question the tutor should ask about into a
    confidently wrong answer. The count must sit next to a frame/capacity cue."""
    n = re.escape(str(f))
    for pat in (rf"\b{n}\b[^.\n]{{0,24}}(?:frames?|page frames?)",
                rf"(?:frames?|page frames?)[^.\n]{{0,16}}\b{n}\b",
                rf"(?:hold|holds|holding|capacity of|memory of)[^.\n]{{0,16}}\b{n}\b"):
        if re.search(pat, question, re.I):
            return True
    return False


def _asks_request(question):
    """Does the question ask whether a RESOURCE REQUEST can be granted?

    Distinct from a plain safety question: the answer is GRANTED or DENIED, not a safe
    sequence."""
    return bool(re.search(r"\brequests?\b[^.\n]{0,60}(?:be granted|granted|be satisfied"
                          r"|safely|immediately)"
                          r"|(?:can|should|may)\b[^.\n]{0,40}\brequests?\b"
                          r"|\brequests?\s*(?:for|of)?\s*[\(\[]", question, re.I))


def _key(s):
    return re.sub(r"[^A-Z0-9]", "", str(s).upper())


def _map(value, table, default=None):
    return table.get(_key(value), default)


def numbers_in(text):
    """Every integer the question states, as a set. Used to prove an extracted value
    was READ rather than invented.

    The lookahead excludes a following DIGIT only, never a following '.'. Excluding
    the dot as well - which this first did - makes every number at the end of a
    sentence invisible ("head starts at 53.", "translate address 10000."), and the
    validator then rejects perfectly correct extractions. That cost four disk
    delegations and two translate delegations. Hex literals count as their value, so
    "0x0A2C" grounds a logical address of 2604."""
    out = {int(t) for t in re.findall(r"(?<![\d.])\d+(?![\d])", text)}
    out |= {int(h, 16) for h in re.findall(r"0[xX]([0-9a-fA-F]+)", text)}
    for word, val in _WORD_NUM.items():
        if re.search(rf"\b{word}\b", text, re.I):
            out.add(val)
    return out


def _flatten(lst):
    """A list of pairs where one column is an index becomes the value column.

    The model often answers with (size, index) or (page, frame) pairs even when asked
    for a flat list. The index column is the one equal to 0..n-1 (or 1..n), so the
    other column carries the values."""
    if not isinstance(lst, list) or not lst or not all(
            isinstance(x, (list, tuple)) and len(x) == 2 for x in lst):
        return lst
    cols = ([x[0] for x in lst], [x[1] for x in lst])
    n = len(lst)
    for i, col in enumerate(cols):
        if col == list(range(n)) or col == list(range(1, n + 1)):
            return cols[1 - i]
    return cols[0]


def _unscale(values, present):
    """Undo a unit conversion the model made on its own (KB written as bytes)."""
    if not values or not isinstance(values, list) or not all(
            isinstance(v, int) for v in values):
        return values
    if all(v in present for v in values):
        return values
    for factor in (1024, 1000):
        scaled = [v // factor for v in values]
        if all(v % factor == 0 for v in values) and all(s in present for s in scaled):
            return scaled
    return values


def normalise(d, question):
    """Coerce the model's JSON into the exact shape the simulators expect."""
    if not isinstance(d, dict) or "kind" not in d:
        return None
    k = _key(d["kind"]).lower()
    kind = {"scheduling": "scheduling", "paging": "paging", "disk": "disk",
            "bankersafety": "banker_safety", "bankerrequest": "banker_request",
            "freespace": "freespace", "translate": "translate",
            "formula": "formula", "concept": "concept", "analysis": "analysis",
            "shell": "shell", "offtopic": "offtopic",
            "incomplete": "incomplete"}.get(k)
    if kind is None:
        return None
    out = dict(d, kind=kind)
    present = numbers_in(question)

    # A Banker's question that states a REQUEST is a request question, whatever the
    # model called it. Misclassifying it as a safety question produces a safe sequence
    # instead of GRANTED/DENIED - a confident answer to a question nobody asked.
    if kind == "banker_safety" and d.get("req") \
            and re.search(r"\brequest", question, re.I):
        kind = out["kind"] = "banker_request"

    if kind == "scheduling":
        out["algo"] = _map(d.get("algo"), _ALGO)
        procs = []
        for p in d.get("procs") or []:
            if isinstance(p, dict):
                p = [p.get("name", f"P{len(procs)+1}"), p.get("arrival", 0),
                     p.get("burst"), p.get("priority", 1)]
            p = list(p)
            while len(p) < 4:
                p.append(1)
            procs.append([str(p[0]), int(p[1]), int(p[2]), int(p[3] or 1)])
        out["procs"] = procs
        out["quantum"] = int(d.get("quantum") or 2)
        if not out["algo"] or not procs:
            return None
        # Round Robin is undefined without a quantum, so it must be STATED rather than
        # defaulted - otherwise the answer is confidently about a different problem.
        if out["algo"] == "RR" and not _quantum_stated(out["quantum"], question):
            return dict(kind="incomplete", missing="the time quantum (time slice)")
    elif kind == "paging":
        out["policy"] = _map(d.get("policy"), _PAGE)
        out["refs"] = [int(x) for x in _flatten(d.get("refs") or [])]
        out["frames"] = int(d.get("frames") or 0)
        if not out["policy"] or not out["refs"] or out["frames"] < 1:
            return None
        # The frame count must be STATED, not merely present somewhere in the text.
        # "How many faults does LRU give for 1 2 3 4 1 2 5 ..." names no frame
        # count; extraction invented frames=3 and grounding accepted it, because a
        # 3 appears in the reference string. That turned a question the tutor
        # should ASK about into a confidently wrong answer.
        if not _frames_stated(out["frames"], question):
            return dict(kind="incomplete", missing="the number of page frames")
    elif kind == "disk":
        out["policy"] = _map(d.get("policy"), _DISK)
        out["reqs"] = [int(x) for x in _flatten(d.get("reqs") or [])]
        out["head"] = int(d.get("head", -1))
        out["size"] = int(d.get("size") or 200)
        out["direction"] = "down" if _key(d.get("direction")) == "DOWN" else "up"
        # A previously-served request fixes the direction, and the renderer explains it
        # ("previous request 125 < head 143, so the head is moving UP"). Without it the
        # direction defaults to up, which silently answers a different question on
        # SCAN/LOOK/C-SCAN/C-LOOK.
        prev = d.get("prev")
        if prev is None:
            m = re.search(r"(?:just (?:served|serviced|finished|completed)|previous(?:ly)?"
                          r"|last (?:served|serviced|request))[^.\n]{0,40}?(\d+)",
                          question, re.I)
            prev = int(m.group(1)) if m else None
        if prev is not None and int(prev) in present:
            out["prev"] = int(prev)
            out["direction"] = "up" if int(prev) < out["head"] else "down"
        elif not re.search(r"\b(?:up|down|higher|lower|increasing|decreasing|toward)\b",
                           question, re.I):
            out["assumed"] = True          # the renderer states the assumption
        if not out["policy"] or not out["reqs"] or out["head"] < 0:
            return None
    elif kind in ("banker_safety", "banker_request"):
        out["alloc"] = [[int(x) for x in row] for row in d.get("alloc") or []]
        out["maxm"] = [[int(x) for x in row] for row in d.get("maxm") or []]
        out["avail"] = [int(x) for x in _flatten(d.get("avail") or [])]
        out["names"] = [str(x) for x in (d.get("names")
                                         or [f"P{i}" for i in range(len(out["alloc"]))])]
        if not out["alloc"] or not out["maxm"] or not out["avail"]:
            return None
        if re.search(r"(?:in total|total of|totals?|altogether)", question, re.I):
            cols = list(zip(*out["alloc"]))
            if len(cols) == len(out["avail"]):
                derived = [tot - sum(c) for tot, c in zip(out["avail"], cols)]
                if all(x >= 0 for x in derived):
                    out["total"], out["avail"] = out["avail"], derived
        if len(out["alloc"]) != len(out["maxm"]):
            return None
        if kind == "banker_request":
            out["req"] = [int(x) for x in _flatten(d.get("req") or [])]
            # The renderer wants `pid` as an INDEX into names, not a name.
            # Passing the name raised KeyError: 'pid' and lost the delegation.
            who = str(d.get("req_proc") or d.get("pid") or out["names"][0])
            if who in out["names"]:
                out["pid"] = out["names"].index(who)
            else:
                digits = re.findall(r"\d+", who)
                out["pid"] = int(digits[0]) if digits else 0
            out.pop("req_proc", None)
            if not out["req"] or out["pid"] >= len(out["names"]):
                return None
    elif kind == "freespace":
        out["policy"] = _map(d.get("policy"), _FIT)
        out["holes"] = _unscale([int(x) for x in _flatten(d.get("holes") or [])], present)
        out["reqs"] = _unscale([int(x) for x in _flatten(d.get("reqs") or [])], present)
        if not out["policy"] or not out["holes"] or not out["reqs"]:
            return None
    elif kind == "translate":
        out["table"] = [int(x) for x in _flatten(d.get("table") or [])]
        out["logical"] = int(d.get("logical", -1))
        out["page_size"] = int(d.get("page_size") or 0)
        hexes = [int(h, 16) for h in re.findall(r"0[xX]([0-9a-fA-F]+)", question)]
        if hexes and out.get("logical") not in present:
            out["logical"] = hexes[0]      # the model mis-decoded 0x0A2C as 16940
            out["hex"] = True
        if out["logical"] < 0 or out["page_size"] < 1 or not out["table"]:
            return None
    return out


def _leaf_numbers(v, keys):
    out = []
    for k in keys:
        x = v.get(k)
        if isinstance(x, list):
            for y in x:
                out.extend(y if isinstance(y, list) else [y])
        elif isinstance(x, int):
            out.append(x)
    return [n for n in out if isinstance(n, int)]


# Values that must literally appear in the question. Derived quantities and defaults
# are excluded: a disk size of 200 or a priority of 1 is often implied, not written.
# `avail` is included deliberately: the one genuine misreading in testing was an
# invented Available vector ([10, 5, 7] for a problem stating [3, 3, 2]), which is
# precisely the error this check exists to catch. A question that gives TOTAL instead
# of Available will fail grounding and fall back to the model answering for itself -
# declining is the safe direction.
_MUST_APPEAR = {"scheduling": [], "paging": ["refs", "frames"],
                "disk": ["reqs", "head"], "banker_safety": ["alloc", "maxm", "avail"],
                "banker_request": ["alloc", "maxm", "avail", "req"],
                "freespace": ["holes", "reqs"], "translate": ["table", "logical"]}


def grounded(v, question):
    """Is every stated parameter actually present in the question?

    This is what makes delegation trustworthy. An execution error is invisible - the
    model produces a clean table from a wrong schedule. An extraction error is
    checkable: the Banker's failure in testing invented Available = [10, 5, 7] for a
    problem that says [3, 3, 2], and that is caught here."""
    present = numbers_in(question)
    if v["kind"] == "scheduling":
        need = [n for p in v["procs"] for n in p[1:3]]
    else:
        need = _leaf_numbers(v, _MUST_APPEAR.get(v["kind"], []))
    missing = [n for n in need if n not in present]
    return (not missing), missing


def parse_json(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def extract(question, ask, tries=3):
    """Parameters for a question, or (None, reason).

    `ask(system, user)` returns the model's reply. Retried with the failure named,
    because the observed errors (a pair instead of a flat list, an invented vector)
    are ones a model corrects when told."""
    note = ""
    for attempt in range(tries):
        raw = ask(EXTRACT_PROMPT + note, question)
        v = normalise(parse_json(raw), question)
        if v is None:
            note = "\n\nYour last answer was not valid JSON in one of the shapes above. Output only the JSON object."
            continue
        if v["kind"] not in SOLVER_KINDS:
            return v, "not a solver kind"
        # "can P0's request for (0,2,0) be granted?" is a REQUEST question. When the
        # model returns banker_safety and simply omits the request vector there is
        # nothing to detect it by, and the answer that comes back is a safe sequence -
        # a confident answer to a question nobody asked. Ask again, pointedly.
        if v["kind"] == "banker_safety" and _asks_request(question):
            note = ("\n\nThat problem asks whether a REQUEST can be granted. Use the "
                    "banker_request shape and include \"req\" (the requested vector) "
                    "and \"req_proc\" (the process making it).")
            continue
        ok, missing = grounded(v, question)
        if ok:
            return v, f"ok (attempt {attempt + 1})"
        note = (f"\n\nYour last answer used numbers that are not in the problem: "
                f"{missing[:6]}. Copy the values exactly as written.")
    return None, "extraction could not be grounded in the question"


def solve(question, ask):
    """(worked_solution, meta). The numbers come from the simulator, so they are right
    whenever extraction is grounded; otherwise this declines and the caller falls back
    to the model answering for itself."""
    v, why = extract(question, ask)
    if v is None:
        return None, dict(delegated=False, reason=why)
    if v["kind"] not in SOLVER_KINDS:
        return None, dict(delegated=False, reason=v["kind"])
    try:
        text = render_solution(v)
    except Exception as e:                      # a shape the simulator rejects
        return None, dict(delegated=False, reason=f"simulator refused: {type(e).__name__}: {e}")
    return text, dict(delegated=True, kind=v["kind"], reason=why, params=v)
