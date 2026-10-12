"""Knowledge base block 5: memory-management internals, scheduling policy, lock-free
synchronisation, kernel I/O paths, file-system semantics, security and virtualisation.

Added because the conceptual category was the binding constraint on dataset size:
the build measured 382 distinct conceptual items, short of the ~450 needed for a
2,000-row training split. The fix is more GENUINE concepts, never looser gates or
more rewordings of existing ones.

Same 7-tuple structure as KB3/KB4:
  (topic, question_core, misconception, why_seductive, correction, example, probe)
"""

KB5 = [
 ("clock_algorithm",
  "how the CLOCK (second-chance) page-replacement algorithm works",
  "CLOCK is just FIFO with a different name",
  "it walks the frames in a fixed circular order, exactly like a FIFO queue",
  "CLOCK approximates LRU using the hardware reference bit. The hand sweeps the frames; "
  "a frame with reference bit 1 gets a second chance (the bit is cleared and the hand "
  "moves on), and the first frame found with bit 0 is evicted. Recently used pages "
  "therefore survive a sweep, which FIFO never allows.",
  "A heavily used page loaded first is always FIFO's next victim. Under CLOCK its "
  "reference bit is set again on every sweep, so it is skipped and a genuinely idle "
  "page is evicted instead.",
  "If a page is referenced constantly, what does the hand find in its reference bit "
  "each time it comes around?"),

 ("global_vs_local_replacement",
  "the difference between global and local page replacement",
  "a process's page faults depend only on its own behaviour",
  "each process has its own page table and its own reference string",
  "Under GLOBAL replacement a faulting process may take a frame from ANY process, so "
  "one process's fault rate depends on what the others are doing. LOCAL replacement "
  "restricts victims to the faulting process's own frames: behaviour is more "
  "predictable, but idle frames held by other processes cannot be reused.",
  "A memory-hungry batch job under global replacement steals frames from an editor; "
  "the editor then faults on every keystroke although its own access pattern never "
  "changed.",
  "Under global replacement, whose frames can a faulting process take?"),

 ("tlb_shootdown",
  "what a TLB shootdown is and why it is needed",
  "updating a page-table entry in memory immediately affects every CPU",
  "the page table is shared memory that every core reads",
  "Each core caches translations in its OWN TLB, and TLBs are not kept coherent by "
  "hardware on common architectures. When the kernel unmaps or downgrades a page it "
  "must interrupt the other cores running that address space (an inter-processor "
  "interrupt) so they invalidate their stale entries. That is a TLB shootdown, and it "
  "is expensive.",
  "Thread A calls munmap() on core 0 while thread B on core 3 still holds the old "
  "translation in its TLB. Without a shootdown, B could keep writing to a physical "
  "frame that has already been reused.",
  "After the kernel changes a PTE on one core, where else might the old translation "
  "still be cached?"),

 ("huge_pages",
  "why huge pages can speed programs up",
  "huge pages help by making memory accesses themselves faster",
  "a bigger page sounds like a bigger, faster unit of memory",
  "DRAM speed is unchanged. Huge pages (for example 2 MB instead of 4 KB) let one TLB "
  "entry cover 512 times more memory, so TLB misses and page walks drop sharply for "
  "large working sets. The costs are internal fragmentation and more expensive "
  "allocation and compaction.",
  "A 1 GB in-memory table needs 262,144 translations with 4 KB pages but only 512 with "
  "2 MB pages - small enough to stay mostly resident in the TLB.",
  "How many TLB entries does a 1 GB region need with 4 KB pages, and how many with "
  "2 MB pages?"),

 ("numa",
  "what NUMA means for memory performance",
  "all RAM in a machine is equally fast to reach from every CPU",
  "RAM is presented to programs as one flat address space",
  "In a NUMA machine each socket has its own local memory controller. Memory attached "
  "to another socket is reachable, but through the interconnect, with higher latency "
  "and lower bandwidth. The OS therefore tries to allocate a thread's memory on the "
  "node where it runs (first-touch policy) and to keep threads near their memory.",
  "A thread migrated to the other socket keeps its data where it was, so every cache "
  "miss now crosses the interconnect and becomes noticeably slower.",
  "If a thread moves to a CPU on the other socket, where does its already-allocated "
  "memory live?"),

 ("page_table_entry_bits",
  "what the bits in a page-table entry are for",
  "a page-table entry holds only the frame number",
  "translation is described as mapping a page number to a frame number",
  "Besides the frame number, a PTE carries control bits: present/valid (is the page "
  "in RAM), read/write and user/supervisor protection, referenced (accessed) and "
  "dirty (modified), and often no-execute. The hardware checks protection on every "
  "access and sets the referenced and dirty bits that page replacement relies on.",
  "A write to a page whose PTE is marked read-only raises a protection fault. That is "
  "exactly how copy-on-write is implemented after fork().",
  "When the CPU translates an address, how does it know whether a write to that page "
  "is allowed?"),

 ("base_limit_registers",
  "how base and limit registers protect memory",
  "base and limit registers are used only for relocation, not protection",
  "the base register is described as the value added to every address",
  "Base and limit registers do both jobs. Every logical address is first compared with the LIMIT; if it is "
  "greater than or equal to the limit, the hardware traps to the OS. Only then is the "
  "BASE added to form the physical address. The comparison is what stops a process "
  "reaching memory outside its own region.",
  "With base 30000 and limit 12000, logical address 5000 maps to physical 35000, but "
  "logical address 13000 traps as an addressing error instead of touching another "
  "process's memory.",
  "What does the hardware do with logical address 13000 if the limit register holds "
  "12000?"),

 ("memory_ballooning",
  "how memory ballooning works in virtual machines",
  "the hypervisor can simply take memory back from a guest whenever it wants",
  "the hypervisor controls the physical hardware",
  "The hypervisor cannot see which guest pages are free, because the guest OS manages "
  "its own memory. A balloon driver inside the guest allocates pages - forcing the "
  "guest to free or swap its least valuable pages by its own policy - and hands them "
  "to the hypervisor. Deflating the balloon returns the memory.",
  "A host running short inflates the balloon in an idle VM. That guest's own kernel "
  "drops cold page-cache pages, and the hypervisor reuses the freed frames for a busy "
  "VM.",
  "Which layer actually knows which of a guest's pages are safe to give up?"),

 ("counting_semaphore",
  "what the value of a counting semaphore represents",
  "a semaphore is just a lock that can be held by many threads",
  "it is often introduced right after mutexes",
  "A counting semaphore is a counter of available units with atomic wait (decrement, "
  "block if none) and signal (increment, wake a waiter). It has no owner: any thread "
  "may signal it. That makes it suitable for counting resources and for signalling "
  "between threads, not only for mutual exclusion.",
  "A pool of 5 database connections uses a semaphore initialised to 5. The sixth "
  "concurrent request blocks in wait() until some thread finishes and signals.",
  "If a semaphore guarding a connection pool starts at 5, what happens to the sixth "
  "thread that calls wait()?"),

 ("compare_and_swap",
  "how compare-and-swap enables lock-free updates",
  "lock-free code means threads never wait or retry",
  "the name suggests the absence of any waiting",
  "CAS atomically replaces a value only if it still equals the value the thread "
  "previously read. Lock-free code reads, computes, then tries CAS; if another thread "
  "changed the value in between, CAS fails and the thread RETRIES. Lock-free "
  "guarantees that SOME thread always makes progress, not that no thread ever "
  "retries.",
  "Two threads read counter = 7 and both try CAS(7 -> 8). Exactly one succeeds; the "
  "other sees 8, recomputes 9 and retries, so no increment is lost.",
  "Two threads both read 7 and both try CAS(7 -> 8). What happens to the second one?"),

 ("aba_problem",
  "what the ABA problem is in lock-free programming",
  "if compare-and-swap succeeds, nothing changed since the value was read",
  "CAS checks that the value is still the one that was read",
  "CAS compares VALUES, not history. Between the read and the CAS another thread can "
  "change A to B and back to A; the CAS then succeeds although the structure has "
  "changed underneath. Fixes include tagged pointers with a version counter, hazard "
  "pointers and epoch-based reclamation.",
  "In a lock-free stack, thread 1 reads top = A (next = B) and is preempted. Thread 2 "
  "pops A and B and pushes A back. Thread 1's CAS(top, A -> B) succeeds and installs "
  "B, which has already been freed.",
  "Can a pointer change from A to B and back to A between your read and your CAS?"),

 ("lock_granularity",
  "the trade-off between coarse and fine-grained locking",
  "finer-grained locking is always faster",
  "more locks allow more parallelism",
  "Fine-grained locks allow more concurrency but add acquisition overhead, memory and "
  "complexity, and they increase deadlock risk because operations must take several "
  "locks in a consistent order. With low contention, a single coarse lock is often "
  "faster. The right granularity follows measured contention.",
  "A hash table with one lock per bucket scales well under heavy concurrent access, "
  "but an operation that resizes the table must now acquire every bucket lock in a "
  "fixed order.",
  "If only one thread ever touches a data structure, what do many small locks buy "
  "you?"),

 ("rcu",
  "how read-copy-update (RCU) synchronisation works",
  "readers must always take a lock to read shared data safely",
  "reading while another thread writes normally causes races",
  "RCU lets readers proceed WITHOUT locks or writes to shared memory. A writer copies "
  "the object, modifies the copy, and publishes it with one atomic pointer update. "
  "The old version is freed only after a grace period, once every reader that could "
  "have seen it has finished. It suits read-mostly data.",
  "The Linux kernel uses RCU for routing tables and many other lookups: thousands of "
  "concurrent readers never block, while a rare update swaps in a new version.",
  "If a writer replaces an object while readers are still using the old one, when is "
  "it safe to free the old version?"),

 ("prevention_vs_avoidance",
  "the difference between deadlock prevention and deadlock avoidance",
  "deadlock prevention and deadlock avoidance are the same thing",
  "both stop deadlock from happening",
  "PREVENTION makes deadlock structurally impossible by breaking one of the four "
  "necessary conditions, for example imposing a global lock order. AVOIDANCE allows "
  "all four conditions but checks each request at run time and grants it only if the "
  "system stays in a safe state, as Banker's algorithm does. Avoidance needs advance "
  "knowledge of maximum demands; prevention does not.",
  "Numbering every lock and acquiring only in increasing order is prevention: circular "
  "wait cannot form. Running Banker's safety check before granting each request is "
  "avoidance.",
  "Which approach needs to know each process's maximum resource demand in advance?"),

 ("rag_cycle",
  "whether a cycle in a resource-allocation graph always means deadlock",
  "a cycle in the resource-allocation graph always means deadlock",
  "circular wait is one of the conditions for deadlock",
  "With a SINGLE instance of each resource type, a cycle is necessary and sufficient "
  "for deadlock. With MULTIPLE instances, a cycle is necessary but not sufficient: a "
  "process outside the cycle may hold an instance, finish and release it, breaking "
  "the cycle.",
  "R1 has two instances. P1 holds one and waits for R2; P2 holds R2 and waits for R1. "
  "The graph has a cycle, but P3 holds the other R1 instance and will release it, so "
  "P2 can proceed.",
  "If a resource type has two instances, could a process outside the cycle free one "
  "of them?"),

 ("lottery_scheduling",
  "how lottery (proportional-share) scheduling works",
  "lottery scheduling is unfair because it is random",
  "randomness sounds like the opposite of a guarantee",
  "Each process holds tickets; each time slice goes to the holder of a randomly drawn "
  "ticket. Over many slices, each process's share of the CPU converges to its fraction "
  "of the tickets. Randomness gives proportional fairness in expectation with almost "
  "no state; stride scheduling achieves the same shares deterministically.",
  "A holds 75 tickets and B holds 25. Over 1,000 slices A receives about 750, although "
  "any short window may deviate.",
  "Over 1,000 draws, roughly how many slices does a process holding 75 of 100 tickets "
  "receive?"),

 ("cfs_scheduler",
  "how Linux's Completely Fair Scheduler chooses the next task",
  "the Linux CFS scheduler uses a fixed time quantum like Round Robin",
  "it switches between runnable tasks in turn, which looks like Round Robin",
  "CFS tracks each task's virtual runtime (CPU time weighted by nice value) and always "
  "runs the task with the SMALLEST vruntime, kept in a red-black tree. The slice "
  "length is derived from a target latency divided among the runnable tasks, so it "
  "shrinks as the number of tasks grows. (Since kernel 6.6 the default is EEVDF, "
  "which keeps the virtual-runtime idea and adds per-task deadlines.)",
  "A task that sleeps on I/O accumulates little vruntime. When it wakes its value is "
  "at or near the minimum, so it runs promptly, which is why interactive tasks feel responsive "
  "under CFS.",
  "When a task wakes after a long sleep, how does its virtual runtime compare with the "
  "others'?"),

 ("nice_values",
  "what the Unix nice value controls",
  "a nicer process runs at a higher priority",
  "the word nice sounds like a reward",
  "The nice value is how nice a process is to OTHERS. Higher nice (up to 19) means "
  "LOWER priority and a smaller CPU share; lower nice (down to -20) means higher "
  "priority. Ordinary users may only raise their niceness; lowering it requires "
  "privilege.",
  "`nice -n 19 make` builds in the background with the smallest CPU weight, so an "
  "interactive shell on the same machine stays responsive.",
  "If a process becomes nicer to other processes, does it get more CPU or less?"),

 ("hard_vs_soft_realtime",
  "the difference between hard and soft real-time systems",
  "real-time systems are simply very fast systems",
  "real-time is associated with high performance",
  "Real-time means PREDICTABLE, not fast. A HARD real-time system treats a missed "
  "deadline as a failure (airbag controllers, flight control), so worst-case timing "
  "must be bounded and proven. A SOFT real-time system tolerates occasional misses at "
  "reduced quality (video playback).",
  "An airbag must fire within about 30 ms every time. A faster average with a rare "
  "200 ms stall is unacceptable, whereas a video player dropping one frame merely "
  "stutters.",
  "Is a system that is usually 1 ms fast but occasionally takes 1 s suitable for "
  "airbag control?"),

 ("dispatch_latency",
  "what dispatch latency is",
  "a woken high-priority process starts running instantly",
  "the scheduler always picks the highest-priority ready process",
  "Dispatch latency is the time from an event making a process runnable to that "
  "process actually executing. It includes interrupt handling, waiting for a "
  "non-preemptible kernel section to finish, releasing resources held by "
  "lower-priority work, and the context switch. Real-time kernels minimise it with "
  "kernel preemption.",
  "A sensor interrupt readies a control task, but the kernel is in the middle of a "
  "non-preemptible section; the task waits until the section ends before the switch "
  "even begins.",
  "What must finish before a newly readied task can actually be switched in?"),

 ("kernel_preemption",
  "what it means for a kernel to be preemptible",
  "a process can always be preempted, even while executing kernel code",
  "user-mode code can be preempted at any moment",
  "Preempting user code is standard. A preemptible KERNEL additionally allows a task "
  "to be switched out while executing in kernel mode, except inside critical regions "
  "such as sections holding spinlocks. Non-preemptive kernels only switch at "
  "well-defined points, which is simpler but increases latency.",
  "In a non-preemptive kernel, a long system call delays a newly woken high-priority "
  "task until the call returns or blocks; a preemptible kernel can switch "
  "immediately.",
  "In a non-preemptive kernel, when is the earliest point another task can run?"),

 ("vdso",
  "how some system calls avoid entering the kernel",
  "every call like gettimeofday() must switch into kernel mode",
  "they are documented as system calls",
  "Linux maps a small shared library, the vDSO, into every process. It lets calls "
  "such as clock_gettime() and gettimeofday() read kernel-maintained time data "
  "directly in user mode, avoiding the mode switch entirely. Calls that change kernel "
  "state still trap.",
  "A program that calls clock_gettime() a million times runs far faster than one "
  "making a million genuine trapping calls such as getppid(), because the vDSO path "
  "never leaves user mode.",
  "Does reading the current time require changing any kernel state?"),

 ("kernel_stack",
  "why each thread has a separate kernel stack",
  "system calls run on the same stack as the user program",
  "the program just calls a function",
  "On entering the kernel, the CPU switches to a per-thread KERNEL stack. The user "
  "stack cannot be trusted - it may be corrupt, too small or deliberately "
  "manipulated - and the kernel must not leave its data where user code can read or "
  "modify it.",
  "A program sets its stack pointer to garbage and executes a system call. The kernel "
  "still runs safely, because the trap switched to that thread's own kernel stack "
  "first.",
  "If the user program's stack pointer is invalid, where can the kernel safely keep "
  "its local variables?"),

 ("top_bottom_half",
  "why interrupt handling is split into top and bottom halves",
  "an interrupt handler does all of the device's work immediately",
  "the interrupt is when the device needs attention",
  "The TOP half runs immediately, often with further interrupts masked, so it does "
  "only the urgent minimum: acknowledge the device and capture data. The deferred "
  "BOTTOM half (softirq, tasklet or workqueue) does the heavier processing later with "
  "interrupts enabled, keeping interrupt latency low for every other device.",
  "A network card's handler copies the packet descriptor and schedules the protocol "
  "processing; the TCP/IP work runs afterwards, so keyboard and disk interrupts are "
  "not delayed.",
  "While a handler runs with interrupts masked, what happens to other devices that "
  "need attention?"),

 ("dynamic_linking",
  "how shared libraries save memory",
  "every program that uses a shared library gets its own copy in RAM",
  "each process appears to have the whole library in its address space",
  "Shared libraries are mapped read-only into each process, so their code pages are "
  "backed by the SAME physical frames in every process. Only writable data, and pages "
  "modified by relocation, become private per process through copy-on-write. "
  "Position-independent code makes this sharing possible.",
  "Fifty processes using libc map its code into fifty address spaces, yet only one "
  "physical copy of those code pages sits in RAM.",
  "If fifty processes map the same read-only code pages, how many physical copies are "
  "needed?"),

 ("unlink_open_file",
  "what happens when a file is deleted while a process has it open",
  "deleting a file immediately frees its space and breaks readers",
  "the name disappears from the directory at once",
  "unlink() removes the NAME and decrements the link count. The inode and its data "
  "blocks are freed only when the link count is zero AND no process still has the "
  "file open. Open readers and writers continue working normally.",
  "Deleting a large log file that a daemon still writes to frees no disk space until "
  "the daemon closes it or restarts - a common puzzle when `df` still shows the disk "
  "full.",
  "After unlink(), what still references the inode if a process has the file open?"),

 ("directory_permissions",
  "what read and execute permissions mean on a directory",
  "execute permission on a directory is meaningless",
  "directories are not programs",
  "For a directory, READ allows listing its names, WRITE allows creating, deleting "
  "and renaming entries (with execute), and EXECUTE (search) allows traversing it to "
  "reach entries by name. Without execute on every directory in a path, the file "
  "cannot be reached, whatever its own permissions.",
  "With mode 644 on /home/alice (no x), others cannot open /home/alice/notes.txt even "
  "though that file is world-readable, because they cannot traverse the directory.",
  "Can you open /a/b/file.txt if you lack execute permission on /a/b?"),

 ("sticky_bit",
  "what the sticky bit does on a directory",
  "anyone who can write to a directory can delete any file in it",
  "deleting a file only needs write permission on the directory",
  "By default, write permission on a directory does allow deleting any entry in "
  "it, which is exactly why the sticky bit exists. On a directory with "
  "the sticky bit set, a file can be deleted or renamed only by its owner, the "
  "directory's owner, or root. Shared writable directories such as /tmp (mode 1777) "
  "rely on it.",
  "In /tmp every user can create files, but bob cannot delete alice's files there, "
  "even though /tmp is world-writable.",
  "Everyone may write to /tmp. What stops one user deleting another's files there?"),

 ("write_back_cache",
  "the difference between write-through and write-back caching",
  "once write() returns, the data is safely on disk",
  "the call completed without an error",
  "Most OSes use WRITE-BACK caching: write() copies data into the page cache, marks "
  "it dirty and returns; the kernel flushes it to disk later. That is fast but loses "
  "the data on power failure. WRITE-THROUGH updates the storage before completing, "
  "which is safer but slower. Durability needs fsync() or an equivalent.",
  "A program writes a file and the machine loses power a second later. The write() "
  "calls succeeded, but the data never reached the disk.",
  "At the moment write() returns, where is the data most likely to be?"),

 ("block_size_tradeoff",
  "the trade-off in choosing a file-system block size",
  "a larger block size is always better for performance",
  "fewer, bigger blocks mean fewer I/O operations",
  "Large blocks help sequential throughput and reduce metadata, but every file wastes "
  "on average half a block at its end (internal fragmentation). Many small files "
  "therefore waste a great deal of space. Small blocks save space but need more "
  "metadata and more I/Os for large files.",
  "Storing one million 1 KB files with 64 KB blocks consumes about 64 GB of disk for "
  "only about 1 GB of data.",
  "How much space does a 1 KB file occupy if the block size is 64 KB?"),

 ("fat_table",
  "how the FAT file system locates a file's blocks",
  "FAT stores a file's blocks contiguously",
  "a file appears as one continuous stream of bytes",
  "FAT is a LINKED allocation scheme with the links moved out of the data blocks into "
  "the File Allocation Table. The directory entry gives the first cluster; each table "
  "entry gives the next cluster of that file, with a special value marking the end. "
  "Keeping the table cached makes random access feasible without reading every data "
  "block.",
  "A file starting at cluster 5 whose FAT entries read 5 -> 9 -> 12 -> EOF occupies "
  "clusters 5, 9 and 12, which are scattered across the disk.",
  "Given only the first cluster number, where does FAT record which cluster comes "
  "next?"),

 ("ssd_wear_trim",
  "why SSDs need TRIM and wear levelling",
  "an SSD can overwrite a page in place, like a hard disk",
  "the OS writes to logical block addresses just as it does on a hard disk",
  "Flash can only be programmed after erasure, and erasure happens in large blocks. "
  "The SSD's flash translation layer writes updates to fresh pages and remaps them; "
  "garbage collection later erases blocks, and wear levelling spreads erasures "
  "evenly. TRIM tells the drive which pages the file system no longer uses, so "
  "garbage collection need not copy dead data.",
  "Without TRIM, a deleted file's pages still look valid to the drive, so it keeps "
  "copying them during garbage collection, increasing write amplification.",
  "When the file system deletes a file, how would the SSD know those pages are "
  "dead?"),

 ("capabilities_vs_acl",
  "the difference between capabilities and access-control lists",
  "capabilities and ACLs are different names for the same mechanism",
  "both decide who may access what",
  "Both represent the access matrix, sliced differently. An ACL is stored WITH THE "
  "OBJECT and lists which subjects may do what. A capability is held BY THE SUBJECT "
  "as an unforgeable token naming an object and rights. ACLs make 'who can access "
  "this file?' easy to answer; capabilities make delegation and least privilege "
  "natural but revocation harder.",
  "A Unix file descriptor behaves like a capability: after open() succeeds, it keeps "
  "granting access even if the file's permissions change, and it can be passed to "
  "another process.",
  "After a file is opened and its permissions are then changed, can the existing file "
  "descriptor still be used?"),

 ("paravirtualization",
  "what paravirtualisation is",
  "a guest OS always runs completely unmodified on a hypervisor",
  "full virtualisation is the most widely known case",
  "In PARAVIRTUALISATION the guest kernel is modified to call the hypervisor directly "
  "(hypercalls) instead of executing sensitive instructions that must be trapped and "
  "emulated. That removes costly traps. Paravirtual device drivers such as virtio are "
  "still widely used even when the CPU has hardware virtualisation support.",
  "A guest using virtio-net hands packet buffers to the hypervisor through shared "
  "rings, instead of emulating every register access of a real network card.",
  "If the guest knows it is virtualised, what could it do instead of touching "
  "emulated hardware registers?"),

 ("io_multiplexing",
  "how one thread can serve many network connections",
  "each network connection needs its own thread",
  "a blocking read() stalls the thread until data arrives",
  "With non-blocking sockets and a readiness API (select, poll, or the scalable "
  "epoll/kqueue), one thread asks the kernel which descriptors are ready and services "
  "only those. This event-loop model handles tens of thousands of mostly idle "
  "connections without a thread per connection.",
  "A server with 10,000 idle clients calls epoll_wait(); the kernel reports the 3 "
  "sockets with pending data, and the thread reads exactly those 3.",
  "If 9,997 of 10,000 connections are idle, why dedicate a blocked thread to each "
  "one?"),

 ("cow_snapshots",
  "how copy-on-write file systems take instant snapshots",
  "taking a snapshot requires copying all of the data",
  "a snapshot is a complete point-in-time copy",
  "Copy-on-write file systems (ZFS, Btrfs) never overwrite live blocks; every change "
  "is written to new blocks. A snapshot just preserves the old root pointer, so it is "
  "created in constant time and initially uses no extra space. Space grows only as "
  "the live file system diverges from the snapshot.",
  "Snapshotting a 2 TB volume takes a moment. Modifying 1 GB afterwards consumes about "
  "1 GB extra, because only the changed blocks now exist in two versions.",
  "If blocks are never overwritten in place, what does a snapshot need to remember?"),
]
