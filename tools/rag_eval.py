"""Measure retrieval on a corpus with a labelled question set, and calibrate the gate.

    python tools/rag_eval.py data/rag/corpus --calibrate   (questions: data/rag/eval/corpus_questions.jsonl)
    python tools/rag_eval.py data/rag/fixture              (questions: data/rag/fixture/queries.jsonl)

Relevance. A corpus question names its document and an evidence phrase copied from the
answering passage; a retrieved chunk is relevant when it is from that document and
contains the phrase (labels survive re-chunking). Fixture questions name a note and a
section instead. Reported over all in-scope questions, per retrieval mode:
  recall@1 / @5      a relevant chunk is in the top 1 / 5   (the brief's measure: recall@5)
  doc recall@5       any chunk of the right document is in the top 5
  MRR@10
  CPU latency per query, p50 / p95 / max (5 timed passes, the first discarded)

Calibration (--calibrate). The abstain gate keeps the passages when the best dense cosine
is at least STRONG or the best BM25 score is at least MIN_BM25. Both thresholds are
chosen on the DEV split only: the pair that abstains on the most out-of-scope questions
while keeping notes for at least 95% of in-scope ones. It is then reported on the TEST
split, which played no part in choosing it, and saved to <corpus>/gate.json, which the
retriever loads.

Writes reports/rag/<corpus>_eval.json and .md.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ostutor.rag.retrieve import Retriever, tokens  # noqa: E402

PASSES = 5
KEEP_TARGET = 0.95
MODES = [("bm25", "bm25"), ("dense", "dense"), ("hybrid", "hybrid")]


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).lower()


def relevant(q: dict, chunk) -> bool:
    if chunk.doc_id != q["doc"]:
        return False
    if q.get("evidence"):
        return norm(q["evidence"]) in norm(chunk.text)
    return chunk.section == q["section"]


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))]


def signals(r: Retriever, query: str) -> tuple[float, float]:
    """(best dense cosine, best BM25 score) - the two inputs of the abstain gate."""
    e = r.model.encode([r.qp + query], normalize_embeddings=True)[0]
    return float((r.emb @ e).max()), float(r.bm25.scores(tokens(query)).max())


def calibrate(dev: list[dict], sig: dict) -> dict:
    ins = [q for q in dev if q["doc"]]
    outs = [q for q in dev if not q["doc"]]
    best = None
    for c in np.arange(0.20, 1.00, 0.01):
        for b in np.arange(0.0, 40.0, 0.5):
            keep = lambda q: sig[q["id"]][0] >= c or sig[q["id"]][1] >= b   # noqa: E731
            kept = sum(keep(q) for q in ins) / len(ins)
            if kept < KEEP_TARGET:
                continue
            abst = sum(not keep(q) for q in outs) / len(outs)
            score = (abst, kept, -c, -b)          # most abstention, then most kept, then loosest
            if best is None or score > best[0]:
                best = (score, round(float(c), 2), round(float(b), 1))
    if best is None:
        raise SystemExit("no gate keeps 95% of in-scope dev questions")
    return dict(strong_cosine=best[1], min_bm25=best[2])


def gate_report(qs: list[dict], sig: dict, g: dict) -> dict:
    keep = lambda q: sig[q["id"]][0] >= g["strong_cosine"] or sig[q["id"]][1] >= g["min_bm25"]  # noqa: E731
    ins = [q for q in qs if q["doc"]]
    outs = [q for q in qs if not q["doc"]]
    return dict(in_scope=len(ins), in_scope_given_notes=sum(keep(q) for q in ins),
                out_of_scope=len(outs), out_of_scope_abstained=sum(not keep(q) for q in outs),
                in_scope_refused=[q["id"] for q in ins if not keep(q)],
                out_of_scope_given_notes=[q["id"] for q in outs if keep(q)])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus")
    ap.add_argument("--questions")
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--embed-model", default=None, help="compare another local embedding model")
    a = ap.parse_args()
    corpus = Path(a.corpus).resolve()
    qfile = Path(a.questions) if a.questions else (
        corpus / "queries.jsonl" if (corpus / "queries.jsonl").is_file()
        else ROOT / "data" / "rag" / "eval" / f"{corpus.name}_questions.jsonl")
    queries = [json.loads(l) for l in open(qfile, encoding="utf-8")]
    t = time.perf_counter()
    r = Retriever(corpus, **({"embed_model": a.embed_model} if a.embed_model else {}))
    build_s = time.perf_counter() - t
    ins = [q for q in queries if q["doc"]]
    outs = [q for q in queries if not q["doc"]]
    docs = {d["id"]: d for d in r.manifest["documents"]}
    res = dict(corpus=str(corpus.relative_to(ROOT)).replace("\\", "/"), questions=str(
        qfile.resolve().relative_to(ROOT)).replace("\\", "/"),
        corpus_sha256=r.manifest["chunks_sha256"], documents=len(docs), chunks=len(r.chunks),
        in_scope=len(ins), out_of_scope=len(outs), load_seconds=round(build_s, 2), modes={})

    for label, mode in MODES:
        r1 = r5 = d5 = 0
        rr, lat, misses = 0.0, [], []
        for q in queries:
            for p in range(PASSES):
                hits, ms = r.timed(q["query"], k=10, mode=mode, gate="none")
                if p:
                    lat.append(ms)
            if not q["doc"]:
                continue
            rank = next((i for i, h in enumerate(hits) if relevant(q, h["chunk"])), None)
            r1 += rank == 0
            r5 += rank is not None and rank < 5
            d5 += any(h["chunk"].doc_id == q["doc"] for h in hits[:5])
            rr += 1 / (rank + 1) if rank is not None else 0
            if rank is None or rank >= 5:
                misses.append(dict(id=q["id"], query=q["query"], want=q["doc"],
                                   got=[h["chunk"].doc_id for h in hits[:3]]))
        n = len(ins)
        res["modes"][label] = dict(
            recall_at_1=round(r1 / n, 4), recall_at_5=round(r5 / n, 4), doc_recall_at_5=round(d5 / n, 4),
            mrr_at_10=round(rr / n, 4), latency_ms_p50=round(statistics.median(lat), 2),
            latency_ms_p95=round(pct(lat, 0.95), 2), latency_ms_max=round(max(lat), 2), misses=misses)

    # in-scope recall split by where the answer lives
    for kind in ("course", "online"):
        sub = [q for q in ins if docs[q["doc"]].get("kind", "course") == kind]
        if sub:
            hit = 0
            for q in sub:
                hits = r.retrieve(q["query"], k=5, gate="none")
                hit += any(relevant(q, h["chunk"]) for h in hits)
            res[f"hybrid_recall_at_5_{kind}"] = dict(n=len(sub), recall=round(hit / len(sub), 4))

    if r.model is not None and any("split" in q for q in queries):
        sig = {q["id"]: signals(r, q["query"]) for q in queries}
        dev = [q for q in queries if q.get("split") == "dev"]
        test = [q for q in queries if q.get("split") == "test"]
        g = calibrate(dev, sig) if a.calibrate or a.embed_model else \
            json.loads((corpus / "gate.json").read_text())
        g = dict(strong_cosine=g["strong_cosine"], min_bm25=g["min_bm25"])
        if a.calibrate and not a.embed_model:
            (corpus / "gate.json").write_text(json.dumps(dict(
                g, fitted_on=res["questions"] + " (split=dev)", keep_target=KEEP_TARGET,
                corpus_sha256=r.manifest["chunks_sha256"]), indent=1) + "\n", encoding="utf-8")
        res["gate"] = dict(thresholds=g, calibrated_in_this_run=a.calibrate,
                           dev=gate_report(dev, sig, g), test=gate_report(test, sig, g))

    out = ROOT / "reports" / "rag"
    out.mkdir(parents=True, exist_ok=True)
    name = corpus.name + (f"_{a.embed_model.split('/')[-1]}" if a.embed_model else "")
    res["embed_model"] = r.embed_model
    (out / f"{name}_eval.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    md = [f"# Retrieval evaluation — `{res['corpus']}`", "",
          f"{res['documents']} documents · {res['chunks']} chunks · {len(ins)} in-scope and {len(outs)} "
          f"out-of-scope questions (`{res['questions']}`) · loaded in {res['load_seconds']} s (CPU)", "",
          "| Mode | Recall@1 | Recall@5 | Doc recall@5 | MRR@10 | p50 ms | p95 ms |", "|---|---|---|---|---|---|---|"]
    for label, m in res["modes"].items():
        md.append(f"| {label} | {m['recall_at_1']:.1%} | {m['recall_at_5']:.1%} | {m['doc_recall_at_5']:.1%} | "
                  f"{m['mrr_at_10']:.3f} | {m['latency_ms_p50']} | {m['latency_ms_p95']} |")
    for kind in ("course", "online"):
        if f"hybrid_recall_at_5_{kind}" in res:
            x = res[f"hybrid_recall_at_5_{kind}"]
            md.append(f"\nHybrid recall@5, answer in {kind} material: {x['recall']:.1%} (n = {x['n']})")
    if "gate" in res:
        g = res["gate"]
        md += ["", f"## Abstain gate: keep notes if cosine ≥ {g['thresholds']['strong_cosine']} or "
                   f"BM25 ≥ {g['thresholds']['min_bm25']}"
                   + (" (calibrated on dev in this run)" if a.calibrate else ""), "",
               "| Split | In-scope given notes | Out-of-scope abstained |", "|---|---|---|"]
        for s in ("dev", "test"):
            x = g[s]
            md.append(f"| {s} | {x['in_scope_given_notes']}/{x['in_scope']} | "
                      f"{x['out_of_scope_abstained']}/{x['out_of_scope']} |")
    md += ["", "## Hybrid misses (relevant passage not in top 5)", ""]
    md += [f"- `{m['id']}` {m['query']} — wanted `{m['want']}`, got {m['got']}"
           for m in res["modes"]["hybrid"]["misses"]] or ["- none"]
    (out / f"{name}_eval.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
