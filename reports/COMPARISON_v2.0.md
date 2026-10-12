| metric | base | fine-tuned | change |
|---|---|---|---|
| OS accuracy, in-distribution | 20.0% | 32.5% | +12.5 pts |
| OS accuracy, in-distribution: answers cut off | 77.5% | 0.0% | -77.5 pts |
| OS accuracy, OOD | 7.5% | 32.5% | +25.0 pts |
| OS accuracy, OOD: answers cut off | 87.5% | 2.5% | -85.0 pts |
| General MMLU (forgetting check) | 80.2% | 80.0% | -0.2 pts |
| Adjacent-CS MMLU | 64.7% | 64.3% | -0.3 pts |
| adjacent_cs: right→wrong / wrong→right flips | | 17 / 16 | |
| general: right→wrong / wrong→right flips | | 18 / 17 | |

| topic (in-dist / OOD) | base | fine-tuned |
|---|---|---|
| banker_request | 100.0% / 0.0% | 100.0% / 81.8% |
| banker_safety | 0.0% / 0.0% | 62.5% / 44.4% |
| disk | 0.0% / 0.0% | 50.0% / 0.0% |
| freespace | 0.0% / 0.0% | 0.0% / 0.0% |
| paging | 0.0% / 0.0% | 37.5% / 0.0% |
| scheduling | 0.0% / 0.0% | 11.1% / 0.0% |
| translate | 87.5% / 100.0% | 25.0% / 0.0% |
