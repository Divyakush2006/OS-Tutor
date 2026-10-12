"""Normalise, scrub, validate and REPAIR - one category-aware pass.

Rules here are applied ONLY if the analysis layer classified them `verdict="defect"`.
Candidate rules the analysis marked `false_positive` are deliberately absent, and
named in the docstring so nobody re-adds them:

  "answer ends mid-sentence"        18.6% hit rate, all shell commands ending
                                    lowercase (`... | xargs grep foo /dev/null`)
  "answer shorter than question"    31.9% hit rate, all correct Socratic turns
  "{{ }} placeholder"               matches `find -exec {} +` and Clojure maps

Applying those three would have destroyed roughly 1,300 good rows.

REPAIR precedes DROP. Discarding a salvageable row is data loss, not a quality win.
"""
import re
import unicodedata
from collections import Counter

import ftfy

from .config import (MAX_CHARS_TOTAL, MIN_CHARS_ASSISTANT, MIN_CHARS_USER)
from .quality import visible_steps
from .scrub import find_secrets, redact_pii

_WS = re.compile(r"[ \t]+")
_NL3 = re.compile(r"\n{3,}")
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

_SELFREF = re.compile(
    r"\b(as an AI language model|I'm an AI|I am an AI|as a large language model"
    r"|I cannot browse|my knowledge cutoff|I don't have access to real-time)\b", re.I)
_REFUSAL = re.compile(r"^\s*(I'm sorry|I am sorry|I cannot|I can't assist|Sorry, )", re.I)
_NONLATIN = re.compile(
    r"[一-鿿぀-ヿ가-힯؀-ۿЀ-ӿऀ-ॿ]")
_KEYSTROKE = re.compile(
    r"<(Esc|Enter|Tab|Left|Right|Up|Down|Space|Ctrl|Alt|Shift|F\d{1,2}"
    r"|PageUp|PageDown|Home|End|Backspace|Delete)>", re.I)
_KEYNAME = re.compile(r"^\s*(Ctrl|Alt|Shift|Cmd)\s*\+", re.I)
_DEGEN = re.compile(
    r"^\s*(yes|no|ok(ay)?|sure|right|correct|good|great|exactly|thanks?"
    r"|yep|nope|i see|got it|perfect|true|false)\W*$", re.I)
_LEAK = re.compile(r"\b(the answer is|the final answer|equals\s*\d|=\s*\d+\s*$)", re.I)
_STEP = re.compile(r"(?m)^\s*(?:\**\s*step\s*\d+|[-*]\s+\S|\d+[.):]\s)", re.I)
_THINK = re.compile(r"<think>|</think>")


def _collapse_inline_ws(line):
    """Collapse runs of spaces/tabs INSIDE a line but preserve the leading indent.

    A global `[ \\t]+ -> " "` destroys code indentation: "    return 1" becomes
    " return 1". This corpus is full of shell scripts and code blocks."""
    stripped = line.lstrip(" \t")
    return line[:len(line) - len(stripped)] + _WS.sub(" ", stripped)


