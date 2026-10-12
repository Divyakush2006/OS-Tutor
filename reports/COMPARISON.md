# Model comparison

| metric | base | v2.2 | v3.0 |
|---|---|---|---|
| **free-form (hand-written)** (n=57) | — | — | 64.9% |
|   answers cut off, free-form (hand-written) | — | — | 1.8% |
| **generator, standard** (n=?) | — | — | — |
|   answers cut off, generator, standard | — | — | — |
| **generator, held-out framings** (n=?) | — | — | — |
|   answers cut off, generator, held-out framings | — | — | — |
| OS theory MCQ (hand-written) | 90.0% | — | — |
|   OS theory MCQ (hand-written): right→wrong / wrong→right vs base | — | — | — |
| General MMLU (forgetting) | 80.2% | 79.8% | — |
|   General MMLU (forgetting): right→wrong / wrong→right vs base | — | 17 / 15 | — |
| Adjacent-CS MMLU | 64.7% | 63.7% | — |
|   Adjacent-CS MMLU: right→wrong / wrong→right vs base | — | 19 / 16 | — |

| question type, free-form suite | base | v2.2 | v3.0 |
|---|---|---|---|
| banker_request | — | — | 100.0% (2) |
| banker_safety | — | — | 75.0% (4) |
| cache_eat | — | — | 100.0% (1) |
| clarify | — | — | 0.0% (3) |
| cpu_util | — | — | 100.0% (1) |
| deadlock_min | — | — | 100.0% (2) |
| disk | — | — | 100.0% (7) |
| disk_access | — | — | 0.0% (1) |
| eat_pagefault | — | — | 100.0% (1) |
| eat_tlb | — | — | 50.0% (2) |
| fork_count | — | — | 50.0% (2) |
| freespace | — | — | 75.0% (4) |
| internal_frag | — | — | 100.0% (1) |
| multilevel_paging | — | — | 100.0% (1) |
| paging | — | — | 62.5% (8) |
| paging_bits | — | — | 100.0% (1) |
| scheduling | — | — | 41.7% (12) |
| semaphore | — | — | 100.0% (1) |
| translate | — | — | 33.3% (3) |
