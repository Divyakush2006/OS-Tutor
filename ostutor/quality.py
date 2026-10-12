"""Deterministic quality scoring.

No model forward passes, so a rerun with the same config gives byte-identical
scores and the manifest is meaningful. Scoring is per-category because the
categories are not the same kind of object: a 40-character shell command is
excellent, a 40-character tutoring turn is not.

`band()` rewards RIGHT-SIZED rather than LONGEST. Length-biased scoring quietly
selects for verbose answers and teaches the model to ramble.

Step detection counts three notations, measured against the real corpus. A
numbered-list-only pattern matched ZERO of 6,900 generated procedural solutions,
handing every one a 40% score penalty and letting the quality gate drop the most
valuable data in favour of worse.
"""
import re

_TOK = re.compile(r"[A-Za-z0-9_]+")
_PIPE = re.compile(r"[|><]|&&")
_FLAG = re.compile(r"(?<!\w)-{1,2}[A-Za-z][\w-]*")
_HEDGE = re.compile(r"\b(the answer is|therefore the answer|so the answer)\b", re.I)
_STEP_NUM = re.compile(r"(?m)^\s*(?:step\s*)?\d+[.):]\s", re.I)
_STEP_HDR = re.compile(r"(?mi)^\s*\**\s*step\s*\d+\b")
_STEP_BUL = re.compile(r"(?m)^\s*[-*]\s+\S")
_TABLE = re.compile(r"(?m)^\s*\|.*\|\s*$")
_EXAMPLE = re.compile(r"(for example|e\.g\.|consider|suppose|imagine|\*\*example)", re.I)
_MISCONCEPT = re.compile(r"(misconception|common error|students? (?:think|believe|say)"
                         r"|usual error|goes wrong)", re.I)


_TABLE_SEP = re.compile(r"(?m)^\s*\|[\s:|-]+\|\s*$")


def count_steps(text):
    return (len(_STEP_NUM.findall(text)) + len(_STEP_HDR.findall(text))
            + len(_STEP_BUL.findall(text)))


def visible_steps(text):
    """Discrete working steps shown, INCLUDING trace-table rows.

    A page-replacement solution is a table with one row per reference - that IS
    the step-by-step working. Counting only bullets and 'Step N' headings scored
    every paging solution as step-less, and the cleaner dropped all ~1,400 of
    them. Table DATA rows (header and separator excluded) count as steps.
    """
    rows = len(_TABLE.findall(text)) - len(_TABLE_SEP.findall(text))
    tables = len(_TABLE_SEP.findall(text))          # one header row per table
    return count_steps(text) + max(0, rows - tables)


def ttr(text):
    w = [x.lower() for x in _TOK.findall(text)]
    return len(set(w)) / len(w) if w else 0.0


def band(x, lo, hi):
    if x < lo:
        return max(0.0, x / lo) if lo else 0.0
    if x > hi:
        return max(0.0, hi / x) if x else 0.0
    return 1.0


def _parts(r):
    u = " ".join(m["content"] for m in r["messages"] if m["role"] == "user")
    a = [m["content"] for m in r["messages"] if m["role"] == "assistant"]
    return u, a


def score_shell(r):
    u, asst = _parts(r); a = asst[-1]
    s = 0.35 * band(len(u), 25, 200)
    s += 0.20 * band(len(a), 5, 160)
    s += 0.15 * min(1.0, (len(_FLAG.findall(a)) + len(_PIPE.findall(a))) / 3)
    s += 0.10 * ttr(u)
    if r["lineage"].get("verified"):
        s += 0.20
    return max(0.0, min(1.0, s))


def score_tutoring(r):
    """Tutoring data comes in two shapes, and the score must not confuse shape with
    quality. A MathDial row is a long dialogue of short teacher moves; a v3.0
    self-distilled OS row is ONE exchange in which the student states the problem and
    their wrong attempt and the tutor diagnoses it in full.

    Scoring assumed the first shape - 0.30 for having 6-16 messages, a 60-400
    character band per turn, and a bonus for a MathDial-only lineage field. A
    single-exchange OS row therefore scored about 0.30 against a 0.46 floor, and the
    quality gate culled nearly all of them. What is actually being judged is: does the
    tutor ask rather than tell, is the reply the right size FOR ITS SHAPE, and is the
    language varied."""
    _, asst = _parts(r)
    if not asst:
        return 0.0
    single = len(r["messages"]) <= 2
    mean_len = sum(map(len, asst)) / len(asst)
    # Depth: one real exchange is sufficient; more turns are not better as such.
    s = 0.20 * (1.0 if single else band(len(r["messages"]), 4, 16))
    # Right-sized for the shape it is: one reply carries the whole diagnosis, a turn
    # inside a dialogue carries a single move.
    s += 0.25 * (band(mean_len, 400, 4000) if single else band(mean_len, 60, 400))
    # Socratic: the tutor asks. This is the behaviour the category exists to teach.
    s += 0.30 * (sum(1 for a in asst if "?" in a) / len(asst))
    s += 0.25 * ttr(" ".join(asst))
    if _HEDGE.search(asst[0]):
        s -= 0.25
    return max(0.0, min(1.0, s))


def score_procedural(r):
    """Auditable worked solutions: visible steps and intermediate state are the
    point. An answer-only target defeats the whole design."""
    u, asst = _parts(r); a = asst[-1]
    s = 0.22 * band(len(u), 60, 900)
    s += 0.18 * band(len(a), 200, 2500)
    s += 0.25 * min(1.0, count_steps(a) / 6)
    s += 0.15 * min(1.0, len(_TABLE.findall(a)) / 4)
    s += 0.20 if r["lineage"].get("verified") else 0.0
    return max(0.0, min(1.0, s))


def score_conceptual(r):
    """Explanations that name the misconception and give an example beat
    definitions, because definitions do not move a student's belief."""
    u, asst = _parts(r); a = asst[-1]
    s = 0.25 * band(len(a), 300, 2000)
    s += 0.20 * ttr(a)
    s += 0.15 * band(len(u), 30, 300)
    s += 0.15 * min(1.0, a.count("\n\n") / 3)
    s += 0.15 if _EXAMPLE.search(a) else 0.0
    s += 0.10 if _MISCONCEPT.search(a) else 0.0
    return max(0.0, min(1.0, s))


def score_replay(r):
    txt = " ".join(m["content"] for m in r["messages"])
    s = 0.40 * band(len(txt), 300, 4000)
    s += 0.35 * ttr(txt)
    s += 0.15 * band(len(r["messages"]), 2, 8)
    s += 0.10
    return max(0.0, min(1.0, s))


SCORERS = dict(shell=score_shell, tutoring=score_tutoring, replay=score_replay,
               procedural=score_procedural, conceptual=score_conceptual)


def score_all(records):
    for r in records:
        r["quality"] = round(SCORERS.get(r["category"], score_replay)(r), 4)
    return records
