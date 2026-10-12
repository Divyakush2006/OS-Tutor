"""Hybrid retrieval with citations: BM25 + dense embeddings, fused by reciprocal rank.

Why both. BM25 finds the exact term a student types ("Belady", "TLB", "inode") that a
small embedding model can blur; the embedding finds the paraphrase BM25 misses ("the
system spends all its time swapping" -> thrashing). Reciprocal-rank fusion (Cormack et
al., SIGIR 2009) combines the two rankings without tuning a weight between scores that
live on different scales.

Why an abstain gate. A passage that is merely the least-bad match is worse than none:
the model would cite it as support. When the gate says "not covered", retrieval returns
nothing and the answer is generated exactly as without RAG.

  gate="cosine"   (v1, chosen before any measurement) abstain if the best dense
                  similarity is below MIN_COSINE. Measured on the fixture it cannot
                  separate the two classes: in-scope questions go as low as 0.34 and
                  out-of-scope ones as high as 0.40 (reports/rag/fixture_eval.md).
  gate="combined" (v2, the default) keep the hits if EITHER signal is strong - a
                  cosine of at least STRONG_COSINE or a BM25 score of at least
                  MIN_BM25. Fitted on the same fixture queries it is reported on, so
                  its fixture numbers are optimistic; MIN_BM25 also depends on corpus
                  statistics and must be refitted on held-out queries over the owners'
                  notes.
"""
from __future__ import annotations

import math
import re
import time
from collections import Counter
from pathlib import Path

import numpy as np

from .corpus import Chunk, load_corpus

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"   # Apache-2.0, 22M params, CPU
RRF_K = 60                # the constant from Cormack et al.
MIN_COSINE = 0.35         # v1 gate: below this the best passage is not about the question
STRONG_COSINE = 0.45      # v2 gate: a clear semantic match on its own ...
MIN_BM25 = 6.0            # ... or a clear lexical one (fitted on the fixture; refit)
_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = set("a an the of to in on for and or is are was be by with as at it its this that "
            "what why how when which does do can there their from into than then".split())


def tokens(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.tf = [Counter(d) for d in docs]
        self.len = [len(d) for d in docs]
        self.avg = sum(self.len) / max(len(docs), 1)
        df = Counter(t for d in docs for t in set(d))
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query: list[str]) -> np.ndarray:
        out = np.zeros(len(self.tf))
        for i, (tf, dl) in enumerate(zip(self.tf, self.len)):
            s = 0.0
            for t in query:
                f = tf.get(t)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (
                        f + self.k1 * (1 - self.b + self.b * dl / self.avg))
            out[i] = s
        return out


class Retriever:
    """Load once at gateway start-up; retrieve() is then a few milliseconds on the CPU."""

    def __init__(self, corpus_dir: Path, dense: bool = True):
        self.chunks, self.manifest = load_corpus(Path(corpus_dir))
        self.bm25 = BM25([tokens(c.section + " " + c.text) for c in self.chunks])
        self.model = None
        self.emb = None
        if dense and self.chunks:
            from sentence_transformers import SentenceTransformer
            # local_files_only: nothing about a query ever leaves the machine
            self.model = SentenceTransformer(EMBED_MODEL, device="cpu", local_files_only=True)
            self.emb = self.model.encode([c.section + ". " + c.text for c in self.chunks],
                                         normalize_embeddings=True, batch_size=32)

    def retrieve(self, query: str, k: int = 4, mode: str = "hybrid",
                 gate: str = "combined") -> list[dict]:
        """Top-k chunks as dicts {chunk, score, cosine}; [] when nothing is relevant."""
        if not self.chunks:
            return []
        rankings, cos, s = [], None, None
        if mode in ("hybrid", "bm25"):
            s = self.bm25.scores(tokens(query))
            rankings.append([i for i in np.argsort(-s) if s[i] > 0])
        if mode in ("hybrid", "dense") and self.model is not None:
            q = self.model.encode([query], normalize_embeddings=True)[0]
            cos = self.emb @ q
            rankings.append(list(np.argsort(-cos)))
        if cos is not None:
            if gate == "cosine" or s is None:
                if cos.max() < MIN_COSINE:
                    return []
            elif cos.max() < STRONG_COSINE and s.max() < MIN_BM25:
                return []
        fused: dict[int, float] = {}
        for ranking in rankings:
            for r, i in enumerate(ranking):
                fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_K + r + 1)
        best = sorted(fused, key=lambda i: -fused[i])[:k]
        return [dict(chunk=self.chunks[i], score=fused[i],
                     cosine=None if cos is None else float(cos[i])) for i in best]

    def timed(self, query: str, **kw) -> tuple[list[dict], float]:
        t = time.perf_counter()
        hits = self.retrieve(query, **kw)
        return hits, (time.perf_counter() - t) * 1000


def augment(system: str, hits: list[dict]) -> str:
    """The system prompt with the retrieved notes appended and a citation rule.

    The trained system prompt is kept word for word at the start, so the adapter still
    sees the prompt it learned the mode under; the notes follow it."""
    if not hits:
        return system
    blocks = []
    for n, h in enumerate(hits, 1):
        c: Chunk = h["chunk"]
        blocks.append(f"[S{n}] {c.citation()}\n{c.text}")
    return (system + "\n\nCourse notes that may be relevant:\n\n" + "\n\n".join(blocks)
            + "\n\nWhere your answer relies on these notes, cite them as [S1], [S2] and so "
              "on. If the notes do not cover the question, answer from your own knowledge "
              "and say that the notes do not cover it. Never invent a citation.")


def sources_footer(hits: list[dict]) -> str:
    """The list of sources shown under the answer, so a student can look them up."""
    if not hits:
        return ""
    lines = [f"> [S{n}] {h['chunk'].citation()} (`{h['chunk'].doc_id}`)"
             for n, h in enumerate(hits, 1)]
    return "\n\n---\n> **Sources from your course notes**\n" + "\n".join(lines)


def cited(answer: str, n_hits: int) -> tuple[set[int], set[int]]:
    """(valid citations used, invented citations) in an answer."""
    used = {int(m) for m in re.findall(r"\[S(\d+)\]", answer)}
    return {u for u in used if 1 <= u <= n_hits}, {u for u in used if not 1 <= u <= n_hits}
