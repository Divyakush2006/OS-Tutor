"""Per-category forensic analysis.

WHY THIS LAYER EXISTS. In v1 the cleaning rules were written first and measured
afterwards. That is backwards, and it was expensive: a forensic pass on the
finished dataset showed the generic rules had enormous false-positive rates -
"answer ends mid-sentence" flagged 503 rows (18.6%) that were shell commands
legitimately ending lowercase; "answer much shorter than question" flagged 864
rows (31.9%) that were correct Socratic teacher turns. Applying them would have
destroyed ~1,300 good rows.

So v2 inverts the order. Each category is PROFILED first. Every candidate rule is
then tested against that profile and reported with its hit rate AND sampled
examples, so a rule can be rejected on evidence before it ever runs. Cleaning
only applies rules that survived this audit.

A category analyzer answers four questions:
  1. What does this data actually look like? (distributions)
  2. What is genuinely broken? (defects, with samples)
  3. Which candidate rules would misfire? (false-positive audit)
  4. What thresholds does the distribution justify? (derived, not guessed)
"""
import json
import re
import statistics
from collections import Counter

_TOK = re.compile(r"[A-Za-z0-9_]+")


def ttr(text):
    w = [x.lower() for x in _TOK.findall(text)]
    return len(set(w)) / len(w) if w else 0.0


def pct(values, p):
    if not values:
        return 0
    s = sorted(values)
    return s[min(len(s) - 1, int(p * len(s)))]


class CategoryAnalyzer:
    """Base profiler. Subclasses add category-specific probes."""
    category = "base"

    def __init__(self, rows):
        self.rows = rows
        self.n = len(rows)
        self.report = dict(category=self.category, rows=self.n)

    # ------------------------------------------------------------- helpers
    @staticmethod
    def parts(r):
        u = " ".join(m["content"] for m in r["messages"] if m["role"] == "user")
        a = [m["content"] for m in r["messages"] if m["role"] == "assistant"]
        return u, a

    def probe(self, name, predicate, verdict=None, note=""):
        """Run a candidate rule; record hit rate and 3 sampled hits.

        `verdict` is the analyst's call - "defect" (genuinely broken) or
        "false_positive" (the rule misfires on legitimate data). Recording the
        verdict next to the measured rate is the whole point: it turns a rule
        from an opinion into an auditable decision.
        """
        hits = []
        for r in self.rows:
            try:
                if predicate(r):
                    hits.append(r)
            except Exception:
                continue
        samples = []
        for h in hits[:3]:
            _, a = self.parts(h)
            samples.append((a[-1] if a else "")[:110])
        self.report.setdefault("probes", {})[name] = dict(
            hits=len(hits), rate=round(len(hits) / max(self.n, 1), 4),
            verdict=verdict or "unclassified", note=note, samples=samples)
        return hits

    # ------------------------------------------------------------ profiling
    def distributions(self):
        ulen, alen, turns, tt = [], [], [], []
        for r in self.rows:
            u, a = self.parts(r)
            ulen.append(len(u))
            alen.append(len(" ".join(a)))
            turns.append(len(r["messages"]))
            tt.append(ttr(" ".join(a)))
        self.report["distributions"] = dict(
            user_chars=dict(p10=pct(ulen, .1), p50=pct(ulen, .5), p90=pct(ulen, .9),
                            mean=round(statistics.fmean(ulen), 1) if ulen else 0),
            assistant_chars=dict(p10=pct(alen, .1), p50=pct(alen, .5), p90=pct(alen, .9),
                                 mean=round(statistics.fmean(alen), 1) if alen else 0),
            turns=dict(p50=pct(turns, .5), p90=pct(turns, .9)),
            type_token_ratio=dict(p10=round(pct(tt, .1), 3), p50=round(pct(tt, .5), 3)),
            sources=dict(Counter(r["subcategory"] for r in self.rows).most_common(8)))
        return self.report["distributions"]

    def redundancy(self):
        """Exact answer duplication - a direct overfitting risk signal."""
        answers = []
        for r in self.rows:
            _, a = self.parts(r)
            answers.append((a[-1] if a else "").strip().lower())
        c = Counter(answers)
        dup = sum(v for v in c.values() if v > 1)
        self.report["redundancy"] = dict(
            distinct_answers=len(c), rows=self.n,
            distinct_ratio=round(len(c) / max(self.n, 1), 4),
            rows_with_duplicated_answer=dup,
            worst=[(k[:70], v) for k, v in c.most_common(3) if v > 1])
        return self.report["redundancy"]

    def probes(self):
        """Category-specific probes. Override."""
        return {}

    def thresholds(self):
        """Derive cleaning thresholds from the measured distribution rather than
        guessing them. Subclasses may extend."""
        d = self.report.get("distributions", {})
        a = d.get("assistant_chars", {})
        self.report["derived_thresholds"] = dict(
            min_assistant_chars=max(12, int(a.get("p10", 40) * 0.5)),
            max_assistant_chars=int(a.get("p90", 4000) * 3))
        return self.report["derived_thresholds"]

    def run(self):
        self.distributions()
        self.redundancy()
        self.probes()
        self.thresholds()
        # summary: only probes marked "defect" are actionable
        p = self.report.get("probes", {})
        self.report["actionable_defects"] = {
            k: v["hits"] for k, v in p.items() if v["verdict"] == "defect" and v["hits"]}
        self.report["rejected_rules"] = {
            k: dict(hits=v["hits"], rate=v["rate"], note=v["note"])
            for k, v in p.items() if v["verdict"] == "false_positive"}
        return self.report


def write_report(report, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
