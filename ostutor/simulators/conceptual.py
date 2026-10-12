"""Conceptual OS explanations grounded in documented student misconceptions.

The computing-education literature (Koli Calling 2013 / 2019, SIGCSE, ITiCSE)
records persistent alternative conceptions around interrupts, I/O, context
switches and system calls, concurrency, deadlock, semaphores and virtual memory.
Explanations that merely restate a definition do not move those beliefs; what
moves them is naming the misconception, showing why it is seductive, and then
giving a concrete counter-example.

So every entry here is a (concept, misconception, correction, example) quadruple
rather than a definition, and the generator renders it through varied framings so
the surface form is not a template.

Facts here are deliberately conservative: standard, uncontroversial OS material
that does not depend on a particular kernel version.
"""
import random

from .conceptual_kb2 import KB2
from .conceptual_kb3 import KB3
from .conceptual_kb4 import KB4
from .conceptual_kb5 import KB5

# (topic, question_core, misconception, why_seductive, correction, example)
KB = [
 ("process_vs_thread",
  "the difference between a process and a thread",
  "threads are just lightweight processes with their own memory",
  "both are schedulable units, so it is natural to assume both are isolated",
  "Threads of one process SHARE the address space - code, globals and heap. Only "
  "the stack, registers and program counter are per-thread. Processes do not share "
  "an address space at all; that is the whole point of the abstraction.",
  "Two threads incrementing the same global counter can interleave and lose an "
  "update. Two processes each have their own copy of that global, so neither can "
  "see the other's increments."),

 ("context_switch",
  "what actually happens during a context switch",
  "a context switch just swaps the program counter",
  "the PC is the most visible piece of CPU state",
  "The kernel must save and restore the whole execution context: all general "
  "registers, the PC, the stack pointer, and the memory-management state. On a "
  "process switch it also swaps the page-table base register, which typically "
  "flushes or invalidates TLB entries. That TLB cost is usually larger than the "
  "register save/restore.",
  "Switching between two THREADS of one process keeps the same page table, so no "
  "TLB flush is needed - which is precisely why thread switches are cheaper than "
  "process switches."),

 ("system_call",
  "how a system call differs from an ordinary function call",
  "a system call is just a library function in the kernel",
  "the C API makes `read()` look exactly like any other function",
  "A system call causes a controlled transition from user mode to kernel mode via "
  "a trap instruction. The CPU changes privilege level, switches to a kernel "
  "stack, and dispatches through a syscall table. An ordinary call is a jump "
  "within the same privilege level and the same stack.",
  "`printf()` is a library function; it eventually invokes the `write()` system "
  "call. You can trace the boundary with `strace`: the library call appears once, "
  "the syscall appears separately."),

 ("interrupt_vs_trap",
  "the difference between an interrupt and a trap",
  "interrupts and traps are the same mechanism with different names",
  "both vector through a table and both enter the kernel",
  "An interrupt is ASYNCHRONOUS and caused by an external device; it can arrive "
  "between any two instructions. A trap (or exception) is SYNCHRONOUS and caused "
  "by the currently executing instruction - a system call, a page fault, a divide "
  "by zero. Re-running the instruction reproduces a trap; it does not reproduce an "
  "interrupt.",
  "A disk completion interrupt may arrive at any moment. A page fault happens at "
  "exactly the instruction that touched the missing page, every time."),

 ("preemption",
  "what makes a scheduler preemptive",
  "a preemptive scheduler runs whichever process has the shortest job",
  "SJF is the example most often shown alongside preemption",
  "Preemption is about whether the scheduler may TAKE the CPU from a running "
  "process before it blocks or exits - nothing to do with which policy picks the "
  "next process. FCFS and SJF are non-preemptive; SRTF and Round Robin are "
  "preemptive. The policy and the preemption decision are independent axes.",
  "Round Robin uses arrival order - the same order as FCFS - yet it is preemptive "
  "because the timer interrupt forcibly ends each quantum."),

 ("starvation_vs_deadlock",
  "the difference between starvation and deadlock",
  "starvation and deadlock are two words for the same stuck state",
  "in both, a process fails to make progress",
  "In DEADLOCK a set of processes each hold a resource and wait for another held "
  "within the set; no process in the set can ever proceed without intervention. In "
  "STARVATION the resource does become available, but the scheduling policy keeps "
  "choosing someone else, so one process waits indefinitely while others progress.",
  "Under strict priority scheduling a low-priority process can starve forever while "
  "the system runs fine. That is not deadlock - the CPU is never idle, and aging "
  "the priority fixes it."),

 ("deadlock_conditions",
  "why all four Coffman conditions are needed for deadlock",
  "any one of the four conditions is enough to cause deadlock",
  "each condition individually sounds dangerous",
  "Mutual exclusion, hold-and-wait, no preemption and circular wait must hold "
  "SIMULTANEOUSLY. They are necessary conditions, and breaking any single one is "
  "enough to make deadlock impossible - which is exactly how prevention schemes "
  "work.",
  "Requiring a process to acquire all its resources at once breaks hold-and-wait, "
  "so deadlock cannot occur even though the other three conditions still hold."),

 ("banker_purpose",
  "what Banker's algorithm actually guarantees",
  "Banker's algorithm detects deadlocks after they happen",
  "it is taught in the deadlock chapter alongside detection",
  "Banker's algorithm is AVOIDANCE, not detection. It never allows the system to "
  "enter an unsafe state, so deadlock cannot occur in the first place. It requires "
  "each process to declare its maximum resource need in advance - a strong "
  "assumption that limits its practical use.",
  "An UNSAFE state is not the same as a deadlocked state: unsafe means deadlock "
  "has become possible, not that it has occurred. Banker's refuses requests that "
  "would move the system into unsafe territory."),

 ("race_condition",
  "what causes a race condition",
  "race conditions only happen on multi-core machines",
  "true parallelism makes the failure obvious",
  "A race needs only INTERLEAVING, not parallelism. On a single core a timer "
  "interrupt can preempt a thread in the middle of a read-modify-write sequence, "
  "and the same lost-update bug appears.",
  "`counter++` compiles to load, add, store. A preemption between load and store "
  "on a single CPU loses an increment exactly as a second core would."),

 ("mutex_vs_semaphore",
  "when to use a mutex rather than a semaphore",
  "a mutex is just a semaphore initialised to 1",
  "a binary semaphore behaves similarly in simple cases",
  "A mutex has an OWNER: only the thread that locked it may unlock it, which "
  "enables priority inheritance and error checking. A semaphore has no owner - any "
  "thread may signal it - which is what makes it suitable for signalling and for "
  "counting a pool of identical resources.",
  "In producer-consumer, the consumer waits on a semaphore the PRODUCER signals. "
  "A mutex cannot express that, because the waiter and the signaller differ."),

 ("busy_waiting",
  "why busy waiting is usually undesirable",
  "busy waiting is always wrong and must never be used",
  "spinning obviously wastes cycles",
  "Busy waiting wastes CPU only while the wait is LONG relative to the cost of "
  "blocking. Blocking costs two context switches, so for very short critical "
  "sections a spinlock is genuinely faster - which is why kernels use spinlocks "
  "internally. The rule is about expected wait duration, not a moral absolute.",
  "A spinlock protecting a three-instruction update outperforms a mutex. A "
  "spinlock held across a disk read is a disaster."),

 ("virtual_memory_size",
  "whether virtual memory lets a program use more memory than exists",
  "virtual memory makes the machine physically larger",
  "the phrase 'virtual memory' suggests extra memory",
  "Virtual memory decouples the address space from physical frames. A process may "
  "have a larger address space than installed RAM because inactive pages live on "
  "disk, but total ACTIVE memory is still bounded by RAM. Exceeding it causes "
  "thrashing, not more capacity.",
  "A 4 GB process on a 2 GB machine runs while its working set fits in RAM. When "
  "the working set exceeds RAM, page-fault rate explodes and throughput collapses."),

 ("thrashing",
  "what causes thrashing",
  "thrashing happens because the disk is too slow",
  "the symptom is overwhelming disk activity",
  "Thrashing is caused by the sum of active working sets exceeding physical "
  "memory. Every process continually faults out pages another process immediately "
  "needs. A faster disk reduces the symptom but not the cause; reducing the degree "
  "of multiprogramming does.",
  "Adding processes when memory is already tight LOWERS total throughput - the "
  "classic thrashing curve, where utilisation falls as load rises."),

 ("page_fault_cost",
  "why page faults are so expensive",
  "a page fault is expensive because the page table lookup is slow",
  "the page table is the visible data structure",
  "A page-table walk costs nanoseconds and is usually cached in the TLB. What makes "
  "a fault expensive is the DISK I/O - milliseconds - plus the context switch while "
  "the process blocks. The gap is roughly five orders of magnitude.",
  "A TLB hit costs ~1 ns; a page fault served from disk costs ~5 ms. One fault can "
  "cost as much as millions of ordinary accesses."),

 ("belady_anomaly",
  "why Belady's anomaly is surprising",
  "adding more frames always reduces page faults",
  "more memory intuitively means fewer misses",
  "FIFO is not a STACK algorithm: the set of pages held with n frames is not "
  "guaranteed to be a subset of the set held with n+1 frames. Therefore adding a "
  "frame can change eviction order badly enough to increase faults. LRU and OPT "
  "are stack algorithms and cannot exhibit the anomaly.",
  "Reference string 1 2 3 4 1 2 5 1 2 3 4 5 under FIFO gives 9 faults with 3 "
  "frames but 10 with 4."),

 ("lru_implementation",
  "why true LRU is rarely implemented exactly",
  "operating systems implement exact LRU",
  "LRU is the policy textbooks analyse most",
  "Exact LRU requires updating a timestamp or list position on EVERY memory "
  "reference, which is impossible to do in software at memory speed and expensive "
  "in hardware. Real systems approximate it - the clock / second-chance algorithm "
  "using a reference bit is the standard approximation.",
  "The clock algorithm sweeps a circular list, clearing reference bits, and evicts "
  "the first page whose bit is already 0 - close to LRU at a fraction of the cost."),

 ("internal_vs_external_frag",
  "the difference between internal and external fragmentation",
  "paging eliminates fragmentation entirely",
  "paging is introduced as the fix for external fragmentation",
  "Paging eliminates EXTERNAL fragmentation, because any free frame can hold any "
  "page. It introduces INTERNAL fragmentation instead: the last page of an "
  "allocation is usually partly unused, averaging half a page per region.",
  "A 5 KB request with 4 KB pages occupies two frames - 8 KB - wasting 3 KB inside "
  "the second frame. No free memory is stranded between allocations, though."),

 ("fork_semantics",
  "what fork() returns and to whom",
  "fork() returns the child's PID to both processes",
  "there is one call, so one return value seems natural",
  "fork() returns TWICE - once in each process. The parent receives the child's "
  "PID (a positive number); the child receives 0. On failure the parent receives "
  "-1 and no child is created. That asymmetry is how each process discovers which "
  "one it is.",
  "`if (fork() == 0) { /* child */ } else { /* parent */ }` is the standard idiom, "
  "and it works precisely because the two returns differ."),

 ("zombie_orphan",
  "the difference between a zombie and an orphan process",
  "a zombie process is still consuming CPU",
  "the name suggests something still moving",
  "A ZOMBIE has already terminated; it holds no memory and consumes no CPU. Only "
  "its exit status remains in the process table until the parent calls wait(). An "
  "ORPHAN is still running but its parent died, so it is re-parented to init/systemd.",
  "A parent that loops forever without calling wait() accumulates zombies and can "
  "exhaust the process table - despite those zombies using no CPU at all."),

 ("io_bound_cpu_bound",
  "why mixing I/O-bound and CPU-bound processes matters",
  "the scheduler should always favour the shortest job",
  "SJF minimises average waiting time, so it seems universally best",
  "Favouring I/O-bound processes keeps DEVICES busy. An I/O-bound process uses the "
  "CPU briefly then blocks, so giving it priority costs little CPU time and keeps "
  "disks and networks working in parallel. Optimising CPU waiting time alone can "
  "leave expensive devices idle.",
  "MLFQ raises the priority of processes that block early - a heuristic for 'this "
  "one is I/O-bound' - which is why interactive programs stay responsive."),

 ("inode_purpose",
  "what an inode stores and what it does not",
  "the inode stores the file's name",
  "the inode is described as holding the file's metadata",
  "An inode holds metadata - permissions, owner, timestamps, size and the block "
  "pointers - but NOT the name. Names live in directory entries, which map a name "
  "to an inode number. That separation is exactly what makes hard links possible.",
  "Two hard links to one file are two directory entries pointing at the same inode "
  "number. Deleting one name only decrements the link count."),

 ("raid_redundancy",
  "whether RAID replaces backups",
  "RAID means the data is backed up",
  "RAID does protect against a failure mode",
  "RAID protects against DISK failure and improves availability. It does not "
  "protect against accidental deletion, corruption, ransomware or fire, because "
  "every one of those is faithfully mirrored to all disks immediately.",
  "`rm -rf` on a RAID-1 volume deletes the data from both disks simultaneously. A "
  "backup from yesterday recovers it; the mirror does not."),
]

