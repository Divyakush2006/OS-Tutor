"""Sanitise and fact-check self-distilled answers (v3.0).

Self-distilled targets inherit the base model's style AND its mistakes. This
module keeps the former and removes the latter:

  SANITISE  emoji, sycophantic openers ("Great question!") and chatty sign-offs
            ("Let me know if...") are removed, so the tutor's voice is professional.
            Content is never rewritten.
  REJECT    answers cut off at the token limit, and answers that assert a known
            OS misconception (each rule below is a mistake that appears in real
            student answers and LLM output). A rejected answer is dropped, never
            "repaired", and every rejection is logged for review.
  TUTOR     a Socratic reply to a student's WRONG attempt must not reveal the
            correct final answer and must not tell the student they are right.
"""
import re

_EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️‍⃣"
                    "←-⇿⌀-⏿■-◿]")

# One filler prefix. Applied repeatedly, because they stack:
# "Absolutely! Let's break down the difference between X and Y." is three of them.
# The clause forms stop at sentence punctuation so they cannot eat real content.
_FILLER = re.compile(
    r"^[ \t]*(?:and[ \t]+)?(?:"
    r"(?:great|excellent|good|very[ \t]+good|fantastic|awesome|nice|important)[ \t]+"
    r"(?:revision[ \t]+)?(?:question|topic|point|focus|area)s?[!.,]*"
    # A bare interjection: "Great! You're working on a Round Robin problem...".
    # Requires the exclamation mark, so "Good practice is to..." is untouched.
    r"|(?:great|excellent|good|nice|awesome|fantastic|well[ \t]+spotted)[!]+"
    r"|(?:sure|certainly|absolutely|of[ \t]+course|okay|ok|alright|yes|indeed)[!.,]*"
    r"|let'?s[ \t]+(?:break[ \t]+(?:it|this|them)[ \t]+down[^\n.!:;]*"
    r"|break[ \t]+down[^\n.!:;]*"
    r"|dive[ \t]+(?:in|into)[^\n.!:;]*"
    r"|(?:go|walk)[ \t]+through[^\n.!:;]*"
    r"|(?:explore|unpack|clarify|start[ \t]+with)[^\n.!:;]*"
    r")[.:!]*"
    r")[ \t]*", re.I)
# A markdown horizontal rule at the very top is always noise.
_LEAD_RULE = re.compile(r"^(?:\s*(?:-{3,}|\*{3,}|_{3,})[ \t]*(?:\n|$))+")
# What an opener leaves behind: "Great question - this is a core idea." -> "- this is..."
_LEAD_DANGLE = re.compile(r"^[ \t]*[-–—:,;][ \t]*")
_SIGNOFF = re.compile(r"\n+[^\n]*(?:let me know|hope this helps|feel free to|would you like|"
                      r"happy (?:learning|studying)|good luck)[^\n]*\s*$", re.I)


def _top(s):
    """Strip leading whitespace and any stacked markdown horizontal rules, to a
    fixed point: removing a rule exposes the blank line that followed it."""
    prev = None
    while s != prev:
        prev = s
        s = _LEAD_RULE.sub("", s.lstrip()).lstrip()
    return s


def _strip_openers(text):
    """Remove stacked conversational openers without leaving a fragment behind.

    The v3.0 audit found the previous single-shot regex did real damage: stripping
    "Great question" from "Great question - this is a core concept." left 42 answers
    starting with a dangling dash, and 65 starting with a bare "---".

    A strip is therefore kept only when the opener ENDED CLEANLY - at sentence
    punctuation or at the end of a line - or when it left a dangling connective,
    which is then removed too. Anything else means the sentence ran on into real
    content ("Let's break this down **simply**, like you're new to this") and
    removing the opener would leave a fragment. Half an opener is worse than a
    whole one, so in that case the text is left alone.
    """
    t = _top(text)
    for _ in range(4):
        m = _FILLER.match(t)
        if not m or not m.end():
            break
        rest = t[m.end():]
        op = m.group(0).rstrip()
        if op.endswith((".", "!", ",")):
            clean = True                     # the opening sentence or clause closed
        elif op.endswith(":"):
            # A colon only ends the opener if nothing follows it on the line. In
            # "Let's break down X and walk through an example: **what read() does**."
            # the colon INTRODUCES the content, and cutting there leaves a fragment.
            clean = rest[:1] in ("", "\n")
        else:
            clean = rest == "" or rest.startswith("\n\n")   # opener alone on its line
        dangled = bool(_LEAD_DANGLE.match(rest))
        if not (clean or dangled):
            break
        cand = _top(_LEAD_DANGLE.sub("", rest, count=1))
        if not cand:
            break
        t = cand
    return t


