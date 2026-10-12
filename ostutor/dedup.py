"""Three-tier deduplication and eval decontamination.

  1. EXACT     blake2b over normalised text
  2. LEXICAL   MinHash-LSH, 5-gram shingles, Jaccard >= 0.80, 128 permutations
  3. SEMANTIC  embedding cosine >= 0.93

All three are needed; none subsumes another. MinHash catches "list files in the
current dir" vs "list files in the current directory". It CANNOT catch "list all
files including hidden ones" vs "show every file, hidden too" - no shared 5-gram,
one training signal. Measured here: semantic dedup removed a further ~16% of the
shell pool that MinHash had already passed, and it is what exposed a generator
producing 5,394 rows that collapsed to 22 distinct items.

Collisions keep the BEST copy (verified > permissive licence > complete), so
dedup upgrades the surviving pool rather than merely shrinking it.
"""
import hashlib
import re
from collections import Counter, defaultdict

import numpy as np
from datasketch import MinHash, MinHashLSH

from .config import (BOILERPLATE_DF, MAX_SHINGLES, MINHASH_PERM, MINHASH_THRESHOLD,
                     NGRAM_N, SEMANTIC_DUP_COSINE, SEMANTIC_DUP_COSINE_BY_CAT,
                     SHINGLE_N)

_TOK = re.compile(r"[a-z0-9]+")


def text_of(r):
    return " ".join(m["content"] for m in r["messages"]).lower()


def _shingles(t, n=SHINGLE_N, cap=MAX_SHINGLES):
    w = _TOK.findall(t)
    if len(w) < n:
        return [" ".join(w)] if w else []
    sh = [" ".join(w[i:i + n]) for i in range(len(w) - n + 1)]
    if len(sh) > cap:
        step = len(sh) / cap
        sh = [sh[int(i * step)] for i in range(cap)]
    return sh


def keep_rank(r):
    s = 0.0
    if r["lineage"].get("verified"):
        s += 100
    if r.get("commercial_ok"):
        s += 10
    if r["license"] in ("mit", "cc-by-4.0", "odc-by-1.0"):
        s += 5
    s += min(r["n_chars"], 4000) / 4000.0
    return s


def exact(records, report=None):
    best, dropped = {}, 0
    for r in records:
        h = hashlib.blake2b(text_of(r).encode(), digest_size=16).hexdigest()
        if h in best:
            dropped += 1
            if keep_rank(r) > keep_rank(best[h]):
                best[h] = r
        else:
            best[h] = r
    if report is not None:
        report["exact_removed"] = dropped
    return list(best.values())


def lexical(records, report=None):
    lsh = MinHashLSH(threshold=MINHASH_THRESHOLD, num_perm=MINHASH_PERM)
    records = sorted(records, key=keep_rank, reverse=True)
    kept, by_cat = [], Counter()
    for r in records:
        sh = _shingles(text_of(r))
        if not sh:
            continue
        m = MinHash(num_perm=MINHASH_PERM)
        m.update_batch([s.encode() for s in sh])
        if lsh.query(m):
            by_cat[r["category"]] += 1
            continue
        lsh.insert(r["id"], m)
        kept.append(r)
    if report is not None:
        report["lexical_removed"] = int(sum(by_cat.values()))
        report["lexical_by_category"] = dict(by_cat)
    return kept


def by_fingerprint(records):
    """Keep the best-quality row per parameter fingerprint. Rows with no fingerprint
    are all kept (the caller routes them through semantic dedup instead)."""
    order = sorted(range(len(records)),
                   key=lambda i: (-records[i]["quality"], records[i]["id"]))
    seen, keep = set(), []
    for i in order:
        fp = records[i]["lineage"].get("fingerprint")
        if fp:
            if fp in seen:
                continue
            seen.add(fp)
        keep.append(i)
    return sorted(keep)


