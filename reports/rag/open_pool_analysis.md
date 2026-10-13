# Open OS corpus: pool analysis

Pool: 3291 documents, 23,131 chunks after dropping 143 stub documents (< 120 words). Kept: **18,578 chunks in 3003 documents**.

Relevance floor **0.307** = the 5th percentile of the two OS textbooks' chunks (it keeps 95% of them).

| Source | Documents | Stubs | Chunks | Kept | Words kept | Median relevance | Main drop reasons |
|---|---|---|---|---|---|---|---|
| hailperin | 8 | 0 | 882 | 800 | 133,033 | 0.537 | mostly code 45, off-syllabus 36, low letter share 1 |
| csbu | 9 | 0 | 471 | 433 | 57,972 | 0.484 | off-syllabus 27, low letter share 8, mostly code 3 |
| wikipedia | 1,176 | 71 | 12,786 | 10,544 | 1,216,081 | 0.433 | off-syllabus 1876, mostly code 237, low letter share 122, duplicate 7 |
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
| OS overview | 28 | 16 | 404 | 39 | 156 | 643 |
| OS structure | 1 | 4 | 298 | 9 | 354 | 666 |
| dual mode | 8 | 7 | 184 | 0 | 48 | 247 |
| system calls | 9 | 113 | 657 | 4 | 258 | 1041 |
| interrupts | 1 | 4 | 175 | 3 | 56 | 239 |
| booting | 0 | 0 | 76 | 13 | 108 | 197 |
| processes | 2 | 8 | 194 | 2 | 135 | 341 |
| process API | 16 | 9 | 89 | 1 | 503 | 618 |
| context switch | 20 | 6 | 183 | 6 | 145 | 360 |
| threads | 73 | 5 | 222 | 4 | 225 | 529 |
| IPC | 7 | 4 | 457 | 1 | 120 | 589 |
| signals | 0 | 10 | 195 | 1 | 485 | 691 |
| CPU scheduling | 34 | 12 | 344 | 15 | 170 | 575 |
| scheduling algorithms | 1 | 0 | 64 | 3 | 48 | 116 |
| MLFQ and fair share | 4 | 0 | 85 | 0 | 24 | 113 |
| multiprocessor scheduling | 28 | 9 | 182 | 1 | 160 | 380 |
| real-time scheduling | 3 | 1 | 101 | 4 | 62 | 171 |
| race conditions | 5 | 0 | 45 | 0 | 37 | 87 |
| locks | 30 | 2 | 143 | 0 | 66 | 241 |
| semaphores | 7 | 1 | 41 | 7 | 45 | 101 |
| monitors and condition variables | 9 | 1 | 124 | 1 | 17 | 152 |
| classic sync problems | 12 | 1 | 131 | 2 | 50 | 196 |
| concurrency bugs | 37 | 13 | 460 | 3 | 93 | 606 |
| deadlock | 17 | 0 | 95 | 14 | 41 | 167 |
| memory basics | 17 | 56 | 419 | 4 | 212 | 708 |
| memory allocation | 3 | 14 | 502 | 3 | 204 | 726 |
| segmentation | 0 | 0 | 13 | 1 | 3 | 17 |
| paging | 10 | 2 | 36 | 0 | 24 | 72 |
| TLB and page tables | 10 | 14 | 50 | 0 | 31 | 105 |
| virtual memory | 123 | 51 | 750 | 9 | 1033 | 1966 |
| page replacement | 5 | 0 | 61 | 0 | 17 | 83 |
| thrashing and working set | 0 | 3 | 102 | 0 | 68 | 173 |
| storage devices | 14 | 2 | 597 | 0 | 69 | 682 |
| disk scheduling | 3 | 0 | 85 | 0 | 68 | 156 |
| RAID | 0 | 0 | 19 | 0 | 22 | 41 |
| I/O systems | 5 | 18 | 691 | 3 | 244 | 961 |
| file system interface | 65 | 27 | 500 | 3 | 411 | 1006 |
| file system implementation | 68 | 12 | 906 | 18 | 635 | 1639 |
| crash consistency | 18 | 3 | 215 | 3 | 138 | 377 |
| protection and security | 98 | 1 | 319 | 0 | 23 | 441 |
| virtualisation | 9 | 4 | 330 | 0 | 16 | 359 |

Topics with fewer than 15 kept chunks: none
