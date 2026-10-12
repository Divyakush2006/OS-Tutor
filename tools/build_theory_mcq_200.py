"""Expand the OS theory MCQ from 70 to 200 items (G2 evaluation target; G3 item set).

    python tools/build_theory_mcq_200.py   (writes data/eval_theory/os_theory_mcq_200.jsonl)

The first 70 items are data/eval_theory/os_theory_mcq.jsonl unchanged (ids t001-t070),
so every earlier number stays comparable. The 130 new items (t071-t200) were written
from general OS knowledge, NOT from the RAG corpus, to cover topics
the 70 miss or touch once. Status: "unreviewed" until checked by hand (brief, G3);
any item rejected is removed, not edited after results are seen.
"""
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "eval_theory" / "os_theory_mcq.jsonl"
OUT = ROOT / "data" / "eval_theory" / "os_theory_mcq_200.jsonl"

# (question, [A, B, C, D], index of the correct choice, topic)
NEW = [
    # ---- OS structure, modes, interrupts, system calls
    ("Which of these is an example of a trap rather than a hardware interrupt?", ["a timer interrupt", "a keyboard key press", "a divide-by-zero exception", "a disk controller finishing a transfer"], 2, "structure"),
    ("The mode bit in the CPU is used to:", ["select between user mode and kernel mode", "choose the page size", "enable the cache", "select big-endian or little-endian byte order"], 0, "structure"),
    ("Why must the instruction that loads the timer be privileged?", ["timers are slow to program", "a user program could otherwise prevent the OS from regaining control", "only the compiler may set it", "it changes the page table"], 1, "structure"),
    ("Which program first runs when a computer is switched on and loads the operating system kernel?", ["the shell", "the init process", "the bootstrap loader (bootloader)", "the device driver"], 2, "structure"),
    ("In a monolithic kernel, device drivers and file systems typically run:", ["as separate user-space servers", "in kernel space, in the same address space as the kernel", "inside the bootloader", "only on a coprocessor"], 1, "structure"),
    ("A loadable kernel module allows:", ["adding functionality such as a driver to a running kernel without rebooting", "running user programs in kernel mode", "replacing the bootloader at run time", "compiling programs faster"], 0, "structure"),
    ("Which category does the open() system call belong to?", ["process control", "file management", "communication", "information maintenance"], 1, "syscalls"),
    ("How are parameters most commonly passed to a system call on modern hardware?", ["in CPU registers, or a pointer in a register to a block in memory", "through a disk file", "by environment variables only", "through the keyboard buffer"], 0, "syscalls"),
    ("printf() in C is best described as:", ["a system call", "a library function that may eventually invoke the write() system call", "a hardware instruction", "a kernel thread"], 1, "syscalls"),
    ("An interrupt vector table maps:", ["virtual pages to frames", "interrupt numbers to the addresses of their handler routines", "process ids to PCBs", "files to inodes"], 1, "structure"),
    ("Polling a device, compared with interrupt-driven I/O, mainly:", ["wastes CPU time busy-checking the device status", "needs more hardware", "cannot work with disks", "requires DMA"], 0, "io"),
    # ---- processes
    ("Which scheduler decides which ready process gets the CPU next?", ["the long-term (job) scheduler", "the short-term (CPU) scheduler", "the medium-term scheduler", "the I/O scheduler"], 1, "process"),
    ("The medium-term scheduler is mainly concerned with:", ["choosing the next process every few milliseconds", "swapping processes out of and back into memory to control the degree of multiprogramming", "booting the system", "scheduling disk requests"], 1, "process"),
    ("The degree of multiprogramming is controlled mainly by:", ["the long-term scheduler", "the dispatcher", "the timer", "the MMU"], 0, "process"),
    ("Dispatch latency is:", ["the time a disk takes to seek", "the time the dispatcher takes to stop one process and start another", "the length of a time quantum", "the time to fork a process"], 1, "process"),
    ("An orphan process is one whose:", ["parent has terminated while it is still running", "exit status has not been collected", "code has been replaced by exec()", "threads have all blocked"], 0, "process"),
    ("A ready process can move directly to which state?", ["waiting (blocked)", "running", "new", "terminated by itself"], 1, "process"),
    ("Which transition happens when a running process's time slice expires under round robin?", ["running to waiting", "running to ready", "waiting to ready", "ready to terminated"], 1, "process"),
    ("Which transition happens when the disk read a process requested completes?", ["waiting to ready", "waiting to running", "ready to running", "running to ready"], 0, "process"),
    # ---- IPC
    ("An ordinary (anonymous) pipe in UNIX:", ["can be used only between related processes, such as parent and child", "can be used between any two processes on the internet", "is bidirectional by default and persists after the processes exit", "is a kind of semaphore"], 0, "ipc"),
    ("A named pipe (FIFO) differs from an anonymous pipe because it:", ["has a name in the file system, so unrelated processes can open it", "is faster", "can only carry integers", "is implemented in hardware"], 0, "ipc"),
    ("Compared with message passing, shared memory IPC is usually:", ["faster for large data, because the kernel is not involved in every transfer", "slower because every byte is copied by the kernel", "impossible on multicore machines", "only usable between threads"], 0, "ipc"),
    ("In blocking (synchronous) send:", ["the sender continues immediately", "the sender waits until the message is received", "the message is discarded", "the receiver is killed"], 1, "ipc"),
    ("A signal in UNIX is:", ["a software notification delivered to a process that an event occurred", "a hardware wire on the motherboard", "a kind of file", "a scheduling queue"], 0, "ipc"),
    ("Which signal is sent to a process when the user presses Ctrl+C in the terminal?", ["SIGKILL", "SIGINT", "SIGSEGV", "SIGCHLD"], 1, "ipc"),
    ("A parent process is notified that a child has terminated by which signal?", ["SIGCHLD", "SIGHUP", "SIGALRM", "SIGSTOP"], 0, "ipc"),
    # ---- threads
    ("In the one-to-one threading model:", ["each user thread maps to its own kernel thread", "all user threads share one kernel thread", "threads cannot block", "only one thread may exist"], 0, "threads"),
    ("A key disadvantage of the one-to-one model is that:", ["one blocking call blocks the whole process", "creating a user thread requires creating a kernel thread, which costs more", "threads cannot run in parallel", "it cannot use multicore CPUs"], 1, "threads"),
    ("Which of these is private to each thread rather than shared by all threads of a process?", ["the heap", "global variables", "the stack", "open files"], 2, "threads"),
    ("pthread_join() is used to:", ["create a new thread", "wait for a specific thread to terminate", "lock a mutex", "send a signal to a thread"], 1, "threads"),
    ("A thread pool is useful because it:", ["avoids the cost of creating a thread for every request and bounds the number of threads", "gives each thread its own address space", "removes the need for locks", "makes threads run in kernel mode"], 0, "threads"),
    # ---- scheduling
    ("SRTF is the preemptive version of:", ["FCFS", "SJF", "Round Robin", "Priority with aging"], 1, "scheduling"),
    ("Which criterion is most important for an interactive time-sharing system?", ["throughput", "response time", "CPU utilisation", "turnaround time of batch jobs"], 1, "scheduling"),
    ("An I/O-bound process typically has:", ["many short CPU bursts", "a few very long CPU bursts", "no CPU bursts", "only kernel-mode bursts"], 0, "scheduling"),
    ("Why is pure SJF hard to implement in a CPU scheduler?", ["it needs the length of the next CPU burst, which is not known in advance", "it requires a large quantum", "it cannot be preemptive", "it starves short jobs"], 0, "scheduling"),
    ("The length of the next CPU burst is often predicted using:", ["an exponential average of previous burst lengths", "the process id", "the size of the executable", "the number of open files"], 0, "scheduling"),
    ("With exponential averaging, tau(n+1) = alpha * t(n) + (1 - alpha) * tau(n). If alpha = 0:", ["only the most recent burst matters", "recent history has no effect on the prediction", "the prediction is always zero", "the prediction alternates"], 1, "scheduling"),
    ("If the Round Robin quantum is very small compared with the context-switch time:", ["the CPU spends a large share of its time switching", "Round Robin becomes FCFS", "throughput improves greatly", "starvation becomes certain"], 0, "scheduling"),
    ("Rate-monotonic scheduling assigns priorities:", ["by deadline, earliest first, dynamically", "statically, with shorter periods getting higher priority", "randomly", "by arrival order"], 1, "scheduling"),
    ("Earliest-deadline-first (EDF) scheduling assigns priorities:", ["statically by period", "dynamically, giving the highest priority to the task whose deadline is nearest", "by process id", "by memory size"], 1, "scheduling"),
    ("In a hard real-time system, missing a deadline is:", ["acceptable occasionally", "a system failure", "only a performance issue", "corrected by the next quantum"], 1, "scheduling"),
    ("Processor affinity in multiprocessor scheduling means:", ["keeping a process on the same CPU to benefit from its warm cache", "running all processes on CPU 0", "giving each process all CPUs", "disabling interrupts on one CPU"], 0, "scheduling"),
    ("Push migration in multiprocessor load balancing means:", ["an idle processor pulls a task from a busy one", "a periodic task moves processes from overloaded to less busy processors", "processes are never moved", "the disk pushes data to memory"], 1, "scheduling"),
    ("Linux's Completely Fair Scheduler picks next the task with the:", ["highest static priority", "smallest virtual runtime", "largest memory footprint", "earliest arrival time"], 1, "scheduling"),
    ("In lottery scheduling, a process holding 30 of 120 tickets receives on average what share of the CPU?", ["30%", "25%", "12%", "4%"], 1, "scheduling"),
    ("Multilevel (non-feedback) queue scheduling differs from MLFQ because:", ["processes are permanently assigned to one queue", "it has only one queue", "it uses aging between queues", "it is always preemptive"], 0, "scheduling"),
    ("Starvation in priority scheduling is caused by:", ["low-priority processes never being selected while higher-priority ones keep arriving", "too many context switches", "a deadlock", "a short quantum"], 0, "scheduling"),
    # ---- synchronisation
    ("Compare-and-swap (CAS) atomically:", ["sets a value only if the current value equals an expected value, returning the old value", "swaps two registers", "compares two strings", "disables interrupts"], 0, "sync"),
    ("A ticket lock improves on a basic test-and-set spinlock by:", ["guaranteeing first-come, first-served order, so no thread starves", "never spinning", "working without atomic instructions", "allowing two holders at once"], 0, "sync"),
    ("A binary semaphore initialised to 1 can be used as:", ["a mutual-exclusion lock", "a counter of free buffer slots", "a barrier for 10 threads", "a timer"], 0, "sync"),
    ("In the bounded-buffer problem with semaphores empty, full and mutex, 'empty' is initialised to:", ["0", "1", "the number of buffer slots", "the number of producers"], 2, "sync"),
    ("In the bounded-buffer solution, 'full' is initialised to:", ["0", "1", "the buffer size", "-1"], 0, "sync"),
    ("If a producer did wait(mutex) before wait(empty) when the buffer is full:", ["it would work faster", "it could deadlock, holding the mutex while waiting for a slot", "consumers would starve", "nothing changes"], 1, "sync"),
    ("A monitor guarantees that:", ["only one thread is active inside the monitor at a time", "threads never wait", "deadlock is impossible", "all threads run in kernel mode"], 0, "sync"),
    ("Under Mesa semantics, after a thread is signalled on a condition variable:", ["it runs immediately and the condition is guaranteed true", "it is moved to the ready queue and must recheck the condition when it runs", "the signaller blocks forever", "the condition variable is destroyed"], 1, "sync"),
    ("In the first readers-writers problem (readers preference), what can starve?", ["readers", "writers", "neither", "the scheduler"], 1, "sync"),
    ("A reader-writer lock allows:", ["many readers at once, or a single writer", "many writers at once", "only one reader at a time", "readers and writers together"], 0, "sync"),
    ("In the dining philosophers problem, if every philosopher picks up the left fork first at the same time:", ["they all eat", "deadlock can occur", "only one starves", "the forks are duplicated"], 1, "sync"),
    ("A barrier synchronisation primitive:", ["makes threads wait until all of a group have reached the same point", "gives one thread priority", "protects a single variable", "prevents page faults"], 0, "sync"),
    ("Disabling interrupts as a way to implement mutual exclusion does NOT work well on:", ["a single-processor system", "a multiprocessor system", "a system with a timer", "a real-time system with one core"], 1, "sync"),
    ("A lock-free data structure guarantees that:", ["no thread ever waits for any other", "at least one thread makes progress in a finite number of steps", "there are no atomic instructions", "only one thread can use it"], 1, "sync"),
    ("The 'lost wakeup' problem with condition variables is avoided by:", ["holding the associated mutex while checking the condition and calling wait", "never using signal", "using a larger stack", "disabling the scheduler"], 0, "sync"),
    # ---- deadlock
    ("Deadlock detection with a single instance of each resource type uses:", ["a wait-for graph and checks for a cycle", "the Banker's safety algorithm only", "page tables", "a timer"], 0, "deadlock"),
    ("Requiring a process to request all its resources before it starts executing attacks which condition?", ["mutual exclusion", "hold and wait", "no preemption", "circular wait"], 1, "deadlock"),
    ("Which deadlock condition generally cannot be removed for resources like printers?", ["mutual exclusion", "hold and wait", "circular wait", "no preemption"], 0, "deadlock"),
    ("In the Banker's algorithm, Need is computed as:", ["Max - Allocation", "Available - Allocation", "Max + Allocation", "Allocation - Available"], 0, "deadlock"),
    ("A safe sequence in the Banker's algorithm is:", ["an order in which every process can obtain its remaining need and finish", "the order in which processes arrived", "a list of deadlocked processes", "the order of resource types"], 0, "deadlock"),
    ("Which recovery method from deadlock involves choosing a victim and rolling it back?", ["resource preemption", "spooling", "aging", "paging"], 0, "deadlock"),
    ("Ignoring deadlocks entirely (the ostrich approach) is used by many general-purpose OSes because:", ["deadlocks are rare and prevention or avoidance is costly", "deadlocks are impossible on modern hardware", "the Banker's algorithm is built into CPUs", "users never share resources"], 0, "deadlock"),
    ("Three processes each need at most 3 instances of a resource. The minimum number of instances that guarantees no deadlock is:", ["6", "7", "8", "9"], 1, "deadlock"),
    # ---- memory: contiguous, allocation
    ("Base and limit registers are used to:", ["protect memory by restricting a process to its own address range", "speed up the cache", "store the page table", "hold system call numbers"], 0, "memory"),
    ("Execution-time address binding is required when:", ["a process can be moved in memory during its execution", "addresses are known at compile time", "the program has no variables", "there is no MMU"], 0, "memory"),
    ("Worst-fit allocation chooses:", ["the largest free hole", "the first hole that fits", "the smallest hole that fits", "a random hole"], 0, "memory"),
    ("A buddy-system allocator rounds requests up to:", ["a power of two", "a multiple of 1000 bytes", "the page size only", "the nearest prime"], 0, "memory"),
    ("A slab allocator is efficient for kernel objects because:", ["it keeps caches of pre-initialised objects of the same size, reducing fragmentation", "it allocates whole disks", "it never frees memory", "it uses the buddy system for every byte"], 0, "memory"),
    # ---- paging details
    ("A logical address of 16 bits with a 1 KB page size has how many bits for the page number?", ["4", "6", "10", "16"], 1, "paging"),
    ("Page size 4 KB, logical address 20,000 (decimal). What is the page number?", ["3", "4", "5", "6"], 1, "paging"),
    ("Page size 4 KB, logical address 20,000. What is the offset?", ["3,616", "4,000", "16,384", "0"], 0, "paging"),
    ("TLB reach is defined as:", ["number of TLB entries times the page size", "the time to search the TLB", "the number of page tables", "the size of the L1 cache"], 0, "paging"),
    ("Address-space identifiers (ASIDs) in TLB entries allow:", ["entries of several processes to coexist in the TLB, avoiding a flush on every context switch", "larger pages", "the OS to skip page tables", "faster disk access"], 0, "paging"),
    ("TLB hit ratio 90%, memory access 100 ns, TLB lookup negligible, single-level page table. The effective access time is:", ["100 ns", "110 ns", "190 ns", "200 ns"], 1, "paging"),
    ("Using huge pages (for example 2 MB) mainly helps by:", ["increasing TLB reach and reducing TLB misses", "eliminating page faults", "removing internal fragmentation", "making page tables larger"], 0, "paging"),
    ("A hashed page table is commonly used for:", ["address spaces larger than 32 bits, where a linear table would be huge", "systems without virtual memory", "only kernel memory", "disk scheduling"], 0, "paging"),
    ("The valid-invalid bit in a page-table entry indicates whether:", ["the page belongs to the process's legal address space (and is mapped)", "the page has been modified", "the page is shared", "the page is in the TLB"], 0, "paging"),
    ("Shared pages are possible with paging mainly for:", ["reentrant (read-only) code used by several processes", "each process's stack", "the heap", "private data"], 0, "paging"),
    ("Segmentation with paging translates an address by:", ["first selecting a segment, then paging within that segment", "paging only", "segmenting only", "using the disk directly"], 0, "paging"),
    # ---- virtual memory & replacement
    ("The clock (second-chance) algorithm approximates:", ["OPT", "LRU", "FIFO with no change", "random replacement"], 1, "replacement"),
    ("In the second-chance algorithm, a page whose reference bit is 1:", ["is replaced immediately", "has its bit cleared and is skipped this time", "is written to disk", "is locked forever"], 1, "replacement"),
    ("The enhanced second-chance algorithm prefers to replace a page that is:", ["referenced and modified", "not referenced and not modified", "referenced but not modified", "not referenced but modified"], 1, "replacement"),
    ("Reference string 1,2,3,4,1,2,5,1,2,3,4,5 with 3 frames under FIFO gives how many page faults?", ["8", "9", "10", "12"], 1, "replacement"),
    ("The same string 1,2,3,4,1,2,5,1,2,3,4,5 with 4 frames under FIFO gives how many faults?", ["8", "9", "10", "11"], 2, "replacement"),
    ("Global page replacement means a process may:", ["take a frame from another process", "only replace its own frames", "never cause a page fault", "use only kernel frames"], 0, "replacement"),
    ("Local replacement's main advantage is that:", ["a process's paging behaviour is not affected by other processes", "it always gives fewer faults", "it needs no page table", "it removes thrashing entirely"], 0, "replacement"),
    ("Page-fault frequency (PFF) control gives a process more frames when:", ["its fault rate rises above an upper bound", "its fault rate falls to zero", "it is idle", "it finishes"], 0, "replacement"),
    ("Pre-paging tries to:", ["bring in pages a process is likely to need before they are referenced", "page out every page at once", "avoid using the TLB", "increase the page size"], 0, "replacement"),
    ("A memory-mapped file lets a process:", ["access a file's contents through ordinary memory reads and writes", "skip the file system permissions", "store files in the CPU cache only", "run a file as a thread"], 0, "vm"),
    ("Locality of reference is the reason that:", ["demand paging and caching work well in practice", "deadlocks happen", "disks need scheduling", "processes starve"], 0, "vm"),
    # ---- storage
    ("Disk access time is the sum of:", ["seek time, rotational latency and transfer time", "only seek time", "page fault time and TLB time", "CPU time and I/O time"], 0, "storage"),
    ("Why does disk scheduling matter little for SSDs?", ["SSDs have no moving head, so access time does not depend on position", "SSDs are always slower", "SSDs cannot be scheduled", "SSDs use tape"], 0, "storage"),
    ("Wear levelling in an SSD:", ["spreads writes across flash blocks so no block wears out early", "makes the disk spin evenly", "defragments files", "encrypts data"], 0, "storage"),
    ("The TRIM command tells an SSD:", ["which blocks no longer hold valid data, so they can be erased in advance", "to spin faster", "to format itself", "to stop wear levelling"], 0, "storage"),
    ("RAID 1 provides:", ["mirroring: every block is written to two disks", "striping without redundancy", "dual parity", "compression"], 0, "storage"),
    ("RAID 6 can survive the failure of:", ["one disk only", "any two disks", "every disk", "no disks"], 1, "storage"),
    ("Head at 50, requests 82, 170, 43, 140, 24, 16, 190. Under SSTF, the first request served is:", ["43", "82", "24", "16"], 0, "storage"),
    ("A disk with 4 ms average seek and 7200 RPM has average rotational latency of about:", ["4.17 ms", "8.33 ms", "2 ms", "7.2 ms"], 0, "storage"),
    # ---- file systems
    ("In a two-level directory structure:", ["each user has their own directory under a master directory", "all files are in one directory", "directories form a general graph", "files have no names"], 0, "fs"),
    ("A tree-structured directory with an acyclic-graph extension allows:", ["sharing a file or directory through links without cycles", "only one user", "no subdirectories", "cycles for faster search"], 0, "fs"),
    ("The FAT file system finds the next block of a file by:", ["following the chain of entries in the file allocation table", "reading an inode's indirect blocks", "computing it from the file name", "a B-tree of extents"], 0, "fs"),
    ("An inode with 12 direct pointers, 4 KB blocks and 4-byte block pointers: how much data can the single-indirect block address?", ["4 MB", "48 KB", "4 KB", "1 GB"], 0, "fs"),
    ("A symbolic (soft) link:", ["stores the path of the target and breaks if the target is deleted", "shares the target's inode", "cannot point to a directory", "keeps the file alive after deletion"], 0, "fs"),
    ("When the last hard link to a file is removed and no process has it open:", ["the inode and data blocks are freed", "the file becomes a symbolic link", "the directory is deleted", "nothing happens"], 0, "fs"),
    ("Mounting a file system means:", ["attaching it at a directory (the mount point) in the existing directory tree", "formatting the disk", "copying all files to memory", "deleting the old file system"], 0, "fs"),
    ("A virtual file system (VFS) layer lets the kernel:", ["support many different file-system types behind one interface", "run without disks", "avoid caching", "use only FAT"], 0, "fs"),
    ("Extents (as in ext4) describe a file's storage as:", ["runs of contiguous blocks given by a start block and a length", "a linked list of single blocks", "a hash of the file name", "a bitmap of the whole disk"], 0, "fs"),
    ("A log-structured file system writes:", ["all updates sequentially to the end of a log", "each block in place", "only metadata", "only to tape"], 0, "fs"),
    ("fsck is used to:", ["check and repair file-system consistency after a crash", "format a disk", "schedule disk requests", "compress files"], 0, "fs"),
    ("UNIX permission bits rwxr-x--- give the group:", ["read and execute", "read, write and execute", "no access", "write only"], 0, "fs"),
    ("A bit-vector free-space map with 1 bit per 4 KB block for a 1 TB disk needs about:", ["32 MB", "256 MB", "1 GB", "4 KB"], 0, "fs"),
    # ---- I/O
    ("Double buffering in I/O is used to:", ["let the device fill one buffer while the process uses the other", "store data twice for safety", "halve memory use", "avoid interrupts entirely"], 0, "io"),
    ("Memory-mapped I/O means:", ["device registers appear at memory addresses and are accessed with ordinary load/store instructions", "files are cached in memory", "the disk holds the page table", "I/O happens only through DMA"], 0, "io"),
    ("In DMA, the CPU is interrupted:", ["once, when the whole block transfer completes", "for every byte", "never", "only on errors"], 0, "io"),
    # ---- protection, security, virtualisation
    ("An access matrix row represents a domain; its columns represent:", ["objects", "users only", "CPU registers", "time slices"], 0, "protection"),
    ("A capability list is associated with:", ["a domain (subject), listing the objects it may access and how", "an object, listing who may access it", "the disk", "the TLB"], 0, "protection"),
    ("An access control list (ACL) is associated with:", ["an object, listing which subjects may access it and how", "a domain", "a CPU core", "a page frame"], 0, "protection"),
    ("The principle of least privilege says a program should:", ["have only the privileges it needs to do its job", "run as administrator", "share all files", "disable logging"], 0, "protection"),
    ("A stack buffer overflow attack typically works by:", ["overwriting a return address so control jumps to attacker-chosen code", "filling the disk", "guessing passwords", "flooding the network"], 0, "protection"),
    ("Address space layout randomisation (ASLR) makes attacks harder by:", ["placing code, stack and heap at unpredictable addresses", "encrypting memory", "removing the stack", "disabling paging"], 0, "protection"),
    ("A type 1 (bare-metal) hypervisor:", ["runs directly on the hardware, below the guest operating systems", "runs as an application on a host OS", "is a kind of compiler", "cannot run more than one guest"], 0, "virtualisation"),
    ("Trap-and-emulate virtualisation works because:", ["privileged instructions executed by a guest trap to the hypervisor, which emulates them", "guests run in kernel mode on the real CPU", "the hypervisor recompiles every program", "guests never use privileged instructions"], 0, "virtualisation"),
    ("Containers differ from virtual machines in that containers:", ["share the host kernel instead of running their own", "always run a separate kernel", "cannot isolate processes", "need a type 1 hypervisor"], 0, "virtualisation"),
]


