"""Gold selection and ratio-enforced mixture sizing.

TOP-N BY QUALITY IS WRONG and this is the central selection insight. The top of a
quality distribution is full of NEAR-IDENTICAL rows: rank the shell pool by score,
take the best 800, and you get 800 variations on `find`. The model overfits a
narrow slice - shortcut learning arriving through SELECTION rather than through
generation. Measured: naive top-N gave nl2bash 360 / tldr 253; the method below
gave tldr 384 / nl2bash 309 / nl2sh_verified 19 / intercode 5 at a HIGHER mean
quality.

Three passes per category:
  1. QUALITY GATE     drop the weakest QUALITY_FLOOR_PCT. This is a floor -
                      diversity must never buy in garbage.
  2. SEMANTIC DEDUP   collapse paraphrases MinHash cannot see.
  3. FARTHEST-POINT   k-centre greedy: repeatedly take the candidate whose MINIMUM
                      distance to the chosen set is largest. Covers the semantic
                      space instead of crowding one corner.

RATIO ENFORCEMENT. v1 treated MIX as ceilings, so when a category came up short
the others kept their full quota and their SHARE ballooned - measured drift was
replay 31% against a 12% target, OS content 29% against 70%. Here MIX is a set of
PROPORTIONS: the achievable total is computed from the binding category and every
quota is derived from it, so the realised mixture always matches the designed one.
"""
import numpy as np

from .config import (FAMILY_WEIGHTS, FINGERPRINT_DEDUP_CATS, MIX, MIN_TOTAL, PROCEDURE_FAMILIES,
                     QUALITY_FLOOR_BY_CAT, QUALITY_FLOOR_PCT, STRATIFIED_CATS, SUBCAT_CAP,
                     SURPRISE_POOL_MULT, SURPRISE_REPLAY, TARGET_TOTAL, TUTORING_WEIGHTS)
from .dedup import by_fingerprint

DIVERSITY_TIEBREAK = 0.15


def farthest_point(emb, quality, k):
    """k-centre greedy over unit-normalised embeddings (cosine distance)."""
    n = len(emb)
    if k >= n:
        return list(range(n))
    start = int(np.argmax(quality))
    chosen = [start]
    mind = 1.0 - (emb @ emb[start])
    mind[start] = -1.0
    while len(chosen) < k:
        nxt = int(np.argmax(mind + DIVERSITY_TIEBREAK * quality))
        chosen.append(nxt)
        mind = np.minimum(mind, 1.0 - (emb @ emb[nxt]))
        mind[nxt] = -1.0
    return chosen


def family_of(subcategory):
    for f in PROCEDURE_FAMILIES:
        if subcategory.startswith(f):
            return f
    return subcategory


def waterfill(supply, total):
    """Split `total` as evenly as possible across keys without exceeding any key's
    supply; what a small key cannot take is redistributed to the others.
    Deterministic: keys are visited in sorted order."""
    alloc = {k: 0 for k in supply}
    left = min(total, sum(supply.values()))
    active = sorted(k for k in supply if supply[k] > 0)
    while left > 0 and active:
        share, extra = divmod(left, len(active))
        for i, k in enumerate(active):
            give = min(share + (1 if i < extra else 0), supply[k] - alloc[k])
            alloc[k] += give
            left -= give
        active = [k for k in active if alloc[k] < supply[k]]
    return alloc


def waterfill_weighted(supply, total, weights):
    """Like waterfill, but each key's target is proportional to its WEIGHT. What a
    key cannot supply is redistributed over the remaining keys by weight.

    v3.0: equal per-family quotas gave address translation (one formula) as much
    budget as CPU scheduling (seven algorithms with arrivals and preemption), and
    every algorithm ended up with ~30 examples - too few to learn a procedure."""
    alloc = {k: 0 for k in supply}
    left = min(total, sum(supply.values()))
    active = sorted(k for k in supply if supply[k] > 0)
    while left > 0 and active:
        wsum = sum(weights.get(k, 0.0) for k in active) or float(len(active))
        before = pool = left
        for k in active:
            w = weights.get(k, 0.0) or (1.0 / len(active))
            # size every share from the SAME pool: decrementing `left` inside the
            # loop gave the first families the whole budget
            give = min(int(pool * w / wsum), supply[k] - alloc[k])
            alloc[k] += give
            left -= give
        if left == before:                      # rounding: hand out one at a time
            for k in sorted(active, key=lambda x: -weights.get(x, 0.0)):
                if left <= 0:
                    break
                if alloc[k] < supply[k]:
                    alloc[k] += 1
                    left -= 1
        active = [k for k in active if alloc[k] < supply[k]]
    return alloc


