"""Measure retrieval on a corpus that has a labelled query set.

    python tools/rag_eval.py data/rag/fixture

For each retrieval mode (bm25, dense, hybrid) it reports, over the in-scope queries:
  section recall@1 and @4 - the labelled section is among the top 1 / 4 chunks
  document recall@4       - any chunk of the labelled note is in the top 4
  MRR@10                  - mean reciprocal rank of the first chunk of the labelled section
  false abstain           - retrieval returned nothing for a question the notes cover
and over the out-of-scope queries:
  abstain rate            - retrieval correctly returned nothing
plus CPU latency per query (p50, p95, max over 5 passes; first pass discarded as warm-up).

Writes reports/rag/<corpus>_eval.json and .md. The labels and notes of the fixture were
written by the same person, so these are an upper bound on what real notes will give.
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ostutor.rag.retrieve import MIN_BM25, MIN_COSINE, STRONG_COSINE, Retriever  # noqa: E402

PASSES = 5
# (label, retrieval mode, abstain gate); the last row is the served configuration
CONFIGS = [("bm25", "bm25", "cosine"), ("dense", "dense", "cosine"),
           ("hybrid, v1 gate", "hybrid", "cosine"), ("hybrid, v2 gate", "hybrid", "combined")]


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))]


def main() -> None:
    corpus = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "data/rag/fixture").resolve()
    queries = [json.loads(l) for l in open(corpus / "queries.jsonl", encoding="utf-8")]
    t = time.perf_counter()
    r = Retriever(corpus)
    build_s = time.perf_counter() - t
    ins = [q for q in queries if q["doc"]]
    outs = [q for q in queries if not q["doc"]]

    res = dict(corpus=str(corpus.relative_to(ROOT)).replace("\\", "/"),
               corpus_sha256=r.manifest["chunks_sha256"], documents=len(r.manifest["documents"]),
               chunks=len(r.chunks), in_scope=len(ins), out_of_scope=len(outs),
               gates=dict(v1=f"cosine < {MIN_COSINE}",
                          v2=f"cosine < {STRONG_COSINE} and bm25 < {MIN_BM25}"), index_build_seconds=round(build_s, 2), modes={}, misses={})
    for label, mode, gate in CONFIGS:
        r1 = r4 = d4 = 0
        rr, false_abstain, abstain, lat, misses = 0.0, 0, 0, [], []
        for q in queries:
            for p in range(PASSES):
                hits, ms = r.timed(q["query"], k=10, mode=mode, gate=gate)
                if p:
                    lat.append(ms)
            if not q["doc"]:
                abstain += not hits
                continue
            if not hits:
                false_abstain += 1
            gold = [i for i, h in enumerate(hits)
                    if h["chunk"].doc_id == q["doc"] and h["chunk"].section == q["section"]]
            r1 += bool(gold) and gold[0] == 0
            r4 += bool(gold) and gold[0] < 4
            d4 += any(h["chunk"].doc_id == q["doc"] for h in hits[:4])
            rr += 1 / (gold[0] + 1) if gold else 0
            if not (gold and gold[0] < 4):
                misses.append(dict(id=q["id"], query=q["query"], want=f"{q['doc']} / {q['section']}",
                                   got=[f"{h['chunk'].doc_id} / {h['chunk'].section}" for h in hits[:2]]))
        n = len(ins)
        res["modes"][label] = dict(
            section_recall_at_1=round(r1 / n, 4), section_recall_at_4=round(r4 / n, 4),
            doc_recall_at_4=round(d4 / n, 4), mrr_at_10=round(rr / n, 4),
            false_abstain=false_abstain, abstain_out_of_scope=abstain,
            latency_ms_p50=round(statistics.median(lat), 2), latency_ms_p95=round(pct(lat, 0.95), 2),
            latency_ms_max=round(max(lat), 2))
        res["misses"][label] = misses

    out = ROOT / "reports" / "rag"
    out.mkdir(parents=True, exist_ok=True)
    name = corpus.name
    (out / f"{name}_eval.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    md = [f"# Retrieval evaluation — `{res['corpus']}`", "",
          f"{res['documents']} notes · {res['chunks']} chunks · {len(ins)} in-scope and "
          f"{len(outs)} out-of-scope queries · gates: v1 abstains if {res['gates']['v1']}, "
          f"v2 if {res['gates']['v2']} · "
          f"index built in {res['index_build_seconds']} s (CPU)", "",
          "| Configuration | Section R@1 | Section R@4 | Doc R@4 | MRR@10 | False abstain | "
          "Out-of-scope abstained | p50 ms | p95 ms |",
          "|---|---|---|---|---|---|---|---|---|"]
    for mode, m in res["modes"].items():
        md.append(f"| {mode} | {m['section_recall_at_1']:.1%} | {m['section_recall_at_4']:.1%} | "
                  f"{m['doc_recall_at_4']:.1%} | {m['mrr_at_10']:.3f} | {m['false_abstain']}/{len(ins)} | "
                  f"{m['abstain_out_of_scope']}/{len(outs)} | {m['latency_ms_p50']} | "
                  f"{m['latency_ms_p95']} |")
    md += ["", "Fixture caveat: the notes and the labels were written by the same person, so "
           "these numbers are an upper bound for real course notes. The v2 gate was fitted on these "
           "same queries, so its row is optimistic as well.", "", "## Misses (hybrid, v2 gate)", ""]
    md += [f"- `{m['id']}` {m['query']} — wanted {m['want']}, got {m['got']}"
           for m in res["misses"]["hybrid, v2 gate"]] or ["- none"]
    (out / f"{name}_eval.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