def sanitise(text):
    t = _EMOJI.sub("", text)
    t = re.sub(r"(#+)\s{2,}", r"\1 ", t)
    t = re.sub(r"[ \t]{2,}(?=\S)", " ", t)
    t = _strip_openers(t)
    for _ in range(2):
        t = _SIGNOFF.sub("", t).rstrip()
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r"(\n\s*(?:-{3,}|\*{3,})\s*)+$", "", t).rstrip()
    if not t:
        return t
    # Capitalise the first letter, reaching inside a leading bold span: removing
    # "Great question -" from "Great question - **copy-on-write** is ..." leaves a
    # correct sentence that merely starts lower-case.
    m = re.match(r"(\*{1,2}|`|_)?([a-z])", t)
    return t[:m.end() - 1] + m.group(2).upper() + t[m.end():] if m else t


_NEG = re.compile(r"\b(?:not|no|never|n't|doesn't|don't|cannot|without|avoid|eliminat|free of|"
                  r"immune|only if|single|one instance|may|might|necessarily)\b", re.I)
# Negation only, without the soft hedges. "may" and "might" normally protect a
# carefully qualified sentence, but for a few claims the hedge does not make the
# statement true: "a large quantum may cause starvation" is wrong either way.
_HARD_NEG = re.compile(r"\b(?:not|no|never|n't|doesn't|don't|cannot|without|avoid|eliminat|"
                       r"free of|immune)\b", re.I)
_HEDGE_IMMUNE = {"rr_large_q_starves"}

# (name, pattern asserting a misconception[, exception pattern]). A sentence is
# flagged only if it matches, contains no negation/hedge ("LRU does NOT suffer from
# Belady's" is fine) and does not match its exception.
MISCONCEPTIONS = [
    ("lru_belady", re.compile(r"\b(?:LRU|optimal|OPT|stack algorithm)s?\b[^.]{0,80}"
                              r"\b(?:suffers?|exhibits?|affected by)\b[^.]{0,40}Belady", re.I)),
    ("unsafe_is_deadlock", re.compile(r"unsafe state[^.]{0,40}\b(?:is|means|implies)\b[^.]{0,15}"
                                      r"\bdeadlock", re.I)),
    ("cycle_always_deadlock", re.compile(r"\bcycle\b[^.]{0,60}\b(?:always|guarantees?|definitely)\b"
                                         r"[^.]{0,30}deadlock", re.I)),
    ("seg_internal_frag", re.compile(r"\bsegmentation\b[^.]{0,100}\b(?:suffers?|causes?|leads? to|"
                                     r"results? in|has)\b[^.]{0,20}internal fragmentation", re.I)),
    ("paging_external_frag", re.compile(r"\bpaging\b[^.]{0,80}\b(?:suffers?|causes?|leads? to|"
                                        r"results? in)\b[^.]{0,20}external fragmentation", re.I)),
    ("sstf_optimal", re.compile(r"\bSSTF\b[^.]{0,60}\b(?:is optimal|optimal|minimi[sz]es? (?:the )?"
                                r"(?:total )?(?:seek|head))", re.I)),
    # The misconception is "fork() RETURNS the child's PID TO THE CHILD" (it returns 0
    # there). "the child gets its own PID" is TRUE and must not be flagged, so the
    # sentence must mention a return value, the child, and not mention zero.
    ("fork_child_pid", re.compile(r"\bfork\(\)?[^.]{0,90}\breturns?\b[^.]{0,60}\bPID\b"
                                  r"[^.]{0,40}\b(?:in|to|for)\s+the\s+child\b"
                                  r"|(?:in|to|for)\s+the\s+child[^.]{0,50}\breturns?\b"
                                  r"[^.]{0,30}\b(?:the\s+)?(?:child'?s?\s+)?PID\b", re.I),
     re.compile(r"\b(?:0|zero)\b")),   # "...the child's PID in the parent and 0 in the child"
    ("rr_large_q_sjf", re.compile(r"(?:large|infinite|very big) (?:time )?quantum[^.]{0,60}"
                                  r"\b(?:becomes?|behaves? like|reduces? to)\b[^.]{0,10}\bSJF\b", re.I)),
    ("mutex_equals_semaphore", re.compile(r"\bmutex\b[^.]{0,20}\bis (?:exactly )?the same as\b[^.]{0,20}"
                                          r"\b(?:binary )?semaphore", re.I)),
    # A large quantum degenerates Round Robin to FCFS: the convoy effect and poor
    # response time, NOT starvation. Every process is still served in bounded time.
    ("rr_large_q_starves", re.compile(r"\b(?:large|larger|long|longer|big|bigger|increasing|"
                                      r"infinite)\b[^.]{0,20}(?:time\s+)?quantum\b[^.]{0,120}"
                                      r"\bstarv\w+"
                                      r"|\bstarv\w+[^.]{0,80}\b(?:large|larger|long|longer|big|"
                                      r"bigger)\b[^.]{0,20}(?:time\s+)?quantum\b", re.I)),
]


