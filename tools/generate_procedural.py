"""Generate the v3.0 procedural pool (simulator-verified, re-verified on render).

    python tools/generate_procedural.py            # pool + OOD holdout
    python tools/generate_procedural.py --only pool

WHY THE VOLUME CHANGED. v2.2 selected ~1,000 procedural rows from a 10.5k pool,
which left about 30 examples per algorithm. Tested on free-worded textbook
questions the model produced the right FORMAT and the right ARITHMETIC but the
wrong DECISIONS (kept the longer job under SRTF, evicted the wrong page, "fitted"
212 KB into a 200 KB hole): far too few repetitions of each procedure. Selection
strategies that suit knowledge data suit skills badly. v3.0 generates a large pool
and fills each family by weight (config.FAMILY_WEIGHTS), so every algorithm gets
hundreds of worked examples.

Composition: normal (exam-sized), large, and xl (very long traces, so no realistic
question can exceed what the model has practised); 11 formula kinds; and
missing-input clarification rows.

Seeds are distinct from every evaluation seed, and the build removes any row whose
parameter fingerprint matches an evaluation item regardless.
"""
import argparse
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ostutor.simulators.generate import (FORMULA_KINDS, GENERATORS, gen_clarify,  # noqa: E402
                                         gen_formula, generate, reverify)

N = dict(normal=9_000, large=3_000, xl=700)
N_FORMULA_PER_KIND = 320
N_CLARIFY = 500
N_HOLDOUT = 600
SEED = 30_260_920            # distinct from every v2 seed and every eval seed


def write(path, rows):
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def build_pool():
    rows, rejected = [], 0
    for regime, n in N.items():
        got, rej = generate(n, seed=SEED + hash(regime) % 1000, regime=regime)
        for r in got:
            r["regime"] = regime
        rows += got
        rejected += rej
        print(f"  {regime:<7} {len(got):>6} rows ({rej} rejected by re-verification)", flush=True)
    rng = random.Random(SEED ^ 0xF0)
    for kind in FORMULA_KINDS:
        made = 0
        while made < N_FORMULA_PER_KIND:
            rec = gen_formula(kind, random.Random(rng.randrange(1 << 30)))
            if not reverify(rec):
                rejected += 1
                continue
            rec.update(regime="formula", verified=True)
            rows.append(rec)
            made += 1
        print(f"  {kind:<18} {made:>6} rows", flush=True)
    made = 0
    while made < N_CLARIFY:
        rec = gen_clarify(random.Random(rng.randrange(1 << 30)))
        if not reverify(rec):
            rejected += 1
            continue
        rec.update(regime="clarify", verified=True)
        rows.append(rec)
        made += 1
    print(f"  clarify            {made:>6} rows", flush=True)
    return rows, rejected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None, choices=["pool", "holdout"])
    a = ap.parse_args()
    raw = ROOT / "data" / "raw"
    if a.only in (None, "pool"):
        rows, rejected = build_pool()
        write(raw / "procedural_v3_pool.jsonl", rows)
        fam = Counter(r["topic"] for r in rows)
        print(f"\n{len(rows)} rows -> data/raw/procedural_v3_pool.jsonl "
              f"({rejected} rejected), {len(fam)} topics")
        print("  smallest topics:", dict(fam.most_common()[-4:]))
    if a.only in (None, "holdout"):
        # Held-out framings the training generator never produces: the OOD monitor.
        ho, rej = generate(N_HOLDOUT, seed=SEED ^ 0x5EED, regime="large", holdout=True)
        write(raw / "procedural_v3_holdout.jsonl", ho)
        print(f"{len(ho)} OOD holdout rows -> data/raw/procedural_v3_holdout.jsonl ({rej} rejected)")


if __name__ == "__main__":
    main()
