"""Knowledge base block 4: synchronisation, deadlock handling, file systems,
protection, virtualisation and boot.

Same 7-tuple structure as KB3:
  (topic, question_core, misconception, why_seductive, correction, example, probe)
"""

KB4 = [
 ("spinlock_uniprocessor",
  "why spinlocks are pointless on a single-CPU system",
  "spinlocks work equally well on one CPU and many",
  "the lock logic is identical in both cases",
  "On one CPU, a thread spinning for a lock prevents the holder from running, so it "
  "just burns its whole time slice. Spinning is useful only when the holder can run "
  "SIMULTANEOUSLY on another CPU. Uniprocessor kernels instead disable preemption "
  "or interrupts around short critical sections.",
  "On a single core, a spinning thread cannot make progress until the scheduler "
  "preempts it and lets the lock holder run and release the lock.",
  "On a machine with exactly one CPU, what is the lock holder doing while another "
  "thread spins?"),

 ("condition_variable",
  "why a condition-variable wait must sit inside a while loop",
  "an if statement is enough to check the condition before waiting",
  "the thread is woken only when the condition becomes true",
  "After wait() returns, the condition may NOT hold: another thread may have consumed "
  "the state first, and spurious wakeups are permitted. So the condition must be "
  "re-checked in a loop - `while (!cond) wait(&cv, &m);`. wait() also atomically "
  "releases the mutex and re-acquires it before returning.",
  "Two consumers woken by one signal: the first takes the only item; if the second "
  "used `if`, it would proceed on an empty buffer.",
  "When a waiting thread is woken, can it be certain the condition it waited for is "
  "still true?"),

 ("signal_vs_broadcast",
  "the difference between signal and broadcast on a condition variable",
  "signal and broadcast wake threads in the same way",
  "both wake waiting threads",
  "signal wakes AT LEAST ONE waiter; broadcast wakes ALL of them. Use broadcast when "
  "several waiters might be able to proceed, or when different waiters wait for "
  "different conditions on the same variable - using signal there can wake the "
  "wrong thread and stall the right one.",
  "A pool where one release can satisfy several waiting requests needs broadcast; a "
  "single-slot hand-off can use signal.",
  "If threads wait on the same condition variable for different reasons, what can go "
  "wrong if you wake only one?"),

 ("reader_writer_lock",
  "when a reader-writer lock helps",
  "a reader-writer lock is always faster than a mutex",
  "it allows more concurrency",
  "It helps only when reads DOMINATE and read sections are long enough to benefit "
  "from running in parallel. Its bookkeeping costs more than a plain mutex, and "
  "naive versions can starve writers if readers keep arriving.",
  "A configuration table read thousands of times per second and updated rarely "
  "suits an RW lock; a counter updated on every access does not.",
  "What happens to a waiting writer in a reader-preferring lock if new readers keep "
  "arriving?"),

 ("test_and_set",
  "why atomic hardware instructions are needed for locks",
  "a lock can be built correctly with an ordinary if-check on a variable",
  "checking a flag and then setting it looks like it would work",
  "Checking then setting is two steps; another thread can run between them and both "
  "can see the lock as free. Atomic instructions such as test-and-set or "
  "compare-and-swap make read-and-update INDIVISIBLE, which is the foundation of "
  "every lock.",
  "`if (!locked) locked = 1;` lets two threads enter together if both read "
  "`locked == 0` before either writes it.",
  "If two threads both read `locked == 0` before either sets it, what happens?"),

 ("peterson",
  "why Peterson's algorithm fails on modern hardware",
  "Peterson's algorithm is a correct lock on any computer",
  "it is proved correct in textbooks",
  "The proof assumes SEQUENTIALLY CONSISTENT memory. Modern CPUs and compilers "
  "reorder loads and stores, so without memory barriers both threads can enter the "
  "critical section. It is a teaching algorithm; real code uses atomic "
  "instructions and fences.",
  "On x86, a later load can be reordered ahead of an earlier store, which is exactly "
  "the pattern that breaks Peterson's flag-and-turn handshake.",
  "What assumption about the order of memory operations does the textbook proof of "
  "Peterson's algorithm rely on?"),

 ("livelock",
  "the difference between livelock and deadlock",
  "livelock is just another name for deadlock",
  "in both, no useful progress is made",
  "In DEADLOCK threads are BLOCKED waiting on each other. In LIVELOCK threads keep "
  "RUNNING and changing state in response to each other, yet none makes progress - "
  "like two people repeatedly stepping aside in a corridor. The CPU is busy in "
  "livelock and idle in deadlock.",
  "Two threads that each release their lock and retry immediately whenever they "
  "detect contention can livelock; random backoff breaks the symmetry.",
  "In a livelock, is the CPU idle or busy?"),

 ("deadlock_detection",
  "how deadlock detection differs from avoidance",
  "detection prevents deadlocks from forming",
  "it sounds proactive",
  "DETECTION lets deadlocks happen and periodically finds them - with a wait-for "
  "graph cycle search for single-instance resources, or a Banker-like matrix "
  "algorithm for multiple instances - and then RECOVERS. AVOIDANCE, such as Banker's "
  "algorithm, refuses unsafe allocations so deadlock never occurs.",
  "A database detects a cycle among transactions waiting for locks and aborts one of "
  "them as the victim.",
  "When deadlock detection finds a cycle, what must the system then do?"),

 ("deadlock_recovery",
  "the ways a system can recover from deadlock",
  "the only way to break a deadlock is to reboot",
  "a deadlocked system looks completely stuck",
  "Recovery either TERMINATES processes - all involved, or one at a time until the "
  "cycle breaks - or PREEMPTS resources and rolls a victim back to a safe state. "
  "Victim choice weighs cost: priority, work done, resources held, and repeated "
  "selection that could cause starvation.",
  "Databases roll back a victim transaction and retry it rather than stopping the "
  "whole server.",
  "If you abort processes one at a time to break a cycle, what must you do after "
  "each abort?"),

 ("wait_for_graph",
  "what a cycle in a resource-allocation graph means",
  "a cycle in the graph always means deadlock",
  "cycles are taught as the sign of deadlock",
  "With SINGLE-INSTANCE resources a cycle is necessary and sufficient for deadlock. "
  "With MULTIPLE instances a cycle means deadlock is POSSIBLE but not certain: a "
  "process outside the cycle may release an instance that breaks it.",
  "Two instances of a printer and a cycle through that resource type can still "
  "resolve if another holder finishes and releases one instance.",
  "If a resource type has several identical instances, does a cycle guarantee "
  "deadlock?"),

 ("lock_ordering",
  "how lock ordering prevents deadlock",
  "you need a deadlock detector whenever you use more than one lock",
  "multiple locks seem inherently risky",
  "If every thread acquires locks in the same GLOBAL ORDER, a circular wait cannot "
  "form, so deadlock is impossible by construction. It is the most practical "
  "prevention technique in real code.",
  "Always locking the account with the lower ID first makes concurrent transfers "
  "between two accounts deadlock-free.",
  "If thread A locks X then Y while thread B locks Y then X, what can happen?"),

 ("file_allocation_contiguous",
  "the trade-offs of contiguous file allocation",
  "contiguous allocation has no drawbacks because reads are fast",
  "sequential and direct access are both very fast with it",
  "Contiguous allocation gives excellent sequential and direct access, but it "
  "suffers EXTERNAL FRAGMENTATION and makes growing a file hard: the space after it "
  "may already be taken. The final size often must be known in advance.",
  "CD-ROM file systems use contiguous allocation because files never change after "
  "the disc is written.",
  "What happens when a contiguously allocated file needs to grow but the next block "
  "is occupied?"),

 ("file_allocation_linked",
  "the weakness of linked file allocation",
  "linked allocation is ideal because it has no fragmentation",
  "it avoids external fragmentation completely",
  "Linked allocation avoids external fragmentation, but DIRECT access is slow - "
  "reaching block n means following n pointers - and one corrupted pointer loses "
  "the rest of the file. FAT keeps the pointers in a separate table, which can be "
  "cached, to soften the access cost.",
  "Seeking to the middle of a large linked file requires walking the chain from the "
  "beginning.",
  "To read the 1,000th block of a linked-allocated file, how many pointers must be "
  "followed?"),

 ("file_allocation_indexed",
  "how indexed allocation supports large files",
  "an index block can only point to a fixed small number of data blocks",
  "a single index block has limited entries",
  "Unix-style inodes combine DIRECT pointers for small files with SINGLE, DOUBLE and "
  "TRIPLE INDIRECT blocks for large ones. Each indirection level multiplies the "
  "reachable size, so small files stay fast while very large files remain possible.",
  "With 4 KB blocks and 4-byte pointers, one indirect block addresses 1,024 blocks "
  "(4 MB); a double indirect block addresses about a million blocks (4 GB).",
  "How does adding a double-indirect pointer change the maximum file size?"),

 ("free_space_bitmap",
  "how a free-space bitmap works",
  "the file system searches every block to find free space",
  "free space is not obviously tracked anywhere",
  "A bitmap stores ONE BIT per block, marking free or used. It is compact, makes "
  "finding runs of contiguous free blocks easy, and can be cached in memory. For "
  "very large disks the bitmap itself grows large, which is why some file systems "
  "use extents or free lists instead.",
  "A 1 TB disk with 4 KB blocks needs about 32 MB of bitmap - small enough to keep "
  "largely in memory.",
  "How many bits of bitmap does each disk block need?"),

 ("directory_structure",
  "why tree-structured directories replaced single-level ones",
  "a single directory for all files is simpler and therefore better",
  "one place to look sounds efficient",
  "A single-level directory forces globally unique names and gives no grouping. A "
  "TREE gives each user and project its own namespace, supports relative paths, and "
  "scales. Acyclic-graph directories then add sharing through links.",
  "Two users can each have a file called report.txt in their own home directories; "
  "in a single-level directory the names would collide.",
  "What happens in a single-level directory when two users both want a file called "
  "notes.txt?"),

 ("mounting",
  "what mounting a file system does",
  "mounting copies the device's files into the directory tree",
  "the files appear inside an existing directory",
  "Mounting ATTACHES a file system at a mount point, so path lookups crossing that "
  "directory continue into the mounted file system. Nothing is copied, and the "
  "mount point's original contents are hidden until it is unmounted.",
  "After mounting a USB drive on /mnt/usb, files you had placed in /mnt/usb earlier "
  "are hidden, not deleted.",
  "If a directory already contains files and another file system is mounted on it, "
  "what happens to those files?"),

 ("vfs_layer",
  "what the virtual file system layer is for",
  "each file system needs its own read() and write() system calls",
  "different on-disk formats seem to need different interfaces",
  "The VFS defines ONE common interface - inode, file and superblock objects with "
  "operation tables - that every concrete file system implements. System calls go "
  "through the VFS, so ext4, NFS and a USB FAT drive are used identically by "
  "programs.",
  "`cp` copies from an NFS share to a local ext4 disk without knowing either file "
  "system exists.",
  "Why does `cat` not need to know which file system a file is stored on?"),

 ("page_cache",
  "what the page cache does",
  "every file read goes to the disk",
  "files are stored on disk",
  "The kernel keeps recently used file data in the PAGE CACHE in otherwise free RAM. "
  "Repeated reads are served from memory, and writes are absorbed and flushed "
  "later. That is why 'free' memory on a busy Linux machine often looks small - it "
  "is being used as cache and is released on demand.",
  "The second `grep` over a large source tree is far faster than the first, because "
  "the files are now in the page cache.",
  "Why is reading the same large file a second time usually much faster?"),

 ("log_structured_fs",
  "the idea behind log-structured file systems",
  "log-structured file systems exist to keep a history of every change",
  "the word 'log' suggests an audit trail",
  "A log-structured file system writes ALL updates sequentially to the end of a log, "
  "turning many small random writes into large sequential ones. The cost is "
  "garbage collection: live data must be copied out of old segments to reclaim "
  "space.",
  "Flash storage suits the log-structured approach, because it cannot overwrite in "
  "place and prefers large sequential writes.",
  "What must eventually happen to old log segments that contain mostly dead data?"),

 ("raid_levels",
  "the difference between RAID 0, RAID 1 and RAID 5",
  "every RAID level adds redundancy",
  "RAID is known as a redundancy technology",
  "RAID 0 STRIPES data for speed with NO redundancy - losing one disk loses "
  "everything. RAID 1 MIRRORS every block. RAID 5 stripes data with distributed "
  "PARITY, surviving one disk failure at the cost of one disk's capacity and a "
  "write penalty on small writes.",
  "Four 1 TB disks give 4 TB in RAID 0 with no fault tolerance, and 3 TB in RAID 5 "
  "tolerating one failure.",
  "If one disk fails in a RAID 0 array, how much data survives?"),

 ("raid5_write_penalty",
  "why small writes are expensive in RAID 5",
  "RAID 5 writes are as fast as reads because data is striped",
  "striping speeds up reads",
  "Updating one block also requires updating its stripe's parity. The classic "
  "read-modify-write needs FOUR I/Os: read old data, read old parity, write new data, "
  "write new parity. Full-stripe writes avoid this, but small random writes pay the "
  "penalty.",
  "A database doing many small random updates on RAID 5 often performs far worse "
  "than on RAID 10 with the same disks.",
  "When one data block in a RAID 5 stripe changes, what else must be rewritten?"),

 ("access_control_lists",
  "the difference between ACLs and capabilities",
  "access control lists and capabilities are the same mechanism",
  "both decide who may access what",
  "An ACL is attached to the OBJECT and lists which subjects may do what to it. A "
  "capability is held by the SUBJECT and is an unforgeable token granting specific "
  "rights to an object. ACLs make revoking easy; capabilities make delegating easy.",
  "Unix file permissions are a simple ACL; a file descriptor behaves like a "
  "capability - once opened, access continues even if the file's permissions "
  "change.",
  "If you remove a user's read permission on a file they already have open, can "
  "they keep reading through that descriptor?"),

 ("setuid",
  "what the setuid bit does",
  "setuid makes a program run as root",
  "the most famous setuid programs run as root",
  "setuid makes a program run with the privileges of its FILE OWNER, whoever that "
  "is, rather than the user who launched it. Root-owned setuid binaries such as "
  "passwd are the common case, which is exactly why they must be written very "
  "carefully.",
  "`passwd` is setuid root so an ordinary user can update the root-owned password "
  "database - but only in the controlled way the program allows.",
  "If a setuid program is owned by the user 'alice', whose privileges does it run "
  "with?"),

 ("least_privilege",
  "the principle of least privilege",
  "running services as root is fine if the code is well tested",
  "testing seems to remove the risk",
  "Every component should have only the privileges it NEEDS. Well-tested code still "
  "has bugs, and least privilege limits the DAMAGE when one is exploited. Daemons "
  "therefore bind to privileged ports and then drop to an unprivileged user.",
  "A web server compromised while running as www-data exposes far less than one "
  "running as root.",
  "If a service running with minimal privileges is exploited, what limits the "
  "attacker?"),

 ("hypervisor_types",
  "the difference between type 1 and type 2 hypervisors",
  "all virtual machines run inside a normal operating system",
  "desktop virtualisation tools run as ordinary applications",
  "A TYPE 1 hypervisor runs directly on the hardware and hosts guest OSes - used in "
  "data centres. A TYPE 2 hypervisor runs as an application on a host OS - common "
  "on desktops. Type 1 generally has less overhead and a smaller trusted base.",
  "Cloud providers run type 1 hypervisors on bare metal; VirtualBox on a laptop is "
  "type 2.",
  "In a type 2 setup, what sits between the hypervisor and the hardware?"),

 ("container_vs_vm",
  "the difference between a container and a virtual machine",
  "containers are lightweight virtual machines, each with its own kernel",
  "both isolate applications",
  "A VM virtualises HARDWARE and runs its own full kernel. Containers SHARE the host "
  "kernel and are isolated with namespaces and cgroups. Containers start faster and "
  "use less memory, but a kernel vulnerability affects every container on the host.",
  "A Linux host cannot natively run a Windows container, because containers share "
  "the host's Linux kernel; a Windows VM can run because it brings its own kernel.",
  "How many kernels are running on a host with ten containers - and with ten VMs?"),

 ("namespaces_cgroups",
  "what namespaces and cgroups each contribute to containers",
  "namespaces limit how much CPU and memory a container can use",
  "both are container features, so they blur together",
  "NAMESPACES control what a process can SEE - its own PID tree, network stack, "
  "mounts and hostname. CGROUPS control how much it can USE - CPU, memory, I/O. "
  "Isolation needs namespaces; resource limits need cgroups.",
  "A container can see only its own processes (PID namespace) yet still be "
  "OOM-killed when it exceeds its memory cgroup limit.",
  "Which mechanism stops a container from using all of the host's memory?"),

 ("trap_and_emulate",
  "how a hypervisor handles privileged instructions from a guest",
  "the guest OS runs its privileged instructions directly on the hardware",
  "the guest believes it is the real kernel",
  "The guest kernel runs WITHOUT real privilege. Its privileged instructions trap to "
  "the hypervisor, which EMULATES their effect on the virtual machine's state. "
  "Hardware extensions such as Intel VT-x and AMD-V make this efficient and handle "
  "instructions that would otherwise not trap.",
  "When a guest tries to change its page-table base, the hypervisor intercepts it "
  "and updates the guest's virtual MMU state instead.",
  "What must happen when a guest kernel executes an instruction only the real kernel "
  "may execute?"),

 ("boot_process",
  "the sequence of steps when a computer boots",
  "the operating system starts running as soon as power is applied",
  "the OS seems to be what is running from the first moment",
  "Firmware (BIOS or UEFI) runs first, initialises hardware and loads a BOOTLOADER. "
  "The bootloader loads the kernel and usually an initial RAM disk. The kernel "
  "initialises itself and then starts the first user process, such as systemd, "
  "which brings up the rest of the system.",
  "A broken bootloader configuration can stop the machine before the kernel is ever "
  "loaded, even though the OS installation is intact.",
  "What program is responsible for loading the kernel into memory?"),

 ("init_process",
  "the special role of PID 1",
  "PID 1 is just the first program that happened to start",
  "process IDs look like simple counters",
  "PID 1 is started by the kernel and is the ancestor of all user processes. It "
  "adopts orphans and must reap them, supervises system services, and if it exits "
  "the kernel panics. That is why containers need a proper init or a reaping "
  "wrapper as PID 1.",
  "A container whose PID 1 is an application that never calls wait() accumulates "
  "zombies from its child processes.",
  "What would happen to orphaned processes if PID 1 never called wait()?"),

 ("proc_filesystem",
  "what /proc actually is",
  "/proc is a directory of files stored on the disk",
  "you browse it with ls and cat like any directory",
  "/proc is a VIRTUAL file system generated by the kernel on demand. Its files "
  "expose kernel data structures - per-process status, memory maps, CPU info - and "
  "some writable entries tune the kernel. Nothing in it lives on disk.",
  "`cat /proc/meminfo` asks the kernel for current memory statistics; the numbers "
  "are produced at the moment you read them.",
  "Why does /proc take up no space on the disk?"),

 ("swappiness",
  "what vm.swappiness controls",
  "setting swappiness to zero disables swap completely",
  "zero sounds like 'off'",
  "swappiness tunes the kernel's PREFERENCE between reclaiming page cache and "
  "swapping out anonymous memory. Low values prefer dropping cache, but under real "
  "memory pressure the kernel may still swap. It is a bias, not a switch.",
  "A database server may lower swappiness so its own memory is not swapped out in "
  "favour of keeping file cache.",
  "Does swappiness=0 guarantee that nothing is ever written to swap?"),

 ("thread_pool",
  "why servers use thread pools",
  "creating a new thread per request is the most responsive design",
  "a dedicated thread per request seems to give each request full attention",
  "Creating and destroying threads costs time and memory, and unbounded thread "
  "creation can exhaust the system under load. A POOL reuses a bounded set of "
  "threads, amortising creation cost and applying back-pressure when all are busy.",
  "Under a traffic spike, thread-per-request can create thousands of threads and "
  "thrash; a pool of fixed size queues the excess requests instead.",
  "What happens to a thread-per-request server when ten thousand requests arrive at "
  "once?"),

 ("thread_local_storage",
  "what thread-local storage provides",
  "global variables are automatically separate for each thread",
  "each thread has its own stack, so globals might be separate too",
  "Globals are SHARED by all threads of a process. Thread-local storage gives each "
  "thread its OWN copy of a variable declared at global scope, which is how errno "
  "can be per-thread in a multithreaded C library.",
  "Without TLS, one thread's failing system call could overwrite errno just before "
  "another thread reads it.",
  "If two threads both write to an ordinary global variable, how many copies of it "
  "exist?"),

 ("false_sharing",
  "what false sharing is",
  "threads only slow each other down when they access the same variable",
  "sharing is associated with the same data",
  "Caches work in LINES, typically 64 bytes. If two threads write different "
  "variables on the SAME cache line, the line bounces between cores on every write "
  "even though no data is logically shared. Padding the variables onto separate "
  "lines fixes it.",
  "Per-thread counters packed into one array can scale worse than a single shared "
  "counter until each is padded to its own cache line.",
  "Two threads update two different variables that sit next to each other in "
  "memory. Why might they still slow each other down?"),

 ("memory_barriers",
  "why memory barriers are needed in concurrent code",
  "memory operations always happen in the order they are written in the source",
  "programs appear to execute line by line",
  "Compilers and CPUs REORDER memory operations for performance, which is invisible "
  "to single-threaded code but observable across threads. Memory barriers, "
  "atomics with acquire and release semantics, and locks constrain that ordering.",
  "Setting `data = 42; ready = 1;` without a release barrier lets another core see "
  "ready == 1 while still reading the old value of data.",
  "Can another CPU observe your two writes in the opposite order from the one in "
  "your code?"),
]
