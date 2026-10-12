# Monitor (synchronization)

In concurrent programming, a monitor is a synchronization construct that prevents threads from concurrently accessing a shared object's state and allows them to wait for the state to change.  They provide a mechanism for threads to temporarily give up exclusive access in order to wait for some condition to be met, before regaining exclusive access and resuming their task.  A monitor consists of a mutex (lock) and at least one condition variable.  A condition variable is explicitly 'signalled' when the object's state is modified, temporarily passing the mutex to another thread 'waiting' on the condition variable.
Another definition of monitor is a thread-safe object, class, or module that contains and uses a mutex to safely allow access to its methods or variables by more than one thread.  The defining characteristic of a monitor is that its methods are executed with mutual exclusion: at each point in time, at most one thread may be executing any of the monitor's methods. By using one or more condition variables it can also provide the ability for threads to wait on a certain condition (thus using the first definition of a "monitor").  For the rest of this article, this sense of "monitor" will be referred to as a "thread-safe object/class/module."
Monitors were invented by Per Brinch Hansen and C. A. R. Hoare, and were first implemented in Brinch Hansen's Concurrent Pascal language.

## Mutual exclusion

While a thread is executing a method of a thread-safe object, it is said to occupy the object, by holding its mutex (lock).  Thread-safe objects are implemented to enforce that at any point in time, at most one thread may occupy the object.  The lock, which is initially unlocked, is locked at the start of each public method, and is unlocked at each return from each public method.
Upon calling one of the methods, a thread must wait until no other thread is executing any of the thread-safe object's methods before starting execution of its method. Note that without this mutual exclusion, two threads could cause data races and logical errors. For example, two threads withdrawing 1000 from the account could both return true, while causing the balance to drop by only 1000, as follows: first, both threads fetch the current balance, find it greater than 1000, and subtract 1000 from it; then, both threads store the balance and return.

## Condition variables

### Problem statement

For many applications, mutual exclusion is not enough. Threads attempting an operation may need to wait until some condition P holds true. A busy waiting loop

while not ( P ) do skip

will not work, as mutual exclusion will prevent any other thread from entering the monitor to make the condition true. Other "solutions" exist such as having a loop that unlocks the monitor, waits a certain amount of time, locks the monitor and checks for the condition P. Theoretically, it works and will not deadlock, but issues arise. It is hard to decide an appropriate amount of waiting time: too small and the thread will hog the CPU, too big and it will be apparently unresponsive. What is needed is a way to signal the thread when the condition P is true (or could be true).

### Case study: classic bounded producer/consumer problem

A classic concurrency problem is that of the bounded producer/consumer, in which there is a queue or ring buffer of tasks with a maximum size, with one or more threads being "producer" threads that add tasks to the queue, and one or more other threads being "consumer" threads that take tasks out of the queue.  The queue is assumed to be non–thread-safe itself, and it can be empty, full, or between empty and full.  Whenever the queue is full of tasks, then we need the producer threads to block until there is room from consumer threads dequeueing tasks.  On the other hand, whenever the queue is empty, then we need the consumer threads to block until more tasks are available due to producer threads adding them.
As the queue is a concurrent object shared between threads, accesses to it must be made atomic, because the queue can be put into an inconsistent state during the course of the queue access that should never be exposed between threads.  Thus, any code that accesses the queue constitutes a critical section that must be synchronized by mutual exclusion.  If code and processor instructions in critical sections of code that access the queue could be interleaved by arbitrary context switches between threads on the same processor or by simultaneously-running threads on multiple processors, then there is a risk of exposing inconsistent state and causing race conditions.

#### Incorrect without synchronization

A naive approach is to design the code with busy-waiting and no synchronization, making the code subject to race conditions:

This code has a serious problem in that accesses to the queue can be interrupted and interleaved with other threads' accesses to the queue.  The queue.enqueue and queue.dequeue methods likely have instructions to update the queue's member variables such as its size, beginning and ending positions, assignment and allocation of queue elements, etc.  In addition, the queue.isEmpty() and queue.isFull() methods read this shared state as well.  If producer/consumer threads are allowed to be interleaved during the calls to enqueue/dequeue, then inconsistent state of the queue can be exposed leading to race conditions.  In addition, if one consumer makes the queue empty in-between another consumer's exiting the busy-wait and calling "dequeue", then the second consumer will attempt to dequeue from an empty queue leading to an error.  Likewise, if a producer makes the queue full in-between another producer's exiting the busy-wait and calling "enqueue", then the second producer will attempt to add to a full queue leading to an error.

