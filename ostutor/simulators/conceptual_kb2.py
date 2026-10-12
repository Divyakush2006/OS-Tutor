"""Second knowledge-base block for conceptual generation.

Split from conceptual.py purely for file size. Same quadruple structure:
(topic, question_core, misconception, why_seductive, correction, example).

These cover scheduling behaviour, memory mechanics, synchronisation and storage -
the parts of the syllabus the first block did not reach. Content is deliberately
conservative and kernel-version independent.
"""

KB2 = [
 ("mlfq_purpose",
  "what problem MLFQ solves that plain priority scheduling does not",
  "MLFQ is just priority scheduling with more queues",
  "it does use multiple priority levels",
  "MLFQ LEARNS a process's behaviour instead of being told it. A job that uses its "
  "whole quantum is demoted (it looks CPU-bound); a job that blocks early stays high "
  "(it looks interactive). Static priority never adapts and starves low-priority "
  "work, so MLFQ periodically boosts everything to prevent exactly that.",
  "A text editor and a compiler start at the same priority. Within a few quanta the "
  "compiler sinks and the editor stays responsive, without anyone declaring which "
  "is which."),

 ("convoy_effect",
  "the convoy effect in FCFS scheduling",
  "FCFS is fair because it serves jobs in arrival order",
  "arrival order feels like the definition of fairness",
  "FCFS lets one long CPU-bound job block every short job behind it - the convoy "
  "effect. Average waiting time becomes dominated by an unlucky ordering, and I/O "
  "devices sit idle while short jobs wait behind the hog.",
  "Bursts 100, 1, 1 arriving in that order give average waiting (0+100+101)/3 = 67. "
  "Reversed, it is (0+1+2)/3 = 1. Same jobs, same policy."),

 ("response_vs_turnaround",
  "the difference between response time and turnaround time",
  "response time and turnaround time measure the same delay",
  "both sound like how long the user waits",
  "RESPONSE time is arrival until the process first RUNS. TURNAROUND is arrival "
  "until it COMPLETES. Interactive systems optimise response, batch systems "
  "optimise turnaround, and the two goals frequently conflict.",
  "Round Robin gives excellent response time because everyone starts quickly, while "
  "worsening turnaround, since every job finishes later than it would under SJF."),

 ("quantum_size",
  "how the time quantum should be chosen in Round Robin",
  "a smaller quantum is always more responsive and therefore better",
  "shorter slices do reduce the wait before first execution",
  "As the quantum shrinks toward the context-switch cost, overhead dominates and "
  "throughput collapses. As it grows past the longest burst, RR degenerates into "
  "FCFS. Usual guidance is a quantum large enough that most bursts finish within "
  "it while staying far above switch cost.",
  "With a 10 microsecond switch cost, a 100 microsecond quantum wastes about 10% of "
  "the CPU on switching; a 1 millisecond quantum wastes about 1%."),

 ("tlb_purpose",
  "what the TLB caches",
  "the TLB caches recently used data",
  "it is a cache, and caches usually hold data",
  "The TLB caches page-table ENTRIES - virtual-to-physical page mappings - not data. "
  "Data lives in the ordinary CPU caches. A TLB hit avoids walking the page table; "
  "it says nothing about whether the data itself is cached.",
  "You can have a TLB hit and still miss in L1, L2 and L3 and go to RAM, or a TLB "
  "miss on data already sitting in L1."),

 ("demand_paging",
  "what demand paging means",
  "the OS loads the whole program into memory before running it",
  "that is how simple loaders behave",
  "Demand paging brings in a page only when it is first referenced. A process starts "
  "with almost nothing resident and faults pages in as it touches them, so startup "
  "is fast and code paths never executed are never loaded at all.",
  "A large application starts quickly because its rarely-used features are never "
  "paged in."),

 ("copy_on_write",
  "how copy-on-write makes fork() cheap",
  "fork() copies the parent's entire address space immediately",
  "fork() is described as creating a duplicate process",
  "Modern kernels mark the parent's pages read-only and SHARE them with the child. A "
  "private copy is made only when one side writes. Since most children call exec() "
  "straight away, almost no copying ever happens.",
  "fork() followed by exec() copies essentially nothing, because the new image "
  "replaces the address space before any write triggers a copy."),

 ("working_set",
  "what a working set is",
  "the working set is all the memory a process has ever allocated",
  "it sounds like a total footprint",
  "The working set is the set of pages referenced within a recent time WINDOW. It "
  "measures current locality, not lifetime allocation, and it changes as the program "
  "moves between phases.",
  "A program that allocates 1 GB but loops over 4 MB has a 4 MB working set and runs "
  "comfortably with far less than 1 GB free."),

 ("swapping_vs_paging",
  "the difference between swapping and paging",
  "swapping and paging are the same thing",
  "both move data between memory and disk",
  "SWAPPING moves an ENTIRE process out of memory; PAGING moves individual pages. "
  "Modern systems page, and use the swap AREA as backing store for evicted pages, "
  "which is why the terms get conflated.",
  "Under memory pressure Linux evicts selected anonymous pages to swap; it does not "
  "suspend and remove whole processes as classical swapping did."),

 ("dirty_bit",
  "why the dirty bit matters for page replacement",
  "every evicted page must be written back to disk",
  "eviction sounds like it should always persist the page",
  "Only MODIFIED pages need writing back. The dirty bit records whether a page has "
  "been written since it was loaded; a clean page can simply be discarded because an "
  "identical copy already exists on disk.",
  "Evicting read-only code pages costs nothing - they are reloaded from the "
  "executable if needed again."),

 ("page_size_tradeoff",
  "the trade-off in choosing a page size",
  "larger pages are always better because there are fewer of them",
  "fewer pages does mean a smaller page table and better TLB reach",
  "Larger pages shrink the page table and improve TLB coverage but increase INTERNAL "
  "fragmentation and make each fault transfer more data. Smaller pages reduce waste "
  "but enlarge the table and raise TLB pressure. Systems compromise around 4 KB and "
  "offer huge pages for specific workloads.",
  "A database with a large contiguous buffer benefits from 2 MB huge pages; a system "
  "running many tiny processes does not."),

 ("critical_section_requirements",
  "the three requirements for a correct critical-section solution",
  "mutual exclusion alone makes a solution correct",
  "mutual exclusion is the property everyone remembers",
  "A correct solution needs MUTUAL EXCLUSION, PROGRESS (if nobody is inside, "
  "choosing who enters cannot be postponed indefinitely) and BOUNDED WAITING (a "
  "limit on how many others may enter first). A lock guaranteeing only exclusion can "
  "still deadlock or starve.",
  "Strict alternation guarantees mutual exclusion but violates progress: if one "
  "process never wants to enter, the other can never enter either."),

 ("producer_consumer_semaphores",
  "why producer-consumer needs more than one semaphore",
  "one mutex is enough to make producer-consumer correct",
  "the shared buffer obviously needs protection",
  "Three synchronisation objects are needed: a mutex for buffer integrity, an "
  "'empty' counting semaphore so producers block when full, and a 'full' counting "
  "semaphore so consumers block when empty. A mutex alone prevents corruption but "
  "cannot express 'wait until there is something to take'.",
  "With only a mutex, a consumer finding an empty buffer must spin or fail; the "
  "counting semaphores let it sleep until a producer wakes it."),

 ("dining_philosophers",
  "why the naive dining-philosophers solution deadlocks",
  "the problem is that there are not enough forks",
  "five philosophers and five forks does look scarce",
  "The resource count is adequate - the ORDERING is not. If every philosopher takes "
  "their left fork first, all five hold one fork and wait forever for the right: a "
  "circular wait. Breaking the symmetry removes the cycle.",
  "Numbering forks and always acquiring the lower-numbered one first eliminates "
  "circular wait entirely - the same lock-ordering trick used in real kernels."),

 ("priority_inversion",
  "what priority inversion is",
  "priority inversion means the scheduler has a bug",
  "a low-priority task running before a high-priority one looks wrong",
  "Priority inversion is a correct scheduler producing a bad outcome: a HIGH priority "
  "task waits on a lock held by a LOW priority task, which is itself preempted by "
  "MEDIUM priority work. Priority inheritance fixes it by temporarily raising the "
  "lock holder's priority.",
  "The Mars Pathfinder resets in 1997 were caused by exactly this, and were fixed by "
  "enabling priority inheritance on the offending mutex."),

 ("monitor_vs_semaphore",
  "what a monitor gives you that raw semaphores do not",
  "monitors and semaphores are interchangeable",
  "both provide mutual exclusion",
  "A monitor bundles the shared data with the procedures that access it and makes "
  "mutual exclusion IMPLICIT - the runtime enforces that only one thread is inside. "
  "Semaphores are explicit and unstructured: one missing signal, or two waits in the "
  "wrong order, breaks the program silently.",
  "Java's synchronized methods with wait/notify form a monitor. Forgetting to release "
  "is impossible; with a semaphore it is one missing line."),

 ("file_descriptor",
  "what a file descriptor actually is",
  "a file descriptor is a pointer to the file on disk",
  "it is used to read and write file contents",
  "A file descriptor is a small integer INDEX into the process's open-file table. "
  "That entry points to a system-wide open-file description holding the offset and "
  "mode, which in turn points to the inode. Three levels of indirection, not a disk "
  "pointer.",
  "After fork(), parent and child share the same open-file description, so a read by "
  "one advances the offset seen by the other."),

 ("hard_vs_soft_link",
  "the difference between a hard link and a symbolic link",
  "hard links and symbolic links are the same with different syntax",
  "both create a second way to reach a file",
  "A HARD link is another directory entry pointing at the same inode; the file "
  "survives until the last link is removed, and hard links cannot cross filesystems. "
  "A SYMBOLIC link is a small file containing a PATH; it can cross filesystems and "
  "dangles if the target disappears.",
  "Delete the original name of a hard-linked file and the data remains reachable. "
  "Delete the target of a symlink and the symlink breaks."),

 ("journaling_purpose",
  "what a journaling filesystem protects against",
  "journaling prevents data loss on power failure",
  "journaling is introduced in the context of crashes",
  "Journaling protects filesystem METADATA consistency, so the filesystem need not "
  "be fully checked after a crash. In the usual ordered mode it does not guarantee "
  "your file DATA was written - only that the structure is coherent.",
  "After a crash a journaled filesystem mounts in seconds instead of a long fsck, but "
  "a partially written file may still contain garbage unless the application called "
  "fsync()."),

 ("seek_vs_rotational",
  "why seek time usually dominates hard-disk access",
  "rotational latency is the main cost of a disk access",
  "the disk is always spinning, so rotation feels continuous",
  "Seek time - moving the arm to the right cylinder - is typically the largest "
  "component, which is why disk schedulers optimise head MOVEMENT. Rotational latency "
  "averages half a revolution and transfer time is small for modest requests.",
  "At 7200 rpm average rotational latency is about 4.2 ms while a full-stroke seek "
  "can exceed 10 ms. SCAN and C-SCAN exist to minimise the seek term."),

 ("ssd_no_seek",
  "why disk scheduling algorithms matter less for SSDs",
  "SCAN and C-SCAN improve SSD performance the same way they do for hard disks",
  "they are taught as general disk algorithms",
  "SSDs have no moving head, so seek time is essentially zero and ordering requests "
  "by cylinder buys nothing. SSD performance is governed by write amplification, "
  "erase-block granularity and the FTL's garbage collection instead.",
  "An SSD serves a random 4 KB read in tens of microseconds regardless of where the "
  "previous read landed; a hard disk can take 10 ms if the arm must cross the "
  "platter."),

 ("kernel_vs_user_thread",
  "the difference between user-level and kernel-level threads",
  "user-level threads run faster because the kernel is not involved",
  "avoiding the kernel does make switching cheaper",
  "User-level threads switch cheaply because the kernel never sees them - but for the "
  "same reason the kernel cannot schedule them independently. One blocking system "
  "call blocks the WHOLE process, and pure user-level threads cannot use multiple "
  "cores.",
  "A purely user-threaded program doing a blocking read() stalls every thread; with "
  "kernel threads only the calling thread blocks."),

 ("external_fragmentation_compaction",
  "why compaction is rarely used to fix external fragmentation",
  "the OS should just compact memory whenever it fragments",
  "compaction obviously removes the holes",
  "Compaction requires moving live data and rewriting every pointer or base register, "
  "and it stalls the affected processes while it runs. It is only possible with "
  "relocatable addressing and is expensive at scale - which is why paging, which "
  "sidesteps external fragmentation entirely, won.",
  "Moving a 1 GB process to close a gap means copying 1 GB while that process cannot "
  "run. Paging avoids the problem rather than repairing it."),

 ("safe_vs_deadlocked",
  "whether an unsafe state means the system has deadlocked",
  "an unsafe state means deadlock has already occurred",
  "unsafe sounds like a failure state",
  "UNSAFE means deadlock has become POSSIBLE, not that it has happened. From an "
  "unsafe state the system may still complete if processes happen to release "
  "resources in a favourable order. Every deadlocked state is unsafe, but not every "
  "unsafe state is deadlocked.",
  "Banker's algorithm refuses requests leading to unsafe states precisely because it "
  "cannot rely on that favourable ordering occurring."),
]
