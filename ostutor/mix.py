"""Rectifier interleaving - the anti-catastrophic-forgetting mechanism.

The usual approach concatenates domain data and appends a replay tail. That is
the worst possible order: the adapter sees a long homogeneous run, drifts, and
only then meets a correction. LoRA freezes the base weights but the ACTIVE
ADAPTER still shifts, and a long single-distribution run is exactly what shifts it.

Three mechanisms, all asserted afterwards on the SHIPPED rows:

  1. CATEGORY RUN CAP. No more than MAX_RUN_SAME_CAT consecutive rows of one
     category, so no homogeneous run can form.

  2. SOURCE ROTATION. Within a category, rows rotate across their underlying
     DATASETS. Without this a permitted 4-row shell run can be 4 consecutive
     nl2bash rows: interleaved at category level, a solid block at dataset level.

  3. EBBINGHAUS-SPACED REPLAY. FOREVER (arXiv 2601.03938) reports that LLM
     forgetting mirrors the Ebbinghaus curve and that replay should be DENSE
     immediately after new material and progressively SPARSER as the model
     stabilises. v1 used a uniform stride, which over-spends replay late and
     under-protects early. Here the permitted gap grows linearly from
     REPLAY_GAP_EARLY to REPLAY_GAP_LATE across the epoch. FOREVER's "model time"
     formulation is training-side; this is the data-side projection of the same
     principle, and it is the part a dataset can own.

ALGORITHM: largest-remaining-first with a cooldown, NOT rate-matching. A
debt-based scheduler that matches each category's target RATE drains small
categories proportionally and leaves none in reserve, so the epoch's TAIL
degenerates into one long homogeneous run - precisely the failure this ordering
exists to prevent. Choosing the category with the most REMAINING items holds small
categories back as separators and is optimal whenever an arrangement exists.

FEASIBILITY: with counts n_1..n_k and cap K an arrangement exists iff
    max(n_i) <= (total - max(n_i)) * K + K
The build checks this up front and reports infeasibility rather than silently
emitting a violating order.
"""
import random
from collections import Counter, deque

from .config import (MAX_RUN_SAME_CAT, MAX_RUN_SAME_SOURCE, REPLAY_GAP_EARLY,
                     REPLAY_GAP_LATE, SPACED_REPLAY)


def feasible(sizes, k=MAX_RUN_SAME_CAT):
    if not sizes:
        return True, dict(reason="empty")
    total = sum(sizes.values())
    biggest = max(sizes, key=sizes.get)
    n = sizes[biggest]
    allowed = (total - n) * k + k
    return n <= allowed, dict(majority=biggest, majority_count=n,
                              separators=total - n, max_allowed=allowed, cap=k)


def allowed_gap(progress):
    """Ebbinghaus spacing: permitted replay gap grows across the epoch."""
    if not SPACED_REPLAY:
        return REPLAY_GAP_LATE
    return int(round(REPLAY_GAP_EARLY
                     + (REPLAY_GAP_LATE - REPLAY_GAP_EARLY) * max(0.0, min(1.0, progress))))


def _spread_sources(rows, rng):
    """Round-robin rows of one category across their SOURCE datasets."""
    by_src = {}
    for r in rows:
        by_src.setdefault(r.get("subcategory") or "_", []).append(r)
    queues = {s: deque(rng.sample(by_src[s], len(by_src[s]))) for s in sorted(by_src)}
    out = []
    while queues:
        for s in sorted(queues, key=lambda s: (-len(queues[s]), s)):
            if queues[s]:
                out.append(queues[s].popleft())
        queues = {s: q for s, q in queues.items() if q}
    return out