#### Spin-waiting

One naive approach to achieve synchronization, as alluded to above, is to use "spin-waiting", in which a mutex is used to protect the critical sections of code and busy-waiting is still used, with the lock being acquired and released in between each busy-wait check.

This method assures that an inconsistent state does not occur, but wastes CPU resources due to the unnecessary busy-waiting.  Even if the queue is empty and producer threads have nothing to add for a long time, consumer threads are always busy-waiting unnecessarily.  Likewise, even if consumers are blocked for a long time on processing their current tasks and the queue is full, producers are always busy-waiting.  This is a wasteful mechanism.  What is needed is a way to make producer threads block until the queue is non-full, and a way to make consumer threads block until the queue is non-empty.
(N.B.: Mutexes themselves can also be spin-locks which involve busy-waiting in order to get the lock, but in order to solve this problem of wasted CPU resources, we assume that queueLock is not a spin-lock and properly uses a blocking lock queue itself.)

### Condition variables

The solution is to use condition variables. Conceptually, a condition variable is a queue of threads, associated with a mutex, on which a thread may wait for some condition to become true. Thus each condition variable c is associated with an assertion Pc. While a thread is waiting on a condition variable, that thread is not considered to occupy the monitor, and so other threads may enter the monitor to change the monitor's state. In most types of monitors, these other threads may signal the condition variable c to indicate that assertion Pc is true in the current state.
Thus there are three main operations on condition variables:

wait c, m, where c is a condition variable and m is a mutex (lock) associated with the monitor.  This operation is called by a thread that needs to wait until the assertion Pc is true before proceeding.  While the thread is waiting, it does not occupy the monitor.  The function, and fundamental contract, of the "wait" operation, is to do the following steps:
Atomically:

Once this thread is subsequently notified/signaled (see below) and resumed, then automatically re-acquire the mutex m.
Steps 1a and 1b can occur in either order, with 1c usually occurring after them.  While the thread is sleeping and in c's wait-queue, the next program counter to be executed is at step 2, in the middle of the "wait" function/subroutine.  Thus, the thread sleeps and later wakes up in the middle of the "wait" operation.
The atomicity of the operations within step 1 is important to avoid race conditions that would be caused by a preemptive thread switch in-between them.  One failure mode that could occur if these were not atomic is a missed wakeup, in which the thread could be on c's sleep-queue and have released the mutex, but a preemptive thread switch occurred before the thread went to sleep, and another thread called a signal operation (see below) on c moving the first thread back out of c's queue.  As soon as the first thread in question is switched back to, its program counter will be at step 1c, and it will sleep and be unable to be woken up again, violating the invariant that it should have been on c's sleep-queue when it slept.  Other race conditions depend on the ordering of steps 1a and 1b, and depend on where a context switch occurs.
signal c, also known as notify c, is called by a thread to indicate that the assertion Pc is true.  Depending on the type and implementation of the monitor, this moves one or more threads from c's sleep-queue to the "ready queue", or another queue for it to be executed.  It is usually considered a best practice to perform the "signal" operation before releasing mutex m that is associated with c, but as long as the code is properly designed for concurrency and depending on the threading implementation, it is often also acceptable to release the lock before signalling.  Depending on the threading implementation, the ordering of this can have scheduling-priority ramifications.  (Some authors instead advocate a preference for releasing the lock before signalling.)  A threading implementation should document any special constraints on this ordering.
broadcast c, also known as notifyAll c, is a similar operation that wakes up all threads in c's wait-queue.  This empties the wait-queue.  Generally, when more than one predicate condition is associated with the same condition variable, the application will require broadcast instead of signal because a thread waiting for the wrong condition might be woken up and then immediately go back to sleep without waking up a thread waiting for the correct condition that just became true.  Otherwise, if the predicate condition is one-to-one with the condition variable associated with it, then signal may be more efficient than broadcast.
As a design rule, multiple condition variables can be associated with the same mutex, but not vice versa.  (This is a one-to-many correspondence.)  This is because the predicate Pc is the same for all threads using the monitor and must be protected with mutual exclusion from all other threads that might cause the condition to be changed or that might read it while the thread in question causes it to be changed, but there may be different threads that want to wait for a different condition on the same variable requiring the same mutex to be used.  In the producer-consumer example described above, the queue must be protected by a unique mutex object, m.  The "producer" threads will want to wait on a monitor using lock m and a condition variable 
  
    
      
        
          c
          
            f
            u
            l
            l
          
        
      
    
    {\displaystyle c_{full}}
  
 which blocks until the queue is non-full.  The "consumer" threads will want to wait on a different monitor using the same mutex m but a different condition variable 
  
    
      
        
          c
          
            e
            m
            p
            t
            y
          
        
      
    
    {\displaystyle c_{empty}}
  
 which blocks until the queue is non-empty.  It would (usually) not make sense to have different mutexes for the same condition variable, but this classic example shows why it often certainly makes sense to have multiple condition variables using the same mutex.  A mutex used by one or more condition variables (one or more monitors) may also be shared with code that does not use condition variables (and which simply acquires/releases it without any wait/signal operations), if those critical sections do not happen to require waiting for a certain condition on the concurrent data.

