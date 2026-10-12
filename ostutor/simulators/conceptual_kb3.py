"""Knowledge base block 3: processes, IPC, scheduling depth, memory depth.

7-tuple entries:
  (topic, question_core, misconception, why_seductive, correction, example, probe)

`probe` is a Socratic question a tutor asks BEFORE explaining - one that makes a
student holding the misconception predict something wrong. It is what lets the
pipeline build OS-domain tutoring dialogues instead of relying only on maths
dialogues from MathDial.

Content is conservative, textbook-standard and kernel-version independent.
"""

KB3 = [
 ("exec_semantics",
  "what exec() does to the calling process",
  "exec() creates a new process to run the program",
  "fork and exec are always taught together, so exec sounds like creation",
  "exec() REPLACES the calling process's memory image with a new program. The PID "
  "stays the same, and open file descriptors without close-on-exec survive. No new "
  "process is created - that is fork()'s job - and on success exec() never returns.",
  "A shell forks a child, and the CHILD calls exec(). If the shell called exec() "
  "directly, the shell itself would be replaced and your terminal session would end.",
  "If exec() succeeds, what happens to the line of code immediately after the "
  "exec() call?"),

 ("wait_purpose",
  "why a parent process calls wait()",
  "wait() is only needed if the parent wants the child's output",
  "wait() is usually shown next to printing the child's result",
  "wait() reaps the child: it collects the exit status and lets the kernel release "
  "the child's process-table entry. Without it a terminated child stays a zombie. "
  "Synchronising on completion is a side effect, not the main purpose.",
  "A server that forks a child per request and never calls wait() slowly fills the "
  "process table with zombies even though every child finished correctly.",
  "After a child process exits, what still has to happen before its entry "
  "disappears from the process table?"),

 ("pipe_semantics",
  "how an anonymous pipe connects two processes",
  "a pipe is a file stored on disk that both processes read and write",
  "processes use read() and write() on it exactly like a file",
  "An anonymous pipe is a bounded in-kernel buffer with a read end and a write end, "
  "created before fork() so both processes inherit the descriptors. Nothing touches "
  "the disk. A reader blocks when it is empty; a writer blocks when it is full.",
  "In `ls | wc -l` the shell creates the pipe, forks twice, and wires ls's stdout "
  "to the write end and wc's stdin to the read end with dup2().",
  "If the writer produces data faster than the reader consumes it, what happens "
  "once the pipe's buffer fills?"),

 ("pipe_eof",
  "why a pipe reader sometimes never sees end-of-file",
  "the reader sees EOF as soon as the writer finishes writing",
  "finishing the writes feels like the end of the stream",
  "The reader sees EOF only when EVERY write-end descriptor has been closed. If any "
  "process - often the reader itself, via an inherited copy - still holds the write "
  "end open, read() blocks forever.",
  "A parent that forks, lets the child write, but forgets to close its own copy of "
  "the write end will hang waiting for EOF that never arrives.",
  "The child has written everything and exited. Why might the parent's read() "
  "still block?"),

 ("signals",
  "what a signal is and how it is delivered",
  "a signal interrupts the process at the exact instruction where it was sent",
  "signals are described as asynchronous interrupts",
  "A signal is recorded as PENDING by the kernel and delivered when the target next "
  "returns to user mode - after a system call or interrupt. The handler then runs "
  "and control resumes where the process left off. Some signals, like SIGKILL and "
  "SIGSTOP, cannot be caught or ignored.",
  "A process blocked in a long read() does not run its SIGINT handler immediately; "
  "the read is interrupted and the handler runs as the process returns to user mode.",
  "If a process is stuck inside a system call, when does its signal handler "
  "actually run?"),

 ("sigkill_vs_sigterm",
  "the difference between SIGTERM and SIGKILL",
  "SIGTERM and SIGKILL both terminate a process in the same way",
  "both are used to stop a process",
  "SIGTERM is a REQUEST: the process can catch it, flush buffers, remove temp files "
  "and exit cleanly, or even ignore it. SIGKILL cannot be caught, blocked or "
  "ignored; the kernel terminates the process with no chance to clean up.",
  "Always try SIGTERM first. Reaching for `kill -9` immediately can leave lock files "
  "and half-written data behind.",
  "Which of the two signals gives a database the chance to flush its buffers before "
  "exiting?"),

 ("pcb_contents",
  "what the process control block holds",
  "the PCB stores the process's code and data",
  "it is described as containing 'everything about the process'",
  "The PCB holds BOOKKEEPING, not the program itself: process state, PID, saved "
  "registers and program counter, scheduling information, memory-management "
  "pointers such as the page-table base, open-file table and accounting data. The "
  "code and data live in the process's address space.",
  "A context switch saves registers INTO the PCB and restores the next process's "
  "registers FROM its PCB - that is why the PCB must hold them.",
  "When the scheduler switches away from a process, where do its register values "
  "go?"),

 ("process_states",
  "the difference between the ready and blocked states",
  "a blocked process is waiting for the CPU",
  "both ready and blocked processes are 'not running'",
  "A READY process has everything it needs except the CPU and is in the ready queue. "
  "A BLOCKED (waiting) process is waiting for an EVENT - I/O completion, a lock, a "
  "signal - and could not use the CPU even if offered it.",
  "A process waiting for a disk read is blocked. When the read completes it moves to "
  "READY, not directly to RUNNING; it still has to be scheduled.",
  "When an I/O operation completes, does the waiting process start running "
  "immediately?"),

 ("shared_memory_ipc",
  "why shared memory is the fastest IPC mechanism",
  "shared memory is fast because the kernel copies data very efficiently",
  "most IPC involves the kernel moving data",
  "After setup, shared memory involves NO kernel copying at all: both processes map "
  "the same physical pages, so a write by one is directly visible to the other. The "
  "cost is that the processes must synchronise access themselves.",
  "Two processes exchanging a large image through a pipe copy it into and out of the "
  "kernel; through shared memory the image is written once and read in place.",
  "Once a shared memory region is mapped, what does the kernel have to do each time "
  "one process writes to it?"),

 ("message_passing",
  "when message passing is preferable to shared memory",
  "message passing is always slower and therefore always worse",
  "it involves kernel copies that shared memory avoids",
  "Message passing trades speed for SAFETY and SIMPLICITY: no shared state means no "
  "races on that state, and it works across machines where shared memory cannot. "
  "For small messages or distributed systems it is often the better design.",
  "Microkernels build most OS services on message passing precisely because isolated "
  "components that communicate by messages cannot corrupt each other's memory.",
  "Which mechanism can work between processes on two different computers?"),

 ("orphan_reparenting",
  "what happens to a child whose parent exits first",
  "the child is killed automatically when its parent dies",
  "the parent-child relationship suggests the child depends on the parent",
  "The child keeps running. The kernel re-parents it to init (or a designated "
  "subreaper such as systemd), which will later reap it with wait(). This is what "
  "prevents orphans from becoming permanent zombies.",
  "Daemons deliberately double-fork so the intermediate parent exits and the daemon "
  "is adopted by init, detaching it from the terminal session.",
  "If a parent exits while its child is still running, who will eventually collect "
  "the child's exit status?"),

 ("sjf_optimality",
  "why SJF is optimal and why it is hard to use",
  "SJF is optimal, so real systems use it directly",
  "it provably minimises average waiting time",
  "SJF minimises average waiting time for a given set of jobs, but it needs the "
  "length of the NEXT CPU burst, which is unknown in advance. Real schedulers "
  "PREDICT it, typically with exponential averaging of previous bursts, and it can "
  "starve long jobs.",
  "With exponential averaging, tau(n+1) = alpha*t(n) + (1-alpha)*tau(n); alpha "
  "controls how quickly the prediction reacts to recent behaviour.",
  "What piece of information does SJF need that the scheduler cannot actually know?"),

 ("aging",
  "how aging prevents starvation",
  "starvation can only be fixed by switching to round robin",
  "round robin is the famous fair scheduler",
  "Aging gradually RAISES the priority of a process the longer it waits, so any "
  "waiting process eventually has high enough priority to run. It keeps priority "
  "scheduling while guaranteeing eventual service.",
  "If priority increases by 1 every 15 minutes, a process starting at priority 127 "
  "reaches priority 0 in about 32 hours even under constant high-priority load.",
  "In a strict priority scheduler with a steady stream of high-priority jobs, what "
  "happens to a low-priority job - and what could change that?"),

 ("rate_monotonic",
  "what rate-monotonic scheduling assigns and guarantees",
  "rate-monotonic scheduling gives higher priority to longer tasks",
  "longer tasks seem to need more help to finish",
  "Rate-monotonic assigns STATIC priorities by PERIOD: the shorter the period, the "
  "higher the priority. It is optimal among fixed-priority schedulers, and a task "
  "set is guaranteed schedulable if CPU utilisation is below n(2^(1/n) - 1), about "
  "69% for large n.",
  "Two tasks: period 50 ms and period 100 ms. RM gives the 50 ms task higher "
  "priority regardless of how long each task's computation is.",
  "Under rate-monotonic scheduling, does a task's execution time affect its "
  "priority?"),

 ("edf_scheduling",
  "how earliest-deadline-first differs from rate-monotonic",
  "EDF and rate-monotonic are the same with different names",
  "both are real-time schedulers built around deadlines and periods",
  "EDF uses DYNAMIC priorities: whichever ready task has the nearest deadline runs "
  "next. For independent preemptible periodic tasks it can reach 100% CPU "
  "utilisation, whereas rate-monotonic's guarantee holds only up to about 69%.",
  "A task set at 90% utilisation may be unschedulable under rate-monotonic yet meet "
  "every deadline under EDF.",
  "Does a task's priority stay fixed under EDF, or can it change over time?"),

 ("processor_affinity",
  "why schedulers try to keep a process on the same CPU",
  "moving a process between CPUs costs nothing on a multiprocessor",
  "all CPUs share the same main memory",
  "Each CPU has its own caches. A process that migrates arrives at a COLD cache and "
  "must refill it from memory, so schedulers prefer processor affinity - rerunning a "
  "process where its data is already cached - while still balancing load.",
  "A compute-heavy thread bounced between cores every few milliseconds can run "
  "noticeably slower than one pinned to a single core, purely from cache refills.",
  "When a process moves to a different CPU, what happens to the data sitting in the "
  "first CPU's cache?"),

 ("load_balancing",
  "the tension between load balancing and affinity",
  "a perfectly balanced load is always the best goal",
  "idle CPUs look like wasted capacity",
  "Balancing moves processes to idle CPUs, which improves utilisation but destroys "
  "cache affinity. Schedulers use push and pull migration with thresholds, moving "
  "work only when the imbalance is large enough to outweigh the cache penalty.",
  "Linux migrates tasks between cores within a shared-cache domain more readily than "
  "across sockets, because the cross-socket cache cost is much higher.",
  "Why might a scheduler deliberately leave a CPU briefly idle rather than migrate a "
  "process to it?"),

 ("multilevel_page_table",
  "why multilevel page tables save memory",
  "multilevel page tables make translation faster",
  "they are presented as an improvement over flat page tables",
  "They save SPACE, not time. A flat table for a 32-bit space with 4 KB pages needs "
  "about a million entries per process even if most of the space is unused. A "
  "multilevel table allocates inner tables only for regions actually in use. Each "
  "level adds a memory access to a TLB miss, so translation gets slower.",
  "A process using a few megabytes needs only a handful of second-level tables "
  "instead of the full 4 MB flat table.",
  "On a TLB miss, does a two-level page table need more or fewer memory accesses "
  "than a flat one?"),

 ("inverted_page_table",
  "what an inverted page table indexes by",
  "an inverted page table has one entry per virtual page, like a normal one",
  "it is still called a page table",
  "An inverted page table has one entry per PHYSICAL FRAME, recording which process "
  "and virtual page occupy it. Its size scales with physical memory rather than "
  "with the virtual address space, but finding a mapping needs a search or a hash "
  "table instead of direct indexing.",
  "With 64-bit address spaces, one entry per virtual page is impossibly large, while "
  "one entry per frame of RAM stays bounded.",
  "Does the size of an inverted page table depend on the virtual address space or on "
  "the amount of RAM?"),

 ("tlb_reach",
  "what TLB reach is and why it matters",
  "a larger TLB is the only way to reduce TLB misses",
  "more entries obviously cover more",
  "TLB reach = number of entries x page size. Using LARGER pages increases reach "
  "without adding entries, which is why huge pages cut TLB misses dramatically for "
  "large working sets.",
  "A 64-entry TLB covers 256 KB with 4 KB pages but 128 MB with 2 MB pages.",
  "Without adding a single TLB entry, how could you let the TLB cover more memory?"),

 ("effective_access_time",
  "how the TLB hit ratio affects effective memory access time",
  "a TLB miss only costs the time of one extra lookup",
  "the page table is just another table",
  "Effective access time = h*(TLB + mem) + (1-h)*(TLB + k*mem + mem), where k is the "
  "number of page-table levels walked on a miss. With multilevel tables a miss costs "
  "several memory accesses, so even a small drop in hit ratio hurts noticeably.",
  "With a 20 ns TLB, 100 ns memory, one page-table level and a 98% hit ratio: "
  "0.98*120 + 0.02*220 = 122 ns.",
  "If the page table has three levels, how many memory accesses does a TLB miss "
  "need before the data itself is fetched?"),

 ("segmentation",
  "how segmentation differs from paging",
  "segmentation and paging both divide memory into fixed-size pieces",
  "both are ways of splitting an address space",
  "Segmentation divides memory into VARIABLE-SIZE logical units - code, stack, heap - "
  "matching the program's structure, and so suffers external fragmentation. Paging "
  "uses FIXED-SIZE pages invisible to the programmer and avoids external "
  "fragmentation. Some architectures combine them.",
  "A segment fault means an offset exceeded that segment's limit; a page fault "
  "usually just means the page is not resident yet.",
  "Which of the two schemes can suffer from external fragmentation, and why?"),

 ("buddy_allocator",
  "how the buddy allocator manages memory",
  "the buddy allocator gives each request exactly the size it asks for",
  "allocators are expected to be exact",
  "The buddy system hands out blocks in POWERS OF TWO. A request is rounded up and a "
  "larger block is split in halves until one fits; when both 'buddy' halves are "
  "free they merge back. Merging is cheap, at the cost of internal fragmentation "
  "from rounding up.",
  "A 33 KB request receives a 64 KB block, wasting 31 KB inside it.",
  "If a process asks for 70 KB from a buddy allocator, what size of block does it "
  "actually receive?"),

 ("slab_allocator",
  "what problem the slab allocator solves",
  "the slab allocator is just another name for the buddy system",
  "both are kernel memory allocators",
  "The slab allocator keeps CACHES of pre-initialised objects of one kernel type - "
  "inodes, task structures - carved from slabs. Freed objects return to the cache "
  "and are reused without rounding waste or re-initialisation. It usually sits on "
  "top of the page allocator.",
  "Creating and destroying thousands of small kernel objects per second is cheap "
  "with slabs; carving each from the buddy allocator would waste memory and time.",
  "Why would a kernel keep a pool of already-initialised inode structures ready?"),

 ("mmap_files",
  "what memory-mapping a file does",
  "mmap() reads the entire file into memory immediately",
  "the file becomes addressable as memory, so it seems it must be loaded",
  "mmap() establishes a MAPPING. Pages are faulted in on first access (demand "
  "paging), so a huge file can be mapped instantly. For a shared mapping, writes to "
  "the memory eventually reach the file.",
  "Mapping a 10 GB file returns immediately; touching one byte in the middle loads "
  "just that page.",
  "Right after a successful mmap() of a large file, how much of it is actually in "
  "RAM?"),

 ("oom_killer",
  "what the Linux OOM killer does",
  "the OOM killer kills the process that most recently requested memory",
  "the latest request is what tipped the system over",
  "When memory is exhausted, the OOM killer picks a victim using a BADNESS score based "
  "mainly on memory footprint, adjustable per process via oom_score_adj. The "
  "victim is usually a large consumer, not necessarily the latest requester.",
  "A small shell command that triggers the shortage usually survives while a large "
  "leaking process is killed.",
  "When Linux runs out of memory, is the victim chosen by who asked last or by some "
  "other measure?"),

 ("overcommit",
  "why malloc() can succeed even when memory is not available",
  "a successful malloc() guarantees the memory exists",
  "the call returned a valid pointer",
  "Linux typically OVERCOMMITS: allocation reserves address space, and physical pages "
  "are assigned only when first touched. If many processes then touch their "
  "allocations, real memory can run out afterwards, which is when the OOM killer "
  "steps in.",
  "malloc(8 GB) can succeed on a 4 GB machine; the process fails only when it writes "
  "to enough of those pages.",
  "Does a successful malloc() mean physical memory has been set aside at that "
  "moment?"),

 ("stack_vs_heap",
  "the difference between stack and heap allocation",
  "stack and heap memory are the same, just used differently",
  "both live in the process's address space",
  "The STACK holds function frames - locals, return addresses - allocated and freed "
  "automatically in LIFO order, very fast, and usually limited in size. The HEAP "
  "holds dynamically allocated memory whose lifetime is controlled explicitly with "
  "malloc/free or a garbage collector.",
  "Returning a pointer to a local variable is a bug: that stack frame is reclaimed "
  "when the function returns, while heap memory survives until freed.",
  "What happens to a function's local variables when the function returns?"),

 ("stack_overflow",
  "why deep recursion can crash a program",
  "recursion crashes only when the heap runs out",
  "memory exhaustion sounds like a heap problem",
  "Each call pushes a stack frame. The stack has a fixed maximum size - often 8 MB "
  "for a Linux main thread - so unbounded or very deep recursion exhausts it and "
  "hits a guard page, causing a segmentation fault long before the heap is "
  "affected.",
  "A recursive function without a correct base case crashes with a stack overflow "
  "even on a machine with gigabytes of free RAM.",
  "Which region of memory grows with every recursive call?"),

 ("aslr",
  "what address space layout randomisation protects against",
  "ASLR encrypts a process's memory",
  "it is a security feature that 'scrambles' memory",
  "ASLR randomises WHERE the stack, heap, libraries and executable are placed each "
  "time a program runs. It does not encrypt anything; it makes exploits that rely "
  "on hard-coded addresses unreliable.",
  "Running `cat /proc/self/maps` twice shows different base addresses for the stack "
  "and the libraries each time.",
  "If an attacker needs the exact address of a library function, what does ASLR "
  "change for them?"),

 ("user_kernel_mode",
  "why the CPU has user mode and kernel mode",
  "kernel mode exists only so the OS can run faster",
  "kernel code often seems more privileged and efficient",
  "The mode bit is a PROTECTION mechanism. Privileged instructions - I/O, changing "
  "page tables, disabling interrupts - trap if attempted in user mode. That is what "
  "stops an ordinary program from taking over the machine.",
  "If a user program executes an instruction to disable interrupts, the CPU raises "
  "an exception instead of obeying it.",
  "What happens if a user-mode program tries to execute a privileged instruction?"),

 ("monolithic_vs_micro",
  "the trade-off between monolithic kernels and microkernels",
  "microkernels are always better because they are smaller",
  "smaller sounds simpler and more reliable",
  "A MICROKERNEL keeps only minimal services in the kernel and runs drivers and file "
  "systems as user-space servers, improving isolation at the cost of IPC overhead. "
  "A MONOLITHIC kernel runs everything in kernel space: faster, but a buggy driver "
  "can crash the whole system. Most real systems are hybrids or modular monoliths.",
  "Linux is monolithic but loads modules dynamically; a faulty module can still bring "
  "down the kernel.",
  "In a microkernel, what extra cost does a file read pay compared with a monolithic "
  "kernel?"),

 ("loadable_modules",
  "what loadable kernel modules provide",
  "loadable modules make Linux a microkernel",
  "they are added and removed at run time like separate components",
  "Modules are loaded INTO kernel space and run with full kernel privilege. They give "
  "flexibility - no reboot to add a driver - but no isolation: a buggy module can "
  "corrupt kernel memory exactly like built-in code.",
  "`insmod` adds a driver to a running Linux kernel, yet a null-pointer bug in it "
  "can still cause a kernel panic.",
  "Does a loaded kernel module run in user space or kernel space?"),

 ("interrupt_handling",
  "why interrupt handlers are split into top and bottom halves",
  "an interrupt handler should do all its work immediately",
  "the device needs attention now",
  "While a top half runs, other interrupts may be masked, so it must be SHORT: "
  "acknowledge the device and capture urgent data. The rest is deferred to a bottom "
  "half - softirq, tasklet or workqueue - which runs later with interrupts enabled.",
  "A network card's handler copies the packet out quickly; protocol processing "
  "happens later in a softirq.",
  "Why is it dangerous for an interrupt handler to run for a long time?"),

 ("dma",
  "what DMA frees the CPU from doing",
  "DMA makes the device faster at reading data",
  "direct memory access sounds like a speed-up of the device itself",
  "DMA lets a device controller transfer a block directly between the device and "
  "memory WITHOUT the CPU copying each word. The CPU sets up the transfer and is "
  "interrupted once when it completes, remaining free for other work in between.",
  "Without DMA the CPU would be interrupted or would copy data for every word of a "
  "large disk read; with DMA it gets one completion interrupt.",
  "During a large DMA transfer, what is the CPU doing?"),

 ("polling_vs_interrupts",
  "when polling a device beats using interrupts",
  "interrupts are always better than polling",
  "polling wastes CPU cycles checking a device",
  "Interrupts are better when events are INFREQUENT. When events arrive very fast, "
  "the per-interrupt overhead can dominate, and polling - or a hybrid such as "
  "Linux's NAPI for network cards - is more efficient.",
  "Under heavy network load, NAPI switches from interrupts to polling so the CPU is "
  "not overwhelmed by one interrupt per packet.",
  "If a device produces an event every microsecond, what happens to a CPU that "
  "takes one interrupt per event?"),

 ("buffering",
  "why the OS buffers I/O",
  "buffering exists only to make I/O faster",
  "buffers are associated with performance",
  "Buffering also copes with SPEED MISMATCHES between producer and consumer, with "
  "different TRANSFER SIZES, and supports copy semantics so a caller can reuse its "
  "buffer immediately after write() returns. Double buffering lets one buffer fill "
  "while the other drains.",
  "write() often returns before data reaches the disk because it only copied into a "
  "kernel buffer - which is why fsync() exists.",
  "When write() returns successfully, is the data guaranteed to be on the disk?"),

 ("fsync_durability",
  "what fsync() guarantees",
  "write() already guarantees the data is saved permanently",
  "a successful write() sounds final",
  "write() usually only copies data into the page cache. fsync() forces the file's "
  "dirty data and metadata to stable storage and returns only when the device "
  "reports completion. Without it, a crash can lose recently written data.",
  "Databases call fsync() at commit time; skipping it makes transactions fast but not "
  "durable.",
  "If the machine loses power a second after write() returns, is the data safe?"),

 ("spooling",
  "what spooling is",
  "spooling is the same as buffering",
  "both hold data temporarily",
  "Spooling holds complete jobs for a device that can serve only ONE job at a time, "
  "such as a printer, queuing them on disk so many processes can submit output "
  "concurrently while the device drains them in order.",
  "Many users print at once; the spooler writes each job to a queue and the printer "
  "prints them one after another without interleaving pages.",
  "Why must output for a printer not be interleaved between two users' jobs?"),
]
