# Retrieval evaluation — `data/rag/fixture`

12 notes · 38 chunks · 45 in-scope and 10 out-of-scope queries · gates: v1 abstains if cosine < 0.35, v2 if cosine < 0.45 and bm25 < 6.0 · index built in 7.29 s (CPU)

| Configuration | Section R@1 | Section R@4 | Doc R@4 | MRR@10 | False abstain | Out-of-scope abstained | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|
| bm25 | 95.6% | 100.0% | 100.0% | 0.978 | 0/45 | 5/10 | 0.03 | 0.05 |
| dense | 93.3% | 93.3% | 93.3% | 0.933 | 2/45 | 6/10 | 4.52 | 5.69 |
| hybrid, v1 gate | 91.1% | 93.3% | 95.6% | 0.927 | 2/45 | 6/10 | 4.57 | 5.71 |
| hybrid, v2 gate | 93.3% | 95.6% | 95.6% | 0.944 | 2/45 | 10/10 | 4.58 | 5.7 |

Fixture caveat: the notes and the labels were written by the same person, so these numbers are an upper bound for real course notes. The v2 gate was fitted on these same queries, so its row is optimistic as well.

## Misses (hybrid, v2 gate)

- `q12` Is SRTF preemptive? — wanted n03 / Preemptive and non-preemptive scheduling, got []
- `q14` When is busy waiting acceptable? — wanted n04 / Mutex locks and semaphores, got []
