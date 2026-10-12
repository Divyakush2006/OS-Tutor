"""The labelled question -> passage set for the course corpus (G2 evaluation).

    python tools/build_rag_questions.py      (writes data/rag/eval/corpus_questions.jsonl)

Each in-scope item names the document that answers it and an EVIDENCE phrase copied
verbatim from the answering passage. A retrieved chunk counts as relevant when it belongs
to that document and contains the phrase, so the labels survive re-chunking. Questions
were written from a seeded sample of 130 passages (78 course,
52 online; exercises, references and code-only passages left out) and phrased the way a
student would ask, avoiding the passage's own wording where possible. Out-of-scope items
are questions the corpus does not cover. Status: unreviewed until checked by hand.

Items alternate dev / test: the dev half calibrates the abstain gate, the test half
reports it. Recall is reported on all in-scope items (nothing in ranking is tuned on them).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "data" / "rag" / "eval" / "corpus_questions.jsonl"

# (document id, question, evidence phrase from the answering passage)
IN = [
    ("course-10-multiprocessor-scheduling-advanced", "Why should a multiprocessor scheduler try to keep a process on the CPU it ran on last time?", "builds up a fair bit of state in the cache"),
    ("course-2-os-functionalities", "Is a program the same thing as a process?", "Program is a passive entity, process is an active entity"),
    ("course-2-os-functionalities", "Which company's research lab first invented the desktop GUI?", "Invented at Xerox PARC"),
    ("course-3-unix-filestructure-related-system-calls", "Do programs usually call system calls directly, or through some API?", "Three most common APIs are"),
    ("course-3-unix-filestructure-related-system-calls", "What does dup() return and what does the copy share with the original descriptor?", "both file descriptors share one file pointer"),
    ("course-4-the-abstraction-the-process", "What basic operations should any OS offer for managing processes?", "Halt a runaway process"),
    ("course-4-the-abstraction-the-process", "When does a process move into the blocked state?", "When a process initiates an I/O request to a disk, it becomes blocked"),
    ("course-6-direct-execution", "In the cooperative approach, how does the OS ever get the CPU back from a program?", "Processes periodically give up the CPU by making system calls such as yield"),
    ("course-6-direct-execution", "Why can't the OS just run a program directly on the CPU with no limits?", "would be “just a library”"),
    ("course-7-scheduling", "Why does round robin do badly on turnaround time even though it is fair?", "RR is fair, but performs poorly on metrics such as turnaround time"),
    ("course-8-multi-level-feedback-scheduling", "In MLFQ, what happens to a job's priority if it uses its entire time slice?", "its priority is reduced"),
    ("course-8-multi-level-feedback-scheduling", "How can a clever program game a basic MLFQ scheduler?", "After running 99% of a time slice, issue an I/O operation"),
    ("course-9-scheduling-proportional-share", "In lottery scheduling, what do tickets stand for?", "Represent the share of a resource that a process should receive"),
    ("course-linux-commands", "How do I send the output of a command into a file instead of the screen?", "the character > redirects stdout to a file"),
    ("course-linux-commands", "What does the ? wildcard match in the shell?", "Any single character (not a blank)"),
    ("course-shell-programming", "Can a shell variable name start with a digit?", "The name of a variable can contain only letters"),
    ("course-shell-programming", "Which special shell variable holds the number of arguments passed to a script?", "The number of arguments supplied to a script"),
    ("course-1-introduction-to-os", "Why is an operating system compared to a government?", "An operating system is similar to a government"),
    ("course-1-introduction-to-os", "What is the difference between hard and soft real-time systems?", "guarantee that critical tasks complete on time"),
    ("course-13-segmentation", "How can segments be shared safely between address spaces?", "A few more bits per segment to indicate permissions"),
    ("course-13-segmentation", "Why is compaction expensive when fixing external fragmentation with segments?", "Compaction is costly"),
    ("course-15-paging", "What does the dirty bit in a page table entry record?", "Indicating whether the page has been modified since it was brought into memory"),
    ("course-17-advanced-page-tables", "Why can't we simply use bigger pages to shrink the page table?", "Big pages lead to internal fragmentation"),
    ("course-17-advanced-page-tables", "In the hybrid segmentation-plus-paging scheme, how does hardware find the page table entry on a TLB miss?", "uses the segment bits(SN) to determine which base and bounds pair to use"),
    ("course-concurrency-bugs", "What four conditions must all hold for a deadlock?", "ALL four of the above conditions must hold for a deadlock to occur"),
    ("course-concurrency-bugs", "Why is the Banker's algorithm rarely used in real systems?", "impractical in real life to assume this knowledge"),
    ("course-condition-variable", "Why must you hold the lock when calling wait and signal on a condition variable?", "Race condition: missed wakeup"),
    ("course-condition-variable", "What is the difference between signal and broadcast on a condition variable?", "signal broadcast wakes up all waiting threads"),
    ("course-deadlock-problem", "Is there a practice problem with four processes and four resource types that asks for a resource allocation graph?", "Draw the resource allocation graph for the above scenario"),
    ("course-introduction-to-os", "What does a compiler produce from a C program, and what is inside it?", "The exe contains instructions that the CPU can understand"),
    ("course-memory-allocation-algorithm", "What is a slab allocator used for in the kernel?", "kernel uses a slab allocator"),
    ("course-memory-allocation-algorithm", "How does the C library get memory from the kernel to hand out with malloc?", "Allocates one or more pages from kernel via brk/sbrk or mmap system calls"),
    ("course-paging-problem", "With 4-byte pages, how is logical address 6 split into page number and offset?", "Logical address 6 = (Page 1,Offset 2)"),
    ("course-process-api", "What is a zombie process and who cleans it up?", "Terminated process exists as a zombie"),
    ("course-process-api", "What happens to child processes whose parent exits first?", "init process adopts orphans and reaps them"),
    ("course-process-api", "Why does POSIX make programs portable across operating systems?", "Programs written to the POSIX API can run on any POSIX compliant OS"),
    ("course-process-execution-mechanism", "Why does the kernel use its own stack instead of the user's stack?", "Kernel does not trust user stack"),
    ("course-process-execution-mechanism", "What exactly does the return-from-trap instruction restore?", "Change CPU privilege from kernel mode to user mode"),
    ("course-reader-writer-problem", "In the readers-writers solution, which reader locks out the writers?", "if (readers==1) WAIT (wrmutex)"),
    ("course-threads-and-concurrency", "Concurrency versus parallelism - what is the difference?", "running multiple threads/processes in parallel over different CPU cores"),
    ("course-threads-and-concurrency", "What do we need to prevent a race condition in a critical section?", "Only one thread should be executing critical section at any time"),
    ("course-virtual-memory", "Who translates virtual addresses to physical addresses using the page table?", "MMU has access to page tables, and uses it to translate VA to PA"),
    ("course-demand-paging", "How can the OS approximate LRU if it does not see every memory access?", "MMU sets a bit in PTE"),
    ("course-demand-paging", "Walk me through what happens on a memory access when the TLB misses.", "If TLB miss, MMU accesses memory, walks page table"),
    ("course-locks", "Why must the kernel disable interrupts while holding a spinlock?", "An interrupt handler could request the same lock, and spin for it forever"),
    ("course-locks", "What goals should a good lock implementation meet?", "Low overhead: acquiring, releasing, and waiting for lock"),
    ("course-paging-1", "What happens to TLB entries on a context switch?", "TLB entries may become invalid on context switch"),
    ("course-paging-1", "What information does a page table entry hold apart from the frame number?", "Present bit: is this page in memory?"),
    ("course-process-api-2", "How can I count how many times a word appears in a file using a pipe?", "grep -o foo file | wc -l"),
    ("course-process-api-2", "Which command-line tool shows which processes are using the most CPU?", "The tool top is also quite helpful"),
    ("course-process-abstraction", "What is the first thing the OS does to turn a program into a running process?", "The first thing that the OS must do to run a program is to load its code"),
    ("course-process-abstraction", "What does a process control block contain?", "a structure that contains information about a specific process"),
    ("course-process-execution-mechanism-2", "Why can't any user process be allowed to issue disk I/O directly?", "a process could simply read or write the entire disk"),
    ("course-process-execution-mechanism-2", "Why is installing the trap table a privileged instruction?", "it is also a privileged operation"),
    ("course-threads-api", "Why does pthread_cond_wait take the mutex as an argument but signal does not?", "the wait call takes a lock as its second parameter"),
    ("course-threads-api", "Does every multithreaded program need to call pthread_join?", "not all code that is multi-threaded uses the join routine"),
    ("course-threads-cv", "Walk through the parent/child join example with condition variables.", "the parent creates the child thread but continues running itself"),
    ("course-threads-cv", "What goes wrong if thr_join waits on the condition variable without a lock?", "it sleeps forever, which is sad"),
    ("course-threads-cv", "In the producer/consumer example, why is waking the wrong consumer a problem?", "will wake up and find the buffer empty"),
    ("course-threads-intro", "What is the expected final value when two threads each add to a shared counter ten million times?", "the desired final result is: 20,000,000"),
    ("course-threads-intro", "Why do interrupts make kernel data structures like inodes and bitmaps critical sections?", "An untimely interrupt causes all of the problems described above"),
    ("course-threads-locks", "How can a lock avoid wasting CPU by spinning?", "Using Queues: Sleeping Instead Of Spinning"),
    ("course-threads-locks", "What does it mean for a thread to own a lock?", "this thread is sometimes said to be the owner of the lock"),
    ("course-threads-locks", "Why does a simple flag variable fail to give mutual exclusion?", "both threads set the flag to 1"),
    ("course-threads-sema", "How can a semaphore stop too many threads entering a memory-hungry region at once?", "a semaphore can naturally throttle the number of threads"),
    ("course-threads-sema", "Why should a semaphore used for ordering start at zero?", "hence, 0 is the initial value"),
    ("course-threads-sema", "Is there a rule of thumb for choosing a semaphore's initial value?", "the number of resources you are willing to give away immediately after initialization"),
    ("course-threads-sema", "Who invented the semaphore?", "the introduction of a synchronization primitive called the semaphore"),
    ("course-threads-bugs", "How do you fix an order-violation concurrency bug?", "The fix to this type of bug is generally to enforce ordering"),
    ("course-shell-programming", "What does $? hold in a shell script?", "The exit status of the last command executed"),
    ("course-1-introduction-to-os", "How does the user view of an OS differ between a single-user PC and a mainframe?", "designed to maximize resource utilization"),
    ("course-4-the-abstraction-the-process", "Which three file descriptors does every new process start with?", "Standard input, output and error"),
    ("course-linux-commands", "Are there tools to copy files to an MS-DOS floppy from Linux?", "The Mtools package allows the transferring of files"),
    ("course-process-abstraction", "Besides memory, what else is part of a process's machine state?", "machine state are registers"),
    ("course-threads-locks", "Why is spin-waiting a performance problem?", "Spin-waiting wastes time waiting for another thread to release"),
    ("wiki-multilevel-feedback-queue", "Who first developed the multilevel feedback queue?", "first developed by Fernando J. Corbató"),
    ("wiki-file-system", "Do tapes need to be formatted before writing new data?", "it is not necessary to format the tape before over-writing new data"),
    ("wiki-system-call", "What role does libc play between programs and system calls?", "provides wrapper functions for the system calls"),
    ("wiki-context-switch", "Why is switching between threads of the same process cheaper than between processes?", "so a TLB flush is not necessary"),
    ("wiki-kernel-operating-system", "How does virtual addressing protect the kernel from applications?", "The applications are not permitted by the processor to address kernel memory"),
    ("wiki-scheduling-computing", "What data structure does Linux CFS use for its run queue?", "the run queue is implemented as a red–black tree"),
    ("wiki-spinlock", "What is an adaptive mutex?", "a hybrid approach called \"adaptive mutex\""),
    ("wiki-lock-computer-science", "Fine-grained versus coarse-grained locking - which performs better for many users?", "fine granularity, such as record locks, tends to give the best performance for multiple users"),
    ("wiki-hard-link", "Which commands can create a hard link or show how many hard links a file has?", "The ln utility"),
    ("hail-threads", "Why can running a CPU-heavy job and a disk-heavy job concurrently finish sooner than running them one after the other?", "spends most of its time using the disk drive to read files"),
    ("wiki-belady-s-anomaly", "Before Belady showed otherwise, what did people believe about adding page frames?", "an increase in the number of page frames would always result in the same number of, or fewer, page faults"),
    ("wiki-i-o-scheduling", "What goals can an I/O scheduler have besides reducing seek time?", "To give a share of the disk bandwidth to each running process"),
    ("wiki-elevator-algorithm", "Why is the SCAN disk algorithm called the elevator algorithm?", "named after the behavior of a building elevator"),
    ("wiki-critical-section", "Do critical sections matter for code that drives I/O devices?", "Critical sections also occur in code which manipulates external peripherals"),
    ("wiki-fork-system-call", "After fork, how can the parent and child exchange data?", "pipes can be used"),
    ("wiki-inode", "Where does the word inode come from?", "a contraction of the term index node"),
    ("wiki-deadlock-computer-science", "Why is removing the no-preemption condition hard in practice?", "The no preemption condition may also be difficult or impossible to avoid"),
    ("hail-intro", "What is middleware and how is it similar to an operating system?", "Middleware is software occupying a middle position"),
    ("wiki-fragmentation-computing", "Why does paging cause internal fragmentation?", "Memory paging creates internal fragmentation because an entire page frame"),
    ("hail-security", "When is a system considered secure?", "A system is secure if it is designed, implemented, and operated"),
    ("hail-synchronization", "Why are these mutex implementations called spinlocks?", "They both engage in busy waiting if the mutex is not immediately available"),
    ("wiki-shortest-seek-first", "Can shortest seek first starve requests?", "starvation may result, with the faraway requests never being able to make progress"),
    ("wiki-thrashing-computer-science", "What is the working set of a program?", "The pages most frequently accessed at any point are called the working set"),
    ("wiki-operating-system", "Which was the first popular operating system to support multiprogramming?", "The OS/360 also was the first popular operating system to support multiprogramming"),
    ("wiki-process-state", "What does the long-term scheduler decide for a newly created process?", "Admission will be approved or delayed by a long-term, or admission, scheduler"),
    ("wiki-race-condition", "How can race conditions happen in file systems, and how are they usually prevented?", "File locking provides a commonly used solution"),
    ("wiki-process-computing", "Why does preemption benefit interactive processes?", "users are immediately assigned computing resources at the simple pressing of a key"),
    ("wiki-semaphore-programming", "What is the passing the baton pattern with semaphores?", "proposed by Gregory R. Andrews"),
    ("wiki-page-fault", "What is the difference between a major and a minor page fault?", "then the fault is major, or hard"),
    ("wiki-banker-s-algorithm", "How does the Banker's algorithm decide whether a state is safe?", "trying to find a hypothetical set of requests by the processes"),
    ("wiki-shortest-remaining-time", "Which algorithm avoids the starvation problem of shortest remaining time?", "highest response ratio next (HRRN)"),
    ("wiki-producer-consumer-problem", "Who first described the producer-consumer problem?", "described by Edsger W. Dijkstra since 1965"),
    ("wiki-resource-starvation", "Is starvation the same thing as deadlock?", "Starvation-freedom is a stronger guarantee than the absence of deadlock"),
    ("wiki-fixed-priority-pre-emptive-scheduling", "What is cooperative scheduling?", "a task can run continuously from start to end without being preempted"),
    ("wiki-virtual-memory", "What are the simplest ways to stop thrashing?", "Adding real memory is the simplest response"),
    ("wiki-monitor-synchronization", "Why is a busy-waiting producer/consumer queue with no synchronization broken?", "accesses to the queue can be interrupted and interleaved"),
    ("wiki-lottery-scheduling", "How does lottery scheduling avoid starvation?", "Giving each process at least one lottery ticket guarantees"),
    ("wiki-process-control-block", "What kinds of information does a PCB keep?", "Process identification Process state Process control"),
    ("wiki-memory-management", "What is the essential requirement of memory management?", "to dynamically allocate portions of memory to programs at their request"),
    ("wiki-readers-writers-problem", "Why is the first readers-writers solution unfair to writers?", "a stream of readers can subsequently lock all potential writers out"),
    ("wiki-demand-paging", "What are the downsides of demand paging?", "Individual programs face extra latency when they access a page for the first time"),
    ("hail-vm", "Why does a linear page table stored in virtual memory need a second translation?", "the virtual address of the page table entry"),
    ("wiki-page-table", "Who sets up the page table?", "The page table is set up by the computer's operating system"),
    ("wiki-dining-philosophers-problem", "Is the resource hierarchy solution to the dining philosophers fair?", "The resource hierarchy solution is not fair"),
    ("wiki-translation-lookaside-buffer", "What does the hardware do when the page number is not in the TLB?", "If the page number is not in the TLB, the page table must be checked"),
    ("hail-persistence", "Why are hard links awkward on file systems that keep metadata in the directory entry?", "store the metadata for a file directly in that file"),
    ("wiki-peterson-s-algorithm", "Does the filter algorithm for N processes guarantee bounded waiting?", "the filter algorithm does not guarantee bounded waiting"),
    ("wiki-memory-management-unit", "Why do larger pages make the page table smaller but waste memory?", "increased internal fragmentation"),
    ("wiki-inter-process-communication", "Why is IPC so important for microkernels?", "IPC is very important to the design process for microkernels"),
]

OUT_OF_SCOPE = [
    "How does TCP's three-way handshake establish a connection?",
    "What is the difference between a B-tree and a B+ tree index in a database?",
    "Explain gradient descent and backpropagation in neural networks.",
    "What is the time complexity of merge sort?",
    "How do I configure a VLAN on a Cisco switch?",
    "What is the capital of Australia?",
    "How does RSA key generation work?",
    "What is a closure in JavaScript?",
    "How does the JVM's garbage collector decide what to free?",
    "Explain the CAP theorem for distributed databases.",
    "What is the difference between SQL INNER JOIN and LEFT JOIN?",
    "How does a convolutional neural network detect edges?",
    "What is the Big-O of binary search?",
    "How do I center a div in CSS?",
    "What causes inflation in an economy?",
    "Explain Newton's second law of motion.",
    "How does photosynthesis work?",
    "What is the difference between HTTP/1.1 and HTTP/2?",
    "How does Dijkstra's shortest path algorithm work on a weighted graph?",
    "What is a React hook?",
    "How do I train a random forest classifier in scikit-learn?",
    "What is the difference between a compiler's lexer and parser?",
    "How does BGP choose a route between autonomous systems?",
    "What is normalization in relational database design?",
    "How does Git rebase differ from merge?",
    "What is the Pythagorean theorem?",
    "How does a transformer's attention mechanism work?",
    "What is the difference between IPv4 and IPv6 addressing?",
    "How do you compute a determinant of a 3x3 matrix?",
    "What is the OSI model's presentation layer for?",
    "How does public cloud auto-scaling work in AWS?",
    "What is a monad in functional programming?",
    "How do you write a regular expression for an email address?",
    "What is the difference between supervised and unsupervised learning?",
    "Explain how blockchain consensus with proof of work works.",
    "What is Kubernetes used for?",
    "How do I solve a quadratic equation?",
    "What is the difference between a virus and a bacterium?",
    "How does DNS resolve a domain name?",
    "What is polymorphism in object-oriented programming?",
]


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for n, (doc, q, ev) in enumerate(IN):
        rows.append(dict(id=f"c{n + 1:03d}", query=q, doc=doc, evidence=ev,
                         split="dev" if n % 2 == 0 else "test", status="unreviewed"))
    for n, q in enumerate(OUT_OF_SCOPE):
        rows.append(dict(id=f"x{n + 1:03d}", query=q, doc=None, evidence=None,
                         split="dev" if n % 2 == 0 else "test", status="unreviewed"))
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(IN)} in-scope, {len(OUT_OF_SCOPE)} out-of-scope -> {OUT}")


if __name__ == "__main__":
    main()
