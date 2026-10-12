# Retrieval evaluation — `data/rag/corpus`

105 documents · 2783 chunks · 124 in-scope and 40 out-of-scope questions (`data/rag/eval/corpus_questions.jsonl`) · loaded in 7.39 s (CPU)

| Mode | Recall@1 | Recall@5 | Doc recall@5 | MRR@10 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|
| bm25 | 46.8% | 75.8% | 88.7% | 0.586 | 0.46 | 0.72 |
| dense | 46.0% | 75.0% | 84.7% | 0.585 | 5.85 | 8.17 |
| hybrid | 46.0% | 79.0% | 87.9% | 0.615 | 6.67 | 9.21 |

Hybrid recall@5, answer in course material: 74.7% (n = 75)

Hybrid recall@5, answer in online material: 85.7% (n = 49)

## Abstain gate: keep notes if cosine ≥ 0.59 or BM25 ≥ 18.5 (calibrated on dev in this run)

| Split | In-scope given notes | Out-of-scope abstained |
|---|---|---|
| dev | 60/62 | 20/20 |
| test | 59/62 | 18/20 |

## Hybrid misses (relevant passage not in top 5)

- `c002` Is a program the same thing as a process? — wanted `course-2-os-functionalities`, got ['wiki-process-computing', 'wiki-process-computing', 'course-process-abstraction']
- `c004` Do programs usually call system calls directly, or through some API? — wanted `course-3-unix-filestructure-related-system-calls`, got ['wiki-system-call', 'wiki-system-call', 'course-process-api']
- `c006` What basic operations should any OS offer for managing processes? — wanted `course-4-the-abstraction-the-process`, got ['course-2-os-functionalities', 'course-process-abstraction', 'course-introduction-to-os']
- `c007` When does a process move into the blocked state? — wanted `course-4-the-abstraction-the-process`, got ['wiki-process-state', 'wiki-process-state', 'course-process-abstraction']
- `c008` In the cooperative approach, how does the OS ever get the CPU back from a program? — wanted `course-6-direct-execution`, got ['course-6-direct-execution', 'course-process-execution-mechanism-2', 'course-process-execution-mechanism-2']
- `c013` In lottery scheduling, what do tickets stand for? — wanted `course-9-scheduling-proportional-share`, got ['wiki-lottery-scheduling', 'wiki-lottery-scheduling', 'course-9-scheduling-proportional-share']
- `c020` How can segments be shared safely between address spaces? — wanted `course-13-segmentation`, got ['hail-processes', 'hail-processes', 'hail-processes']
- `c026` Why is the Banker's algorithm rarely used in real systems? — wanted `course-concurrency-bugs`, got ['wiki-banker-s-algorithm', 'wiki-banker-s-algorithm', 'wiki-banker-s-algorithm']
- `c035` What happens to child processes whose parent exits first? — wanted `course-process-api`, got ['wiki-fork-system-call', 'course-process-api', 'course-process-api']
- `c039` In the readers-writers solution, which reader locks out the writers? — wanted `course-reader-writer-problem`, got ['wiki-readers-writers-problem', 'wiki-readers-writers-problem', 'wiki-readers-writers-problem']
- `c042` Who translates virtual addresses to physical addresses using the page table? — wanted `course-virtual-memory`, got ['wiki-page-table', 'hail-vm', 'hail-vm']
- `c044` Walk me through what happens on a memory access when the TLB misses. — wanted `course-demand-paging`, got ['wiki-page-table', 'wiki-translation-lookaside-buffer', 'wiki-translation-lookaside-buffer']
- `c047` What happens to TLB entries on a context switch? — wanted `course-paging-1`, got ['wiki-translation-lookaside-buffer', 'wiki-context-switch', 'wiki-translation-lookaside-buffer']
- `c048` What information does a page table entry hold apart from the frame number? — wanted `course-paging-1`, got ['wiki-page-table', 'hail-vm', 'hail-vm']
- `c052` What does a process control block contain? — wanted `course-process-abstraction`, got ['wiki-process-control-block', 'wiki-process-control-block', 'wiki-process-control-block']
- `c066` Why should a semaphore used for ordering start at zero? — wanted `course-threads-sema`, got ['course-threads-sema', 'course-threads-sema', 'course-threads-sema']
- `c068` Who invented the semaphore? — wanted `course-threads-sema`, got ['wiki-semaphore-programming', 'wiki-semaphore-programming', 'course-semaphore-ppt-copy']
- `c069` How do you fix an order-violation concurrency bug? — wanted `course-threads-bugs`, got ['course-concurrency-bugs', 'course-concurrency-bugs', 'course-concurrency-bugs']
- `c075` Why is spin-waiting a performance problem? — wanted `course-threads-locks`, got ['wiki-monitor-synchronization', 'course-threads-locks', 'course-threads-locks']
- `c082` What is an adaptive mutex? — wanted `wiki-spinlock`, got ['hail-synchronization', 'hail-synchronization', 'hail-synchronization']
- `c085` Why can running a CPU-heavy job and a disk-heavy job concurrently finish sooner than running them one after the other? — wanted `hail-threads`, got ['course-1-introduction-to-os', 'wiki-scheduling-computing', 'hail-threads']
- `c086` Before Belady showed otherwise, what did people believe about adding page frames? — wanted `wiki-belady-s-anomaly`, got ['hail-vm', 'wiki-page-table', 'hail-vm']
- `c098` What is the working set of a program? — wanted `wiki-thrashing-computer-science`, got ['wiki-page-replacement-algorithm', 'course-linux-commands', 'course-introduction-to-os']
- `c109` What is cooperative scheduling? — wanted `wiki-fixed-priority-pre-emptive-scheduling`, got ['wiki-thread-computing', 'wiki-scheduling-computing', 'wiki-scheduling-computing']
- `c116` What are the downsides of demand paging? — wanted `wiki-demand-paging`, got ['wiki-demand-paging', 'hail-vm', 'wiki-demand-paging']
- `c123` Why do larger pages make the page table smaller but waste memory? — wanted `wiki-memory-management-unit`, got ['course-paging-1', 'course-17-advanced-page-tables', 'hail-vm']
