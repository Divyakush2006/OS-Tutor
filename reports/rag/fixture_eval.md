# Retrieval evaluation — `data/rag/fixture`

12 documents · 38 chunks · 45 in-scope and 10 out-of-scope questions (`data/rag/fixture/queries.jsonl`) · loaded in 7.04 s (CPU)

| Mode | Recall@1 | Recall@5 | Doc recall@5 | MRR@10 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|
| bm25 | 97.8% | 100.0% | 100.0% | 0.989 | 0.01 | 0.02 |
| dense | 95.6% | 97.8% | 100.0% | 0.969 | 4.48 | 5.63 |
| hybrid | 97.8% | 100.0% | 100.0% | 0.982 | 4.56 | 5.83 |

Hybrid recall@5, answer in course material: 100.0% (n = 45)

## Hybrid misses (relevant passage not in top 5)

- none
