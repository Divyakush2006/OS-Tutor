# Peterson's algorithm

Peterson's algorithm (or Peterson's solution) is a concurrent programming algorithm for mutual exclusion that allows two or more processes to share a single-use resource without conflict, using only shared memory for communication. It was formulated by Gary L. Peterson in 1981. Peterson's original algorithm worked with only two processes; it can be generalized for more than two.

## The algorithm

The algorithm uses two variables: flag and turn. A flag[n] value of true indicates that the process n wants to enter the critical section. Entrance to the critical section is granted for process P0 if P1 does not want to enter its critical section or if P1 has given priority to P0 by setting turn to 0.

The algorithm satisfies the three essential criteria to solve the critical-section problem. The while condition works even with preemption.
The three criteria are mutual exclusion, progress, and bounded waiting.
Since turn can take on one of two values, it can be replaced by a single bit, meaning that the algorithm requires only three bits of memory.

### Mutual exclusion

P0 and P1 can never be in the critical section at the same time. If P0 is in its critical section, then flag[0] is true. In addition, either flag[1] is false (meaning that P1 has left its critical section), or turn is 0 (meaning that P1 is just now trying to enter the critical section, but graciously waiting), or P1 is at label P1_gate (trying to enter its critical section, after setting flag[1] to true but before setting turn to 0 and busy waiting). So if both processes are in their critical sections, then we conclude that the state must satisfy flag[0] and flag[1] and turn = 0 and turn = 1. No state can satisfy both turn = 0 and turn = 1, so there can be no state where both processes are in their critical sections.
(This recounts an argument that is made rigorous in Schneider 1997.)

### Progress

Progress is defined as the following: if no process is executing in its critical section and some processes wish to enter their critical sections, then only those processes that are not executing in their remainder sections can participate in making the decision as to which process will enter its critical section next. Note that for a process or thread, the remainder sections are parts of the code that are not related to the critical section. This selection cannot be postponed indefinitely. A process cannot immediately re-enter the critical section if the other process has set its flag to say that it would like to enter its critical section.

### Bounded waiting

Bounded waiting, or bounded bypass, means that the number of times a process is bypassed by another process after it has indicated its desire to enter the critical section is bounded by a function of the number of processes in the system. In Peterson's algorithm, a process will never wait longer than one turn for entrance to the critical section.

### Filter algorithm: Peterson's algorithm for more than two processes

The filter algorithm generalizes Peterson's algorithm to N > 2 processes. Instead of a boolean flag, it requires an integer variable per process, stored in a single-writer/multiple-reader (SWMR) atomic register, and N − 1 additional variables in similar registers. The registers can be represented in pseudocode as arrays:

level : array of N integers
last_to_enter : array of N − 1 integers

The level variables take on values up to N − 1, each representing a distinct "waiting room" before the critical section. Processes advance from one room to the next, finishing in room N − 1, which is the critical section. Specifically, to acquire a lock, process i executes

i ← ProcessNo
for ℓ from 0 to N − 1 exclusive
    level[i] ← ℓ
    last_to_enter[ℓ] ← i
    while last_to_enter[ℓ] = i and there exists k ≠ i, such that level[k] ≥ ℓ
        wait

To release the lock upon exiting the critical section, process i sets level[i] to −1.
That this algorithm achieves mutual exclusion can be proven as follows. Process i exits the inner loop when there is either no process with a higher level than level[i], so the next waiting room is free; or, when i ≠ last_to_enter[ℓ], so another process joined its waiting room. At level zero, then, even if all N processes were to enter waiting room zero at the same time, no more than N − 1 will proceed to the next room, the final one finding itself the last to enter the room. Similarly, at the next level, N − 2 will proceed, etc., until at the final level, only one process is allowed to leave the waiting room and enter the critical section, giving mutual exclusion.
Unlike the two-process Peterson algorithm, the filter algorithm does not guarantee bounded waiting.

## Modern problems

On modern machines, Peterson's algorithm (as shown here) fails to provide mutual exclusion. Additional declarations and/or instructions can make it work (although different methods using the language features and/or new machine instructions can accomplish mutual exclusion more efficiently). Computers have been made far more complex since 1981; they no longer execute instructions in lockstep. Most compilers change the order of operations in ways that produce the same results faster, but they do not consider the interaction of concurrent operations that access the same data. CPUs reorder instructions within their execution pipelines. CPUs pre-read memory contents, cache memory contents, and delay and combine writes. Multiple CPU cores can access the same memory with true concurrency. Multiple CPUs can have separate caches that can delay synchronization. Any of these can break Peterson's algorithm. To allow usable mutual exclusion in this new environment, machine instructions have been added, such as memory barrier and atomic read-and-modify operations. These instructions let things "catch up" when necessary. Programming languages have added features that invoke these instructions. In several languages, declaring a variable volatile produces executable code that accesses the variable more carefully.
Peterson's algorithm is typically not needed to ensure atomic access. In earlier processors and operating systems, it sufficed to disable interrupts immediately before a critical section and then re-enable interrupts after it was complete. Most modern processors have special instructions that provide ways to build synchronization primitives more efficiently than can be done with pure shared-memory approaches. These instructions, by locking the memory bus, can be used to guarantee atomicity and provide mutual exclusion in symmetric multiprocessing systems. Examples include test-and-set (XCHG) and compare-and-swap (CMPXCHG) on x86 processors and load-link/store-conditional on Alpha, MIPS, PowerPC, and other architectures. 
Most modern CPUs reorder memory accesses to improve execution efficiency (see memory ordering for types of reordering allowed). Such processors invariably provide some way to force ordering in a stream of memory accesses, typically through a memory barrier instruction. Implementation of Peterson's and related algorithms on processors that reorder memory accesses generally requires use of such operations to work correctly to keep sequential operations from happening in an incorrect order. Reordering of memory accesses can happen even on processors that don't reorder instructions (such as the PowerPC processor in the Xbox 360).
