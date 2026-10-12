"""Hand-written, fact-checked explanations of the most-confused OS topics (v3.0).

Self-distilled answers (tools/generate_theory_sdft.py) carry the base model's
breadth; these carry precision on exactly the points students and LLMs get wrong.
Each answer states the correct fact, the tempting wrong version and why it is
wrong, and a concrete example - the misconception-repair format that tutoring
research finds most effective. Every claim was checked against Silberschatz
(10th ed.), Tanenbaum (MOS 4th ed.) and OSTEP; numbers in examples are computed.
"""

GOLD = [
    ("Does LRU suffer from Belady's anomaly?",
     """No. **LRU never suffers from Belady's anomaly; FIFO can.**

**Why.** LRU is a *stack algorithm*: at every point in the reference string, the set of pages held with *n* frames is a subset of the set held with *n + 1* frames (the n most recently used pages are always among the n + 1 most recently used). So adding a frame can only turn misses into hits, never the reverse. OPT is also a stack algorithm.

FIFO is not: its contents depend on load order, so the page set with 4 frames need not contain the set with 3 frames.

**Example (FIFO).** Reference string 1 2 3 4 1 2 5 1 2 3 4 5:
- 3 frames: **9** faults
- 4 frames: **10** faults, more frames but more faults. That is Belady's anomaly.

With LRU the same string gives 10 faults with 3 frames and 8 with 4 frames, so the fault count goes down as expected."""),
    ("Is an unsafe state the same as a deadlock?",
     """No. **Every deadlocked state is unsafe, but an unsafe state is not necessarily deadlocked.**

- **Safe state:** there is at least one order (a safe sequence) in which every process can obtain its *maximum* remaining need and finish. Deadlock is impossible if the OS stays in safe states.
- **Unsafe state:** no such order is guaranteed. A deadlock *can* happen if processes actually request their maximum needs, but they may not: a process might release resources or finish without asking for its full maximum.

The Banker's algorithm is conservative: it refuses any request that would lead to an unsafe state, even though that state might never have deadlocked.

**Example (Silberschatz).** 12 tape drives. P0 holds 5 (max 10), P1 holds 2 (max 4), P2 holds 2 (max 9), so 3 are free. This is safe: <P1, P0, P2> works. Now suppose P2 is granted 1 more drive, leaving 2 free. P1 can still finish (needs 2), which frees 4 drives, but then P0 needs 5 and P2 needs 6, and neither fits. The state is **unsafe**, yet nothing is deadlocked at that moment: if P0 or P2 released drives instead of requesting more, everyone could finish. The Banker's algorithm would refuse P2's request."""),
    ("If a resource-allocation graph has a cycle, is there a deadlock?",
     """It depends on how many instances each resource has.

- **Every resource type has a single instance:** a cycle is **necessary and sufficient**. A cycle means deadlock.
- **Some resource types have several instances:** a cycle is **necessary but not sufficient**. A cycle means a deadlock is *possible*, not certain.

**Example with multiple instances.** R1 has 2 instances and R2 has 2. P1 holds one R1 and requests R2; P2 holds one R2 and requests R1; P3 holds the other R1 and P4 holds the other R2. The graph has the cycle P1 → R2 → P2 → R1 → P1. But P3 and P4 are not waiting for anything: when P4 finishes and releases R2, P1 gets it and finishes, which frees R1 for P2. So there is no deadlock.

To decide for multi-instance resources you need a detection algorithm (like the Banker's safety check, using current requests instead of maximum needs)."""),
    ("Does segmentation cause internal or external fragmentation?",
     """**Segmentation causes external fragmentation, not internal fragmentation.**

- Each segment is allocated exactly as large as it needs (a 7,300-byte data segment gets 7,300 bytes), so there is no wasted space *inside* an allocation, and therefore no internal fragmentation.
- Segments have *variable sizes*. As they are loaded and freed, memory becomes a patchwork of variable-sized holes. Eventually there can be enough total free memory for a new segment but no single hole large enough. That is **external fragmentation**, the same problem as variable-partition allocation.

**Contrast with paging:** paging uses fixed-size frames, so any free frame fits any page, which eliminates external fragmentation. It causes *internal* fragmentation in the last page of a process (on average half a page).

That is why systems combine them (segmentation with paging, as in x86): segments give a logical structure and protection, and paging each segment removes the external fragmentation."""),
    ("Why is SJF optimal, and why can't it be implemented exactly?",
     """**Why optimal.** For a set of jobs available together, running the shortest first minimises the *average waiting time*. Moving a short job ahead of a long one reduces the short job's wait by the long job's burst and increases the long job's wait by the short job's burst, a net decrease. Any order other than shortest-first can be improved by such a swap.

**Example:** bursts 7, 3, 9, 5 (all at t = 0). SJF order 3, 5, 7, 9 gives waits 0, 3, 8, 15, so the average is **6.5**. FCFS in the given order gives 0, 7, 10, 19, an average of 9.

**Why not implementable exactly.** The scheduler cannot know the length of the *next* CPU burst in advance. Real systems **predict** it with exponential averaging:

τ(n+1) = α · t(n) + (1 − α) · τ(n)

where t(n) is the last actual burst and α (often 0.5) weights recent history.

**Caveats:** SJF can starve long jobs (fixed by aging), and it is only optimal among non-preemptive schedules. Its preemptive form, SRTF, is optimal when jobs arrive over time."""),
    ("What is the difference between SJF and SRTF?",
     """Both favour short jobs; the difference is **preemption**.

| | SJF (non-preemptive) | SRTF (preemptive SJF) |
|---|---|---|
| When it decides | only when the CPU becomes free | at every **arrival** and every completion |
| Compares | burst lengths of ready jobs | **remaining** time of ready jobs, including the running one |
| Running job | always runs to completion | is preempted if a new job has a shorter remaining time |

**Example:** P1 (arrives 0, burst 7), P2 (2, 4), P3 (4, 1), P4 (5, 4).
- **SRTF:** at t = 2, P2 (4) < P1's remaining 5, so P1 is preempted. Order P1[0-2] P2[2-4] P3[4-5] P2[5-7] P4[7-11] P1[11-16]; average waiting = **3**.
- **SJF:** P1 runs 0-7 uninterrupted, then P3, P2, P4; average waiting = **4**.

SRTF gives the lower average waiting time but more context switches, and it can starve long jobs."""),
    ("What happens to Round Robin when the time quantum is very large or very small?",
     """- **Very large quantum** (larger than every burst): no process is ever preempted, so Round Robin degenerates to **FCFS**, with FCFS's convoy effect and poor response time.
- **Very small quantum:** response time improves in principle, but the CPU spends a growing fraction of its time **context switching**. With a quantum of 1 ms and a 0.1 ms switch, about 9% of the CPU is overhead; if the quantum approaches the switch cost, almost no useful work gets done.

**Rule of thumb:** choose the quantum so that about 80% of CPU bursts finish within one quantum. It should be large compared with the context-switch time (typical quanta are 10-100 ms, and switches are microseconds).

Also note: Round Robin's average **turnaround** time does not necessarily improve as the quantum shrinks, and it is usually worse than SJF's. Round Robin's advantage is **response time and fairness**, not turnaround."""),
    ("What is the difference between a mutex and a binary semaphore?",
     """They look similar (both hold values 0/1) but differ in **ownership and intent**.

| | Mutex | Binary semaphore |
|---|---|---|
| Purpose | mutual exclusion (locking) | signalling / synchronisation between threads |
| Ownership | **owned**: only the thread that locked it may unlock it | **no owner**: any thread may signal (V) |
| Priority inheritance | usually supported | usually not |
| Typical use | protect a critical section | "thread A tells thread B that data is ready" |

**Why ownership matters.** Because a mutex knows its owner, the OS can detect errors (unlocking a mutex you do not hold), support recursive locking, and apply priority inheritance to fix priority inversion. A semaphore cannot, because anyone may call signal().

**Example of signalling (a semaphore, not a mutex):** a producer thread calls `sem_post(&ready)` after filling a buffer, and a consumer blocked in `sem_wait(&ready)` wakes up. The producer never "locked" anything, so a mutex would be the wrong tool."""),
    ("What does fork() return, and how many processes do n calls create?",
     """`fork()` creates a new process that is a copy of the caller, and it **returns twice**:
- in the **parent**: the child's PID (a positive number);
- in the **child**: **0**;
- on failure: −1 in the parent, and no child is created.

That is how code distinguishes the two:

```c
pid_t pid = fork();
if (pid == 0)      { /* child */ }
else if (pid > 0)  { /* parent: pid is the child's PID */ }
else               { /* error */ }
```

**Counting.** Every existing process executes each subsequent `fork()`, so each call **doubles** the number of processes. After *n* sequential calls there are **2ⁿ** processes in total, of which **2ⁿ − 1** are new children.

Example: three `fork()` calls followed by `printf("hi")` gives 1 → 2 → 4 → 8 processes, so "hi" is printed **8** times."""),
    ("What is thrashing and how can it be prevented?",
     """**Thrashing** is when a system spends more time servicing page faults than executing instructions. CPU utilisation collapses while the paging disk is saturated.

**Cause.** The processes' *working sets* (the pages each is actively using) together exceed physical memory. Each process steals frames from the others, every process faults constantly, and processes queue for the paging device. A classic trap: the OS sees low CPU utilisation, **raises** the degree of multiprogramming by admitting more processes, and makes thrashing worse.

**Prevention:**
1. **Working-set model:** track each process's working set (pages referenced in the last Δ references). If the sum exceeds the available frames, **suspend (swap out) a process** instead of admitting new ones.
2. **Page-fault frequency (PFF):** set upper and lower bounds on each process's fault rate. Above the upper bound, give it more frames; below the lower bound, take frames away. If no frames are free, suspend a process.
3. **Local replacement:** a thrashing process then cannot steal frames from others (this limits the damage but does not cure it).
4. **More memory**, or fewer concurrent processes.

**Example:** 10 processes each needing 128 MB of working set on a machine with 1 GB of free frames need 1.25 GB, so they thrash. Suspending two of them brings the demand to 1 GB, and the fault rate drops back to normal."""),
    ("What are the four necessary conditions for deadlock?",
     """All four must hold **at the same time** for a deadlock to occur (the Coffman conditions):

1. **Mutual exclusion:** at least one resource is non-shareable. *Example:* a printer can print only one job at a time.
2. **Hold and wait:** a process holds at least one resource while waiting for another. *Example:* P1 holds the scanner and waits for the printer.
3. **No preemption:** a resource cannot be forcibly taken away; it is released only voluntarily. *Example:* the OS cannot take the printer mid-job and give it to someone else.
4. **Circular wait:** there is a cycle P1 → P2 → … → Pn → P1 in which each process waits for a resource held by the next. *Example:* P1 holds the scanner and wants the printer, while P2 holds the printer and wants the scanner.

**Prevention breaks one condition:**
- mutual exclusion: make resources shareable (rarely possible);
- hold and wait: request everything at once (poor utilisation, possible starvation);
- no preemption: take resources from a waiting process;
- circular wait: impose a global order on resource types and always request them in increasing order (the most practical)."""),
    ("How do the Banker's safety algorithm and the resource-request algorithm differ?",
     """They are two parts of the Banker's algorithm.

**Safety algorithm** answers: *is the current state safe?*
1. Work = Available; Finish[i] = false for all i.
2. Find a process i with Finish[i] = false and Need[i] ≤ Work (compare **component by component**).
3. If found: Work = Work + Allocation[i], set Finish[i] = true, and repeat from step 2.
4. If every Finish[i] is true, the state is **safe**, and the order found is a safe sequence.

**Resource-request algorithm** answers: *can Request_i be granted right now?*
1. If Request_i > Need_i: **error**, because the process exceeded its declared maximum.
2. If Request_i > Available: the process **must wait**, because the resources are not free.
3. *Pretend* to grant: Available −= Request_i, Allocation_i += Request_i, Need_i −= Request_i. Run the **safety algorithm** on this new state. If it is safe, grant; if not, restore the old state and make the process wait.

**Common mistake:** skipping test 3. A request can pass tests 1 and 2 and still be denied, because granting it would make the system unsafe."""),
    ("What is the difference between internal and external fragmentation?",
     """- **Internal fragmentation:** wasted space **inside** an allocated block, because the block is larger than requested. *Example:* with 4 KB pages, a 10 KB process gets 3 pages (12 KB), so 2 KB in its last page is wasted.
- **External fragmentation:** enough total free memory exists, but it is split into **non-contiguous holes**, none large enough for a request. *Example:* free holes of 100 KB, 50 KB and 80 KB (230 KB free) cannot hold a 150 KB process under contiguous allocation.

| Scheme | Internal | External |
|---|---|---|
| Fixed partitions | yes | no |
| Variable partitions / segmentation | no | **yes** |
| Paging | **yes** (last page) | no |

**Fixes:** external fragmentation is reduced by **compaction** (moving allocations together, which is expensive and needs relocation at run time) or avoided by paging. Internal fragmentation is reduced by smaller pages or allocation units, at the cost of bigger page tables."""),
    ("How does a TLB affect effective memory access time?",
     """Without a TLB, every memory reference with a single-level page table needs **two** memory accesses: one for the page-table entry and one for the data. The TLB caches recent translations to skip the first.

**Effective access time** with TLB lookup time t, memory access time m and hit ratio h:

EAT = h × (t + m) + (1 − h) × (t + 2m)

(With a k-level page table, a miss costs t + (k + 1) × m.)

**Example:** t = 10 ns, m = 80 ns, h = 0.90:
- hit: 10 + 80 = 90 ns
- miss: 10 + 80 + 80 = 170 ns
- EAT = 0.9 × 90 + 0.1 × 170 = 81 + 17 = **98 ns**

A 98% hit ratio gives 0.98 × 90 + 0.02 × 170 = 88.2 + 3.4 = 91.6 ns, only about 15% slower than a single memory access. This is why TLBs make paging practical: programs have strong locality, so hit ratios are typically above 99%."""),
    ("What happens when a page fault occurs?",
     """1. The CPU references a page whose page-table entry is marked **invalid**. The MMU raises a **trap** to the OS.
2. The OS checks whether the reference is legal (inside the process's address space). If it is not, the process is terminated (a segmentation fault).
3. If it is legal but the page is not in memory, the OS finds a **free frame**. If none is free, it runs the page-replacement algorithm to choose a victim, and writes the victim to disk first if its **dirty bit** is set.
4. The OS schedules a **disk read** of the needed page into the frame. The faulting process is blocked, and the CPU runs another process meanwhile.
5. When the I/O completes (an interrupt), the OS updates the page table (frame number, valid bit set).
6. The faulting instruction is **restarted** from the beginning, and now it succeeds.

**Cost:** a memory access is about 100 ns, while a fault serviced from an SSD or disk takes about 0.1-10 ms. That is why the fault rate must be tiny: with ma = 100 ns and a 5 ms fault time, even 1 fault per 10,000 accesses gives EAT ≈ 600 ns, a **6× slowdown**."""),
    ("Why do we need multi-level page tables?",
     """A single-level page table must have one entry for **every page in the virtual address space**, whether used or not.

*Example:* 32-bit addresses with 4 KB pages give 2^20 pages. With 4-byte entries that is **4 MB of page table per process**, allocated contiguously. With 48-bit addresses it would be 2^36 entries × 8 bytes = **512 GB**, which is impossible.

**Multi-level paging** pages the page table itself. The virtual page number is split into indexes; the top-level table points to second-level tables, and so on. **Second-level tables that cover unused regions are never allocated**, so a sparse address space (a program using a little code, heap and stack) needs only a few small tables.

*Example (x86 32-bit):* 10-bit outer index, 10-bit inner index and 12-bit offset. Each table has 1,024 entries of 4 bytes, which is exactly one 4 KB page.

**Cost:** each TLB miss now needs one memory access **per level** (x86-64 uses 4 levels, or 5 with LA57). This is why the TLB matters even more for multi-level tables.

The number of levels needed is ceil((VA bits − offset bits) / log2(page size / PTE size)): for 48-bit addresses, 4 KB pages and 8-byte PTEs, that is ceil(36 / 9) = **4**."""),
    ("What is the difference between a hard link and a symbolic link?",
     """| | Hard link | Symbolic (soft) link |
|---|---|---|
| What it is | another directory entry for the **same inode** | a small file containing a **path** to another file |
| Deleting the original name | file survives (data is freed only when the link count reaches 0) | link becomes **dangling** |
| Across file systems | no (inode numbers are per file system) | yes |
| To directories | not allowed for users (it could create cycles) | allowed |
| `ls -li` | same inode number | different inode, type `l` |

**Example:**
```
echo data > a
ln a b        # hard link: a and b share one inode, link count 2
ln -s a c     # symlink: c contains the text "a"
rm a          # b still shows "data"; c is now dangling
```

A hard link is not a copy: writing through `b` changes the data seen through every name, because there is only one file."""),
    ("What is the difference between a process and a thread?",
     """A **process** is a program in execution with its **own address space** and resources. A **thread** is a unit of execution **within** a process; threads of the same process share its resources.

| Shared by threads of a process | Private to each thread |
|---|---|
| code, global data, heap | stack |
| open files, sockets | registers, program counter |
| address space, PID | thread ID, scheduling state |

**Consequences:**
- **Creation and switching** are cheaper for threads: switching between threads of the same process does not change the address space, so there is no page-table switch or TLB flush.
- **Communication:** threads communicate through shared memory directly (with synchronisation); processes need IPC (pipes, sockets, shared-memory segments).
- **Isolation:** a crash (for example a segmentation fault) in one thread kills the whole process; a crash in one process does not affect other processes.

**Example:** a web browser often runs each tab as a separate **process** for isolation, while a single tab uses several **threads** for rendering, networking and JavaScript."""),
    ("What is the difference between SCAN, C-SCAN, LOOK and C-LOOK?",
     """All four sweep the disk arm instead of jumping between the nearest requests; they differ in **where the arm turns** and whether it **serves on the way back**.

| | Turns at | Serves on return? |
|---|---|---|
| **SCAN** (elevator) | the **disk edge** (cylinder 0 or the maximum) | yes |
| **C-SCAN** | the edge, then **jumps** to the other edge | **no**, it only serves in one direction |
| **LOOK** | the **last request** in that direction | yes |
| **C-LOOK** | the last request, then jumps to the **farthest request** on the other side | no |

**Example:** head 100, moving toward 0, queue 23 89 132 42 187 on disk 0-199:
- SCAN: 100 → 89 → 42 → 23 → **0** → 132 → 187, so the total is 100 + 187 = **287**.
- LOOK: turns at 23 instead of 0, so the total is 77 + 164 = **241**.

**Why the circular variants:** with SCAN, requests just behind the arm wait almost two full sweeps, while those at the middle wait less. C-SCAN treats the cylinders as a circle, so waiting times are more **uniform**.

**Convention note:** whether the return jump in C-SCAN / C-LOOK counts toward head movement varies between textbooks, so always state which one you use."""),
    ("What is priority inversion and how is it solved?",
     """**Priority inversion:** a high-priority task H waits for a resource held by a low-priority task L, and a **medium-priority** task M (which does not need the resource) preempts L. H is now effectively blocked by M, a lower-priority task, for an unbounded time.

**Real example: Mars Pathfinder (1997).** A high-priority bus-management task waited on a mutex held by a low-priority meteorological task. Medium-priority communication tasks kept preempting the low-priority one, the high-priority task missed its deadline, and a watchdog kept **resetting the spacecraft**.

**Solutions:**
- **Priority inheritance:** while L holds a resource that H needs, L temporarily runs at H's priority, so M cannot preempt it. When L releases the resource, it drops back to its own priority. (Pathfinder was fixed by enabling this option on the mutex, remotely.)
- **Priority ceiling:** each resource has a ceiling equal to the highest priority of any task that uses it; a task holding it runs at that ceiling. This also prevents some deadlocks.

This is also one reason a **mutex** (which has an owner) is preferred over a semaphore for locking: the OS needs to know whose priority to raise."""),
    ("How does the Linux Completely Fair Scheduler (CFS) work, and what replaced it?",
     """**CFS** (Linux 2.6.23-6.5) models an "ideal" CPU that runs every task simultaneously at an equal share.
- Each task has a **vruntime**: the CPU time it has received, scaled by its weight (derived from its nice value). Higher-priority tasks accumulate vruntime more slowly.
- Runnable tasks are kept in a **red-black tree** ordered by vruntime, and the scheduler always runs the task with the **smallest vruntime** (the one furthest behind its fair share). Picking it is O(1) with a cached leftmost node; insertion is O(log n).
- There is no fixed quantum: time slices come from a target latency divided among the runnable tasks, with a minimum granularity.

**Replacement: EEVDF (Linux 6.6, 2023).** *Earliest Eligible Virtual Deadline First* keeps the weighted-fairness idea but adds **lag** (how much service a task is owed) and a **virtual deadline** per request. Among eligible tasks (those with non-negative lag), it runs the one with the earliest virtual deadline. This gives better latency control: a task can ask for shorter slices to get lower latency without getting a larger share of the CPU. It also replaced many of CFS's heuristics."""),
    ("What is the difference between paging and swapping?",
     """- **Swapping** (in the classic sense) moves an **entire process** between memory and a backing store. The whole address space leaves memory, typically to free memory for other processes; this is medium-term scheduling.
- **Paging** moves **individual pages**. Only the pages actually needed are brought in (demand paging), and only chosen victim pages are written out.

Modern systems page; whole-process swapping is rare. Confusingly, Linux calls its paging area **swap space** and says pages are "swapped out", but it moves pages, not whole processes.

**Why paging won:** moving a 2 GB process to disk to make room for one page is enormously wasteful. Paging moves 4 KB at a time and exploits locality: a process can run with only its working set resident.

Mobile operating systems (iOS, Android) typically do **not** page out to flash at all (flash has limited write endurance). Under memory pressure they ask apps to release memory, or they terminate them."""),
    ("What is a race condition, and how is it prevented?",
     """A **race condition** occurs when the result of concurrent execution depends on the **timing** (interleaving) of accesses to shared data.

**Example:** two threads each execute `count++` 1,000,000 times on a shared counter. `count++` is really three machine steps: *load, add, store*. Interleaving can lose updates:

```
T1: load count (5)
T2: load count (5)
T1: add, store 6
T2: add, store 6     <- one increment lost
```

The final value is often well below 2,000,000, and it differs from run to run.

**Prevention:** make the **critical section** (the code that touches shared data) execute atomically with respect to other threads:
- a **mutex** around the increment;
- an **atomic** operation (`atomic_fetch_add`, or CPU instructions such as `lock xadd`);
- avoiding sharing (per-thread counters summed at the end).

A correct solution must provide **mutual exclusion**, **progress** and **bounded waiting**."""),
    ("What is the difference between response time, waiting time and turnaround time?",
     """For a process with arrival time A, burst time B, first time on the CPU S, and completion time C:

- **Turnaround time = C − A**: the total time from arrival to completion.
- **Waiting time = Turnaround − B = C − A − B**: the total time spent in the ready queue (for a CPU-only job).
- **Response time = S − A**: the time until the process *first* gets the CPU.

**Example (Round Robin, q = 3):** P1 (arrives 0, burst 10), P2 (0, 4), P3 (0, 6). Schedule: P1[0-3] P2[3-6] P3[6-9] P1[9-12] P2[12-13] P3[13-16] P1[16-20].
- P1: turnaround 20, waiting 20 − 10 = 10, response 0
- P2: turnaround 13, waiting 9, response 3
- P3: turnaround 16, waiting 10, response 6

The average waiting time is 29/3 ≈ **9.67**, while the average response time is only 3.

**Which matters when:** batch systems care about turnaround; interactive systems care about **response time**. That is why Round Robin, with poor turnaround but good response, is used for time-sharing."""),
    ("What is copy-on-write, and why does it make fork() fast?",
     """With **copy-on-write (COW)**, `fork()` does **not** copy the parent's memory. Instead:

1. The child gets a copy of the parent's **page tables**, pointing to the **same physical frames**.
2. All those pages are marked **read-only** in both processes (and flagged COW).
3. When either process **writes** to a page, the write traps (a protection fault). The kernel then copies just **that one page**, gives the writer its own copy with write permission, and restarts the instruction.

**Why it matters:** the most common pattern is `fork()` followed immediately by `exec()`, which throws away the entire address space. Without COW, the kernel would copy gigabytes of memory only to discard it. With COW, fork costs little more than copying page tables, and only pages that are actually modified are ever duplicated.

**Example:** a 1 GB process forks, and the child calls `exec("ls")`. With COW, essentially no data pages are copied. Without it, 1 GB would be copied first."""),
    ("What is the working-set model?",
     """The **working set** of a process, W(t, Δ), is the set of distinct pages it referenced in the most recent **Δ** memory references (the working-set window). By locality, this approximates the pages it needs right now.

**Use in frame allocation:**
- Each process should get at least |W|, its working-set size, in frames.
- Total demand D = Σ |Wᵢ|. If D exceeds the available frames, **thrashing** will occur, so the OS **suspends a process** (swapping it out) instead of letting everyone thrash, and resumes it when memory is available.

**Choosing Δ:** too small and it misses the current locality; too large and it overlaps several localities (in the limit, the whole program).

**Implementation:** tracking exact references is too expensive, so it is approximated with a timer interrupt plus the **reference bits**. At each interval the bits are copied (and cleared), and a page referenced in the last few intervals counts as part of the working set.

**Example:** with Δ = 10 and recent references 2 6 1 5 7 7 7 7 5 1, the working set is {1, 2, 5, 6, 7}, so |W| = 5."""),
    ("What is Amdahl's law?",
     """Amdahl's law bounds the **speedup** of a program from parallelising it. If a fraction **S** of the work is inherently serial and the rest is spread over **N** cores:

speedup ≤ 1 / (S + (1 − S) / N)

As N → ∞ the limit is **1 / S**: the serial part alone determines the ceiling.

**Examples:**
- S = 25%, N = 2: 1 / (0.25 + 0.375) = **1.6×**
- S = 25%, N = 4: 1 / (0.25 + 0.1875) ≈ **2.29×**
- S = 25%, N → ∞: at most **4×**
- S = 5%: at most **20×**, even with thousands of cores.

**Lesson for OS and application design:** shrinking serial sections (lock contention, single-threaded phases) matters more than adding cores. Gustafson's law gives the more optimistic view that larger problems usually have proportionally smaller serial fractions."""),
    ("What does the dirty bit do?",
     """The **dirty (modify) bit** in a page-table entry is set by hardware whenever the page is **written**.

**Why it matters for page replacement:** when a page is evicted,
- if its dirty bit is **0**, the copy on disk is still correct, so the frame can be reused immediately with **one** disk I/O (reading in the new page);
- if it is **1**, the page must first be **written back** to disk, so the eviction costs **two** I/Os.

So replacement algorithms prefer clean pages. The **enhanced second-chance** algorithm ranks pages by (reference bit, dirty bit):
1. (0, 0): not recently used, clean. This is the best victim.
2. (0, 1): not recently used, dirty. It needs a write-back.
3. (1, 0): recently used, clean.
4. (1, 1): recently used and dirty. This is the worst victim.

The dirty bit also makes **page buffering** and background write-back effective: the OS can flush dirty pages when the disk is idle, so that later evictions find clean pages."""),
    ("What is the critical-section problem and what must a solution guarantee?",
     """The **critical section** is the part of a program that accesses shared data. The problem is to design a protocol (an *entry section* and an *exit section*) so that cooperating processes can use shared data safely.

A correct solution must guarantee all three:

1. **Mutual exclusion:** at most one process is in its critical section at any time.
2. **Progress:** if no process is in the critical section and some want to enter, the choice of who enters next cannot be postponed indefinitely, and only processes trying to enter take part in the decision.
3. **Bounded waiting:** there is a limit on how many times other processes can enter before a waiting process gets its turn (no starvation).

**Common confusion:** "progress" is not "no deadlock among the waiting processes" in general. It specifically rules out a *free* critical section staying unused because of the protocol.

**Examples:** Peterson's algorithm satisfies all three for two processes (assuming sequentially consistent memory). A simple spinlock using test-and-set gives mutual exclusion and progress, but **not** bounded waiting unless a queue or ticket scheme is added."""),
    ("What is the difference between preemptive and non-preemptive scheduling?",
     """- **Non-preemptive (cooperative):** once a process has the CPU, it keeps it until it **terminates or blocks** (for I/O, or by waiting on an event). The scheduler runs only at those points. *Examples:* FCFS, SJF, non-preemptive priority, HRRN.
- **Preemptive:** the OS can **take the CPU away** from a running process: when its quantum expires (timer interrupt), or when a higher-priority or shorter job arrives. *Examples:* Round Robin, SRTF, preemptive priority, and all modern general-purpose kernels.

**Trade-offs:**
| | Non-preemptive | Preemptive |
|---|---|---|
| Response time | poor (one long job delays everyone) | good |
| Overhead | fewer context switches | more context switches |
| Races on shared data | fewer | kernel data must be protected against preemption |
| Robustness | a looping process can hog the CPU | the OS stays in control |

**Scheduling decisions happen when a process:** (1) switches from running to waiting, (2) switches from running to ready (preemption), (3) switches from waiting to ready, or (4) terminates. A scheduler that decides only at (1) and (4) is non-preemptive."""),
    ("How does an inode store a file's data blocks, and what is the maximum file size?",
     """A classic UNIX inode has **12 direct pointers**, **1 single indirect**, **1 double indirect** and **1 triple indirect** pointer.

With block size **B** and pointer size **p**, each indirect block holds **k = B / p** pointers:
- direct: 12 blocks
- single indirect: k blocks
- double indirect: k² blocks
- triple indirect: k³ blocks

**Example:** B = 4 KB, p = 4 bytes, so k = 1,024.
- direct: 12 × 4 KB = 48 KB
- single: 1,024 × 4 KB = 4 MB
- double: 1,024² × 4 KB = 4 GB
- triple: 1,024³ × 4 KB = 4 TB
- **maximum ≈ 4 TB + 4 GB + 4 MB + 48 KB**

**Why this design:** most files are small, so they fit in the direct blocks with no extra disk reads. Large files pay one to three extra block reads to reach their data. Access is still random (indexed), and there is no external fragmentation.

(In practice other limits, such as 32-bit block numbers or file-size fields, can cap the size below this. ext4 replaced indirect blocks with **extents**.)"""),
    ("What is a monitor and how do condition variables work?",
     """A **monitor** is a language-level synchronisation construct: an abstract data type whose procedures are guaranteed to execute with **mutual exclusion**, because only one thread can be active inside the monitor at a time. The compiler or runtime inserts the locking, so programmers cannot forget it.

To **wait for a condition** inside a monitor, you use **condition variables**:
- `x.wait()`: the caller **releases the monitor** and sleeps on x, atomically.
- `x.signal()`: wakes **one** thread waiting on x. If none is waiting, it has **no effect** (unlike a semaphore's V, which is remembered).

**Signal semantics:**
- **Hoare (signal-and-wait):** the signalled thread runs immediately, so the condition is guaranteed true when it resumes.
- **Mesa (signal-and-continue):** the signaller keeps running, and the woken thread competes for the lock later, by which time the condition may be false again. Used by Java, pthreads and most real systems.

So with Mesa semantics, always wait in a **while** loop:
```
while (count == 0)
    notEmpty.wait();
```
This also handles **spurious wakeups**."""),
    ("What is demand paging and what is the page-fault rate's effect on performance?",
     """**Demand paging** loads a page into memory **only when it is first referenced**, instead of loading the whole program at start. Pages never touched are never loaded, which saves memory and I/O and allows programs larger than physical memory.

**Effective access time** with page-fault probability p, memory access time ma and page-fault service time f:

EAT = (1 − p) × ma + p × f

**Example:** ma = 100 ns and f = 5 ms = 5,000,000 ns.
- p = 1/10,000: EAT = 0.9999 × 100 + 0.0001 × 5,000,000 = 99.99 + 500 = **599.99 ns**, a 6× slowdown.
- To keep the slowdown under 10% (EAT < 110 ns): 10 > p × (5,000,000 − 100), so p < **0.000002**, fewer than one fault per 500,000 accesses.

This works in practice because of **locality of reference**: a process uses a small working set of pages for long stretches."""),
    ("What is spooling, and how is it different from buffering and caching?",
     """- **Buffering:** temporary storage that smooths a speed or size mismatch between a producer and a consumer during a transfer. *Example:* a network card's receive buffer, or double buffering for disk I/O.
- **Caching:** keeping a **copy** of data in faster storage because it is likely to be reused. The original stays elsewhere. *Example:* the page cache holding recently read file blocks.
- **Spooling** (Simultaneous Peripheral Operations On-Line): **queueing whole jobs** for a device that can serve only **one job at a time** and cannot interleave jobs. *Example:* a printer. Each application's print output is written to a spool file on disk, and a daemon sends the files to the printer one at a time, so applications do not wait for the printer and their output never interleaves.

Key difference: a buffer holds data *in transit*; a cache holds a *copy* for reuse; a spool holds *complete jobs* waiting for an exclusive device."""),
]
