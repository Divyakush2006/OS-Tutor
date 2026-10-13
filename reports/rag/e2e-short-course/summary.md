# RAG end to end — `data/rag/corpus`

Commit `4983451d0d` (dirty: False) · corpus `4a2a5c9dbac6` · greedy · prompt cache off · one adapter per server


## Short-answer questions, test (72 items; pre-registered grading)

| Configuration | Correct | Accuracy |
|---|---|---|
| base+norag | 48/72 | 66.67% |
| base+rag | 59/72 | 81.94% |
| v3+norag | 49/72 | 68.06% |
| v3+rag | 59/72 | 81.94% |

| Comparison | Right→wrong | Wrong→right | exact McNemar p |
|---|---|---|---|
| v3+norag -> v3+rag | 4 | 14 | 0.0309 |
| base+norag -> base+rag | 3 | 14 | 0.0127 |
| base+norag -> v3+rag | 3 | 14 | 0.0127 |
| base+norag -> v3+norag | 3 | 4 | 1.0000 |

Notes given to v3 contained an accepted answer for 48/72 items.

## Short-answer questions, all (144 items; pre-registered grading)

| Configuration | Correct | Accuracy |
|---|---|---|
| base+norag | 100/144 | 69.44% |
| base+rag | 122/144 | 84.72% |
| v3+norag | 102/144 | 70.83% |
| v3+rag | 124/144 | 86.11% |

| Comparison | Right→wrong | Wrong→right | exact McNemar p |
|---|---|---|---|
| v3+norag -> v3+rag | 4 | 26 | 0.0001 |
| base+norag -> base+rag | 4 | 26 | 0.0001 |
| base+norag -> v3+rag | 3 | 27 | 0.0000 |
| base+norag -> v3+norag | 6 | 8 | 0.7905 |

Notes given to v3 contained an accepted answer for 95/144 items.

## Short-answer questions, test (72 items; amended grading, secondary)

| Configuration | Correct | Accuracy |
|---|---|---|
| base+norag | 50/72 | 69.44% |
| base+rag | 59/72 | 81.94% |
| v3+norag | 51/72 | 70.83% |
| v3+rag | 60/72 | 83.33% |

| Comparison | Right→wrong | Wrong→right | exact McNemar p |
|---|---|---|---|
| v3+norag -> v3+rag | 4 | 13 | 0.0490 |
| base+norag -> base+rag | 3 | 12 | 0.0352 |
| base+norag -> v3+rag | 3 | 13 | 0.0213 |
| base+norag -> v3+norag | 3 | 4 | 1.0000 |

Notes given to v3 contained an accepted answer for 48/72 items.

## Short-answer questions, all (144 items; amended grading, secondary)

| Configuration | Correct | Accuracy |
|---|---|---|
| base+norag | 104/144 | 72.22% |
| base+rag | 122/144 | 84.72% |
| v3+norag | 105/144 | 72.92% |
| v3+rag | 125/144 | 86.81% |

| Comparison | Right→wrong | Wrong→right | exact McNemar p |
|---|---|---|---|
| v3+norag -> v3+rag | 4 | 24 | 0.0002 |
| base+norag -> base+rag | 4 | 22 | 0.0005 |
| base+norag -> v3+rag | 3 | 24 | 0.0000 |
| base+norag -> v3+norag | 6 | 7 | 1.0000 |

Notes given to v3 contained an accepted answer for 95/144 items.
