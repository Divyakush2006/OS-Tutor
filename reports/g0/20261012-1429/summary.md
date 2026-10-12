# G0 ablation — 2026-10-12T08:59:28+00:00

Commit `f86cd5c380` · dataset `f56a7113e4aa` · version: 0.4.1-dev (build 11050, commit 60b06ab9a)

## 57-item suite (served path, one adapter per server)

| Configuration | Correct | Accuracy | Delegated | Truncated |
|---|---|---|---|---|
| base | 25/57 | 43.9% | 0 | 3 |
| base+solver | 49/57 | 86.0% | 38 | 0 |
| v2.2 | 19/57 | 33.3% | 0 | 6 |
| v2.2+solver | 43/57 | 75.4% | 38 | 1 |
| v3 | 34/57 | 59.7% | 0 | 0 |
| v3+solver | 57/57 | 100.0% | 38 | 0 |

## Paired comparisons (exact McNemar)

| Question | A → B | Accuracy A → B | Right→wrong | Wrong→right | p |
|---|---|---|---|---|---|
| adapter, no solver | base → v3 | 43.9% → 59.7% | 10 | 19 | 0.1360 |
| adapter, with solver | base+solver → v3+solver | 86.0% → 100.0% | 0 | 8 | 0.0078 |
| solver, on the base model | base → base+solver | 43.9% → 86.0% | 0 | 24 | 0.0000 |
| solver, on v3 | v3 → v3+solver | 59.7% → 100.0% | 0 | 23 | 0.0000 |
| v2.2 adapter, no solver | base → v2.2 | 43.9% → 33.3% | 16 | 10 | 0.3269 |
| v2.2 -> v3, no solver | v2.2 → v3 | 33.3% → 59.7% | 2 | 17 | 0.0007 |
| v2.2 -> v3, with solver | v2.2+solver → v3+solver | 75.4% → 100.0% | 0 | 14 | 0.0001 |

Extraction at LoRA scale 0 vs the base server (identical traces): v2.2+solver 55/57, v3+solver 55/57

## OOD holdout, end to end (v3 + solver)

| Kind | n | Extraction | Grounding rejected (any / final) | Delegated | Correct | Delegated but misread |
|---|---|---|---|---|---|---|
| banker_request | 91 | 98.9% | 0.0% / 0.0% | 98.9% | 100.0% | 0 |
| banker_safety | 96 | 96.9% | 0.0% / 0.0% | 96.9% | 100.0% | 0 |
| disk | 80 | 88.8% | 0.0% / 0.0% | 100.0% | 92.5% | 9 |
| freespace | 74 | 100.0% | 0.0% / 0.0% | 100.0% | 100.0% | 0 |
| paging | 86 | 98.8% | 0.0% / 0.0% | 100.0% | 100.0% | 1 |
| scheduling | 91 | 98.9% | 0.0% / 0.0% | 98.9% | 98.9% | 0 |
| translate | 82 | 100.0% | 0.0% / 0.0% | 100.0% | 100.0% | 0 |
| **all** | 600 | 97.5% | 0.0% / 0.0% | 99.2% | 98.8% | 10 |

## Fact checker — base

- probe: 3/10 drafts flagged, 0 corrections attached, 3 finals still flagged

## Fact checker — v3

- probe: 3/10 drafts flagged, 0 corrections attached, 0 finals still flagged
- broad: 0/70 drafts flagged, 0 corrections attached, 0 finals still flagged