def main() -> None:
    old = [json.loads(l) for l in open(SRC, encoding="utf-8")]
    if len(old) != 70:
        raise SystemExit(f"expected the 70-item set, found {len(old)}")
    if len(NEW) != 130:
        raise SystemExit(f"expected 130 new items, have {len(NEW)}")
    for q, ch, a, t in NEW:
        assert len(ch) == 4 and 0 <= a < 4 and len(set(ch)) == 4, q
    seen = {o["question"].lower() for o in old}
    for q, *_ in NEW:
        if q.lower() in seen:
            raise SystemExit(f"duplicate of an existing item: {q}")
        seen.add(q.lower())
    rows = [dict(id=f"t{n + 1:03d}", **o, source="os_theory_mcq.jsonl", status="as before")
            for n, o in enumerate(old)]
    # the options were written with the answer first more often than not; shuffle each
    # item's options with a fixed seed so the answer position carries no signal
    rng = random.Random(200)
    for n, (q, ch, a, t) in enumerate(NEW):
        order = list(range(4))
        rng.shuffle(order)
        rows.append(dict(id=f"t{71 + n:03d}", question=q, choices=[ch[i] for i in order],
                         answer=order.index(a), subject="os_theory", topic=t,
                         source="tools/build_theory_mcq_200.py", status="unreviewed"))
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    from collections import Counter
    print(f"{len(rows)} items -> {OUT}")
    print("answer position balance (new):", dict(Counter("ABCD"[r["answer"]] for r in rows[70:])))


if __name__ == "__main__":
    main()