### Monitor usage

The proper basic usage of a monitor is:

The following is the same pseudocode but with more verbose comments to better explain what is going on:

#### Solving the bounded producer/consumer problem

Having introduced the usage of condition variables, let us use it to revisit and solve the classic bounded producer/consumer problem.  The classic solution is to use two monitors, comprising two condition variables sharing one lock on the queue:

This ensures concurrency between the producer and consumer threads sharing the task queue, and blocks the threads that have nothing to do rather than busy-waiting as shown in the aforementioned approach using spin-locks.
A variant of this solution could use a single condition variable for both producers and consumers, perhaps named "queueFullOrEmptyCV" or "queueSizeChangedCV".  In this case, more than one condition is associated with the condition variable, such that the condition variable represents a weaker condition than the conditions being checked by individual threads.  The condition variable represents threads that are waiting for the queue to be non-full and ones waiting for it to be non-empty.  However, doing this would require using broadcast in all the threads using the condition variable and cannot use a regular signal.  This is because the regular signal might wake up a thread of the wrong type whose condition has not yet been met, and that thread would go back to sleep without a thread of the correct type getting signaled.  For example, a producer might make the queue full and wake up another producer instead of a consumer, and the woken producer would go back to sleep.  In the complementary case, a consumer might make the queue empty and wake up another consumer instead of a producer, and the consumer would go back to sleep.  Using broadcast ensures that some thread of the right type will proceed as expected by the problem statement.
Here is the variant using only one condition variable and broadcast:

### Synchronization primitives

Monitors are implemented using an atomic read-modify-write primitive and a waiting primitive. The read-modify-write primitive (usually test-and-set or compare-and-swap) is usually in the form of a memory-locking instruction provided by the ISA, but can also be composed of non-locking instructions on single-processor devices when interrupts are disabled. The waiting primitive can be a busy-wait loop or an OS-provided primitive that prevents the thread from being scheduled until it is ready to proceed.
Here is an example pseudocode implementation of parts of a threading system and mutexes and Mesa-style condition variables, using test-and-set and a first-come, first-served policy:

#### Sample Mesa-monitor implementation with Test-and-Set

### Blocking condition variables

The original proposals by C. A. R. Hoare and Per Brinch Hansen were for blocking condition variables. With a blocking condition variable, the signaling thread must wait outside the monitor (at least) until the signaled thread relinquishes occupancy of the monitor by either returning or by again waiting on a condition variable. Monitors using blocking condition variables are often called Hoare-style monitors or signal-and-urgent-wait monitors.

We assume there are two queues of threads associated with each monitor object

e is the entrance queue
s is a queue of threads that have signaled.
In addition we assume that for each condition variable c, there is a queue

c.q, which is a queue for threads waiting on condition variable c
All queues are typically guaranteed to be fair and, in some implementations, may be guaranteed to be first in first out.
The implementation of each operation is as follows. (We assume that each operation runs in mutual exclusion to the others; thus restarted threads do not begin executing until the operation is complete.)

enter the monitor:
    enter the method
    if the monitor is locked
        add this thread to e
        block this thread
    else
        lock the monitor

leave the monitor:
    schedule
    return from the method

wait c:
    add this thread to c.q
    schedule
    block this thread

