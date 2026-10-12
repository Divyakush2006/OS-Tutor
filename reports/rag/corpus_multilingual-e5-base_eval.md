# Retrieval evaluation — `data/rag/corpus`

105 documents · 2783 chunks · 124 in-scope and 40 out-of-scope questions (`data/rag/eval/corpus_questions.jsonl`) · loaded in 9.4 s (CPU)

| Mode | Recall@1 | Recall@5 | Doc recall@5 | MRR@10 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|
| bm25 | 46.8% | 75.8% | 88.7% | 0.586 | 0.46 | 0.63 |
| dense | 48.4% | 76.6% | 85.5% | 0.605 | 21.49 | 25.0 |
| hybrid | 48.4% | 81.5% | 91.1% | 0.625 | 21.76 | 25.24 |

Hybrid recall@5, answer in course material: 78.7% (n = 75)

Hybrid recall@5, answer in online material: 85.7% (n = 49)

## Abstain gate: keep notes if cosine ≥ 0.84 or BM25 ≥ 18.5

| Split | In-scope given notes | Out-of-scope abstained |
|---|---|---|
| dev | 60/62 | 16/20 |
| test | 59/62 | 18/20 |

## Hybrid misses (relevant passage not in top 5)

- `c002` Is a program the same thing as a process? — wanted `course-2-os-functionalities`, got ['wiki-process-computing', 'course-process-abstraction', 'wiki-process-computing']
- `c006` What basic operations should any OS offer for managing processes? — wanted `course-4-the-abstraction-the-process`, got ['course-2-os-functionalities', 'course-2-os-functionalities', 'hail-processes']
- `c020` How can segments be shared safely between address spaces? — wanted `course-13-segmentation`, got ['hail-processes', 'wiki-virtual-memory', 'hail-processes']
- `c026` Why is the Banker's algorithm rarely used in real systems? — wanted `course-concurrency-bugs`, got ['wiki-banker-s-algorithm', 'wiki-banker-s-algorithm', 'wiki-banker-s-algorithm']
- `c035` What happens to child processes whose parent exits first? — wanted `course-process-api`, got ['wiki-fork-system-call', 'hail-processes', 'hail-processes']
- `c037` Why does the kernel use its own stack instead of the user's stack? — wanted `course-process-execution-mechanism`, got ['hail-threads', 'course-process-execution-mechanism', 'wiki-thread-computing']
- `c039` In the readers-writers solution, which reader locks out the writers? — wanted `course-reader-writer-problem`, got ['wiki-readers-writers-problem', 'wiki-readers-writers-problem', 'wiki-readers-writers-problem']
- `c042` Who translates virtual addresses to physical addresses using the page table? — wanted `course-virtual-memory`, got ['wiki-page-table', 'hail-vm', 'hail-vm']
- `c047` What happens to TLB entries on a context switch? — wanted `course-paging-1`, got ['wiki-translation-lookaside-buffer', 'wiki-context-switch', 'wiki-translation-lookaside-buffer']
- `c048` What information does a page table entry hold apart from the frame number? — wanted `course-paging-1`, got ['wiki-page-table', 'hail-vm', 'course-17-advanced-page-tables']
- `c052` What does a process control block contain? — wanted `course-process-abstraction`, got ['wiki-process-control-block', 'wiki-process-control-block', 'wiki-process-control-block']
- `c059` In the producer/consumer example, why is waking the wrong consumer a problem? — wanted `course-threads-cv`, got ['course-threads-cv', 'wiki-monitor-synchronization', 'wiki-monitor-synchronization']
- `c060` What is the expected final value when two threads each add to a shared counter ten million times? — wanted `course-threads-intro`, got ['course-threads-and-concurrency', 'course-threads-intro', 'course-threads-intro']
- `c066` Why should a semaphore used for ordering start at zero? — wanted `course-threads-sema`, got ['course-threads-sema', 'wiki-semaphore-programming', 'course-threads-sema']
- `c069` How do you fix an order-violation concurrency bug? — wanted `course-threads-bugs`, got ['course-concurrency-bugs', 'course-concurrency-bugs', 'course-threads-bugs']
- `c072` Which three file descriptors does every new process start with? — wanted `course-4-the-abstraction-the-process`, got ['course-3-unix-filestructure-related-system-calls', 'hail-persistence', 'hail-persistence']
- `c086` Before Belady showed otherwise, what did people believe about adding page frames? — wanted `wiki-belady-s-anomaly`, got ['hail-vm', 'hail-vm', 'hail-vm']
- `c100` What does the long-term scheduler decide for a newly created process? — wanted `wiki-process-state`, got ['wiki-scheduling-computing', 'wiki-scheduling-computing', 'wiki-scheduling-computing']
- `c101` How can race conditions happen in file systems, and how are they usually prevented? — wanted `wiki-race-condition`, got ['wiki-race-condition', 'wiki-race-condition', 'wiki-race-condition']
- `c113` What kinds of information does a PCB keep? — wanted `wiki-process-control-block`, got ['wiki-process-control-block', 'wiki-context-switch', 'wiki-process-control-block']
- `c116` What are the downsides of demand paging? — wanted `wiki-demand-paging`, got ['wiki-demand-paging', 'wiki-memory-paging', 'hail-vm']
- `c117` Why does a linear page table stored in virtual memory need a second translation? — wanted `hail-vm`, got ['hail-vm', 'hail-vm', 'hail-vm']
- `c123` Why do larger pages make the page table smaller but waste memory? — wanted `wiki-memory-management-unit`, got ['course-17-advanced-page-tables', 'wiki-page-table', 'wiki-memory-management-unit']
