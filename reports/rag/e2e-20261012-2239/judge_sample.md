# Faithfulness: sample for a human check

For each row: does the passage support everything the sentence states? Mark the `human` column yes/no. `judge` is the base model's verdict.

## 1. `c120|9|3` — judge: **yes** — human: ____

**Sentence:** **Memory Access**: Once the physical frame number is known, the hardware uses it to compute the physical memory address and access the actual data. > **Note**: In some systems, the hardware may automatically handle this lookup (e.g., with a page table walker), while in others, it triggers an interrupt to the operating system, which then performs the lookup and updates the TLB [S3].

**Passage [S3] Hailperin, Operating Systems and Middleware — Virtual Memory — Mechanisms for Virtual Memory › Software/Hardware Interface:** system just loads this register and lets the hardware deal with loading individual TLB entries. Of course, there are some additional complications. For example, if the operating system stores updated mapping information into the page table, it needs to flush obsolete entries from the TLB. In other processors, the hardware has no specialized access to the page table. When the TLB misses, the hardware transfers control to the operating system using an interrupt. The operating system software looks up the missing address translation in the page table, loads the translation into the TLB using a special instruction, and resumes normal execution. Because the operating system does the page table lookup, it can use whatever data structure its designer wishes. The lookup operation is done not with a special hardware walker, but with normal instructions to load from memory. Thus, the omission of a page table walker renders the processor more flexible, as well as simpler. However, TLB misses become more expensive, as they entail a context switch to the operating system with attendant loss of cache locality. The MIPS processor,

## 2. `c066|9|3` — judge: **yes** — human: ____

