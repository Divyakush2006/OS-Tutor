# RAG end to end — `data/rag/open`

Commit `4983451d0d` (dirty: False) · corpus `f16f42d89331` · greedy · prompt cache off · one adapter per server

## Theory MCQ, 200 items (generated letter)

| Configuration | Correct | Accuracy |
|---|---|---|
| base+norag | 185/200 | 92.50% |
| base+rag | 184/200 | 92.00% |
| v3+norag | 186/200 | 93.00% |
| v3+rag | 186/200 | 93.00% |

| Comparison | Right→wrong | Wrong→right | exact McNemar p |
|---|---|---|---|
| base+norag -> v3+rag | 6 | 7 | 1.0000 |
| v3+norag -> v3+rag | 5 | 5 | 1.0000 |
| base+norag -> base+rag | 6 | 5 | 1.0000 |
| base+norag -> v3+norag | 1 | 2 | 1.0000 |

Items given notes by the gate: 187/200. Correct on the 130 new (unreviewed) items only: {'base+norag': 121, 'base+rag': 121, 'v3+norag': 121, 'v3+rag': 121}

## Short-answer questions, test (72 items; pre-registered grading)

| Configuration | Correct | Accuracy |
|---|---|---|
| base+norag | 48/72 | 66.67% |
| base+rag | 62/72 | 86.11% |
| v3+norag | 49/72 | 68.06% |
| v3+rag | 62/72 | 86.11% |

| Comparison | Right→wrong | Wrong→right | exact McNemar p |
|---|---|---|---|
| v3+norag -> v3+rag | 4 | 17 | 0.0072 |
| base+norag -> base+rag | 3 | 17 | 0.0026 |
| base+norag -> v3+rag | 2 | 16 | 0.0013 |
| base+norag -> v3+norag | 3 | 4 | 1.0000 |

Notes given to v3 contained an accepted answer for 59/72 items.

## Short-answer questions, all (144 items; pre-registered grading)

| Configuration | Correct | Accuracy |
|---|---|---|
| base+norag | 100/144 | 69.44% |
| base+rag | 124/144 | 86.11% |
| v3+norag | 102/144 | 70.83% |
| v3+rag | 123/144 | 85.42% |

| Comparison | Right→wrong | Wrong→right | exact McNemar p |
|---|---|---|---|
| v3+norag -> v3+rag | 9 | 30 | 0.0011 |
| base+norag -> base+rag | 7 | 31 | 0.0001 |
| base+norag -> v3+rag | 6 | 29 | 0.0001 |
| base+norag -> v3+norag | 6 | 8 | 0.7905 |

Notes given to v3 contained an accepted answer for 116/144 items.

## Short-answer questions, test (72 items; amended grading, secondary)

| Configuration | Correct | Accuracy |
|---|---|---|
| base+norag | 50/72 | 69.44% |
| base+rag | 64/72 | 88.89% |
| v3+norag | 51/72 | 70.83% |
| v3+rag | 64/72 | 88.89% |

| Comparison | Right→wrong | Wrong→right | exact McNemar p |
|---|---|---|---|
| v3+norag -> v3+rag | 3 | 16 | 0.0044 |
| base+norag -> base+rag | 2 | 16 | 0.0013 |
| base+norag -> v3+rag | 1 | 15 | 0.0005 |
| base+norag -> v3+norag | 3 | 4 | 1.0000 |

Notes given to v3 contained an accepted answer for 59/72 items.

## Short-answer questions, all (144 items; amended grading, secondary)

| Configuration | Correct | Accuracy |
|---|---|---|
| base+norag | 104/144 | 72.22% |
| base+rag | 127/144 | 88.19% |
| v3+norag | 105/144 | 72.92% |
| v3+rag | 126/144 | 87.50% |

| Comparison | Right→wrong | Wrong→right | exact McNemar p |
|---|---|---|---|
| v3+norag -> v3+rag | 7 | 28 | 0.0005 |
| base+norag -> base+rag | 5 | 28 | 0.0001 |
| base+norag -> v3+rag | 4 | 26 | 0.0001 |
| base+norag -> v3+norag | 6 | 7 | 1.0000 |

Notes given to v3 contained an accepted answer for 116/144 items.

## Explain answers (72 test-split questions, v3 + RAG)

- given notes: 72/72; notes included the labelled document (other corpora: an accepted answer): 59
- answers citing at least one note: **69/72**
- invented citations: **0**
- truncated at 1500 tokens: 0; fact-checker flags: 0
- median prompt 902.5 tokens, answer 137.5 tokens, 3.6 s; decode median 42.05 tok/s, slowest 39.22 tok/s

## Faithfulness

- cited-sentence checks: 138; judged supported: **110 (79.7%)**
- sentences carrying a citation: 127 of 309
- judge: untuned base model (Qwen3-4B-Instruct-2507), one yes/no per cited sentence; human-check sample: `judge_sample.md`
