# 20261012-1429 re-graded with the grader at `18e5025ea5`

| Configuration | As run | Re-graded | Items that changed |
|---|---|---|---|
| base | 25/57 | 30/57 | fcfs_disk, lru_4f, scan_down, sstf_2, translate_4k |
| base+solver | 49/57 | 49/57 | — |
| v2.2 | 19/57 | 19/57 | — |
| v2.2+solver | 43/57 | 43/57 | — |
| v3 | 34/57 | 34/57 | — |
| v3+solver | 57/57 | 57/57 | — |

| Question | A → B | Correct A → B | Right→wrong | Wrong→right | exact McNemar p |
|---|---|---|---|---|---|
| adapter, no solver | base → v3 | 30 → 34 | 11 | 15 | 0.5572 |
| adapter, with solver | base+solver → v3+solver | 49 → 57 | 0 | 8 | 0.0078 |
| solver, on the base model | base → base+solver | 30 → 49 | 0 | 19 | 0.0000 |
| solver, on v3 | v3 → v3+solver | 34 → 57 | 0 | 23 | 0.0000 |
| v2.2 adapter, no solver | base → v2.2 | 30 → 19 | 17 | 6 | 0.0347 |
| v2.2 -> v3, no solver | v2.2 → v3 | 19 → 34 | 2 | 17 | 0.0007 |
