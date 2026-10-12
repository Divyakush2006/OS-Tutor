"""Category-specific analyzers.

Each one encodes what its category IS, so that a probe knows the difference
between a defect and a legitimate feature of that data. The `verdict` on every
probe is the analyst's call, recorded next to the measured hit rate so the
decision is auditable rather than assumed.
"""
import json
import re

from ..quality import visible_steps
from .base import CategoryAnalyzer

# ------------------------------------------------------------------- shell
_KEYSTROKE = re.compile(
    r"<(Esc|Enter|Tab|Left|Right|Up|Down|Space|Ctrl|Alt|Shift|F\d{1,2}"
    r"|PageUp|PageDown|Home|End|Backspace|Delete)>", re.I)
_KEYNAME = re.compile(r"^\s*(Ctrl|Alt|Shift|Cmd)\s*\+", re.I)
_TRUNC = re.compile(r"[a-z,;:\-]\s*$")
_BRACE = re.compile(r"\{\{|\}\}")


class ShellAnalyzer(CategoryAnalyzer):
    category = "shell"

    def __init__(self, rows, syntax_blocklist=None):
        super().__init__(rows)
        self.block = syntax_blocklist or {}

    def probes(self):
        # ---- genuine defects ----
        self.probe("editor_keystrokes",
                   lambda r: bool(_KEYSTROKE.search(self.parts(r)[1][-1])
                                  or _KEYNAME.match(self.parts(r)[1][-1])),
                   verdict="defect",
                   note="tldr ships interactive-editor pages; '<Esc>:%s/re/x/g<Enter>' "
                        "is a vim keystroke sequence, not a shell command. Training on "
                        "these teaches the model to emit keystrokes.")
        self.probe("bash_syntax_error", lambda r: r["id"] in self.block,
                   verdict="defect",
                   note="fails `bash -n`; validated offline in a real bash "
                        "(Python subprocess cannot reach WSL)")
        self.probe("instruction_too_vague",
                   lambda r: len(self.parts(r)[0].split()) < 3,
                   verdict="defect", note="a two-word prompt cannot specify a command")
        self.probe("absurd_length", lambda r: len(self.parts(r)[1][-1]) > 500,
                   verdict="defect", note="not a teachable one-liner")

        # ---- candidate rules that MISFIRE on shell data ----
        self.probe("answer_ends_midsentence",
                   lambda r: bool(_TRUNC.search(self.parts(r)[1][-1]))
                   and len(self.parts(r)[1][-1]) > 40,
                   verdict="false_positive",
                   note="shell commands legitimately end lowercase: "
                        "`... | xargs grep foo /dev/null`. REJECTED.")
        self.probe("brace_placeholder", lambda r: bool(_BRACE.search(self.parts(r)[1][-1])),
                   verdict="false_positive",
                   note="matches `find -exec {} +` and Clojure `{:deps {...}}`. REJECTED.")
        return self.report["probes"]


# ---------------------------------------------------------------- tutoring
_DEGEN = re.compile(
    r"^\s*(yes|no|ok(ay)?|sure|right|correct|good|great|exactly|thanks?"
    r"|yep|nope|i see|got it|perfect|true|false)\W*$", re.I)
_LEAK = re.compile(r"\b(the answer is|the final answer|equals\s*\d|=\s*\d+\s*$)", re.I)


class TutoringAnalyzer(CategoryAnalyzer):
    category = "tutoring"

    def probes(self):
        def roles_nonalt(r):
            rl = [m["role"] for m in r["messages"]]
            return any(rl[i] == rl[i + 1] for i in range(len(rl) - 1))

        self.probe("non_alternating_roles", roles_nonalt, verdict="defect",
                   note="breaks the chat template; REPAIRABLE by merging turns")
        self.probe("dead_tail",
                   lambda r: bool(_DEGEN.match(self.parts(r)[1][-1])),
                   verdict="defect",
                   note="dialogue ends on 'correct'/'ok' - a target with no teaching "
                        "signal; REPAIRABLE by trimming the tail")
        self.probe("never_asks_question",
                   lambda r: not any("?" in a for a in self.parts(r)[1]),
                   verdict="defect",
                   note="a tutor that never questions is not Socratic")
        self.probe("leaks_answer_first_turn",
                   lambda r: bool(_LEAK.search(self.parts(r)[1][0])),
                   verdict="defect",
                   note="reveals the result before the student attempts it")
        self.probe("mostly_degenerate",
                   lambda r: (sum(1 for a in self.parts(r)[1] if _DEGEN.match(a))
                              / max(len(self.parts(r)[1]), 1)) > 0.4,
                   verdict="defect", note="majority of teacher turns carry no content")

        # ---- rule that MISFIRES on dialogue ----
        self.probe("answer_shorter_than_question",
                   lambda r: (len(self.parts(r)[1][-1]) < 0.12 * len(self.parts(r)[0])
                              and len(self.parts(r)[0]) > 200),
                   verdict="false_positive",
                   note="a SHORT Socratic teacher turn after a long student answer is "
                        "the desired behaviour, not a defect. REJECTED.")
        return self.report["probes"]

    def thresholds(self):
        t = super().thresholds()
        t["min_turns"] = 4
        t["max_degenerate_share"] = 0.4
        return t