def normalise(s):
    s = ftfy.fix_text(s or "")
    s = unicodedata.normalize("NFKC", s)
    s = _CTRL.sub("", s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = "\n".join(_collapse_inline_ws(ln).rstrip() for ln in s.split("\n"))
    return _NL3.sub("\n\n", s).strip()


def merge_same_role(msgs):
    """REPAIR non-alternating dialogues by merging consecutive same-role turns."""
    out = []
    for m in msgs:
        if out and out[-1]["role"] == m["role"]:
            out[-1]["content"] = (out[-1]["content"].rstrip() + " " + m["content"].lstrip()).strip()
        else:
            out.append(dict(m))
    return out


def trim_dead_tail(msgs):
    """REPAIR dialogues ending on a degenerate teacher turn carrying no signal."""
    while len(msgs) >= 3 and msgs[-1]["role"] == "assistant" and _DEGEN.match(msgs[-1]["content"]):
        msgs = msgs[:-1]
        if msgs and msgs[-1]["role"] == "user":
            msgs = msgs[:-1]
    return msgs


def clean_records(records, shell_blocklist=None, report=None):
    shell_blocklist = shell_blocklist or {}
    drop, repair, pii = Counter(), Counter(), Counter()
    out = []

    for r in records:
        cat = r["category"]
        msgs = [dict(role=m["role"], content=normalise(m["content"])) for m in r["messages"]]
        msgs = [m for m in msgs if m["content"]]
        if len(msgs) < 2:
            drop["empty_after_normalise"] += 1
            continue

        blob = "\n".join(m["content"] for m in msgs)
        if find_secrets(blob):
            drop["secret_material"] += 1          # DESTROY, never redact
            continue
        for m in msgs:
            m["content"], hits = redact_pii(m["content"], cat)
            for k, v in hits.items():
                pii[k] += v

        # Tail normalisation runs BEFORE category dispatch. Doing it afterwards
        # lets a dropped trailing user turn RE-CREATE a dead assistant tail that
        # trim_dead_tail already removed - a real bug that once shipped.
        if msgs[0]["role"] != "user":
            drop["not_opening_user"] += 1
            continue
        while msgs and msgs[-1]["role"] != "assistant":
            msgs = msgs[:-1]
        if len(msgs) < 2:
            drop["no_assistant_turn"] += 1
            continue

        if cat == "shell":
            cmd = msgs[-1]["content"]
            if r["id"] in shell_blocklist:
                drop["shell_bash_syntax_error"] += 1; continue
            if _KEYSTROKE.search(cmd) or _KEYNAME.match(cmd):
                drop["shell_editor_keystrokes"] += 1; continue
            if len(cmd) > 500:
                drop["shell_absurd_length"] += 1; continue
            if len(msgs[0]["content"].split()) < 3:
                drop["shell_instruction_vague"] += 1; continue

        elif cat == "tutoring":
            roles = [m["role"] for m in msgs]
            if any(roles[i] == roles[i + 1] for i in range(len(roles) - 1)):
                msgs = merge_same_role(msgs)
                repair["merged_same_role_turns"] += 1
            before = len(msgs)
            msgs = trim_dead_tail(msgs)
            if len(msgs) < before:
                repair["trimmed_dead_tail"] += 1
            asst = [m["content"] for m in msgs if m["role"] == "assistant"]
            # One exchange is enough. This was `< 4` - written when OS tutoring came
            # from multi-turn template dialogues - and it silently discarded every
            # one of v3.0's self-distilled OS rows, which are a single exchange by
            # design: the student states the problem AND their wrong attempt, the
            # tutor diagnoses it and asks one question. The result was a dataset whose
            # entire tutoring category was MathDial, i.e. an OS tutor that had never
            # seen OS tutoring. Depth is not what makes a row valid; the rules below
            # (a teacher turn, a question asked, no leaked answer, not degenerate) are.
            # MathDial is unaffected: ingest already requires 4+ turns of it.
            if len(msgs) < 2:
                drop["tutoring_too_short"] += 1; continue
            if not asst:
                drop["tutoring_no_teacher_turn"] += 1; continue
            if not any("?" in a for a in asst):
                drop["tutoring_never_asks_question"] += 1; continue
            if _LEAK.search(asst[0]):
                drop["tutoring_leaks_answer_turn1"] += 1; continue
            if sum(1 for a in asst if _DEGEN.match(a)) / len(asst) > 0.4:
                drop["tutoring_mostly_degenerate"] += 1; continue

        elif cat == "replay":
            body = " ".join(m["content"] for m in msgs)
            if _NONLATIN.search(body):
                drop["replay_non_latin_script"] += 1; continue
            if _THINK.search(body):
                drop["replay_think_block"] += 1; continue
            if len(msgs[-1]["content"]) < 30:
                drop["replay_answer_tiny"] += 1; continue
            if msgs[-1]["content"].count("\n") > 120:
                drop["replay_answer_wall"] += 1; continue

        elif cat == "procedural":
            a = msgs[-1]["content"]
            # Clarification rows have no worked steps BY DESIGN: the question omits
            # an input, so the correct answer asks for it instead of inventing a
            # number. The release gate already exempts them; this rule did not, and
            # silently discarded 278 of the 500 of them. The behaviour they teach -
            # ask rather than guess - is one of the reasons v3.0 exists.
            if not r["subcategory"].startswith("clarify") and visible_steps(a) < 2:
                drop["procedural_no_visible_steps"] += 1; continue
            if not r.get("lineage", {}).get("verified"):
                drop["procedural_unverified"] += 1; continue

        elif cat == "conceptual":
            a = msgs[-1]["content"]
            if len(a) < 200:
                drop["conceptual_too_short"] += 1; continue
            if a.count("\n\n") == 0 and len(a) > 900:
                drop["conceptual_unstructured_wall"] += 1; continue

        if not msgs or msgs[-1]["role"] != "assistant":
            drop["not_closing_assistant"] += 1; continue

        u = " ".join(m["content"] for m in msgs if m["role"] == "user")
        a = " ".join(m["content"] for m in msgs if m["role"] == "assistant")
        total = sum(len(m["content"]) for m in msgs)
        if len(u) < MIN_CHARS_USER:
            drop["user_too_short"] += 1; continue
        if len(a) < MIN_CHARS_ASSISTANT:
            drop["assistant_too_short"] += 1; continue
        if total > MAX_CHARS_TOTAL:
            drop["over_char_budget"] += 1; continue
        if _SELFREF.search(a):
            drop["model_self_reference"] += 1; continue
        if _REFUSAL.match(a):
            drop["refusal"] += 1; continue
        lines = [l for l in a.split("\n") if l.strip()]
        if lines and max(Counter(lines).values()) > 8:
            drop["degenerate_repetition"] += 1; continue

        r["messages"] = msgs
        r["n_chars"] = total
        r.setdefault("lineage", {})["cleaned"] = True
        out.append(r)

    if report is not None:
        report.update(dict(input=len(records), kept=len(out), dropped=dict(drop),
                           repaired=dict(repair), pii_redactions=dict(pii)))
    return out