# The correct fact for each rule above, phrased so it can be handed straight back to
# the model as a correction.
#
# Rejecting a misconception from TRAINING data removes the error; it does not teach the
# truth. The Belady correction is in the shipped dataset exactly once, and the trained
# model still answers "Yes, LRU suffers from Belady's anomaly" - one row cannot
# outweigh a confident pretrained prior. Serving therefore checks the drafted answer
# and, when a known misconception appears, re-asks with the fact stated.
CORRECTIONS = {
    "lru_belady":
        "LRU never suffers from Belady's anomaly: it is a stack algorithm, so the pages "
        "held with n frames are always a subset of those held with n+1. FIFO can suffer "
        "from it; the classic example is 1 2 3 4 1 2 5 1 2 3 4 5, which gives 9 faults "
        "with 3 frames and 10 with 4.",
    "unsafe_is_deadlock":
        "An unsafe state is not a deadlock. It means no safe sequence is guaranteed, so "
        "deadlock BECOMES POSSIBLE; the system may still complete if processes do not "
        "request their maximum.",
    "cycle_always_deadlock":
        "A cycle in the resource-allocation graph guarantees deadlock only when every "
        "resource type has a single instance. With multiple instances a cycle is "
        "necessary but not sufficient.",
    "seg_internal_frag":
        "Segmentation causes EXTERNAL fragmentation, because segments vary in size and "
        "leave gaps between them. Internal fragmentation is the paging problem, from "
        "rounding the last page up to a fixed frame.",
    "paging_external_frag":
        "Paging eliminates external fragmentation, because every frame is the same size "
        "and any free frame will do. Its cost is INTERNAL fragmentation in the last page.",
    "sstf_optimal":
        "SSTF is greedy, not optimal: it minimises the NEXT seek only, and can starve "
        "requests at the far end of the disk. Minimising total head movement over a whole "
        "queue requires looking further ahead.",
    "fork_child_pid":
        "fork() returns the child's PID to the PARENT and 0 to the CHILD (and a negative "
        "value on failure). That asymmetry is how the two processes tell each other apart.",
    "rr_large_q_sjf":
        "Round Robin with a very large quantum degenerates to FCFS, not to SJF: each "
        "process simply runs to completion in arrival order. Nothing in RR ever inspects "
        "burst length.",
    "rr_large_q_starves":
        "A large quantum does not starve anyone. Round Robin stays starvation-free "
        "because the queue is cyclic; a large quantum degenerates it to FCFS, whose cost "
        "is the convoy effect and poor response time for short jobs.",
    "mutex_equals_semaphore":
        "A mutex is not simply a binary semaphore: a mutex has an OWNER and must be "
        "released by the thread that acquired it, which is what makes priority "
        "inheritance possible. A binary semaphore may be signalled by any thread.",
}


def _units(text):
    """Sentences, plus each pair of adjacent lines joined.

    Markdown splits a claim across lines: "- **Large quantum**:" then "- ... but may
    cause starvation of short processes." Neither line holds both halves, so a
    per-sentence scan cannot see the claim. Joining adjacent lines recovers it, and
    gives any negation in either line the chance to suppress a false positive."""
    sents = re.split(r"(?<=[.!?])\s+|\n", text)
    lines = [l for l in (x.strip() for x in text.splitlines()) if l]
    return sents + [f"{a} {b}" for a, b in zip(lines, lines[1:])]


_QUESTION = re.compile(r"[^.?!\n]*\?")
NEG_WINDOW = 30   # characters before a claim that can negate it ("does not suffer from")
# A hedge just AFTER the claim also undoes it: "an unsafe state means deadlock is
# POSSIBLE". Negation after the claim does not: in "suffers from internal fragmentation
# but not external" the "not" belongs to the next clause.
_AFTER_HEDGE = re.compile(r"\b(?:possible|possibly|possibility|may|might|could|risk)\b", re.I)


def _negated(neg, unit, m):
    """Serving scope: a negation counts only inside the claim or just before it.

    Sentence-wide negation let the probes through both ways. "Segmentation suffers from
    internal fragmentation but not external" passed because of the "not" in the other
    clause (a miss), and question headings ("Does a cycle always indicate deadlock?")
    were read as assertions (false alarms)."""
    return bool(neg.search(unit[max(0, m.start() - NEG_WINDOW): m.end()])
                or _AFTER_HEDGE.search(unit[m.end(): m.end() + 25]))