def semantic(records, emb, thr=None):
    """Greedy best-quality-first: drop anything too close to an existing keeper.
    The threshold is per-category (see SEMANTIC_DUP_COSINE_BY_CAT)."""
    if thr is None:
        cat = records[0]["category"] if records else None
        thr = SEMANTIC_DUP_COSINE_BY_CAT.get(cat, SEMANTIC_DUP_COSINE)
    order = sorted(range(len(records)), key=lambda i: -records[i]["quality"])
    keep_idx, keep_emb = [], []
    for i in order:
        if keep_emb and float(np.max(np.asarray(keep_emb) @ emb[i])) >= thr:
            continue
        keep_idx.append(i)
        keep_emb.append(emb[i])
    return sorted(keep_idx)


def _grams(t, n=NGRAM_N):
    w = _TOK.findall(t.lower())
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


def decontaminate(records, eval_texts, report=None, boilerplate_df=BOILERPLATE_DF,
                  eval_fingerprints=None):
    """Drop any training row that shares a DISTINCTIVE N-gram with a held-out item.

    Without this every accuracy number the project reports is unfalsifiable.

    BOILERPLATE IS NOT CONTAMINATION. A naive "any shared 13-gram" rule removed
    5,554 of 9,500 procedural rows (58%) because eval and train problems share
    template text - the Banker's table header "p alloc a alloc b alloc c max a max
    b max c" alone appears in 428 training rows. That removes nothing leaked and
    destroys most of the OS content.

    A genuinely leaked eval item leaves n-grams that are RARE in training (its
    specific numbers, names, phrasing); boilerplate is COMMON by construction. So
    an eval n-gram counts only if at most `boilerplate_df` training rows contain
    it. Document frequency is counted only for n-grams that occur in the eval set,
    which keeps memory bounded by the eval size rather than the corpus size.

    GENERATED ROWS ARE CHECKED EXACTLY. For simulator-generated rows even
    distinctive-n-gram matching misfires: template phrases next to small random
    integers ("3 7 is this state safe ...") produce rare-looking 13-grams that
    collide by chance. Their identity is their PARAMETERS, so they are
    decontaminated by exact parameter fingerprint instead - a leak is the same
    problem, however it is worded.

    That test is "does this row have a fingerprint", not "is this row procedural".
    It was written as the latter, and v3.0's self-distilled OS TUTORING rows - whose
    user turn is a generated problem, but whose category is 'tutoring' - fell back to
    n-gram matching and lost 58% of themselves to it, the same proportion this
    docstring already records for the procedural case.
    """
    eval_fingerprints = eval_fingerprints or set()
    bad = set()
    for t in eval_texts:
        bad |= _grams(t)

    shared = []
    df = Counter()
    for r in records:
        if r["lineage"].get("fingerprint"):
            shared.append(None)                  # judged by fingerprint below
            continue
        s = _grams(" ".join(m["content"] for m in r["messages"])) & bad
        shared.append(s)
        for g in s:
            df[g] += 1

    distinctive = {g for g, c in df.items() if c <= boilerplate_df}
    kept, hits = [], Counter()
    fp_hits = 0
    for r, s in zip(records, shared):
        if s is None:
            if r["lineage"]["fingerprint"] in eval_fingerprints:
                hits[r["category"]] += 1
                fp_hits += 1
            else:
                kept.append(r)
            continue
        if s & distinctive:
            hits[r["category"]] += 1
        else:
            kept.append(r)
    if report is not None:
        report.update(ngram_n=NGRAM_N, eval_items=len(eval_texts), eval_ngrams=len(bad),
                      shared_ngrams=len(df), boilerplate_ngrams=len(df) - len(distinctive),
                      boilerplate_df_threshold=boilerplate_df,
                      eval_fingerprints=len(eval_fingerprints),
                      fingerprint_matches=fp_hits,
                      removed=dict(hits), removed_total=int(sum(hits.values())))
    return kept


def diversity(emb):
    """1 - mean pairwise cosine. An overfitting early-warning signal: a category
    whose examples cluster tightly carries far less signal than its row count."""
    if len(emb) < 2:
        return 0.0
    n = min(len(emb), 600)
    sub = emb[np.linspace(0, len(emb) - 1, n).astype(int)]
    sim = sub @ sub.T
    iu = np.triu_indices(n, 1)
    return float(1.0 - sim[iu].mean())
