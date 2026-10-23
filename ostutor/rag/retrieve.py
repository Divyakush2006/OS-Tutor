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
                  cosine of at least strong_cosine or a BM25 score of at least
                  min_bm25. BM25 scores depend on corpus statistics, so the two
                  thresholds are calibrated per corpus on held-out questions by
                  tools/rag_eval.py --calibrate and read from <corpus>/gate.json;
                  the constants below are only the fallback (fitted on the fixture).
  gate="none"     never abstain (used to measure ranking on its own).
"""
from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from pathlib import Path

import numpy as np

from .corpus import Chunk, load_corpus

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"   # Apache-2.0, 22M params, CPU
# models with an asymmetric query/passage format need their prefixes (e5: "query: ")
PREFIX = {"intfloat/multilingual-e5-base": ("query: ", "passage: ")}
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
    """Okapi BM25 over an inverted index, so a query touches only the chunks that
    contain one of its terms."""

    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b, self.n = k1, b, len(docs)
        lens = np.array([len(d) for d in docs], dtype=float)
        norm = k1 * (1 - b + b * lens / max(lens.mean() if len(docs) else 1, 1e-9))
        self.post: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        acc: dict[str, list[tuple[int, int]]] = {}
        for i, d in enumerate(docs):
            for t, f in Counter(d).items():
                acc.setdefault(t, []).append((i, f))
        for t, pl in acc.items():
            idx = np.array([i for i, _ in pl])
            f = np.array([f for _, f in pl], dtype=float)
            idf = math.log(1 + (self.n - len(pl) + 0.5) / (len(pl) + 0.5))
            self.post[t] = (idx, idf * f * (k1 + 1) / (f + norm[idx]))

    def scores(self, query: list[str]) -> np.ndarray:
        out = np.zeros(self.n)
        for t in query:
            if t in self.post:
                idx, w = self.post[t]
                out[idx] += w
        return out


class Retriever:
    """Load once at gateway start-up; retrieve() is then a few milliseconds on the CPU."""

    def __init__(self, corpus_dir: Path, dense: bool = True, embed_model: str = EMBED_MODEL):
        self.embed_model = embed_model
        self.qp, self.pp = PREFIX.get(embed_model, ("", ""))
        self.chunks, self.manifest = load_corpus(Path(corpus_dir))
        # what the passages are called to the model and to the student (manifest "label";
        # a corpus that is not the students' own notes must not be presented as such)
        lab = self.manifest.get("label", {})
        self.noun = lab.get("noun", NOUN)
        self.sources_heading = lab.get("sources_heading", SOURCES_HEADING)
        self.not_found = lab.get("not_found", "")
        self.bm25 = BM25([tokens(c.title + " " + c.section + " " + c.text) for c in self.chunks])
        self.model = None
        self.emb = None
        gate = Path(corpus_dir) / "gate.json"
        g = json.loads(gate.read_text(encoding="utf-8")) if gate.is_file() else {}
        self.strong_cosine = g.get("strong_cosine", STRONG_COSINE)
        self.min_bm25 = g.get("min_bm25", MIN_BM25)
        if dense and self.chunks:
            from sentence_transformers import SentenceTransformer
            # local_files_only: nothing about a query ever leaves the machine
            self.model = SentenceTransformer(embed_model, device="cpu", local_files_only=True)
            self.emb = self._embeddings(Path(corpus_dir))

    def _embeddings(self, root: Path) -> np.ndarray:
        """Chunk embeddings, cached in <corpus>/index/ under the corpus hash, so a gateway
        restart does not re-embed thousands of chunks."""
        key = f"{self.embed_model}|{self.manifest['chunks_sha256']}"
        stem = "embeddings" if self.embed_model == EMBED_MODEL else "emb-" + self.embed_model.split("/")[-1]
        npy, tag = root / "index" / f"{stem}.npy", root / "index" / f"{stem}.key"
        if npy.is_file() and tag.is_file() and tag.read_text(encoding="utf-8") == key:
            return np.load(npy)
        emb = self.model.encode([self.pp + c.title + ". " + c.section + ". " + c.text for c in self.chunks],
                                normalize_embeddings=True, batch_size=32)
        npy.parent.mkdir(parents=True, exist_ok=True)
        np.save(npy, emb)
        tag.write_text(key, encoding="utf-8")
        return emb

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
            q = self.model.encode([self.qp + query], normalize_embeddings=True)[0]
            cos = self.emb @ q
            rankings.append(list(np.argsort(-cos)))
        if cos is not None and gate != "none":
            if gate == "cosine" or s is None:
                if cos.max() < MIN_COSINE:
                    return []
            elif cos.max() < self.strong_cosine and s.max() < self.min_bm25:
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


NOUN = "course notes"
SOURCES_HEADING = "Sources from your course notes"


def augment(system: str, hits: list[dict], noun: str = NOUN) -> str:
    """The system prompt with the retrieved notes appended and a citation rule.

    The trained system prompt is kept word for word at the start, so the adapter still
    sees the prompt it learned the mode under; the notes follow it."""
    if not hits:
        return system
    blocks = []
    for n, h in enumerate(hits, 1):
        c: Chunk = h["chunk"]
        blocks.append(f"[S{n}] {c.citation()}\n{c.text}")
    short = "notes" if noun == NOUN else noun
    return (system + f"\n\n{noun[0].upper() + noun[1:]} that may be relevant:\n\n" + "\n\n".join(blocks)
            + f"\n\nWhere your answer relies on these {short}, cite them as [S1], [S2] and so "
              f"on. If the {short} do not cover the question, answer from your own knowledge "
              f"and say that the {short} do not cover it. Never invent a citation.")


# Words that point back to something said earlier ("Does LRU suffer from IT?").
_REFERS = re.compile(r"\b(?:it|its|this|that|these|those|they|them|their|the same|the above|"
                     r"the previous|the former|the latter)\b", re.I)
FOLLOWUP_MAX_WORDS = 12


def contextual_query(messages: list[dict], latest: str) -> str:
    """The text to retrieve with. A short follow-up that points back ("Does LRU suffer from
    it?") names nothing the indexes can match on its own; read together with the student's
    previous question it does. A rule on the CPU rather than a model rewrite: a rewrite
    would put a GPU call in front of every answer on a one-slot server. Only a short message
    that refers back, in a chat with an earlier question, is widened; a standalone question
    is retrieved as typed."""
    users = [m["content"] for m in messages
             if m.get("role") == "user" and isinstance(m.get("content"), str)]
    if not latest or len(users) < 2 or users[-1] != latest:
        return latest
    if len(latest.split()) > FOLLOWUP_MAX_WORDS or not _REFERS.search(latest):
        return latest
    return f"{users[-2]} {latest}"


def sources_footer(hits: list[dict], heading: str = SOURCES_HEADING) -> str:
    """The list of sources shown under the answer, so a student can look them up."""
    if not hits:
        return ""
    # One line per DOCUMENT: several passages of one article used to be listed as near-
    # identical sources. Every passage label stays on its line, so an [S3] in the answer
    # can still be found.
    docs = {}
    for n, h in enumerate(hits, 1):
        docs.setdefault(h["chunk"].doc_id, []).append((n, h["chunk"]))
    lines = []
    for doc_id, items in docs.items():
        labels = ", ".join(f"S{n}" for n, _ in items)
        sections = list(dict.fromkeys(c.section for _, c in items if c.section))
        where = f" — {'; '.join(sections)}" if sections else ""
        lines.append(f"> [{labels}] {items[0][1].title}{where} (`{doc_id}`)")
    return f"\n\n---\n> **{heading}**\n" + "\n".join(lines)


def cited(answer: str, n_hits: int) -> tuple[set[int], set[int]]:
    """(valid citations used, invented citations) in an answer."""
    used = {int(m) for m in re.findall(r"\[S(\d+)\]", answer)}
    return {u for u in used if 1 <= u <= n_hits}, {u for u in used if not 1 <= u <= n_hits}