def stratified_pick(rows, emb, quality, quota):
    """Equal quota per procedure family, then per variant, farthest-point inside
    each cell. Returns (indices, per-family allocation)."""
    cells = {}
    for j, r in enumerate(rows):
        cells.setdefault(family_of(r["subcategory"]), {}).setdefault(
            r["subcategory"], []).append(j)
    fam_alloc = waterfill_weighted({f: sum(map(len, s.values())) for f, s in cells.items()},
                                   quota, FAMILY_WEIGHTS)
    pick = []
    for f in sorted(cells):
        sub_alloc = waterfill({s: len(ix) for s, ix in cells[f].items()}, fam_alloc[f])
        for s in sorted(cells[f]):
            ix, k = cells[f][s], sub_alloc[s]
            if k:
                pick += [ix[i] for i in farthest_point(emb[ix], quality[ix], k)]
    return pick, fam_alloc


def domain_pick(rows, emb, quality, quota, weights):
    """Weighted quota per DOMAIN, farthest-point inside each domain.

    Used for tutoring. Selecting across the whole category at once let the domain
    with more embedding spread take almost everything; allocating first and
    selecting within each domain keeps both, and still picks the most diverse rows
    available inside each one. Returns (indices, allocation)."""
    cells = {}
    for j, r in enumerate(rows):
        cells.setdefault(r.get("domain", "?"), []).append(j)
    alloc = waterfill_weighted({d: len(ix) for d, ix in cells.items()}, quota, weights)
    pick = []
    for d in sorted(cells):
        ix, k = cells[d], alloc.get(d, 0)
        if k:
            pick += [ix[i] for i in farthest_point(emb[ix], quality[ix], k)]
    return pick, alloc


def _subcat_cap(rows, idx, quota):
    """No single source may exceed SUBCAT_CAP of a category. Without this one
    large source becomes a monoculture even after diversity selection, because
    it simply dominates the candidate pool."""
    cap = max(1, int(quota * SUBCAT_CAP))
    per, out, overflow = {}, [], []
    for i in idx:
        # Stop at quota. Callers may pass MORE candidates than quota (the SuRe
        # path passes a 3x pool ranked by surprise); without this the category
        # overshoots and silently breaks ratio enforcement.
        if len(out) >= quota:
            overflow.append(i)
            continue
        sc = rows[i]["subcategory"]
        if per.get(sc, 0) < cap:
            per[sc] = per.get(sc, 0) + 1
            out.append(i)
        else:
            overflow.append(i)
    # Backfill to quota, but take from the subcategories furthest below the cap
    # first. Popping the overflow in order refilled with the very source that had
    # just been capped (tutoring: MathDial capped at 336, then backfilled to 912),
    # which made the cap decorative. The cap can still be exceeded when nothing
    # else is left - reaching quota matters more - but only as a last resort.
    starved = 0
    overflow.sort(key=lambda i: per.get(rows[i]["subcategory"], 0))
    while len(out) < quota and overflow:
        i = overflow.pop(0)
        sc = rows[i]["subcategory"]
        per[sc] = per.get(sc, 0) + 1
        out.append(i)
        starved += 1
        overflow.sort(key=lambda j: per.get(rows[j]["subcategory"], 0))
    return out, per, starved


