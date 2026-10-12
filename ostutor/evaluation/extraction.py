"""Score a parameter extraction against the ground-truth simulator parameters.

"Extraction accuracy" here means: the fields that determine the answer were read
correctly. A field that cannot change the answer is not compared — the quantum of a
non-Round-Robin schedule, the disk size for FCFS, process names — because counting
those would report reading errors that no student would ever see.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

_DIRECTIONAL = {"SCAN", "LOOK", "CSCAN", "CLOOK"}
_END_AWARE = {"SCAN", "CSCAN"}            # these travel to the disk edge
_PRIORITY = {"PRIORITY", "PRIORITYP", "PRIORITY_P", "PREEMPTIVEPRIORITY"}


def _canon(s: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(s).upper())


def answer_fields(kind: str, truth: Mapping) -> list[str]:
    """The truth fields that determine the answer for this question."""
    if kind == "scheduling":
        f = ["algo", "procs"]
        if _canon(truth.get("algo")) == "RR":
            f.append("quantum")
        return f
    if kind == "paging":
        return ["policy", "refs", "frames"]
    if kind == "disk":
        f = ["policy", "reqs", "head"]
        pol = _canon(truth.get("policy"))
        if pol in _DIRECTIONAL:
            f.append("direction")
        if pol in _END_AWARE:
            f.append("size")
        return f
    if kind == "banker_safety":
        return ["alloc", "maxm", "avail"]
    if kind == "banker_request":
        return ["alloc", "maxm", "avail", "req", "pid"]
    if kind == "freespace":
        return ["policy", "holes", "reqs"]
    if kind == "translate":
        return ["logical", "page_size", "table"]
    raise ValueError(f"no answer fields defined for kind {kind!r}")


def _procs(value: Any, with_priority: bool) -> list[tuple]:
    out = []
    for p in value or []:
        p = list(p)
        row = (int(p[1]), int(p[2]))                 # arrival, burst; names ignored
        if with_priority:
            row += (int(p[3]) if len(p) > 3 else 1,)
        out.append(row)
    return out


def _same(field: str, got: Any, want: Any, truth: Mapping) -> bool:
    if field in ("algo", "policy", "direction"):
        return _canon(got) == _canon(want)
    if field == "procs":
        pri = _canon(truth.get("algo")) in {_canon(x) for x in _PRIORITY}
        return _procs(got, pri) == _procs(want, pri)
    if field in ("alloc", "maxm"):
        return [list(map(int, r)) for r in got or []] == [list(map(int, r)) for r in want]
    if isinstance(want, list):
        return [int(x) for x in got or []] == [int(x) for x in want]
    try:
        return int(got) == int(want)
    except (TypeError, ValueError):
        return got == want


def fields_match(extracted: Mapping | None, truth: Mapping) -> tuple[bool, list[str]]:
    """(all answer-determining fields correct, list of wrong fields).

    A wrong `kind` is reported as the single mismatch `kind`: nothing else is
    comparable when the question was read as a different problem.
    """
    if not extracted:
        return False, ["missing"]
    kind = truth["kind"]
    if extracted.get("kind") != kind:
        return False, ["kind"]
    wrong = [f for f in answer_fields(kind, truth)
             if not _same(f, extracted.get(f), truth.get(f), truth)]
    return not wrong, wrong