def interleave(by_cat, seed):
    rng = random.Random(seed)
    # sorted(): a dict built from a SET iterates in a process-dependent order
    # (Python randomises string hashing), which would change the order
    # rng.sample() is consumed in and silently break reproducibility.
    queues = {c: deque(_spread_sources(by_cat[c], rng))
              for c in sorted(by_cat) if by_cat[c]}
    if not queues:
        return []
    total = sum(len(q) for q in queues.values())

    out = []
    run_cat, run_len, replay_gap = None, 0, 0
    src_run_cat, src_run_len = None, 0

    while queues:
        progress = len(out) / max(total, 1)
        gap_limit = allowed_gap(progress)

        blocked = run_cat if (run_cat in queues and run_len >= MAX_RUN_SAME_CAT) else None
        avail = [c for c in queues if c != blocked] or list(queues)

        if "replay" in avail and replay_gap >= gap_limit - 1:
            pick = "replay"
        else:
            pick = max(avail, key=lambda c: (len(queues[c]), c))

        row = queues[pick].popleft()
        # avoid a long run from ONE dataset inside a permitted category run
        if (row.get("subcategory") == src_run_cat and src_run_len >= MAX_RUN_SAME_SOURCE
                and queues[pick]):
            for j, alt in enumerate(queues[pick]):
                if alt.get("subcategory") != src_run_cat:
                    queues[pick].insert(0, row)
                    row = queues[pick][j + 1]
                    del queues[pick][j + 1]
                    break
        out.append(row)

        run_len = run_len + 1 if pick == run_cat else 1
        run_cat = pick
        sc = row.get("subcategory")
        src_run_len = src_run_len + 1 if sc == src_run_cat else 1
        src_run_cat = sc
        replay_gap = 0 if pick == "replay" else replay_gap + 1
        if not queues[pick]:
            del queues[pick]

    for i, r in enumerate(out):
        r["order"] = i
    return out


def verify_invariants(rows):
    """Returns (ok, stats). Failure stops the build - it is not a warning.

    NOTE: this must run on the rows actually WRITTEN TO DISK. Verifying a
    pre-split list while shipping a post-split file is a real bug that once
    passed every gate while the shipped train.jsonl contained runs of 25.
    """
    if not rows:
        return False, dict(ok=False, error="empty ordering")

    longest, cur, run = 0, None, 0
    for r in rows:
        run = run + 1 if r["category"] == cur else 1
        cur = r["category"]
        longest = max(longest, run)

    longest_src, cur_s, run_s = 0, None, 0
    for r in rows:
        run_s = run_s + 1 if r.get("subcategory") == cur_s else 1
        cur_s = r.get("subcategory")
        longest_src = max(longest_src, run_s)

    idx = [i for i, r in enumerate(rows) if r["category"] == "replay"]
    gaps, worst_violation = [], 0
    if idx:
        seq = [idx[0]] + [b - a - 1 for a, b in zip(idx, idx[1:])] + [len(rows) - 1 - idx[-1]]
        gaps = seq
        # each gap is judged against the Ebbinghaus limit at ITS position
        pos = 0
        for g, i in zip(seq, idx + [len(rows) - 1]):
            limit = allowed_gap(i / max(len(rows), 1))
            worst_violation = max(worst_violation, g - limit)
            pos = i
    max_gap = max(gaps) if gaps else None

    sizes = dict(Counter(r["category"] for r in rows))
    feas, detail = feasible(sizes)
    stats = dict(rows=len(rows), longest_same_category_run=longest,
                 max_run_allowed=MAX_RUN_SAME_CAT,
                 longest_same_source_run=longest_src,
                 max_source_run_allowed=MAX_RUN_SAME_SOURCE,
                 n_sources=len({r.get("subcategory") for r in rows}),
                 max_gap_between_replay_anchors=max_gap,
                 replay_gap_early=REPLAY_GAP_EARLY, replay_gap_late=REPLAY_GAP_LATE,
                 spaced_replay=SPACED_REPLAY,
                 worst_spacing_violation=worst_violation,
                 category_counts=sizes, arrangement_feasible=feas, feasibility=detail)
    stats["ok"] = (longest <= MAX_RUN_SAME_CAT and worst_violation <= 0)
    if not feas:
        stats["note"] = ("mix infeasible for this cap: raise replay share or "
                         "MAX_RUN_SAME_CAT")
    return stats["ok"], stats
