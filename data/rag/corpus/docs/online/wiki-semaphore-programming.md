# Semaphore (programming)

In computer science, a semaphore is a synchronization device used to control access to a common resource by multiple threads or processes in a concurrent system, such as a multitasking operating system. It allows simultaneous access to a critical section by some predetermined number of processes.
A useful way to think of a semaphore is as a record of how many units of a particular resource are available, coupled with operations to adjust that record safely (i.e., to avoid race conditions) as units are acquired or become free, and, if necessary, wait until a unit of the resource becomes available. Though semaphores are useful for preventing race conditions, they do not guarantee their absence. 
Semaphores that allow an arbitrary resource count are called counting semaphores, while semaphores that are restricted to the values 0 and 1 (or locked/unlocked, unavailable/available) are called binary semaphores and are used to implement locks.
The semaphore concept was invented by Dutch computer scientist Edsger Dijkstra in 1962 or 1963, when Dijkstra and his team were developing an operating system for the Electrologica X8. That system eventually became known as the THE multiprogramming system.

## Library analogy

Suppose a physical library has ten identical study rooms, to be used by one student at a time. Students must request a room from the front desk. If no rooms are free, students wait at the desk until someone relinquishes a room. When a student has finished using a room, the student must return to the desk and indicate that the room is free.
In the simplest implementation, the clerk at the front desk knows only the number of free rooms available. This requires that all of the students use their room while they have signed up for it and return it when they are done. When a student requests a room, the clerk decreases this number. When a student releases a room, the clerk increases this number. The room can be used as long as desired and rooms cannot be booked in advance.
In this scenario, the front desk count-holder represents a counting semaphore, the rooms are the resource, and the students represent processes/threads. The value of the semaphore in this scenario is initially 10, with all rooms empty. When a student requests a room, they are granted access, and the value of the semaphore is changed to 9. After the next student comes, it drops to 8, then 7, and so on. If someone requests a room and the current value of the semaphore is 0, they are forced to wait until a room is freed (when the count is increased from 0). If one of the rooms was released, but there are several students waiting, any method can be used to select the one who will occupy the room (like FIFO or random selection). And of course, a student must inform the clerk about releasing their room only after leaving it.

### Important observations

When used to control access to a pool of resources, a semaphore tracks only how many resources are free. It does not keep track of which of the resources are free. Some other mechanism (possibly involving more semaphores) may be required to select a particular free resource.
The paradigm is especially powerful because the semaphore count may serve as a useful trigger for a number of different actions. The librarian above may turn the lights off in the study hall when there are no students remaining, or may place a sign that says the rooms are very busy when most of the rooms are occupied.
The success of the protocol requires applications to follow it correctly. Fairness and safety are likely to be compromised (which practically means a program may behave slowly, act erratically, hang, or crash) if even a single process acts incorrectly. This includes:

requesting a resource and forgetting to release it;
releasing a resource that was never requested;
holding a resource for a long time without needing it;
using a resource without requesting it first (or after releasing it).
Even if all processes follow these rules, multi-resource deadlock may still occur when there are different resources managed by different semaphores and when processes need to use more than one resource at a time, as illustrated by the dining philosophers problem.

## Semantics and implementation

Counting semaphores are equipped with two operations, historically denoted as P and V (see § Operation names for alternative names). Operation V increments the semaphore S, and operation P decrements it.
The value of the semaphore S represents the number of units of available resource units when non-negative. In some implementations, negative values indicate the number of processes waiting for the resource. The P operation wastes time or sleeps until a resource protected by the semaphore becomes available, at which time the resource is immediately claimed. The V operation is the inverse: it makes a resource available again after the process has finished using it.
One important property of semaphore S is that its value cannot be changed except by using the V and P operations.
A simple way to understand wait (P) and signal (V) operations is:

