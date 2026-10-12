"""Release gates. These FAIL THE BUILD - they do not warn.

A pipeline that emits warnings nobody reads is a pipeline that ships bad data.
Every gate encodes a defect class that was MEASURED in this corpus, so none is
hypothetical. Gates added in v2 and the failure each prevents:

  mixture_drift          v1 treated quotas as ceilings; when a category came up
                         short the others kept their full quota and their SHARE
                         ballooned - replay reached 31% against a 12% target and
                         OS content fell to 29% against 70%. Nothing flagged it.
  pairwise_diversity     a generator produced 6,900 "distinct" rows that
                         collapsed to 22 under semantic dedup (cosine 0.997
                         between supposedly different problems). Row count is
                         not signal count.
  distinct_answers       duplicated targets are direct overfitting pressure.
  template_share         one solution skeleton dominating a category teaches the
                         skeleton rather than the procedure.
  source_run_bounded     a permitted 4-row category run made of 4 rows from ONE
                         dataset is a block, not an interleave.
  ood_holdout_present    a same-generator OOD split tests size generalisation
                         only; template learning is invisible to it.
"""
import re
from collections import Counter

from .config import FAMILY_WEIGHTS, GATES, MIX
from .quality import visible_steps
from .select import family_of
from .schema import validate
from .scrub import find_secrets

_KEYSTROKE = re.compile(r"<(Esc|Enter|Tab|Left|Right|Up|Down|Ctrl|Alt|Shift|F\d{1,2})>", re.I)
_DEGEN = re.compile(r"^\s*(yes|no|ok(ay)?|sure|right|correct|good|great|exactly|thanks?)\W*$", re.I)
_NONLATIN = re.compile(r"[一-鿿぀-ヿ가-힯؀-ۿЀ-ӿ]")
_LEAK = re.compile(r"\b(the answer is|the final answer|equals\s*\d)", re.I)
_STEP = re.compile(r"(?m)^\s*(?:\**\s*step\s*\d+|[-*]\s+\S|\d+[.):]\s)", re.I)