def fact_flags(text, serving=False):
    """Known misconceptions asserted in `text`, as (rule, sentence) pairs.

    `serving=True` is the gateway's reading: markdown emphasis removed, questions
    skipped, and negation scoped to the claim. The default is the reading the v3.0.0
    dataset was built with, kept so the build stays byte-identical."""
    if serving:
        text = re.sub(r"\*\*|__|`", "", text)
    flags, seen = [], set()
    for unit in _units(text):
        if serving:
            unit = _QUESTION.sub("", unit)
        for rule in MISCONCEPTIONS:
            name, pat = rule[0], rule[1]
            unless = rule[2] if len(rule) > 2 else None
            neg = _HARD_NEG if name in _HEDGE_IMMUNE else _NEG
            m = pat.search(unit)
            negated = m and (_negated(neg, unit, m) if serving else neg.search(unit))
            if m and not negated \
                    and not (unless and unless.search(unit)):
                key = (name, unit[:80])
                if key not in seen:
                    seen.add(key)
                    flags.append((name, unit.strip()[:200]))
    return flags


def accept_theory(rec):
    """Returns (clean_text or None, reason)."""
    if rec.get("finish_reason") not in (None, "stop"):
        return None, "truncated"
    t = sanitise(rec["answer"])
    if len(t) < 150:
        return None, "too short"
    flags = fact_flags(t)
    if flags:
        return None, "misconception:" + ",".join(sorted({f for f, _ in flags}))
    return t, "ok"


_AFFIRM = re.compile(r"^\W*(?:yes|correct|that'?s (?:right|correct)|you(?:'re| are) (?:right|correct)|"
                     r"exactly|perfect|well done)\b", re.I)


# Answer-asserting context around a number: "= 9", "is 9", "should be 9", "9 page
# faults", "average waiting time | 8.8". Matched on ONE line, so a trace table's row
# index cannot borrow a keyword from the row above it.
_ASSERTS = (r"(?:=|\bis\b|\bare\b|\bgives?\b|\bget|\bgot\b|\bobtain|\banswer\b|\btotal\b|"
            r"\bresult\b|\bshould\b|\bactually\b|\bcorrect\b|\bnot\b|\bwaiting\b|"
            r"\bturnaround\b|\bfaults?\b|\bplacement\b|\baverage\b|\bavg\b|\bAWT\b|\bTAT\b)")
_QUANTITY = r"(?:page faults?|faults?|ms\b|milliseconds?|hole)"
# Nouns that make the number an INPUT being restated, not the answer: "there are 3
# processes", "with 3 frames". "page" is excluded only when "page faults" does not
# follow, since that IS the answer for paging questions.
_INPUT_NOUN = (r"(?!\s*(?:processes|process|frames?|pages?(?!\s*faults?)|requests?|steps?|"
               r"rows?|columns?|cylinders?|tracks?|jobs|threads?|segments?|bits?|levels?|"
               r"KB|MB|GB|bytes?)\b)")


def _reveals(text, right):
    """Does the reply hand the student the correct final answer?

    A bare digit match is not enough: the v3.0 audit found good Socratic replies
    discarded because the correct fault count (11) also appeared as a row index in a
    trace table ("|11 | 1 | Hit"). So the number must appear either in an
    answer-asserting context, or emphasised - which is how an answer gets stated.
    """
    if isinstance(right, list):
        return str(right) in text or ", ".join(map(str, right)) in text
    r = float(right)
    # How the number would be written: 9, 9.0 and 9.00 are the same answer.
    forms = {f"{r:g}", str(right)}
    if r == int(r):
        forms |= {str(int(r)), f"{int(r)}.0"}
    num = "|".join(re.escape(f) for f in sorted(forms, key=len, reverse=True))
    pats = [rf"{_ASSERTS}[^\n]{{0,34}}?(?<![\d.])(?:{num})(?![\d.]){_INPUT_NOUN}",
            rf"(?<![\d.])(?:{num})(?![\d.])[^\n]{{0,16}}?{_QUANTITY}",
            rf"\*\*\s*(?:{num})\s*\*\*", rf"\\boxed\{{\s*(?:{num})"]
    return any(re.search(p, text, re.I) for p in pats)


def accept_tutor(rec):
    if rec.get("finish_reason") not in (None, "stop"):
        return None, "truncated"
    t = sanitise(rec["answer"])
    if "?" not in t:
        return None, "asks no question"
    # Checked against the RAW answer as well: sanitise() strips a leading "Yes,"
    # as a conversational opener, which would otherwise hide exactly the affirmation
    # this test exists to catch. The student's attempt is wrong by construction, so
    # any opening agreement is disqualifying.
    if _AFFIRM.search(t) or _AFFIRM.search(rec["answer"].lstrip()):
        return None, "affirms a wrong answer"
    if _reveals(t, rec["right"]):
        return None, "reveals the answer"
    if len(t) < 80:
        return None, "too short"
    return t, "ok"
