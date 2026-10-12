"""Build the OS-Solve evaluation suite: in-distribution + genuine OOD.

Both suites are decontaminated against training by construction - the OOD suite
uses held-out framings the training generator never emits, and every item's seed
is disjoint from the training seeds.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ostutor import config as C
from ostutor.simulators.generate import generate

OUT = C.ROOT / "data" / "eval"
OUT.mkdir(parents=True, exist_ok=True)

# v3.0 seeds: distinct from the v3 training pool seed (tools/generate_procedural.py)
ind, _ = generate(400, seed=40_987_654, regime="normal")
ood, _ = generate(400, seed=41_123_457, regime="large", holdout=True)

for name, rows in (("os_solve_indist", ind), ("os_solve_ood", ood)):
    p = OUT / f"{name}.jsonl"
    with open(p, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{name:<20}{len(rows):>5} items -> {p}")

train = set()
tp = C.RAW / "procedural_v3_pool.jsonl"
if tp.exists():
    train = {json.loads(l)["problem"] for l in open(tp, encoding="utf-8")}
for name, rows in (("os_solve_indist", ind), ("os_solve_ood", ood)):
    ov = len({r["problem"] for r in rows} & train)
    print(f"  {name} overlap with training pool: {ov}  {'OK' if ov == 0 else 'CONTAMINATED'}")
