"""OS-Solve evaluation harness.

The single highest-value missing piece: without it, "peak accuracy" is a hope
rather than a target. Nothing else in this project is measurable until a baseline
exists.

It is cheap to build because the simulators already contain the oracle. The same
verifier that certifies a training target grades a model's output, so grading is
exact rather than an LLM-judge approximation.

Three graded tiers:

  FINAL ANSWER   exact match on the parsed numeric/structural answer.
  STEP TRACE     do the intermediate values the model showed agree with the
                 simulator's? A model that reaches the right number by wrong
                 reasoning is not a tutor, and answer-only scoring cannot tell.
  OOD            held-out framings the training generator never produced. If
                 in-distribution accuracy is high and OOD accuracy collapses, the
                 model learned the template rather than the procedure - the exact
                 failure a same-generator split cannot detect.

Banker's safe sequences are validated, never string-matched: they are not unique,
and a grader comparing against one published key marks correct work wrong.
"""
import json
import re

from ..simulators import formulas
from ..simulators.banker import is_safe
from ..simulators.banker import request as banker_request
from ..simulators.banker import verify_sequence
from ..simulators.memory import disk_schedule, fit_allocation, page_replacement, translate
from ..simulators.scheduling import ALGORITHMS, Proc

_NUM = re.compile(r"-?\d+(?:\.\d+)?")
# A sequence looks like < A, B, C >: identifier-ish tokens only. A naive
# `<[^>]+>` also matches "<= Work [5, 5, 5] ->" from the step trace, which is how
# banker grading silently scored 0.0 against its own reference solutions.
# \w covers alphanumeric process names including bare numeric PIDs (1543), while
# requiring COMMA-SEPARATED bare tokens rejects "<= Work [5, 5, 5] ->" - the '<'
# of '<=' is followed by '=', which is not \w, so no match starts there.
_SEQ = re.compile(r"<\s*(\w+(?:\s*,\s*\w+)+)\s*>")


def _answer_number(text, *keys):
    """Pull the number the model presented as its FINAL answer for a keyword.

    Takes the last number on the matching line, not the first: a line like
    "Average waiting time = (13 + 13 + 3 + 9) / 4 = **9.5**" begins with the
    terms of the sum, and reading the first number scores the working instead of
    the result.
    """
    best = None
    # v3.0 answer lines carry several quantities ("average waiting time = 6.5,
    # average turnaround time = 13.0"): take the number that follows the keyword's
    # "=" or ":" (the last such occurrence), not the last number on the line.
    # The quantity's segment runs from the keyword to the next ", <word>" (the next
    # quantity) or the end of the line; its answer is the last number in it, so
    # "Average waiting time = 48 / 5 = **9.6**" reads 9.6, not 48.
    for k in keys:
        segs = re.findall(re.escape(k) + r"[^=:\n\d]{0,40}[=:]([^\n]*?)(?=,\s*[A-Za-z]|\n|$)",
                          text, re.I)
        for seg in reversed(segs):
            seg = re.sub(r"0x[0-9a-fA-F]+", " ", seg)       # "13474 (0x34a2)" -> 13474
            nums = re.findall(r"-?\d[\d,]*(?:\.\d+)?", seg)
            if nums:
                return float(nums[-1].replace(",", ""))
    for line in text.splitlines():
        low = line.lower()
        if any(k.lower() in low for k in keys):
            nums = _NUM.findall(line)
            if nums:
                best = float(nums[-1])
    if best is None:                      # fall back to a window after the keyword
        low = text.lower()
        for k in keys:
            m = re.search(re.escape(k.lower()), low)
            if m:
                nums = _NUM.findall(text[m.end():m.end() + 120])
                if nums:
                    best = float(nums[-1])
    return best


def _sequence_after(text, *keys):
    """Find the safe sequence the model stated, preferring one near a keyword."""
    for line in text.splitlines():
        if any(k.lower() in line.lower() for k in keys):
            m = _SEQ.search(line)
            if m:
                return [s.strip() for s in m.group(1).split(",") if s.strip()]
    matches = _SEQ.findall(text)
    if matches:
        return [s.strip() for s in matches[-1].split(",") if s.strip()]
    return []