def run_gates(rows, invariants, diversity_by_cat, ood_count, ood_from_file):
    n = max(len(rows), 1)
    d = Counter()
    schema_problems = []

    for r in rows:
        body = [m for m in r["messages"] if m["role"] != "system"]
        asst = [m["content"] for m in body if m["role"] == "assistant"]
        blob = " ".join(m["content"] for m in body)

        p = validate(r, strict=True)
        if p:
            schema_problems.append((r["id"], p[0]))
            d["schema_invalid"] += 1
        if "<think>" in r.get("text", ""):
            d["think_blocks"] += 1
        if find_secrets(blob):
            d["secrets"] += 1
        if not r.get("commercial_ok"):
            d["non_commercial"] += 1
        if _NONLATIN.search(blob):
            d["non_latin"] += 1

        cat = r["category"]
        if cat == "shell" and asst and _KEYSTROKE.search(asst[-1]):
            d["shell_editor_keystrokes"] += 1
        if cat == "tutoring" and asst:
            if _DEGEN.match(asst[-1]):
                d["tutoring_dead_tail"] += 1
            if not any("?" in a for a in asst):
                d["tutoring_never_asks_question"] += 1
            if _LEAK.search(asst[0]):
                d["tutoring_leaks_answer_turn1"] += 1
        if cat == "replay" and asst and len(asst[-1]) < 30:
            d["replay_answer_tiny"] += 1
        # clarification rows correctly contain NO working: they ask for the missing input
        if cat == "procedural" and asst and visible_steps(asst[-1]) < 2                 and not r.get("subcategory", "").startswith("clarify_"):
            d["procedural_no_steps"] += 1

    defects = sum(d[k] for k in (
        "shell_editor_keystrokes", "tutoring_dead_tail", "tutoring_never_asks_question",
        "tutoring_leaks_answer_turn1", "replay_answer_tiny", "procedural_no_steps",
        "schema_invalid"))

    by_cat = Counter(r["category"] for r in rows)
    p99 = sorted(r["n_tokens"] for r in rows)[int(0.99 * (len(rows) - 1))] if rows else 0
    tut = [r for r in rows if r["category"] == "tutoring"]
    tut_total = len(tut)
    os_tut = sum(1 for r in tut if r.get("domain") == "os")

    n_proc = by_cat.get("procedural", 0)
    fam_counts = Counter(family_of(r["subcategory"]) for r in rows
                         if r["category"] == "procedural")
    starved_families = {f: fam_counts.get(f, 0) for f, w in FAMILY_WEIGHTS.items()
                        if fam_counts.get(f, 0) < 0.5 * w * n_proc}

    # ---- mixture drift ----
    drift = {}
    for cat, share in MIX.items():
        realised = by_cat.get(cat, 0) / n
        drift[cat] = round((realised - share) * 100, 2)
    worst_drift = max((abs(v) for v in drift.values()), default=0.0)

    # ---- distinct answers / template share ----
    worst_distinct, worst_distinct_cat = 1.0, None
    worst_template, worst_template_cat = 0.0, None
    for cat in by_cat:
        sub = [r for r in rows if r["category"] == cat]
        answers = [" ".join(m["content"] for m in r["messages"] if m["role"] == "assistant")
                   for r in sub]
        ratio = len(set(answers)) / max(len(answers), 1)
        if worst_distinct_cat is None or ratio < worst_distinct:
            worst_distinct, worst_distinct_cat = ratio, cat
        # Template share only means something for GENERATED rows, which carry a
        # template_id. Falling back to subcategory scored every human MathDial
        # dialogue as "one template" (share 1.0) - a gate bug, not a data defect.
        gen = [r for r in sub if r.get("template_id")]
        tpl = Counter(r["template_id"] for r in gen)
        share = tpl.most_common(1)[0][1] / max(len(gen), 1) if tpl else 0
        if share > worst_template:
            worst_template, worst_template_cat = share, cat

    unsolvable = unsolvable_procedural()

    worst_div, worst_div_cat = 1.0, None
    for cat, dv in (diversity_by_cat or {}).items():
        if dv < worst_div:
            worst_div, worst_div_cat = dv, cat

    checks = [
        ("secrets_zero", d["secrets"] <= GATES["max_secret_hits"],
         f'{d["secrets"]} rows with credential material (limit {GATES["max_secret_hits"]})'),
        ("no_think_blocks", d["think_blocks"] <= GATES["max_think_blocks"],
         f'{d["think_blocks"]} rows contain <think>'),
        ("licence_commercial", (not GATES["require_all_commercial"]) or d["non_commercial"] == 0,
         f'{d["non_commercial"]} non-commercial rows'),
        ("schema_valid", d["schema_invalid"] == 0,
         f'{d["schema_invalid"]} rows fail schema'
         + (f' (first: {schema_problems[0][1]})' if schema_problems else "")),
        ("defect_rate", defects / n <= GATES["max_defect_rate"],
         f'{defects} known defects = {100*defects/n:.3f}% (limit {100*GATES["max_defect_rate"]:.3f}%)'),
        ("non_latin_rate", d["non_latin"] / n <= GATES["max_nonlatin_rate"],
         f'{d["non_latin"]} non-Latin-script rows'),
        ("token_p99", p99 <= GATES["max_token_p99"],
         f'p99 token length {p99} (limit {GATES["max_token_p99"]})'),
        ("rectifier_invariants", bool(invariants.get("ok")),
         f'category run {invariants.get("longest_same_category_run")}/'
         f'{invariants.get("max_run_allowed")}, worst spacing violation '
         f'{invariants.get("worst_spacing_violation")}'),
        ("source_run_bounded",
         invariants.get("longest_same_source_run", 0) <= GATES["max_run_same_source"],
         f'longest single-dataset run {invariants.get("longest_same_source_run")} '
         f'across {invariants.get("n_sources")} sources (max {GATES["max_run_same_source"]})'),
        ("mixture_drift", worst_drift <= GATES["max_mixture_drift_pp"],
         f'worst drift {worst_drift:+.2f}pp (limit {GATES["max_mixture_drift_pp"]}pp) {drift}'),
        ("distinct_answers", worst_distinct >= GATES["min_distinct_answer_ratio"],
         f'lowest distinct-answer ratio {worst_distinct:.3f} in "{worst_distinct_cat}" '
         f'(min {GATES["min_distinct_answer_ratio"]})'),
        ("template_share", worst_template <= GATES["max_template_share"],
         f'largest template share {worst_template:.3f} in "{worst_template_cat}" (max {GATES["max_template_share"]})'),
        ("pairwise_diversity", worst_div >= GATES["min_pairwise_diversity"],
         f'lowest diversity {worst_div:.3f} in "{worst_div_cat}" '
         f'(min {GATES["min_pairwise_diversity"]})'),
        ("min_rows_per_category",
         all(v >= GATES["min_rows_per_category"] for v in by_cat.values()),
         f'smallest category {min(by_cat.values()) if by_cat else 0} rows '
         f'(min {GATES["min_rows_per_category"]})'),
        ("min_total_rows", len(rows) >= GATES["min_total_rows"],
         f'{len(rows)} train rows (min {GATES["min_total_rows"]})'),
        ("ood_holdout_present",
         (not GATES["require_ood_holdout"]) or ood_from_file > 0,
         f'{ood_from_file} genuinely out-of-distribution rows in the holdout '
         f'({ood_count} total ood)'),
        ("procedural_inputs_complete", not unsolvable,
         f'{sum(unsolvable.values())} procedural questions omit an input they need '
         f'{dict(unsolvable) or ""}(train sources, OOD holdout, eval suites)'),
        # Two v3.0 builds passed every other gate while the tutoring category was
        # 100% MathDial: three separate filters had removed every OS tutoring row
        # (a 4-message minimum, n-gram decontamination, and a shape-biased quality
        # score). Nothing failed, because no gate asserted that an Operating Systems
        # tutor had ever seen OS tutoring. A count is not a composition.
        ("os_tutoring_present",
         os_tut >= GATES["min_os_tutoring_rows"],
         f'{os_tut} OS-domain tutoring rows '
         f'(min {GATES["min_os_tutoring_rows"]}, {tut_total} tutoring rows in total)'),
        # The same failure as os_tutoring_present, one level down. Clarification rows
        # reached the training set 5 times out of a designed 384, because the cleaner
        # dropped them for having no worked steps (they ask a question by design) and
        # their fingerprint did not include their parameters. Every gate passed: the
        # procedural count was right, only its INTERNAL composition was wrong. A
        # family may fall short of its weight when supply is genuinely scarce, so the
        # floor is half the designed share, not the whole of it.
        ("family_weights_honoured", not starved_families,
         f'{len(starved_families)} procedural families below half their designed share '
         f'{starved_families or ""}'),
    ]
    results = [dict(gate=k, passed=bool(ok), detail=v) for k, ok, v in checks]
    extra = dict(mixture_drift_pp=drift, worst_distinct_answer_ratio=round(worst_distinct, 4),
                 worst_template_share=round(worst_template, 4),
                 diversity_by_category={k: round(v, 4) for k, v in (diversity_by_cat or {}).items()})
    return all(r["passed"] for r in results), results, extra


def unsolvable_procedural():
    """Every simulator-generated question must state every input its answer
    depends on. v2.2.0 shipped 169 OOD eval questions (and 235 holdout rows) whose
    reframed first paragraph had dropped Available / the request list; the model
    could only guess. Counted per (file, kind, missing input)."""
    import json
    from .config import RAW, ROOT
    from .simulators.generate import missing_inputs
    files = sorted(RAW.glob("procedural*.jsonl")) + sorted((ROOT / "data" / "eval").glob("*.jsonl"))
    bad = Counter()
    for f in files:
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                if "verify" in r:
                    for k in missing_inputs(r):
                        bad[f"{f.stem}:{r['verify']['kind']}.{k}"] += 1
    return bad


def print_gates(results):
    w = max(len(r["gate"]) for r in results)
    print(f"\n{'RELEASE GATES':<{w + 8}}")
    print("-" * (w + 70))
    for r in results:
        print(f"  [{'PASS' if r['passed'] else 'FAIL'}] {r['gate']:<{w}}  {r['detail']}")
    print("-" * (w + 70))
