# Short-answer accuracy with retrieval: `data/rag/corpus` (A) vs `data/rag/open` (B)

Runs `e2e-short-course` and `e2e-20261013-1339`. Retrieval-off replies identical across the runs: 288/288.

| Grading | Split | Model + RAG | A correct | B correct | B lost | B gained | exact McNemar p |
|---|---|---|---|---|---|---|---|
| pre-registered | test | v3 | 59/72 | 62/72 | 4 | 7 | 0.5488 |
| pre-registered | test | base | 59/72 | 62/72 | 6 | 9 | 0.6072 |
| pre-registered | all | v3 | 124/144 | 123/144 | 11 | 10 | 1.0000 |
| pre-registered | all | base | 122/144 | 124/144 | 11 | 13 | 0.8388 |
| amended | test | v3 | 60/72 | 64/72 | 3 | 7 | 0.3438 |
| amended | test | base | 59/72 | 64/72 | 4 | 9 | 0.2668 |
| amended | all | v3 | 125/144 | 126/144 | 9 | 10 | 1.0000 |
| amended | all | base | 122/144 | 127/144 | 8 | 13 | 0.3833 |