# KB3/KB4 are 7-tuples (they add a Socratic probe); the explanation generator
# uses only the first six fields.
KB = KB + KB2 + [tuple(e[:6]) for e in KB3 + KB4 + KB5]

FRAMINGS = [
 "A student asks: what is {q}?",
 "Explain {q}.",
 "In an exam, a student writes that {m}. Is that right?",
 "Can you clarify {q}?",
 "My classmate insists that {m}. Help me understand.",
 "I'm confused about {q}. Could you explain it with an example?",
 "Why do people say {m}? Is that accurate?",
 "During revision I wrote down that {m}. Correct me if that's wrong.",
 "Our lecturer mentioned {q} but I didn't follow. Can you break it down?",
 "What's the precise answer to {q}?",
]


def generate(n, seed=42):
    """Emit n conceptual records. Surface form varies; content is fixed and
    conservative. Each record names the misconception it corrects, so the model
    learns diagnostic structure rather than definition recall."""
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        topic, q, mis, why, corr, ex = rng.choice(KB)
        framing = rng.choice(FRAMINGS).format(q=q, m=mis)
        opener = rng.choice([
            f"That's a common belief, and it's worth unpicking.",
            f"This one trips a lot of people up.",
            f"Short answer: not quite - here's why.",
            f"Good question; the usual intuition points the wrong way here.",
            f"It's worth being precise about this.",
        ])
        body = rng.choice([
            f"**The common misconception:** {mis}.\n\n"
            f"**Why it's tempting:** {why}.\n\n"
            f"**What is actually true:** {corr}\n\n"
            f"**Concrete example:** {ex}",
            f"Many students believe {mis} - {why}.\n\n"
            f"{corr}\n\n"
            f"To see it concretely: {ex}",
            f"{corr}\n\n"
            f"The usual error is to think {mis}, because {why}.\n\n"
            f"**Example.** {ex}",
        ])
        answer = f"{opener}\n\n{body}"
        out.append(dict(topic=f"concept_{topic}", question=framing, answer=answer,
                        misconception=mis, seed=rng.randrange(1 << 30),
                        template_id=f"concept_{topic}",
                        difficulty=round(rng.uniform(0.3, 0.8), 2)))
    return out