signal c:
    if there is a thread waiting on c.q
        select and remove one such thread t from c.q
        (t is called "the signaled thread")
        add this thread to s
        restart t
        (so t will occupy the monitor next)
        block this thread

schedule:
    if there is a thread on s
        select and remove one thread from s and restart it
        (this thread will occupy the monitor next)
    else if there is a thread on e
        select and remove one thread from e and restart it
        (this thread will occupy the monitor next)
    else
        unlock the monitor
        (the monitor will become unoccupied)

The schedule routine selects the next thread to occupy the monitor
or, in the absence of any candidate threads, unlocks the monitor.
The resulting signaling discipline is known as "signal and urgent wait," as the signaler must wait, but is given priority over threads on the entrance queue. An alternative is "signal and wait," in which there is no s queue and signaler waits on the e queue instead.
Some implementations provide a signal and return operation that combines signaling with returning from a procedure.

signal c and return:
    if there is a thread waiting on c.q
        select and remove one such thread t from c.q
        (t is called "the signaled thread")
        restart t
        (so t will occupy the monitor next)
    else
        schedule
    return from the method

In either case ("signal and urgent wait" or "signal and wait"), when a condition variable is signaled and there is at least one thread waiting on the condition variable, the signaling thread hands occupancy over to the signaled thread seamlessly, so that no other thread can gain occupancy in between. If Pc is true at the start of each signal c operation, it will be true at the end of each wait c operation. This is summarized by the following contracts. In these contracts, I is the monitor's invariant.

enter the monitor:
    postcondition I

leave the monitor:
    precondition I

wait c:
    precondition I
    modifies the state of the monitor
    postcondition Pc and I

signal c:
    precondition Pc and I
    modifies the state of the monitor
    postcondition I

signal c and return:
    precondition Pc and I