_DENY = re.compile(r"\b(?:not\s+(?:be\s+)?granted|cannot\s+be\s+granted|deny|denied|"
                   r"must\s+wait|refused?|rejected?)\b", re.I)
_GRANT = re.compile(r"\bgrant(?:ed)?\b", re.I)
_CONCLUDE = re.compile(r"conclusion|final|therefore|thus|hence|answer|decision|result",
                       re.I)
_CONDITIONAL = re.compile(r"\b(?:if|unless|whether)\b", re.I)


def _request_decision(output):
    """The CONCLUDED decision on a Banker's request, or None.

    Only a concluding line that states a decision counts, and conditional lines
    ("... could be granted if ...") are skipped. Matching "grant"/"deny" anywhere
    scored truncated mid-derivation traces as correct and read "cannot be granted"
    as a grant; negations are checked before "grant" for the same reason."""
    lines = [l for l in output.splitlines() if _CONCLUDE.search(l)
             and not _CONDITIONAL.search(l)
             and (_DENY.search(l) or _GRANT.search(l))]
    if not lines:
        return None
    span = lines[-1]
    if _DENY.search(span):
        return False
    if _GRANT.search(span):
        return True
    return None


_UNSAFE = re.compile(r"\bunsafe\b|not\s+(?:in\s+)?(?:a\s+)?safe|no\s+safe\s+sequence", re.I)


def _final_lines(output, n=8):
    return "\n".join([l for l in output.splitlines() if l.strip()][-n:])


def _close(a, b):
    a, b = float(a), float(b)
    return abs(a - b) <= max(0.011, 0.005 * abs(b))


def _grade_formula(v, output):
    """Every expected quantity must appear in the concluding lines (tolerance 0.5%,
    at least 0.011 absolute - answers are shown rounded to 4 decimals)."""
    exp = formulas.expected(v)
    tail = _final_lines(output)
    m = re.findall(r"\*\*Answer:?\*?\*?(.*)", output)
    if m:
        tail = m[-1] + "\n" + tail
    nums = [float(x.replace(",", "")) for x in re.findall(r"-?\d[\d,]*(?:\.\d+)?(?:e-?\d+)?", tail)]
    ok = all(any(_close(x, val) for x in nums) for val in exp.values())
    return ok, {k: float(x) for k, x in exp.items()}


_ASKS_BACK = re.compile(r"\?|please (?:share|give|provide|tell)|could you", re.I)