def prepare_pools(rows, emb, semantic_fn, report):
    """Quality-gate and semantically dedup every category BEFORE sizing, so the
    ratio calculation is based on genuinely distinct supply rather than raw rows."""
    pools = {}
    for cat in MIX:
        idx = [i for i, r in enumerate(rows) if r["category"] == cat]
        rep = dict(raw_pool=len(idx))
        if not idx:
            pools[cat] = ([], None)
            rep.update(after_gate=0, distinct_supply=0, status="NOT_BUILT")
            report[cat] = rep
            continue
        sub = [rows[i] for i in idx]
        sube = emb[idx]
        q = np.array([r["quality"] for r in sub])
        floor = float(np.quantile(q, QUALITY_FLOOR_BY_CAT.get(cat, QUALITY_FLOOR_PCT)))
        gate = [j for j in range(len(sub)) if sub[j]["quality"] >= floor]
        g_rows, g_emb = [sub[j] for j in gate], sube[gate]
        if cat in FINGERPRINT_DEDUP_CATS:
            # Parameter identity for generated rows; embedding dedup for the rest.
            keep = by_fingerprint(g_rows)
            nofp = [j for j in keep if not g_rows[j]["lineage"].get("fingerprint")]
            if nofp:
                ok = set(nofp[j] for j in semantic_fn([g_rows[j] for j in nofp],
                                                      g_emb[nofp]))
                keep = [j for j in keep if j in ok or j not in set(nofp)]
        else:
            keep = semantic_fn(g_rows, g_emb)
        d_rows, d_emb = [g_rows[j] for j in keep], g_emb[keep]
        pools[cat] = (d_rows, d_emb)
        rep.update(quality_floor=round(floor, 4), after_gate=len(g_rows),
                   distinct_supply=len(d_rows),
                   semdup_removed=len(g_rows) - len(keep))
        report[cat] = rep
    return pools


def achievable_total(pools):
    """Largest total for which every category can meet its designed PROPORTION.

    total = min over categories of (distinct_supply_c / share_c), capped at
    TARGET_TOTAL. The binding category is reported so the deficit is attributable.
    """
    limits = {}
    for cat, share in MIX.items():
        supply = len(pools.get(cat, ([], None))[0])
        limits[cat] = int(supply / share) if share > 0 else TARGET_TOTAL
    binding = min(limits, key=limits.get)
    total = min(TARGET_TOTAL, limits[binding])
    return total, binding, limits


def select_all(rows, emb, semantic_fn, report):
    pools = prepare_pools(rows, emb, semantic_fn, report)
    total, binding, limits = achievable_total(pools)
    report["_sizing"] = dict(target_ceiling=TARGET_TOTAL, achievable_total=total,
                             binding_category=binding, per_category_limit=limits,
                             note=("total is bound by the category with the least "
                                   "distinct supply relative to its designed share"))
    if total < MIN_TOTAL:
        report["_sizing"]["status"] = "BELOW_MIN_TOTAL"

    selected = []
    for cat, share in MIX.items():
        quota = int(round(share * total))
        d_rows, d_emb = pools.get(cat, ([], None))
        rep = report[cat]
        if not d_rows or quota == 0:
            rep.update(quota=quota, selected=0, status=rep.get("status", "EMPTY"))
            continue
        qv = np.array([r["quality"] for r in d_rows])
        if cat == "replay" and SURPRISE_REPLAY and len(d_rows) > quota:
            # SuRe: diverse candidate pool first, then rank by base-model NLL.
            from .surprise import compute
            pool = farthest_point(d_emb, qv, min(len(d_rows), quota * SURPRISE_POOL_MULT))
            nll = compute([d_rows[j] for j in pool])
            for j in pool:
                d_rows[j]["surprise"] = nll.get(d_rows[j]["id"], 0.0)
            pick = sorted(pool, key=lambda j: (-d_rows[j]["surprise"], d_rows[j]["id"]))
            rep["surprise_pool"] = len(pool)
            rep["surprise_mean_selected"] = round(float(np.mean(
                [d_rows[j]["surprise"] for j in pick[:quota]])), 4)
            rep["surprise_mean_pool"] = round(float(np.mean(
                [d_rows[j]["surprise"] for j in pool])), 4)
        elif cat in STRATIFIED_CATS:
            pick, fam_alloc = stratified_pick(d_rows, d_emb, qv, min(quota, len(d_rows)))
            rep["family_allocation"] = fam_alloc
        elif cat == "tutoring":
            pick, dom_alloc = domain_pick(d_rows, d_emb, qv, min(quota, len(d_rows)),
                                          TUTORING_WEIGHTS)
            rep["domain_allocation"] = dom_alloc
        else:
            pick = farthest_point(d_emb, qv, min(quota, len(d_rows)))
        pick, per, starved = _subcat_cap(d_rows, pick, quota)
        sel = [d_rows[j] for j in pick]
        selected += sel
        rep.update(quota=quota, selected=len(sel), cap_backfilled=starved,
                   mean_quality=round(float(np.mean([r["quality"] for r in sel])), 4),
                   subcategories=dict(per),
                   status="OK" if len(sel) >= quota else "SHORT")
    return selected, total, binding