In these contracts, it is assumed that I and Pc do not depend on the
contents or lengths of any queues.
(When the condition variable can be queried as to the number of threads waiting on its queue, more sophisticated contracts can be given. For example, a useful pair of contracts, allowing occupancy to be passed without establishing the invariant, is:

wait c:
    precondition I
    modifies the state of the monitor
    postcondition Pc

signal c
    precondition (not empty(c) and Pc) or (empty(c) and I)
    modifies the state of the monitor
    postcondition I

(See Howard and Buhr et al. for more.)
The assertion Pc is entirely up to the programmer; he or she simply needs to be consistent about what it is.
We conclude this section with an example of a thread-safe class using a blocking monitor that implements a bounded, thread-safe stack.

monitor class SharedStack {
    private const capacity := 10
    private int[capacity] A
    private int size := 0
    invariant 0 <= size and size <= capacity
    private BlockingCondition theStackIsNotEmpty /* associated with 0 < size and size <= capacity */
    private BlockingCondition theStackIsNotFull /* associated with 0 <= size and size < capacity */

    public method push(int value)
    {
        if size = capacity then wait theStackIsNotFull
        assert 0 <= size and size < capacity
        A[size] := value ; size := size + 1
        assert 0 < size and size <= capacity
        signal theStackIsNotEmpty and return
    }

    public method int pop()
    {
        if size = 0 then wait theStackIsNotEmpty
        assert 0 < size and size <= capacity
        size := size - 1 ;
        assert 0 <= size and size < capacity
        signal theStackIsNotFull and return A[size]
    }
}

Note that, in this example, the thread-safe stack is internally providing a mutex, which, as in the earlier producer/consumer example, is shared by both condition variables, which are checking different conditions on the same concurrent data.  The only difference is that the producer/consumer example assumed a regular non-thread-safe queue and was using a standalone mutex and condition variables, without these details of the monitor abstracted away, as is the case here.  In this example, when the "wait" operation is called, it must somehow be supplied with the thread-safe stack's mutex, such as if the "wait" operation is an integrated part of the "monitor class".  Aside from this kind of abstracted functionality, when a "raw" monitor is used, it will always have to include a mutex and a condition variable, with a unique mutex for each condition variable.

### Nonblocking condition variables

With nonblocking condition variables (also called "Mesa style" condition variables or "signal and continue" condition variables), signaling does not cause the signaling thread to lose occupancy of the monitor. Instead, the signaled threads are moved to the e queue. There is no need for the s queue.

With nonblocking condition variables, the signal operation is often called notify — a terminology we will follow here. It is also common to provide a notify all operation that moves all threads waiting on a condition variable to the e queue.
The meaning of various operations are given here. (We assume that each operation runs in mutual exclusion to the others; thus restarted threads do not begin executing until the operation is complete.)

enter the monitor:
    enter the method
    if the monitor is locked
        add this thread to e
        block this thread
    else
        lock the monitor

leave the monitor:
    schedule
    return from the method

wait c:
    add this thread to c.q
    schedule
    block this thread

notify c:
    if there is a thread waiting on c.q
        select and remove one thread t from c.q
        (t is called "the notified thread")
        move t to e

notify all c:
    move all threads waiting on c.q to e

schedule :
    if there is a thread on e
        select and remove one thread from e and restart it
    else
        unlock the monitor

As a variation on this scheme, the notified thread may be moved to a queue called w, which has priority over e. See Howard and Buhr et al. for further discussion.
It is possible to associate an assertion Pc with each condition variable c such that Pc is sure to be true upon return from wait c. However, one must
ensure that Pc is preserved from the time the notifying thread gives up occupancy until the notified thread is selected to re-enter the monitor. Between these times, there could be activity by other occupants. Thus, it is common for Pc to simply be true.
For this reason, it is usually necessary to enclose each wait operation in a loop like this

while not ( P ) do
    wait c

where P is some condition stronger than Pc. The operations notify c and notify all c are treated as "hints" that P may be true for some waiting thread.
Every iteration of such a loop past the first represents a lost notification; thus with nonblocking monitors, one must be careful to ensure that too many notifications cannot be lost.
As an example of "hinting," consider a bank account in which a withdrawing thread will wait until the account has sufficient funds before proceeding

monitor class Account {
    private int balance := 0
    invariant balance >= 0
    private NonblockingCondition balanceMayBeBigEnough

    public method withdraw(int amount)
        precondition amount >= 0
    {
        while balance < amount do wait balanceMayBeBigEnough
        assert balance >= amount
        balance := balance - amount
    }

    public method deposit(int amount)
        precondition amount >= 0
    {
        balance := balance + amount
        notify all balanceMayBeBigEnough
    }
}

In this example, the condition being waited for is a function of the amount to be withdrawn, so it is impossible for a depositing thread to know that it made such a condition true. It makes sense in this case to allow each waiting thread into the monitor (one at a time) to check if its assertion is true.

### Implicit condition variable monitors

In the Java language, each object may be used as a monitor. Methods requiring mutual exclusion must be explicitly marked with the synchronized keyword. Blocks of code may also be marked by synchronized.
Rather than having explicit condition variables, each monitor (i.e., object) is equipped with a single wait queue in addition to its entrance queue. All waiting is done on this single wait queue and all notify and notifyAll operations apply to this queue. This approach has been adopted in other languages, for example C#.

### Implicit signaling

Another approach to signaling is to omit the signal operation. Whenever a thread leaves the monitor (by returning or waiting), the assertions of all waiting threads are evaluated until one is found to be true. In such a system, condition variables are not needed, but the assertions must be explicitly coded. The contract for wait is

wait P:
    precondition I
    modifies the state of the monitor
    postcondition P and I

## History

Brinch Hansen and Hoare developed the monitor concept in the early 1970s, based on earlier ideas of their own and of Edsger Dijkstra. Brinch Hansen published the first monitor notation, adopting the class concept of Simula 67, and invented a queueing mechanism. Hoare refined the rules of process resumption. Brinch Hansen created the first implementation of monitors, in Concurrent Pascal. Hoare demonstrated their equivalence to semaphores.
Monitors (and Concurrent Pascal) were soon used to structure process synchronization in the Solo operating system.
Programming languages that have supported monitors include:

Ada since Ada 95 (as protected objects)
C# (and other languages that use the .NET Framework)
Concurrent Euclid
Concurrent Pascal
D
Delphi (Delphi 2009 and above, via TObject.Monitor)
Java (via the wait and notify methods)
Go
Mesa
Modula-3
Python (via threading.Condition object)
Ruby
Squeak Smalltalk
Turing, Turing+, and Object-Oriented Turing
μC++
Visual Prolog
A number of libraries have been written that allow monitors to be constructed in languages that do not support them natively. When library calls are used, it is up to the programmer to explicitly mark the start and end of code executed with mutual exclusion. Pthreads is one such library.
