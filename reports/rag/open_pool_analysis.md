# Open OS corpus: pool analysis

Pool: 3291 documents, 21,740 chunks after dropping 164 stub documents (< 120 words). Kept: **17,420 chunks in 2970 documents**.

Relevance floor **0.307** = the 5th percentile of the two OS textbooks' chunks (it keeps 95% of them).

| Source | Documents | Stubs | Chunks | Kept | Words kept | Median relevance | Main drop reasons |
|---|---|---|---|---|---|---|---|
| hailperin | 8 | 0 | 882 | 800 | 133,033 | 0.537 | mostly code 45, off-syllabus 36, low letter share 1 |
| csbu | 9 | 0 | 471 | 433 | 57,972 | 0.484 | off-syllabus 27, low letter share 8, mostly code 3 |
| wikipedia | 1,176 | 92 | 11,395 | 9,386 | 1,178,390 | 0.432 | off-syllabus 1679, mostly code 236, low letter share 89, duplicate 5 |
| wikibooks | 79 | 20 | 243 | 177 | 19,136 | 0.544 | duplicate 63, off-syllabus 3 |
| stackexchange | 2,019 | 54 | 8,749 | 6,624 | 858,371 | 0.407 | off-syllabus 1602, mostly code 281, low letter share 242 |

## Answer coverage (dev short-answer questions, n = 72)

Questions for which at least one chunk contains an accepted answer — the ceiling for retrieval.

| Chunks | Questions covered |
|---|---|
| pool (all chunks) | 71/72 |
| kept | 71/72 |
| kept: hailperin | 45/72 |
| kept: csbu | 30/72 |
| kept: wikipedia | 70/72 |
| kept: wikibooks | 26/72 |
| kept: stackexchange | 63/72 |
| course corpus (for comparison) | 65/72 |

## Kept chunks per syllabus topic

| Topic | hailperin | csbu | wikipedia | wikibooks | stackexchange | Total |
|---|---|---|---|---|---|---|
| OS overview | 28 | 16 | 363 | 39 | 156 | 602 |
| OS structure | 1 | 4 | 272 | 9 | 354 | 640 |
| dual mode | 8 | 7 | 162 | 0 | 48 | 225 |
| system calls | 9 | 113 | 577 | 4 | 258 | 961 |
| interrupts | 1 | 4 | 141 | 3 | 56 | 205 |
| booting | 0 | 0 | 69 | 13 | 108 | 190 |
| processes | 2 | 8 | 179 | 2 | 135 | 326 |
| process API | 16 | 9 | 79 | 1 | 503 | 608 |
| context switch | 20 | 6 | 174 | 6 | 145 | 351 |
| threads | 73 | 5 | 199 | 4 | 225 | 506 |
| IPC | 7 | 4 | 392 | 1 | 120 | 524 |
| signals | 0 | 10 | 167 | 1 | 485 | 663 |
| CPU scheduling | 34 | 12 | 311 | 15 | 170 | 542 |
| scheduling algorithms | 1 | 0 | 57 | 3 | 48 | 109 |
| MLFQ and fair share | 4 | 0 | 74 | 0 | 24 | 102 |
| multiprocessor scheduling | 28 | 9 | 159 | 1 | 160 | 357 |
| real-time scheduling | 3 | 1 | 91 | 4 | 62 | 161 |
| race conditions | 5 | 0 | 41 | 0 | 37 | 83 |
| locks | 30 | 2 | 125 | 0 | 66 | 223 |
| semaphores | 7 | 1 | 38 | 7 | 45 | 98 |
| monitors and condition variables | 9 | 1 | 113 | 1 | 17 | 141 |
| classic sync problems | 12 | 1 | 112 | 2 | 50 | 177 |
| concurrency bugs | 37 | 13 | 415 | 3 | 93 | 561 |
| deadlock | 17 | 0 | 90 | 14 | 41 | 162 |
| memory basics | 17 | 56 | 400 | 4 | 212 | 689 |
| memory allocation | 3 | 14 | 449 | 3 | 204 | 673 |
| segmentation | 0 | 0 | 10 | 1 | 3 | 14 |
| paging | 10 | 2 | 31 | 0 | 24 | 67 |
| TLB and page tables | 10 | 14 | 49 | 0 | 31 | 104 |
| virtual memory | 123 | 51 | 660 | 9 | 1033 | 1876 |
| page replacement | 5 | 0 | 53 | 0 | 17 | 75 |
| thrashing and working set | 0 | 3 | 97 | 0 | 68 | 168 |
| storage devices | 14 | 2 | 558 | 0 | 69 | 643 |
| disk scheduling | 3 | 0 | 70 | 0 | 68 | 141 |
| RAID | 0 | 0 | 17 | 0 | 22 | 39 |
| I/O systems | 5 | 18 | 609 | 3 | 244 | 879 |
| file system interface | 65 | 27 | 400 | 3 | 411 | 906 |
| file system implementation | 68 | 12 | 833 | 18 | 635 | 1566 |
| crash consistency | 18 | 3 | 196 | 3 | 138 | 358 |
| protection and security | 98 | 1 | 277 | 0 | 23 | 399 |
| virtualisation | 9 | 4 | 277 | 0 | 16 | 306 |

Topics with fewer than 15 kept chunks: segmentation
