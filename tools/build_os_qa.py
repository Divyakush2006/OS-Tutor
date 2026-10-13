"""Corpus-independent OS short-answer set (G2 data selection and accuracy; D-009).

    python tools/build_os_qa.py        (writes data/eval_rag/os_short_answer.jsonl)

Each item is a question with a short, distinctive answer and its accepted aliases. The
answer never appears in the question. Two uses:
  * retrieval answer recall@k - does any of the top-k passages contain an alias?  This is
    the standard open-domain QA retrieval measure (as in DPR): it needs no passage labels,
    so it compares DIFFERENT corpora, and different sources within one, on equal terms.
  * end-to-end accuracy - does the tutor's short answer contain an alias, with and
    without retrieval?
Written from general OS knowledge, not from any corpus, to
cover the syllabus evenly. Items alternate dev / test. Status: unreviewed.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "eval_rag" / "os_short_answer.jsonl"

# (topic, question, [answer aliases])
QA = [
    # structure, kernel, system calls, interrupts
    ("structure", "What is the name of the CPU mode in which privileged instructions may be executed?", ["kernel mode", "supervisor mode", "privileged mode", "ring 0"]),
    ("structure", "What kind of kernel moves most services such as drivers and file systems into user-space server processes?", ["microkernel"]),
    ("structure", "What is the small program that loads the operating system kernel into memory at power-on called?", ["bootloader", "boot loader", "bootstrap"]),
    ("structure", "Which instruction-level mechanism does a user program use to transfer control into the kernel for a service?", ["trap", "syscall", "software interrupt", "int 0x80"]),
    ("structure", "What table maps interrupt numbers to the addresses of their handler routines?", ["interrupt vector", "interrupt descriptor table", "IDT"]),
    ("structure", "What is the name for a kernel extension that can be loaded into a running Linux kernel without rebooting?", ["loadable kernel module", "kernel module", "LKM"]),
    ("structure", "Which UNIX system call creates a new process by duplicating the calling process?", ["fork"]),
    ("structure", "Which family of UNIX system calls replaces the current process image with a new program?", ["exec"]),
    ("structure", "Which system call does a parent use to collect the exit status of a terminated child?", ["wait", "waitpid"]),
    ("structure", "Which standard defines a portable operating-system API that Linux and macOS largely follow?", ["POSIX"]),
    ("structure", "What periodic hardware interrupt guarantees the operating system regains control even if a program never makes a system call?", ["timer", "clock interrupt"]),
    # processes
    ("process", "What data structure does the kernel keep for each process, holding its state, registers and scheduling information?", ["process control block", "PCB", "task_struct"]),
    ("process", "What is a terminated process whose exit status has not yet been collected by its parent called?", ["zombie"]),
    ("process", "Which process in UNIX traditionally adopts orphaned processes?", ["init", "PID 1", "systemd"]),
    ("process", "What is the act of saving one process's CPU state and restoring another's called?", ["context switch"]),
    ("process", "Apart from ready and running, what state is a process in until its disk read completes?", ["blocked", "waiting", "sleeping"]),
    ("process", "Which scheduler decides which jobs are admitted into the ready queue and so controls the degree of multiprogramming?", ["long-term scheduler", "long term scheduler", "job scheduler", "admission scheduler"]),
    ("process", "What value does fork() return in the child process?", ["0", "zero"]),
    ("process", "What is the name of the optimisation that lets parent and child share pages after fork until one of them writes?", ["copy-on-write", "copy on write", "COW"]),
    # threads
    ("threads", "In which threading model does every user-level thread map to its own kernel thread?", ["one-to-one", "one to one", "1:1"]),
    ("threads", "Which pthreads function waits for a specific thread to finish?", ["pthread_join"]),
    ("threads", "Which register, private to each thread, points to the top of that thread's own call stack?", ["stack pointer", "SP", "RSP", "ESP"]),
    ("threads", "What is a pool of pre-created worker threads that take tasks from a queue called?", ["thread pool"]),
    ("threads", "What is a lightweight, cooperatively scheduled user-level thread sometimes called on Windows?", ["fiber", "fibre"]),
    # IPC
    ("ipc", "Which shell operator connects the standard output of one command to the standard input of the next?", ["pipe"]),
    ("ipc", "What is a pipe that has a name in the file system, so unrelated processes can use it, called?", ["named pipe", "FIFO"]),
    ("ipc", "Which signal cannot be caught or ignored and always terminates the process?", ["SIGKILL"]),
    ("ipc", "Which signal does the kernel send to a parent when one of its children terminates?", ["SIGCHLD"]),
    ("ipc", "Which signal is sent to a foreground process when the user presses Ctrl+C?", ["SIGINT"]),
    ("ipc", "Which signal is delivered to a process that accesses memory it is not allowed to access?", ["SIGSEGV", "segmentation fault"]),
    ("ipc", "Which IPC mechanism lets processes on different machines communicate through an endpoint?", ["socket"]),
    ("ipc", "Which System V call allocates a shared memory segment?", ["shmget"]),
    # scheduling
    ("scheduling", "Which scheduling algorithm minimises average waiting time when all burst lengths are known in advance?", ["shortest job first", "SJF", "shortest-job-first", "shortest job next"]),
    ("scheduling", "What is the preemptive version of shortest job first called?", ["shortest remaining time", "SRTF", "shortest-remaining-time"]),
    ("scheduling", "What is the slowdown caused when short processes queue behind one long CPU-bound process under FCFS called?", ["convoy effect"]),
    ("scheduling", "Which technique raises the priority of a process the longer it waits, to prevent starvation?", ["aging", "ageing"]),
    ("scheduling", "What is the fixed amount of CPU time each process gets per turn in round-robin scheduling called?", ["time quantum", "quantum", "time slice"]),
    ("scheduling", "Which scheduler moves jobs between priority queues based on how they used their previous time slice?", ["multilevel feedback queue", "MLFQ", "multi-level feedback queue"]),
    ("scheduling", "Who developed the multilevel feedback queue scheduler and received the Turing Award?", ["Corbató", "Corbato"]),
    ("scheduling", "Which scheduler, introduced in Linux 2.6.23, picks the task with the smallest virtual runtime?", ["Completely Fair Scheduler", "CFS"]),
    ("scheduling", "What data structure does Linux's Completely Fair Scheduler use to order runnable tasks?", ["red-black tree", "red–black tree", "red black tree", "rbtree"]),
    ("scheduling", "Which proportional-share scheduler gives processes tickets and draws a random winner?", ["lottery scheduling", "lottery"]),
    ("scheduling", "Which static-priority real-time policy gives higher priority to tasks with shorter periods?", ["rate-monotonic", "rate monotonic", "RMS"]),
    ("scheduling", "Which dynamic real-time policy always runs the task whose deadline is nearest?", ["earliest deadline first", "EDF", "earliest-deadline-first"]),
    ("scheduling", "What is the tendency to keep a process on the CPU whose cache it has warmed called?", ["processor affinity", "cpu affinity", "cache affinity"]),
    ("scheduling", "Which scheduling algorithm uses the ratio (waiting time + service time) / service time?", ["highest response ratio next", "HRRN"]),
    ("scheduling", "What is the component that gives control of the CPU to the process chosen by the short-term scheduler called?", ["dispatcher"]),
    # synchronisation
    ("sync", "What is the section of code that accesses shared data and must not be executed by two threads at once called?", ["critical section", "critical region"]),
    ("sync", "Who devised the first correct software solution to mutual exclusion for two processes, in 1965?", ["Dekker"]),
    ("sync", "Which two-process mutual-exclusion algorithm uses a flag array and a turn variable and was published in 1981?", ["Peterson"]),
    ("sync", "What are the two classic semaphore operations, originally named by their Dutch initials?", ["P and V", "wait and signal", "down and up", "P() and V()"]),
    ("sync", "What kind of lock busy-waits in a loop until it becomes free?", ["spinlock", "spin lock", "spin-lock"]),
    ("sync", "Which atomic instruction sets a memory word and returns its old value, and is used to build spinlocks?", ["test-and-set", "test and set", "TestAndSet", "TSL"]),
    ("sync", "Which atomic instruction updates a word only if it still holds an expected value?", ["compare-and-swap", "compare and swap", "CAS", "compare-and-exchange", "cmpxchg"]),
    ("sync", "Which high-level synchronisation construct, proposed by Hoare and Brinch Hansen, allows only one thread inside at a time?", ["monitor"]),
    ("sync", "Which signalling semantics leaves the signalled thread to recheck its condition because it does not run immediately?", ["Mesa"]),
    ("sync", "What is the situation where a high-priority task waits for a lock held by a low-priority one that is preempted by a medium-priority task called?", ["priority inversion"]),
    ("sync", "Which Mars rover mission famously suffered resets caused by priority inversion?", ["Pathfinder", "Mars Pathfinder"]),
    ("sync", "What protocol temporarily raises a lock holder's priority to that of the highest waiter?", ["priority inheritance"]),
    ("sync", "Which classic synchronisation problem has five diners sharing forks around a table?", ["dining philosophers"]),
    ("sync", "Which classic problem is also called the bounded-buffer problem?", ["producer-consumer", "producer–consumer", "producer consumer"]),
    ("sync", "Which primitive makes a group of threads wait until all of them have reached the same point?", ["barrier"]),
    ("sync", "What is it called when processes keep changing state in response to each other but make no progress?", ["livelock"]),
    ("sync", "What property does an algorithm have if every thread is guaranteed to finish its operation in a bounded number of its own steps?", ["wait-free", "wait free"]),
    ("sync", "What Linux kernel mechanism lets readers proceed without locks while writers publish new versions, freeing old ones after a grace period?", ["read-copy-update", "RCU", "read copy update"]),
    ("sync", "What Linux system call provides fast user-space locking that only enters the kernel on contention?", ["futex"]),
    # deadlock
    ("deadlock", "Who formalised the four necessary conditions for deadlock in 1971?", ["Coffman"]),
    ("deadlock", "Which deadlock condition is broken by imposing a global ordering on resource acquisition?", ["circular wait"]),
    ("deadlock", "Which deadlock condition is broken by requiring a process to request all its resources at once?", ["hold and wait", "hold-and-wait"]),
    ("deadlock", "Which deadlock-avoidance algorithm, devised by Dijkstra, grants a request only if the system stays in a safe state?", ["Banker"]),
    ("deadlock", "In the Banker's algorithm, what is Max minus Allocation called?", ["Need"]),
    ("deadlock", "What graph with an edge from a waiting process to the process holding its resource is used for deadlock detection?", ["wait-for graph", "wait for graph"]),
    ("deadlock", "What is the strategy of simply ignoring deadlocks, used by many general-purpose operating systems, nicknamed?", ["ostrich"]),
    # memory
    ("memory", "What kind of fragmentation is wasted space inside an allocated block?", ["internal fragmentation", "internal"]),
    ("memory", "What kind of fragmentation leaves enough total free memory but no single hole large enough?", ["external fragmentation", "external"]),
    ("memory", "What is the technique of moving allocated blocks together to merge free holes called?", ["compaction"]),
    ("memory", "Which placement strategy chooses the smallest free hole that is big enough?", ["best fit", "best-fit"]),
    ("memory", "Which placement strategy chooses the largest free hole?", ["worst fit", "worst-fit"]),
    ("memory", "Which allocator splits memory into blocks whose sizes are powers of two and merges pairs when they are freed?", ["buddy"]),
    ("memory", "Which kernel allocator, introduced in SunOS by Bonwick, keeps caches of pre-initialised objects of one size?", ["slab"]),
    ("memory", "Which hardware unit translates virtual addresses to physical addresses?", ["memory management unit", "MMU"]),
    ("memory", "Which pair of registers restricts a process to a contiguous region of physical memory?", ["base and limit", "base and bounds", "relocation and limit"]),
    ("memory", "What is the fixed-size block of physical memory that holds one page called?", ["frame", "page frame"]),
    ("memory", "What is the cache of recent page-table translations inside the CPU called?", ["translation lookaside buffer", "TLB", "translation look-aside buffer"]),
    ("memory", "What do address-space identifiers in TLB entries let the hardware avoid on every context switch?", ["flush", "flushing"]),
    ("memory", "What page-table design has one entry per physical frame rather than per virtual page?", ["inverted page table", "inverted"]),
    ("memory", "What is the product of the number of TLB entries and the page size called?", ["TLB reach", "TLB coverage"]),
    ("memory", "What page-table entry bit records that a page has been written since it was loaded?", ["dirty bit", "modified bit", "modify bit", "dirty"]),
    ("memory", "What page-table entry bit does the hardware set when a page is read or written, for use by replacement algorithms?", ["reference bit", "accessed bit", "use bit", "referenced bit"]),
    ("memory", "What address-space randomisation technique places stack, heap and libraries at unpredictable addresses?", ["ASLR", "address space layout randomization", "address space layout randomisation"]),
    ("memory", "What memory-management scheme divides a program into variable-sized logical units such as code, stack and heap?", ["segmentation"]),
    ("memory", "What Linux system call maps a file or anonymous memory into a process's address space?", ["mmap"]),
    ("memory", "What do programs call to grow the heap's end in traditional UNIX?", ["brk", "sbrk"]),
    # virtual memory and replacement
    ("vm", "What is the trap raised when a program references a page that is not currently in memory?", ["page fault"]),
    ("vm", "What is it called when a system spends most of its time paging rather than doing useful work?", ["thrashing"]),
    ("vm", "Who proposed the working-set model of program behaviour?", ["Denning"]),
    ("vm", "Which policy loads a page only when it is first referenced?", ["demand paging"]),
    ("vm", "Which page-replacement algorithm evicts the page that will not be used for the longest time in the future?", ["OPT", "optimal", "Belady's algorithm", "MIN", "clairvoyant"]),
    ("vm", "Which approximation of LRU sweeps a circular list of frames using a reference bit?", ["clock", "second chance", "second-chance"]),
    ("vm", "What class of replacement algorithms, which includes LRU and OPT, can never suffer from Belady's anomaly?", ["stack algorithm", "stack algorithms", "stack property"]),
    ("vm", "Which replacement anomaly makes FIFO produce more faults with more frames?", ["Belady", "Bélády"]),
    ("vm", "What is the area of disk used to hold pages evicted from memory called?", ["swap space", "swap", "backing store", "paging file", "swap partition"]),
    ("vm", "What is a page fault that does not need disk I/O because the page is already in memory called?", ["minor", "soft"]),
    ("vm", "What replacement scope lets a process take a frame from another process?", ["global replacement", "global"]),
    ("vm", "What control scheme gives a process more frames when its fault rate exceeds an upper bound?", ["page-fault frequency", "page fault frequency", "PFF"]),
    ("vm", "What Linux kernel mechanism kills a process when the system runs out of memory?", ["OOM killer", "out-of-memory killer", "out of memory killer", "OOM"]),
    ("vm", "What are pages much larger than the base page size, used to increase TLB reach, called on Linux?", ["huge pages", "hugepages", "large pages", "superpages"]),
    # storage and disk scheduling
    ("storage", "What is the time for the disk arm to move the head to the right cylinder called?", ["seek time", "seek"]),
    ("storage", "What is the wait for the desired sector to rotate under the head called?", ["rotational latency", "rotational delay"]),
    ("storage", "Which disk-scheduling algorithm is also called the elevator algorithm?", ["SCAN"]),
    ("storage", "Which disk-scheduling algorithm services the request closest to the current head position next?", ["shortest seek time first", "SSTF", "shortest seek first"]),
    ("storage", "Which variant of SCAN services requests in one direction only and then jumps back to the start?", ["C-SCAN", "circular SCAN", "CSCAN"]),
    ("storage", "Which SCAN variant reverses at the last pending request instead of the end of the disk?", ["LOOK"]),
    ("storage", "Which RAID level stripes data with no redundancy?", ["RAID 0", "RAID-0", "RAID0"]),
    ("storage", "Which RAID level mirrors every block onto a second disk?", ["RAID 1", "RAID-1", "RAID1"]),
    ("storage", "Which RAID level stripes blocks with parity distributed across all disks?", ["RAID 5", "RAID-5", "RAID5"]),
    ("storage", "Which RAID level uses two independent parity blocks and survives two disk failures?", ["RAID 6", "RAID-6", "RAID6"]),
    ("storage", "What does an SSD do to spread writes evenly so that no flash block wears out early?", ["wear leveling", "wear levelling", "wear-leveling"]),
    ("storage", "Which command tells an SSD which blocks no longer hold valid data?", ["TRIM"]),
    ("storage", "What technique lets a device transfer data to memory without the CPU copying each byte?", ["direct memory access", "DMA"]),
    ("storage", "What is checking a device's status register in a loop, instead of waiting for an interrupt, called?", ["polling", "busy waiting", "busy-waiting"]),
    # file systems
    ("fs", "What UNIX on-disk structure stores a file's metadata and block pointers but not its name?", ["inode", "index node", "i-node"]),
    ("fs", "What is a directory entry that points to the same inode as another name called?", ["hard link"]),
    ("fs", "What kind of link stores the path of its target and breaks if the target is removed?", ["symbolic link", "soft link", "symlink"]),
    ("fs", "What does a file system keep, written before the actual changes, so that it can recover quickly after a crash?", ["journal", "log", "write-ahead log"]),
    ("fs", "Which tool checks and repairs a UNIX file system's consistency after a crash?", ["fsck"]),
    ("fs", "Which Microsoft file system follows a chain of entries in an allocation table to find a file's next cluster?", ["FAT", "File Allocation Table"]),
    ("fs", "What does ext4 use instead of block maps to describe runs of contiguous blocks?", ["extent", "extents"]),
    ("fs", "What is attaching a file system at a directory in the existing tree called?", ["mounting", "mount"]),
    ("fs", "What kernel layer gives many different file-system types one common interface?", ["virtual file system", "VFS", "virtual filesystem"]),
    ("fs", "Which file-system design writes all updates sequentially to the end of a log, proposed by Rosenblum and Ousterhout?", ["log-structured", "log structured", "LFS"]),
    ("fs", "What small integer does open() return for the process to use in later read and write calls?", ["file descriptor", "fd"]),
    ("fs", "Which pseudo file system mounted at a three-letter path in Linux exposes per-process status and memory maps?", ["/proc", "procfs"]),
    ("fs", "Which allocation method gives each file an index block listing its data blocks?", ["indexed allocation", "indexed"]),
    ("fs", "What free-space structure uses one bit per disk block?", ["bitmap", "bit vector", "bit map"]),
    ("fs", "What is the per-file list of users and the operations each may perform called?", ["access control list", "ACL"]),
    ("fs", "Which UNIX permission bit lets a program run with the privileges of its owner?", ["setuid", "set-user-ID", "SUID", "set user id"]),
    # protection and virtualisation
    ("protection", "What is a list of objects a domain may access, with the rights for each, called?", ["capability list", "capabilities", "capability"]),
    ("protection", "Which design principle says a program should get only the privileges it needs?", ["least privilege"]),
    ("protection", "What attack overwrites a function's return address by writing past the end of a stack array?", ["buffer overflow", "stack smashing", "stack overflow"]),
    ("protection", "What is a hypervisor that runs directly on the hardware, below the guest operating systems, called?", ["type 1", "bare-metal", "bare metal", "native hypervisor"]),
    ("protection", "What virtualisation technique runs a guest kernel deprivileged so its privileged instructions trap to the hypervisor for emulation?", ["trap-and-emulate", "trap and emulate"]),
    ("protection", "Which Linux kernel features give containers their own view of process ids, mounts and network?", ["namespaces", "namespace"]),
    ("protection", "Which Linux kernel feature limits and accounts the CPU and memory used by a group of processes?", ["cgroups", "control groups", "cgroup"]),
]


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        for n, (topic, q, ans) in enumerate(QA):
            assert q not in seen, q
            seen.add(q)
            low = q.lower()
            leaked = [a for a in ans if len(a) > 3 and a.lower() in low]
            assert not leaked, (q, leaked)
            f.write(json.dumps(dict(id=f"q{n + 1:03d}", topic=topic, question=q, answers=ans,
                                    split="dev" if n % 2 == 0 else "test", status="unreviewed"),
                               ensure_ascii=False) + "\n")
    from collections import Counter
    print(f"{len(QA)} questions -> {OUT}")
    print(dict(Counter(t for t, _, _ in QA)))


if __name__ == "__main__":
    main()