# ------------------------------------------------------------------ replay
_NONLATIN = re.compile(
    r"[一-鿿぀-ヿ가-힯؀-ۿЀ-ӿऀ-ॿ]")
_SELFREF = re.compile(
    r"\b(as an AI language model|I'm an AI|I am an AI|as a large language model"
    r"|I cannot browse|my knowledge cutoff)\b", re.I)
_REFUSAL = re.compile(r"^\s*(I'm sorry|I am sorry|I cannot|I can't assist|Sorry, )", re.I)
_THINK = re.compile(r"<think>|</think>")


class ReplayAnalyzer(CategoryAnalyzer):
    category = "replay"

    def probes(self):
        self.probe("non_latin_script",
                   lambda r: bool(_NONLATIN.search(" ".join(m["content"] for m in r["messages"]))),
                   verdict="defect",
                   note="translation tasks inside an English corpus")
        self.probe("answer_tiny", lambda r: len(self.parts(r)[1][-1]) < 30,
                   verdict="defect", note="no instruction-following signal")
        self.probe("answer_wall", lambda r: self.parts(r)[1][-1].count("\n") > 120,
                   verdict="defect", note="dumps that dominate the token budget")
        self.probe("model_self_reference",
                   lambda r: bool(_SELFREF.search(" ".join(self.parts(r)[1]))),
                   verdict="defect", note="persona leakage a tutor must not inherit")
        self.probe("refusal", lambda r: bool(_REFUSAL.match(self.parts(r)[1][-1])),
                   verdict="defect", note="teaches refusal on benign requests")
        self.probe("think_block",
                   lambda r: bool(_THINK.search(" ".join(m["content"] for m in r["messages"]))),
                   verdict="defect",
                   note="CoT replay would reintroduce thinking into a model chosen "
                        "specifically for having none")
        return self.report["probes"]


# -------------------------------------------------------------- procedural
_STEP = re.compile(r"(?m)^\s*(?:\**\s*step\s*\d+|[-*]\s+\S|\d+[.):]\s)", re.I)
_TABLE = re.compile(r"(?m)^\s*\|.*\|\s*$")
_FINAL = re.compile(r"\*\*[^*]*=\s*[^*]*\*\*|\*\*Total[^*]*\*\*|\*\*Physical[^*]*\*\*")


class ProceduralAnalyzer(CategoryAnalyzer):
    category = "procedural"

    def probes(self):
        self.probe("no_visible_steps", lambda r: visible_steps(self.parts(r)[1][-1]) < 2,
                   verdict="defect",
                   note="answer-only target defeats the auditable-steps design")
        self.probe("no_final_answer_marker",
                   lambda r: not _FINAL.search(self.parts(r)[1][-1]),
                   verdict="defect", note="no parseable final answer to grade against")
        self.probe("unverified",
                   lambda r: not r.get("lineage", {}).get("verified"),
                   verdict="defect",
                   note="every procedural row must be simulator-verified")
        # diagnostic, not a drop rule
        self.probe("has_state_table", lambda r: len(_TABLE.findall(self.parts(r)[1][-1])) >= 2,
                   verdict="diagnostic",
                   note="intermediate state shown - desirable, informs quality score")
        return self.report["probes"]

    def thresholds(self):
        t = super().thresholds()
        t["min_visible_steps"] = 2
        return t


# -------------------------------------------------------------- conceptual
class ConceptualAnalyzer(CategoryAnalyzer):
    category = "conceptual"

    def probes(self):
        self.probe("too_short", lambda r: len(self.parts(r)[1][-1]) < 200,
                   verdict="defect", note="an explanation needs substance")
        self.probe("unstructured_wall",
                   lambda r: self.parts(r)[1][-1].count("\n\n") == 0
                   and len(self.parts(r)[1][-1]) > 900,
                   verdict="defect", note="a long single paragraph is unreadable")
        self.probe("no_example",
                   lambda r: not re.search(r"(for example|e\.g\.|consider|suppose|imagine)",
                                           self.parts(r)[1][-1], re.I),
                   verdict="diagnostic",
                   note="concrete example present - informs quality score")
        return self.report["probes"]


ANALYZERS = dict(shell=ShellAnalyzer, tutoring=TutoringAnalyzer,
                 replay=ReplayAnalyzer, procedural=ProceduralAnalyzer,
                 conceptual=ConceptualAnalyzer)


def analyze_all(rows_by_cat, syntax_blocklist=None, out_dir=None):
    """Profile every category; returns {category: report}."""
    from .base import write_report
    reports = {}
    for cat, rows in rows_by_cat.items():
        if not rows:
            reports[cat] = dict(category=cat, rows=0, status="NOT_BUILT")
            continue
        cls = ANALYZERS.get(cat, CategoryAnalyzer)
        a = cls(rows, syntax_blocklist) if cat == "shell" else cls(rows)
        reports[cat] = a.run()
        if out_dir:
            write_report(reports[cat], out_dir / f"{cat}.json")
    return reports