def grade(record, output):
    """Grade one model output against the simulator. Returns a dict."""
    v = record["verify"]
    kind = v["kind"]
    res = dict(kind=kind, final_correct=False, steps_checked=0, steps_correct=0)

    if kind == "scheduling":
        procs = [Proc(p, a, b, pr) for p, a, b, pr in v["procs"]]
        truth = ALGORITHMS[v["algo"]](procs, quantum=v["quantum"])
        got_w = _answer_number(output, "average waiting", "avg waiting", "mean waiting",
                               "avg. waiting", "AWT")
        got_t = _answer_number(output, "average turnaround", "avg turnaround",
                               "mean turnaround", "avg. turnaround", "ATAT", "TAT")
        res["final_correct"] = (got_w is not None
                                and abs(got_w - truth.avg_waiting) < 0.011)
        res["expected"] = truth.avg_waiting
        res["got"] = got_w
        # step check: every per-process completion time the model stated
        for row in truth.table:
            pat = re.search(rf"{re.escape(row['pid'])}\D{{0,80}}?(\d+)", output)
            if pat:
                res["steps_checked"] += 1
                if int(pat.group(1)) == row["completion"] or int(pat.group(1)) == row["burst"]:
                    res["steps_correct"] += 1
        if got_t is not None:
            res["turnaround_correct"] = abs(got_t - truth.avg_turnaround) < 0.011

    elif kind == "banker_safety":
        truly_safe, _, _ = is_safe(v["avail"], v["maxm"], v["alloc"], v.get("names"))
        claims_unsafe = bool(_UNSAFE.search(_final_lines(output, 6)))
        if not truly_safe:
            ok, why = claims_unsafe, "expected UNSAFE"
        else:
            seq = _sequence_after(output, "safe sequence", "sequence is", "sequence:")
            ok, why = verify_sequence(seq, v["avail"], v["maxm"], v["alloc"], v.get("names"))
            ok = ok and not claims_unsafe
        res["final_correct"] = ok
        res["detail"] = why
        res["steps_checked"] = 1
        res["steps_correct"] = int(ok)

    elif kind == "banker_request":
        truth, _ = banker_request(v["avail"], v["maxm"], v["alloc"], v["pid"],
                                  v["req"], v.get("names"))
        got = _request_decision(output)
        res["final_correct"] = got is not None and got == truth
        res["expected"] = truth
        res["got"] = got

    elif kind == "paging":
        truth = page_replacement(v["refs"], v["frames"], v["policy"])["faults"]
        # Targeted: the integer immediately after "faults". Taking the last number
        # on the line instead picks up "hit ratio = 0.25" from the same sentence.
        got = None
        for m in re.finditer(r"(?:page\s+)?faults?\s*(?:=|:|is|are)?\s*\**\s*(\d+)",
                             output, re.I):
            got = int(m.group(1))
        res["final_correct"] = got is not None and got == truth
        res["expected"] = truth
        res["got"] = got

    elif kind == "disk":
        truth = disk_schedule(v["reqs"], v["head"], v["policy"], v["size"],
                              v["direction"])["total_head_movement"]
        got = _answer_number(output, "total head movement", "head movement", "total distance")
        res["final_correct"] = got is not None and int(got) == truth
        res["expected"] = truth
        res["got"] = got

    elif kind == "translate":
        truth = translate(v["logical"], v["page_size"], v["table"])["physical"]
        got = _answer_number(output, "physical address")
        res["final_correct"] = got is not None and int(got) == truth
        res["expected"] = truth
        res["got"] = got

    elif kind == "freespace":
        # v3.0 renders "**Placement:** 212 KB -> hole 4; 339 KB -> WAIT" with holes
        # numbered from 1; the bracketed list form is still accepted.
        truth = fit_allocation(v["holes"], v["reqs"], v["policy"])["placement"]
        got = None
        lines = [l for l in output.splitlines() if re.search(r"placement", l, re.I)]
        if lines:
            line = lines[-1]
            toks = re.findall(r"hole\s*#?(\d+)|partition\s*#?(\d+)|\b(wait|none|not allocated)\b",
                              line, re.I)
            if toks:
                got = [int(a or b) if (a or b) else None for a, b, _ in toks]
            else:
                m = re.search(r"\[([^\]]*)\]", line)
                if m:
                    got = [None if t.strip().lower() in ("none", "null", "-", "wait")
                           else int(t) for t in m.group(1).split(",") if t.strip()]
        res["final_correct"] = got is not None and got == truth
        res["expected"] = truth
        res["got"] = got

    elif kind in formulas.KINDS:
        ok, exp = _grade_formula(v, output)
        res["final_correct"] = ok
        res["expected"] = exp

    elif kind == "clarify":
        # Correct behaviour: ask for the missing input, produce no numeric answer.
        res["final_correct"] = bool(_ASKS_BACK.search(output)) and "**Answer:" not in output

    res["step_accuracy"] = (res["steps_correct"] / res["steps_checked"]
                            if res["steps_checked"] else None)
    return res


def load_suite(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f]


def summarise(results):
    n = len(results)
    if not n:
        return {}
    by_kind = {}
    for r in results:
        b = by_kind.setdefault(r["kind"], dict(n=0, correct=0))
        b["n"] += 1
        b["correct"] += int(r["final_correct"])
    checked = [r for r in results if r["steps_checked"]]
    return dict(
        n=n,
        final_answer_accuracy=round(sum(r["final_correct"] for r in results) / n, 4),
        step_accuracy=(round(sum(r["steps_correct"] for r in checked)
                             / max(sum(r["steps_checked"] for r in checked), 1), 4)
                       if checked else None),
        by_topic={k: dict(n=v["n"], accuracy=round(v["correct"] / v["n"], 4))
                  for k, v in sorted(by_kind.items())})
