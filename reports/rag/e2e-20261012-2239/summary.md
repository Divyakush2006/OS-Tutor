# RAG end to end — `data/rag/corpus`

Commit `e92fa8b055` (dirty: False) · corpus `4a2a5c9dbac6` · greedy · prompt cache off · one adapter per server

## Theory MCQ, 200 items (generated letter)

| Configuration | Correct | Accuracy |
|---|---|---|
| base+norag | 185/200 | 92.50% |
| base+rag | 186/200 | 93.00% |
| v3+norag | 186/200 | 93.00% |
| v3+rag | 184/200 | 92.00% |

| Comparison | Right→wrong | Wrong→right | exact McNemar p |
|---|---|---|---|
| base+norag -> v3+rag | 5 | 4 | 1.0000 |
| v3+norag -> v3+rag | 6 | 4 | 0.7539 |
| base+norag -> base+rag | 3 | 4 | 1.0000 |
| base+norag -> v3+norag | 1 | 2 | 1.0000 |

Items given notes by the gate: 152/200. Correct on the 130 new (unreviewed) items only: {'base+norag': 121, 'base+rag': 121, 'v3+norag': 121, 'v3+rag': 120}

## Explain answers (62 test-split questions, v3 + RAG)

- given notes: 59/62; notes included the labelled document: 46
- answers citing at least one note: **50/59**
- invented citations: **0**
- truncated at 1500 tokens: 0; fact-checker flags: 0
- median prompt 816.0 tokens, answer 261.5 tokens, 6.49 s; decode median 42.88 tok/s, slowest 41.6 tok/s

## Faithfulness

- cited-sentence checks: 143; judged supported: **117 (81.8%)**
- sentences carrying a citation: 132 of 446
- judge: untuned base model (Qwen3-4B-Instruct-2507), one yes/no per cited sentence; human-check sample: `judge_sample.md`