**Sentence:** In summary, starting a semaphore at zero ensures that the waiting thread (e.g., the parent) only proceeds after the event (e.g., the child's completion) has actually occurred [S3].

**Passage [S3] OSTEP ch. 31: Semaphores (course reading) — Page 5:** [course material withheld: not for redistribution]

## 3. `c006|15|2` — judge: **no** — human: ____

**Sentence:** This helps in debugging and performance optimization [S2].

**Passage [S2] OSTEP ch. 4: The Abstraction: The Process (course reading) — Page 9:** [course material withheld: not for redistribution]

## 4. `c048|10|2` — judge: **no** — human: ____

**Sentence:** It is often used by the operating system to manage page replacement algorithms [S2]. 5.

**Passage [S2] Hailperin, Operating Systems and Middleware — Virtual Memory — Mechanisms for Virtual Memory › Linear Page Tables:** *Linear page tables* are conceptually the simplest form of page table, though as you will see, they turn out to be not quite so simple in practice as they are in concept. A linear page table is an array with one entry per page in the virtual address space. The first entry in the table describes page 0, the next describes page 1, and so forth. To find the information about page $`n`$, one uses the same approach as for any array access: multiply $`n`$ by the size of a page table entry and add that to the base address of the page table. Recall that each page either has a corresponding page frame or has none. Therefore, each page table entry contains, at a minimum, a *valid bit* and a page frame number. If the valid bit is 0, the page has no corresponding frame, and the page frame number is unused. If the valid bit is 1, the page is mapped to the specified page frame. Real page tables often contain other bits indicating permissions (for example, whether

## 5. `c054|6|2` — judge: **yes** — human: ____

**Sentence:** As noted in [S2], "being able to execute the instruction to tell the hardware where the trap tables are is a very powerful capability.

**Passage [S2] OSTEP ch. 6: Mechanism: Limited Direct Execution (course reading) — Page 6:** [course material withheld: not for redistribution]

## 6. `c012|8|1` — judge: **yes** — human: ____

**Sentence:** This highlights a key limitation of the basic MLFQ: **it can be exploited by programs that manipulate their own behavior** [S1].

**Passage [S1] Lecture slides: Multi-Level Feedback Queue — Slide 10: Problems with the Basic MLFQ:** [course material withheld: not for redistribution]

## 7. `c090|0|3` — judge: **yes** — human: ____

**Sentence:** After a `fork()` system call, the parent and child processes have identical memory images initially, including shared file descriptors and memory pages [S3].

**Passage [S3] Wikipedia — Fork (system call) — Overview:** follow the virtual memory model from SunOS-4.0, copy-on-write semantics are implemented and the physical memory need not be actually copied. Instead, virtual memory pages in both processes may refer to the same pages of physical memory until one of them writes to such a page: then it is copied. This optimization is important in the common case where fork is used in conjunction with exec to execute a new program: typically, the child process performs only a small set of actions before it ceases execution of its program in favour of the program to be started, and it requires very few, if any, of its parent's data structures. When a process calls fork, it is deemed the parent process and the newly created process is its child. After the fork, both processes not only run the same program, but they resume execution as though both had called the system call. They can then inspect the call's return value to determine their status, child or parent, and act accordingly. The history of fork dates back to the 1960s as one of

## 8. `c080|4|1` — judge: **no** — human: ____

**Sentence:** **Prevention of Unauthorized Access**:    - Because applications are confined to their own virtual address space, they cannot accidentally or intentionally overwrite kernel data structures (like system calls, device drivers, or memory management tables).    - This isolation ensures that even if an application crashes or contains a bug, it cannot crash or corrupt the kernel [S1]. 4.

**Passage [S1] Wikipedia — Kernel (operating system) — Memory management:** The kernel has full access to the system's memory and must allow processes to safely access this memory as they require it. Often the first step in doing this is virtual addressing, usually achieved by paging and/or segmentation. Virtual addressing allows the kernel to make a given physical address appear to be another address, the virtual address. Virtual address spaces may be different for different processes; the memory that one process accesses at a particular (virtual) address may be different memory from what another process accesses at the same address. This allows every program to behave as if it is the only one (apart from the kernel) running and thus prevents applications from crashing each other. On many systems, a program's virtual address may refer to data that is not currently in memory. The layer of indirection provided by virtual addressing allows the operating system to use other data stores, like a hard drive, to store what would otherwise have to remain in main memory (RAM). As a result, operating systems can allow programs to use more memory than the

## 9. `c038|2|4` — judge: **yes** — human: ____

**Sentence:** These registers hold the state of the user process before the trap occurred [S4]. 2.

**Passage [S4] OSTEP ch. 6: Mechanism: Limited Direct Execution (course reading) — Page 4:** [course material withheld: not for redistribution]

## 10. `c024|6|1` — judge: **no** — human: ____

**Sentence:** The hardware retrieves the base address of the segment's page table from this entry [S1]. 3.

**Passage [S1] Lecture slides: Advanced Page Tables — Slide 8: TLB miss on Hybrid Approach:** [course material withheld: not for redistribution]

## 11. `c104|2|2` — judge: **yes** — human: ____

**Sentence:** The page is already in memory, so only the page table entry needs to be updated [S2]. ### **Major Page Fault (Hard Page Fault)** - Occurs when the page **is not in memory** at all. - The OS must **load the page from disk** (e.g., from a file or swap space) into RAM. - This involves:   1.

**Passage [S2] Wikipedia — Page fault — Types › Minor page fault:** If the page is loaded in memory at the time the fault is generated, but is not marked in the memory management unit as being loaded in memory, then it is called a minor, or soft, page fault. The page fault handler in the operating system merely needs to make the entry for that page in the memory management unit point to the page in memory and indicate that the page is loaded in memory; it does not need to read the page into memory. This could happen if the memory is shared by different programs and the page has already been brought into memory for another program.

## 12. `c006|3|1` — judge: **no** — human: ____

**Sentence:** For example, when a user starts a web browser, the OS creates a new process to run the browser [S1]. 2.

**Passage [S1] Lecture slides: OS Functionalities — Slide 3: Process Management:** [course material withheld: not for redistribution]

## 13. `c052|11|4` — judge: **no** — human: ____

**Sentence:** **Stack and Register Information**:    - In some systems, the PCB may store the process's stack pointer and register values to enable context switching [S4].

**Passage [S4] Wikipedia — Process control block — Location:** The PCB must be kept in an area of memory protected from normal process access. In some operating systems the PCB is placed at the bottom of the process stack.

## 14. `c006|13|1` — judge: **no** — human: ____

**Sentence:** This prevents race conditions and ensures data consistency [S1]. 7.

**Passage [S1] Lecture slides: OS Functionalities — Slide 3: Process Management:** [course material withheld: not for redistribution]

## 15. `c022|2|2` — judge: **yes** — human: ____

**Sentence:** If the page has not been modified, the dirty bit is clear, and the page can be safely discarded without writing back to disk, improving performance [S2].

**Passage [S2] Wikipedia — Page table — Page table data › Page table entry:** written back to disk, since the page has not changed. However, if the page was written to after it is paged in, its dirty bit will be set, indicating that the page must be written back to the backing store. This strategy requires that the backing store retain a copy of the page after it is paged in to memory. When a dirty bit is not used, the backing store need only be as large as the instantaneous total size of all paged-out pages at any moment. When a dirty bit is used, at all times some pages will exist in both physical memory and the backing store. In operating systems that are not single address space operating systems, address space or process ID information is necessary so the virtual memory management system knows what pages to associate to what process. Two processes may use two identical virtual addresses for different purposes. The page table must supply different virtual memory mappings for the two processes. This can be done by assigning the two processes distinct address map identifiers, or by

## 16. `c042|0|1` — judge: **yes** — human: ____

**Sentence:** The **memory management unit (MMU)** translates virtual addresses to physical addresses using the page table [S1].

**Passage [S1] Wikipedia — Page table:** A page table is a data structure used by a virtual memory system in a computer to store mappings between virtual addresses and physical addresses. Virtual addresses are used by the program executed by the accessing process, while physical addresses are used by the hardware, or more specifically, by the random-access memory (RAM) subsystem. The page table is a key component of virtual address translation that is necessary to access data in memory. The page table is set up by the computer's operating system, and may be read and written during the virtual address translation process by the memory management unit or by low-level system software or firmware.

## 17. `c100|3|3` — judge: **yes** — human: ____

**Sentence:** This decision helps control the degree of multiprogramming and ensures that the system can efficiently manage resources and meet performance goals [S3].

**Passage [S3] Wikipedia — Scheduling (computing) — Types of operating system schedulers › Process scheduler › Long-term scheduling:** The long-term scheduler, or admission scheduler, decides which jobs or processes are to be admitted to the ready queue (in main memory); that is, when an attempt is made to execute a program, its admission to the set of currently executing processes is either authorized or delayed by the long-term scheduler. Thus, this scheduler dictates what processes are to run on a system, the degree of concurrency to be supported at any one time – whether many or few processes are to be executed concurrently, and how the split between I/O-intensive and CPU-intensive processes is to be handled. The long-term scheduler is responsible for controlling the degree of multiprogramming. In general, most processes can be described as either I/O-bound or CPU-bound. An I/O-bound process is one that spends more of its time doing I/O than it spends doing computations. A CPU-bound process, in contrast, generates I/O requests infrequently, using more of its time doing computations. It is important that a long-term scheduler selects a good process mix of I/O-bound and CPU-bound processes. If all processes are I/O-bound, the ready queue

## 18. `c094|3|3` — judge: **yes** — human: ____

**Sentence:** This internal fragmentation is inherent to paging because the allocation unit (the page size) is fixed, regardless of the actual memory needs of the process [S3].

**Passage [S3] Wikipedia — Virtual memory — Segmented virtual memory:** block address only needs to be updated in a single descriptor, since all copies refer to the master descriptor. Paging is not free from fragmentation – the fragmentation is internal to pages (internal fragmentation). If a requested block is smaller than a page, then some space in the page will be wasted. If a block requires larger than a page, a small area in another page is required resulting in large wasted space. The fragmentation thus becomes a problem passed to programmers who may well distort their program to match certain page sizes. With segmentation, the fragmentation is external to segments (external fragmentation) and thus a system problem, which was the aim of virtual memory in the first place, to relieve programmers of such memory considerations. In multi-processing systems, optimal operation of the system depends on the mix of independent processes at any time. Hybrid schemes of segmentation and paging may be used. The Intel 80286 supports a similar segmentation scheme as an option, but it is rarely used. Segmentation and paging can be used together by dividing each segment

## 19. `c090|10|3` — judge: **no** — human: ____

**Sentence:** **Sockets** Sockets can be used for communication between processes, especially if they need to communicate over a network or across different systems. --- ### Summary After `fork()`, the parent and child can exchange data using: - **Pipes** (simple, unidirectional) - **Shared memory** (fast, direct access) - **Message queues** (flexible, supports multiple messages) - **Sockets** (network-capable) > **Important:** While the initial memory is shared, changes made by one process (e.g., writing to a page) trigger a **copy-on-write (COW)** mechanism, meaning the page is only copied when actually modified [S3].

**Passage [S3] Wikipedia — Fork (system call) — Overview:** follow the virtual memory model from SunOS-4.0, copy-on-write semantics are implemented and the physical memory need not be actually copied. Instead, virtual memory pages in both processes may refer to the same pages of physical memory until one of them writes to such a page: then it is copied. This optimization is important in the common case where fork is used in conjunction with exec to execute a new program: typically, the child process performs only a small set of actions before it ceases execution of its program in favour of the program to be started, and it requires very few, if any, of its parent's data structures. When a process calls fork, it is deemed the parent process and the newly created process is its child. After the fork, both processes not only run the same program, but they resume execution as though both had called the system call. They can then inspect the call's return value to determine their status, child or parent, and act accordingly. The history of fork dates back to the 1960s as one of

## 20. `c068|0|2` — judge: **yes** — human: ____

**Sentence:** The semaphore was invented by Dutch computer scientist Edsger Dijkstra in 1962 or 1963 [S1][S2].

**Passage [S2] Wikipedia — Semaphore (programming):** In computer science, a semaphore is a synchronization device used to control access to a common resource by multiple threads or processes in a concurrent system, such as a multitasking operating system. It allows simultaneous access to a critical section by some predetermined number of processes. A useful way to think of a semaphore is as a record of how many units of a particular resource are available, coupled with operations to adjust that record safely (i.e., to avoid race conditions) as units are acquired or become free, and, if necessary, wait until a unit of the resource becomes available. Though semaphores are useful for preventing race conditions, they do not guarantee their absence. Semaphores that allow an arbitrary resource count are called counting semaphores, while semaphores that are restricted to the values 0 and 1 (or locked/unlocked, unavailable/available) are called binary semaphores and are used to implement locks. The semaphore concept was invented by Dutch computer scientist Edsger Dijkstra in 1962 or 1963, when Dijkstra and his team were developing an operating system for the Electrologica X8. That system

## 21. `c056|5|3` — judge: **yes** — human: ____

**Sentence:** You can pass `NULL` as the second argument to `pthread_join` if you don't need the thread's return value. > As noted in [S3], "a multi-threaded web server might create a number of worker threads, and then use the main thread to accept requests and pass them to the workers, indefinitely.

**Passage [S3] OSTEP ch. 26: Concurrency: An Introduction (course reading) — Page 4:** [course material withheld: not for redistribution]

## 22. `c102|0|2` — judge: **yes** — human: ____

**Sentence:** Preemption benefits interactive processes because it allows the operating system to interrupt a running process and allocate CPU time to a higher-priority interactive process, such as a user interface or a response to user input [S2].

**Passage [S2] Wikipedia — Process (computing):** Preemption has an important side effect for interactive processes that are given higher priority with respect to CPU-bound processes; therefore users are immediately assigned computing resources at the simple pressing of a key or when moving a mouse. Furthermore, applications like video and music reproduction are given some kind of real-time priority, preempting any other lower priority process. In time-sharing systems, context switches are performed rapidly, which makes it seem like multiple processes are being executed simultaneously on the same processor. This seemingly-simultaneous execution of multiple processes is called concurrency. For security and reliability, most modern operating systems prevent direct communication between independent processes, providing strictly mediated and controlled inter-process communication.

## 23. `c048|6|2` — judge: **yes** — human: ____

**Sentence:** For example, a page might be marked as read-only, read-write, or executable [S2]. 3.

**Passage [S2] Hailperin, Operating Systems and Middleware — Virtual Memory — Mechanisms for Virtual Memory › Linear Page Tables:** *Linear page tables* are conceptually the simplest form of page table, though as you will see, they turn out to be not quite so simple in practice as they are in concept. A linear page table is an array with one entry per page in the virtual address space. The first entry in the table describes page 0, the next describes page 1, and so forth. To find the information about page $`n`$, one uses the same approach as for any array access: multiply $`n`$ by the size of a page table entry and add that to the base address of the page table. Recall that each page either has a corresponding page frame or has none. Therefore, each page table entry contains, at a minimum, a *valid bit* and a page frame number. If the valid bit is 0, the page has no corresponding frame, and the page frame number is unused. If the valid bit is 1, the page is mapped to the specified page frame. Real page tables often contain other bits indicating permissions (for example, whether

## 24. `c094|1|2` — judge: **yes** — human: ____

**Sentence:** This means that any unused space within a page—called **slack space**—is wasted and cannot be reused by other processes [S2].

**Passage [S2] Wikipedia — Fragmentation (computing) — Types › Memory › Internal fragmentation:** Due to the rules governing memory allocation, more computer memory is sometimes allocated than is needed. When this happens, the excess memory goes to waste. In this scenario, the unusable memory, known as slack space, is contained within an allocated region. This arrangement, termed fixed partitions, suffers from inefficient memory use - any process, no matter how small, occupies an entire partition. This waste is called internal fragmentation. Memory paging creates internal fragmentation because an entire page frame (typically 4–64 KiB) will be allocated whether or not that much storage is needed. malloc and similar allocators tend to provide a degree of alignment, so that memory can only be provided to programs in chunks (usually a multiple of 4 bytes). As a result if a program requests perhaps 29 bytes, it will actually get a chunk of 32 bytes. Internal fragmentation on the allocator level is very difficult to reclaim after it has occurred; usually the best way to remove it is with a design change. For example, in dynamic memory allocation, memory pools drastically cut internal fragmentation by spreading

## 25. `c074|3|2` — judge: **no** — human: ____

**Sentence:** **Stack Pointer (SP)**: This register points to the top of the call stack, which is used to manage function calls and local variables [S2]. 4.

**Passage [S2] OSTEP ch. 4: The Abstraction: The Process (course reading) — Page 2:** [course material withheld: not for redistribution]

## 26. `c044|6|4` — judge: **yes** — human: ____

**Sentence:** A well-designed TLB (with good hit rates) is crucial for performance. > [S4] "A TLB miss can be more expensive than an instruction or data cache miss, due to the need for not just a load from main memory, but a page walk, requiring several memory accesses." --- ### Example (Concrete): Suppose a program accesses virtual address `0x12345678`. - TLB checks: no entry for `0x12345678` → **TLB miss**. - MMU walks page tables:  - Root page directory entry points to a page table.  - Page table entry points to a page frame. - PTE valid bit = 1 → frame number = `0x1000`. - Physical address = `0x1000 + 0x345678 = 0x1345678`. - TLB is updated with `0x12345678 -> 0x1345678`. - CPU now accesses physical memory at `0x1345678`. ---  TLB misses are a normal part of virtual memory management, but minimizing them is key to system performance.

**Passage [S4] Wikipedia — Translation lookaside buffer — Performance implications:** The CPU has to access main memory for an instruction-cache miss, data-cache miss, or TLB miss. The third case (the simplest one) is where the desired information itself actually is in a cache, but the information for virtual-to-physical translation is not in a TLB. These are all slow, due to the need to access a slower level of the memory hierarchy, so a well-functioning TLB is important. Indeed, a TLB miss can be more expensive than an instruction or data cache miss, due to the need for not just a load from main memory, but a page walk, requiring several memory accesses. The flowchart provided explains the working of a TLB. If it is a TLB miss, then the CPU checks the page table for the page table entry. If the present bit is set, then the page is in main memory, and the processor can retrieve the frame number from the page-table entry to form the physical address. The processor also updates the TLB to include the new page-table entry. Finally, if the present bit is not set, then

## 27. `c058|12|1` — judge: **yes** — human: ____

**Sentence:** When the parent runs again, it sleeps forever, which is sad." [S1] ### Correct approach: - Always **acquire the mutex before calling `pthread_cond_wait()`**. - The mutex ensures that:  - The shared state (`done`) is not modified while a thread is waiting.  - The condition variable is used in a safe, synchronized context. ### Summary: If `thr_join` waits on the condition variable without a lock, **a race condition can cause the parent to sleep forever**, because the child's signal may be lost or ignored.

**Passage [S1] OSTEP ch. 30: Condition Variables (course reading) — Page 5:** [course material withheld: not for redistribution]

## 28. `c096|4|1` — judge: **yes** — human: ____

**Sentence:** This is especially true for **spinlocks** used in the **kernel**, such as in the Linux kernel, where operations are very short and the cost of context switching (sleeping and waking up) is high [S1].

**Passage [S1] Lecture slides: Locks — Slide 11: Spinlock vs. sleeping mutex:** [course material withheld: not for redistribution]

## 29. `c008|0|2` — judge: **yes** — human: ____

**Sentence:** In the cooperative approach, the OS regains control of the CPU only when a running process voluntarily yields control, typically by making a system call or performing an illegal operation [S2].

**Passage [S2] OSTEP ch. 6: Mechanism: Limited Direct Execution (course reading) — Page 7:** [course material withheld: not for redistribution]

## 30. `c104|6|3` — judge: **no** — human: ____

**Sentence:** Updating the MMU's page table to point to the new location. - This is **slower** and **involves disk I/O**, which introduces significant latency [S1][S3]. ### Summary | Feature | Minor Page Fault | Major Page Fault | |--------|------------------|------------------| | Page in memory? | Yes (but entry missing) | No | | Disk access? | No | Yes | | Speed | Fast | Slow | | Example | Reusing a shared page from another process | Loading a new part of a program from disk | In short: > A **minor page fault** is a quick fix — the page was just forgotten in the memory map.

**Passage [S3] Wikipedia — Page fault — Types › Major page fault:** This is the mechanism used by an operating system to increase the amount of program memory available on demand. The operating system delays loading parts of the program from disk until the program attempts to use them, at which time page faults are generated. If the page is not loaded in memory at the time of the fault, then the fault is major, or hard. The page fault handler in the OS needs to load the page into working memory, and to do so it must choose a location: either a free page or, when free space is scarce, a page in use by another process. In the latter case the OS needs to write the data in that page out to mass storage (if it has not been written out since it was last modified) and mark that page as not being in memory in its process page table. Once the space has thus been made available, the OS reads the data for the new page into memory, adds an entry for its location in the memory management unit,

## 31. `c006|7|3` — judge: **yes** — human: ____

**Sentence:** This ensures efficient use of the CPU by switching between processes (time-sharing) [S3]. 4.

**Passage [S3] Lecture slides: Introduction to OS (short) — Slide 6: OS manages CPU:** [course material withheld: not for redistribution]

## 32. `c030|1|1` — judge: **yes** — human: ____

**Sentence:** Inside this executable file are instructions that the CPU can understand and execute, along with data that the program uses, all of which is numbered with memory addresses [S1].

**Passage [S1] Lecture slides: Introduction to OS (short) — Slide 3: What happens when you run a  program? (Background):** [course material withheld: not for redistribution]

## 33. `c090|7|1` — judge: **yes** — human: ____

**Sentence:** **Example:** - Use `shmget()` and `shmat()` to create and attach a shared memory segment. - Both parent and child can read/write to the same memory area. ```c #include <sys/shm.h> #include <stdio.h> int main() {     int shmid = shmget(IPC_PRIVATE, 1024, IPC_CREAT | 0666);     char *shared_mem = (char*)shmat(shmid, NULL, 0);     pid_t pid = fork();     if (pid == 0) {         // Child         shared_mem[0] = 'C';         printf("Child wrote 'C'\n");     } else {         // Parent         shared_mem[0] = 'P';         printf("Parent wrote 'P'\n");     }     shmdt(shared_mem);     shmctl(shmid, IPC_RMID, NULL);     return 0; } ``` > **Note:** Shared memory requires careful management to avoid race conditions [S1]. --- ### 3.

**Passage [S1] Wikipedia — Fork (system call) — Technical › Communication:** The child process starts off with a copy of its parent's file descriptors. For inter-process communication with data exchange and synchronization between parent and child processes, pipes can be used. The parent process will often create one or several pipes, and then after forking the processes will close the ends of the pipes that they do not need. To share the same variable between the parent and child processes, memory mapping or shared memory must be used.

## 34. `c064|6|2` — judge: **no** — human: ____

**Sentence:** This is known as a **race condition**. ### Example from the Notes In [S2], it says: *"A process can test-and-set on a location in shared memory, and since the operation is atomic, only one process can set the flag at a time."* This shows that a simple flag (without atomicity) does not work — only an **atomic operation** (like test-and-set) ensures mutual exclusion. ### Solution To fix this, you need an **atomic operation** (like test-and-set or compare-and-swap) that ensures only one process can set the flag at a time.

**Passage [S2] Wikipedia — Mutual exclusion — Enforcing mutual exclusion › Hardware solutions:** On uni-processor systems, the simplest solution to achieve mutual exclusion is to disable interrupts during a process's critical section. This will prevent any interrupt service routines from running (effectively preventing a process from being preempted). Although this solution is effective, it leads to many problems. If a critical section is long, then the system clock will drift every time a critical section is executed because the timer interrupt is no longer serviced, so tracking time is impossible during the critical section. Also, if a process halts during its critical section, control will never be returned to another process, effectively halting the entire system. A more elegant method for achieving mutual exclusion is the busy-wait. Busy-waiting is effective for both uniprocessor and multiprocessor systems. The use of shared memory and an atomic test-and-set instruction provide the mutual exclusion. A process can test-and-set on a location in shared memory, and since the operation is atomic, only one process can set the flag at a time. Any process that is unsuccessful in setting the flag can either go on to do other tasks

## 35. `c074|6|3` — judge: **yes** — human: ____

**Sentence:** **Process Privileges**: These define the permissions and access rights of the process to system resources [S3]. 7.

**Passage [S3] Wikipedia — Process control block — Structure:** the amount of time elapsed since the process gained control of the CPU or since it was suspended. Also, in case of a suspended process, event identification data must be recorded for the event the process is waiting for; Process structuring information – the process's children id's, or the id's of other processes related to the current one in some functional way, which may be represented as a queue, a ring or other data structures; Interprocess communication information – flags, signals and messages associated with the communication among independent processes; Process Privileges – allowed/disallowed access to system resources; Process State – new, ready, running, waiting, dead; Process Number (PID) – unique identification number for each process (also known as Process ID); Program Counter (PC) – a pointer to the address of the next instruction to be executed for this process; CPU Registers – register set where process needs to be stored for execution for running state; CPU Scheduling Information – information scheduling CPU time; Memory Management Information – page table, memory limits, segment table; Accounting Information – amount of CPU

## 36. `c038|3|1` — judge: **yes** — human: ____

**Sentence:** **Privilege level** - It switches the CPU from **kernel mode** back to **user mode**, ensuring that the user process resumes execution with the appropriate privilege level [S1]. 3.

**Passage [S1] Lecture slides: Process Execution Mechanism — Slide 8: Return from trap:** [course material withheld: not for redistribution]

## 37. `c080|5|2` — judge: **yes** — human: ____

**Sentence:** **Demand Paging and Memory Management**:    - Virtual addressing allows the kernel to manage memory efficiently using **demand paging**—only loading pages into physical RAM when needed.    - If an application tries to access a page not currently in memory, the kernel handles the request by loading it from disk, but it still ensures that the application cannot access kernel pages directly [S2].

**Passage [S2] Wikipedia — Kernel (operating system) — Memory management:** like a hard drive, to store what would otherwise have to remain in main memory (RAM). As a result, operating systems can allow programs to use more memory than the system has physically available. When a program needs data that is not currently in RAM, the CPU signals to the kernel that this has happened, and the kernel responds by writing the contents of an inactive memory block to disk (if necessary) and replacing it with the data requested by the program. The program can then be resumed from the point where it was stopped. This scheme is generally known as demand paging. Virtual addressing also allows creation of virtual partitions of memory in two disjoint areas, one being reserved for the kernel (kernel space) and the other for the applications (user space). The applications are not permitted by the processor to address kernel memory, thus preventing an application from damaging the running kernel. This fundamental partition of memory space has contributed much to the current designs of actual general-purpose kernels and is almost universal in such systems, although some

## 38. `c048|11|2` — judge: **yes** — human: ____

**Sentence:** **Protection Bits**: These can include additional bits for security and access control, such as whether the page is accessible only by certain processes or users [S2]. 6.

**Passage [S2] Hailperin, Operating Systems and Middleware — Virtual Memory — Mechanisms for Virtual Memory › Linear Page Tables:** *Linear page tables* are conceptually the simplest form of page table, though as you will see, they turn out to be not quite so simple in practice as they are in concept. A linear page table is an array with one entry per page in the virtual address space. The first entry in the table describes page 0, the next describes page 1, and so forth. To find the information about page $`n`$, one uses the same approach as for any array access: multiply $`n`$ by the size of a page table entry and add that to the base address of the page table. Recall that each page either has a corresponding page frame or has none. Therefore, each page table entry contains, at a minimum, a *valid bit* and a page frame number. If the valid bit is 0, the page has no corresponding frame, and the page frame number is unused. If the valid bit is 1, the page is mapped to the specified page frame. Real page tables often contain other bits indicating permissions (for example, whether

## 39. `c094|5|2` — judge: **yes** — human: ____

**Sentence:** In summary: > Paging causes internal fragmentation because it allocates entire pages even when only a portion of the page is needed, leading to wasted memory within each page [S2][S3].

**Passage [S2] Wikipedia — Fragmentation (computing) — Types › Memory › Internal fragmentation:** Due to the rules governing memory allocation, more computer memory is sometimes allocated than is needed. When this happens, the excess memory goes to waste. In this scenario, the unusable memory, known as slack space, is contained within an allocated region. This arrangement, termed fixed partitions, suffers from inefficient memory use - any process, no matter how small, occupies an entire partition. This waste is called internal fragmentation. Memory paging creates internal fragmentation because an entire page frame (typically 4–64 KiB) will be allocated whether or not that much storage is needed. malloc and similar allocators tend to provide a degree of alignment, so that memory can only be provided to programs in chunks (usually a multiple of 4 bytes). As a result if a program requests perhaps 29 bytes, it will actually get a chunk of 32 bytes. Internal fragmentation on the allocator level is very difficult to reclaim after it has occurred; usually the best way to remove it is with a design change. For example, in dynamic memory allocation, memory pools drastically cut internal fragmentation by spreading

## 40. `c120|8|1` — judge: **yes** — human: ____

**Sentence:** If the TLB is full, a **replacement algorithm** (like LRU or FIFO) is used to evict an existing entry [S1]. 5.

**Passage [S1] Wikipedia — Translation lookaside buffer — Overview:** each virtual memory reference, the hardware checks the TLB to see whether the page number is held therein. If yes, it is a TLB hit, and the translation is made. The frame number is returned and is used to access the memory. If the page number is not in the TLB, the page table must be checked. Depending on the CPU, this can be done automatically in hardware or using an interrupt to the operating system. When the frame number is obtained, it can be used to access the memory. In addition, we add the page number and frame number to the TLB, so that they will be found quickly on the next reference. If the TLB is already full, a suitable block must be selected for replacement. There are different replacement methods like least recently used (LRU), first in, first out (FIFO) etc.; see the address translation section in the cache article for more details about virtual addressing as it pertains to caches and TLBs.
