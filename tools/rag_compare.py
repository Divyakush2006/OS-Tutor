"""Compare corpora (and the sources inside one) by answer recall on the short-answer set.

    python tools/rag_compare.py [--split dev|test|all]

For each configuration, hybrid retrieval with no abstain gate over the 144 questions of
data/eval_rag/os_short_answer.jsonl: answer recall@1/@5/@10 (a top-k chunk contains an
accepted answer, word-bounded, aliases under 3 characters and bare digits ignored) and
the paired exact McNemar test of each configuration's recall@5 against the course corpus
and against the compiled open corpus. Configurations:

  course            data/rag/corpus  (the owners' material + Hailperin + 55 Wikipedia articles)
  open              data/rag/open    (compiled by tools/analyze_rag_pool.py)
  open_all          data/rag/open_all (the same pool, unfiltered: the control for the filters)
  open - <source>   the open corpus with one source left out (ablation)

Choices are made on the dev split; the test split is reported once, for the chosen corpus.
Writes reports/rag/compare_<split>.json and .md.

    python tools/rag_compare.py --calibrate data/rag/open

fits the abstain gate of one corpus the way tools/rag_eval.py does (DEV split only: the
pair of thresholds that abstains on the most out-of-scope questions while keeping notes
for at least 95% of in-scope ones), with the short-answer questions as the in-scope set
and the 40 out-of-scope questions of data/rag/eval/corpus_questions.jsonl, reports it on
the TEST split and saves <corpus>/gate.json.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ostutor.evaluation.stats import mcnemar_exact  # noqa: E402
from ostutor.rag.retrieve import BM25, Retriever, tokens  # noqa: E402

QA = ROOT / "data" / "eval_rag" / "os_short_answer.jsonl"
OOS = ROOT / "data" / "rag" / "eval" / "corpus_questions.jsonl"


def contains(text: str, answers: list[str]) -> bool:
    low = text.lower()
    return any(re.search(r"(?<![a-z0-9])" + re.escape(a.lower()) + r"(?![a-z0-9])", low)
               for a in answers if len(a) >= 3 and not a.isdigit())


def subset(r: Retriever, keep) -> Retriever:
    """A retriever over the chunks for which keep(chunk) is true (embeddings reused)."""
    s = object.__new__(Retriever)
    idx = [i for i, c in enumerate(r.chunks) if keep(c)]
    s.__dict__.update(r.__dict__)
    s.chunks = [r.chunks[i] for i in idx]
    s.emb = r.emb[idx]
    s.bm25 = BM25([tokens(c.title + " " + c.section + " " + c.text) for c in s.chunks])
    return s


def evaluate(r: Retriever, qs: list[dict]) -> dict:
    hit = {1: {}, 5: {}, 10: {}}
    for q in qs:
        hits = r.retrieve(q["question"], k=10, gate="none")
        ranks = [i for i, h in enumerate(hits) if contains(h["chunk"].text, q["answers"])]
        for k in hit:
            hit[k][q["id"]] = bool(ranks) and ranks[0] < k
    n = len(qs)
    return dict(n=n, chunks=len(r.chunks), **{f"recall_at_{k}": round(sum(v.values()) / n, 4) for k, v in hit.items()},
                hits5=hit[5])


def fit_gate(corpus: Path) -> None:
    from rag_eval import KEEP_TARGET, calibrate, gate_report, signals
    r = Retriever(corpus)
    qs = [dict(id=q["id"], query=q["question"], doc="in", split=q["split"])
          for q in map(json.loads, open(QA, encoding="utf-8"))]
    qs += [dict(id=q["id"], query=q["query"], doc=None, split=q["split"])
           for q in map(json.loads, open(OOS, encoding="utf-8")) if not q["doc"]]
    sig = {q["id"]: signals(r, q["query"]) for q in qs}
    dev = [q for q in qs if q["split"] == "dev"]
    test = [q for q in qs if q["split"] == "test"]
    g = calibrate(dev, sig)
    rel = lambda p: str(p.resolve().relative_to(ROOT)).replace("\\", "/")   # noqa: E731
    (corpus / "gate.json").write_text(json.dumps(dict(
        g, fitted_on=f"{rel(QA)} (in scope) + {rel(OOS)} out-of-scope questions (split=dev)",
        keep_target=KEEP_TARGET, corpus_sha256=r.manifest["chunks_sha256"]), indent=1) + "\n", encoding="utf-8")
    res = dict(corpus=rel(corpus), thresholds=g, dev=gate_report(dev, sig, g), test=gate_report(test, sig, g))
    out = ROOT / "reports" / "rag" / f"{corpus.name}_gate.json"
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    for s in ("dev", "test"):
        x = res[s]
        print(f"{s}: in-scope given notes {x['in_scope_given_notes']}/{x['in_scope']}, "
              f"out-of-scope abstained {x['out_of_scope_abstained']}/{x['out_of_scope']}")
    print("gate:", g, "->", out.relative_to(ROOT))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=["dev", "test", "all"])
    ap.add_argument("--calibrate", metavar="CORPUS")
    a = ap.parse_args()
    if a.calibrate:
        sys.path.insert(0, str(ROOT / "tools"))
        return fit_gate(Path(a.calibrate).resolve())
    qs = [json.loads(l) for l in open(QA, encoding="utf-8")]
    qs = [q for q in qs if a.split == "all" or q["split"] == a.split]
    configs = {}
    course = Retriever(ROOT / "data/rag/corpus")
    configs["course"] = course
    configs["course minus course material"] = subset(course, lambda c: not c.doc_id.startswith("course-"))
    if (ROOT / "data/rag/open_all/manifest.json").is_file():
        configs["open_all (unfiltered pool)"] = Retriever(ROOT / "data/rag/open_all")
    op = Retriever(ROOT / "data/rag/open")
    configs["open (compiled)"] = op
    kinds = sorted({d.get("kind") for d in op.manifest["documents"]})
    docs = {d["id"]: d.get("kind") for d in op.manifest["documents"]}
    for k in kinds:
        configs[f"open minus {k}"] = subset(op, lambda c, k=k: docs.get(c.doc_id) != k)
        configs[f"only {k}"] = subset(op, lambda c, k=k: docs.get(c.doc_id) == k)
    res = {name: evaluate(r, qs) for name, r in configs.items()}
    for ref in ("course", "open (compiled)"):
        for name, v in res.items():
            if name == ref:
                continue
            a_, b_ = res[ref]["hits5"], v["hits5"]
            rw = sum(a_[i] and not b_[i] for i in a_)
            wr = sum(b_[i] and not a_[i] for i in a_)
            v.setdefault("vs", {})[ref] = dict(lost=rw, gained=wr, p=round(mcnemar_exact(rw, wr), 4))
    out = ROOT / "reports" / "rag"
    (out / f"compare_{a.split}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    md = [f"# Corpus comparison — answer recall, {a.split} split (n = {len(qs)})", "",
          "| Configuration | Chunks | Recall@1 | Recall@5 | Recall@10 | vs course (lost/gained, p) | vs open (lost/gained, p) |",
          "|---|---|---|---|---|---|---|"]
    for name, v in res.items():
        vs = v.get("vs", {})
        f = lambda ref: f"{vs[ref]['lost']}/{vs[ref]['gained']}, {vs[ref]['p']:.3f}" if ref in vs else "—"   # noqa: E731
        md.append(f"| {name} | {v['chunks']:,} | {v['recall_at_1']:.1%} | {v['recall_at_5']:.1%} | "
                  f"{v['recall_at_10']:.1%} | {f('course')} | {f('open (compiled)')} |")
    (out / f"compare_{a.split}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