wait: Decrements the value of the semaphore variable by 1. If the new value of the semaphore variable is negative, the process executing wait is blocked (i.e., added to the semaphore's queue). Otherwise, the process continues execution, having used a unit of the resource.
signal: Increments the value of the semaphore variable by 1. After the increment, if the pre-increment value was negative (meaning there are processes waiting for a resource), it transfers a blocked process from the semaphore's waiting queue to the ready queue.
Many operating systems provide efficient semaphore primitives that unblock a waiting process when the semaphore is incremented. This means that processes do not waste time checking the semaphore value unnecessarily.
The counting semaphore concept can be extended with the ability to claim or return more than one "unit" from the semaphore. This is sometimes called a weighted semaphore. The modified V and P operations are as follows, using square brackets to indicate atomic operations, i.e., operations that appear indivisible to other processes:

function V(semaphore S, integer I):
    [S ← S + I]

function P(semaphore S, integer I):
    repeat:
        [if S ≥ I:
        S ← S − I
        break]

Weighted semaphores are useful for limiting access to, e.g., memory or disk space: a process that needs N megabytes of space to run needs to decrease the semaphore by N units. However, doing this in N separate calls to P can cause deadlocks.
However, the rest of this section refers to semaphores with unary V and P operations, unless otherwise specified.
To avoid starvation, a semaphore has an associated queue of processes (usually with FIFO semantics). If a process performs a P operation on a semaphore that has the value zero, the process is added to the semaphore's queue and its execution is suspended. When another process increments the semaphore by performing a V operation, and there are processes on the queue, one of them is removed from the queue and resumes execution. When processes have different priorities the queue may be ordered thereby, such that the highest priority process is taken from the queue first.
If the implementation does not ensure atomicity of the increment, decrement, and comparison operations, there is a risk of increments or decrements being forgotten, or of the semaphore value becoming negative. Atomicity may be achieved by using a machine instruction that can read, modify, and then write the semaphore in a single operation. Without such a hardware instruction, an atomic operation may be synthesized by using a software mutual exclusion algorithm. On uniprocessor systems, atomic operations can be ensured by temporarily suspending preemption or disabling hardware interrupts. This approach does not work on multiprocessor systems where it is possible for two programs sharing a semaphore to run on different processors at the same time. To solve this problem in a multiprocessor system, a locking variable can be used to control access to the semaphore. The locking variable is manipulated using a test-and-set-lock command.

## Examples

### Trivial example

Consider a variable A and a Boolean variable S. A is only accessed when S is marked true. Thus, S is a semaphore for A.
One can imagine a stoplight signal (S) just before a train station (A). In this case, if the signal is green, then one can enter the train station. If it is yellow or red (or any other color), the train station cannot be accessed.

### Login queue

Consider a system that can only support ten users (S=10). Whenever a user logs in, P is called, decrementing the semaphore S by 1. Whenever a user logs out, V is called, incrementing S by 1 representing a login slot that has become available. When S is 0, any users wishing to log in must wait until S increases. The login request is enqueued onto a FIFO queue until a slot is freed. Mutual exclusion is used to ensure that requests are enqueued in order. Whenever S increases (login slots available), a login request is dequeued, and the user owning the request is allowed to log in. If S is already greater than 0, then login requests are immediately dequeued.

### Producer–consumer problem

In the producer–consumer problem, one process (the producer) generates data items and another process (the consumer) receives and uses them. They communicate using a queue of maximum size N and are subject to the following conditions:

the consumer must wait for the producer to produce something if the queue is empty;
the producer must wait for the consumer to consume something if the queue is full.
The semaphore solution to the producer–consumer problem tracks the state of the queue with two semaphores: emptyCount, the number of empty places in the queue, and fullCount, the number of elements in the queue. To maintain integrity, emptyCount may be lower (but never higher) than the actual number of empty places in the queue, and fullCount may be lower (but never higher) than the actual number of items in the queue. Empty places and items represent two kinds of resources, empty boxes and full boxes, and the semaphores emptyCount and fullCount maintain control over these resources.
The binary semaphore useQueue ensures that the integrity of the state of the queue itself is not compromised, for example, by two producers attempting to add items to an empty queue simultaneously, thereby corrupting its internal state. Alternatively a mutex could be used in place of the binary semaphore.
The emptyCount is initially N, fullCount is initially 0, and useQueue is initially 1.
The producer does the following repeatedly:

produce:
    P(emptyCount)
    P(useQueue)
    putItemIntoQueue(item)
    V(useQueue)
    V(fullCount)

The consumer does the following repeatedly

consume:
    P(fullCount)
    P(useQueue)
    item ← getItemFromQueue()
    V(useQueue)
    V(emptyCount)

Below is a substantive example:

A single consumer enters its critical section. Since fullCount is 0, the consumer blocks.
Several producers enter the producer critical section. No more than N producers may enter their critical section due to emptyCount constraining their entry.
The producers, one at a time, gain access to the queue through useQueue and deposit items in the queue.
Once the first producer exits its critical section, fullCount is incremented, allowing one consumer to enter its critical section.
Note that emptyCount may be much lower than the actual number of empty places in the queue, for example, where many producers have decremented it but are waiting their turn on useQueue before filling empty places. Note that emptyCount + fullCount ≤ N always holds, with equality if and only if no producers or consumers are executing their critical sections.

### Passing the baton pattern

The "Passing the baton" pattern proposed by Gregory R. Andrews is a generic scheme to solve many complex concurrent programming problems in which multiple processes compete for the same resource with complex access conditions (such as satisfying specific priority criteria or avoiding starvation). Given a shared resource, the pattern requires a private "priv" semaphore (initialized to zero) for each process (or class of processes) involved and a single mutual exclusion "mutex" semaphore (initialized to one). 
The pseudo-code for each process is:

The pseudo-code of the resource acquisition and release primitives are:

Both primitives in turn use the "pass_the_baton" method, whose pseudo-code is:

Remarks
The pattern is called "passing the baton" because a process that releases the resource as well as a freshly reactivated process will activate at most one suspended process, that is, shall "pass the baton to it". The mutex is released only when a process is going to suspend itself (resource_acquire), or when pass_the_baton is unable to reactivate another suspended process.

## Operation names

The canonical names V and P come from the initials of Dutch words. V is generally explained as verhogen ("increase"). Several explanations have been offered for P, including proberen ("to test" or "to try"), passeren ("pass"), and pakken ("grab"). Dijkstra's earliest paper on the subject gives passering ("passing") as the meaning for P, and vrijgave ("release") as the meaning for V. It also mentions that the terminology is taken from that used in railroad signals. Dijkstra subsequently wrote that he intended P to stand for prolaag, short for probeer te verlagen, literally "try to reduce", or to parallel the terms used in the other case, "try to decrease".
In ALGOL 68, the Linux kernel, and in some English textbooks, the V and P operations are called, respectively, up and down. In software engineering practice, they are often called signal and wait, release and acquire (standard Java library), or post and pend. Some texts call them vacate and procure to match the original Dutch initials.

## Semaphores vs. mutexes

A mutex is a locking mechanism that sometimes uses the same basic implementation as the binary semaphore. However, they differ in how they are used. While a binary semaphore may be colloquially referred to as a mutex, a true mutex has a more specific use-case and definition, in that only the task that locked the mutex is supposed to unlock it. This constraint aims to handle some potential problems of using semaphores:

Priority inversion: If the mutex knows who locked it and is supposed to unlock it, it is possible to promote the priority of that task whenever a higher-priority task starts waiting on the mutex.
Premature task termination: Mutexes may also provide deletion safety, where the task holding the mutex cannot be accidentally deleted.   (This is also a cost; if the mutex can prevent a task from being reclaimed, then a garbage collector has to monitor the mutex.)
Termination deadlock: If a mutex-holding task terminates for any reason, the OS can release the mutex and signal waiting tasks of this condition.
Recursion deadlock: a task is allowed to lock a reentrant mutex multiple times as it unlocks it an equal number of times.
Accidental release: An error is raised on the release of the mutex if the releasing task is not its owner.
