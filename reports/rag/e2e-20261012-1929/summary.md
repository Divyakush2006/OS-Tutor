# RAG end to end — `data/rag/fixture`

Commit `18e5025ea5` (dirty: False) · v3 adapter, one adapter per server · greedy · prompt cache off

## A. Theory MCQ (70 items, generated letter; not comparable to the logit-scored 85.71%)

| Items | Off | On | Right→wrong | Wrong→right | exact McNemar p |
|---|---|---|---|---|---|
| all 70 | 65/70 | 65/70 | 1 | 1 | 1.0000 |
| 53 with notes retrieved | 48/53 | 48/53 | 1 | 1 | 1.0000 |

## B. Explain answers

- in-scope questions given notes: 43; answers citing at least one note: **41/43**
- invented citations (a [S*n*] with no such note), all answers: **0**
- out-of-scope questions given notes: 0/10
- answers flagged by the fact checker: off 1, on 0 (of 55)
- median prompt tokens (in-scope): off 42, on 424
- median answer length, tokens: off 700, on 225
- median time to full answer, s: off 16.18, on 5.54
- generation speed, median tok/s: off 43.36, on 43.14; slowest answer with RAG 41.66 tok/s (brief: >= 20)
