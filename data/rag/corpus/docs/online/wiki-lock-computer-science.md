# Lock (computer science)

In computer science, a lock or mutex (from mutual exclusion) is a synchronization primitive that prevents state from being modified or accessed by multiple threads of execution at once. Locks enforce mutual exclusion concurrency control policies, and with a variety of possible methods there exist multiple unique implementations for different applications.

## Types

Generally, locks are advisory locks, where each thread cooperates by acquiring the lock before accessing the corresponding data. Some systems also implement mandatory locks, where attempting unauthorized access to a locked resource will force an exception in the entity attempting to make the access.
The simplest type of lock is a binary semaphore. It provides exclusive access to the locked data. Other schemes also provide shared access for reading data. Other widely implemented access modes are exclusive, intend-to-exclude and intend-to-upgrade.
Another way to classify locks is by what happens when the lock strategy prevents the progress of a thread. Most locking designs block the execution of the thread requesting the lock until it is allowed to access the locked resource. With a spinlock, the thread simply waits ("spins") until the lock becomes available. This is efficient if threads are blocked for a short time, because it avoids the overhead of operating system process rescheduling. It is inefficient if the lock is held for a long time, or if the progress of the thread that is holding the lock depends on preemption of the locked thread.
Locks typically require hardware support for efficient implementation. This support usually takes the form of one or more atomic instructions such as "test-and-set", "fetch-and-add" or "compare-and-swap". These instructions allow a single process to test if the lock is free, and if free, acquire the lock in a single atomic operation.
Uniprocessor architectures have the option of using uninterruptible sequences of instructions—using special instructions or instruction prefixes to disable interrupts temporarily—but this technique does not work for multiprocessor shared-memory machines. Proper support for locks in a multiprocessor environment can require quite complex hardware or software support, with substantial synchronization issues.
The reason an atomic operation is required is because of concurrency, where more than one task executes the same logic. For example, consider the following C code:

The above example does not guarantee that the task has the lock, since more than one task can be testing the lock at the same time. Since both tasks will detect that the lock is free, both tasks will attempt to set the lock, not knowing that the other task is also setting the lock. Dekker's or Peterson's algorithm are possible substitutes if atomic locking operations are not available.
Careless use of locks can result in deadlock or livelock. A number of strategies can be used to avoid or recover from deadlocks or livelocks, both at design-time and at run-time. (The most common strategy is to standardize the lock acquisition sequences so that combinations of inter-dependent locks are always acquired in a specifically defined "cascade" order.)
Some languages do support locks syntactically. An example in C# follows:

C# introduced System.Threading.Lock in C# 13 on .NET 9.
The code lock(this) can lead to problems if the instance can be accessed publicly.
Similar to Java, C# can also synchronize entire methods, by using the MethodImplOptions.Synchronized attribute.

## Granularity

Before being introduced to lock granularity, one needs to understand three concepts about locks:

lock overhead: the extra resources for using locks, like the memory space allocated for locks, the CPU time to initialize and destroy locks, and the time for acquiring or releasing locks. The more locks a program uses, the more overhead associated with the usage;
lock contention: this occurs whenever one process or thread attempts to acquire a lock held by another process or thread. The more fine-grained the available locks, the less likely one process/thread will request a lock held by the other. (For example, locking a row rather than the entire table, or locking a cell rather than the entire row);
deadlock: the situation when each of at least two tasks is waiting for a lock that the other task holds. Unless something is done, the two tasks will wait forever.
There is a tradeoff between decreasing lock overhead and decreasing lock contention when choosing the number of locks in synchronization.
An important property of a lock is its granularity. The granularity is a measure of the amount of data the lock is protecting. In general, choosing a coarse granularity (a small number of locks, each protecting a large segment of data) results in less lock overhead when a single process is accessing the protected data, but worse performance when multiple processes are running concurrently. This is because of increased lock contention. The more coarse the lock, the higher the likelihood that the lock will stop an unrelated process from proceeding. Conversely, using a fine granularity (a larger number of locks, each protecting a fairly small amount of data) increases the overhead of the locks themselves but reduces lock contention. Granular locking where each process must hold multiple locks from a common set of locks can create subtle lock dependencies. This subtlety can increase the chance that a programmer will unknowingly introduce a deadlock.
In a database management system, for example, a lock could protect, in order of decreasing granularity, part of a field, a field, a record, a data page, or an entire table. Coarse granularity, such as using table locks, tends to give the best performance for a single user, whereas fine granularity, such as record locks, tends to give the best performance for multiple users.

## Database locks

Database locks can be used as a means of ensuring transaction synchronicity. i.e. when making transaction processing concurrent (interleaving transactions), using 2-phased locks ensures that the concurrent execution of the transaction turns out equivalent to some serial ordering of the transaction. However, deadlocks become an unfortunate side-effect of locking in databases. Deadlocks are either prevented by pre-determining the locking order between transactions or are detected using waits-for graphs. An alternate to locking for database synchronicity while avoiding deadlocks involves the use of totally ordered global timestamps.
There are mechanisms employed to manage the actions of multiple concurrent users on a database—the purpose is to prevent lost updates and dirty reads. The two types of locking are pessimistic locking and optimistic locking:

Pessimistic locking: a user who reads a record with the intention of updating it places an exclusive lock on the record to prevent other users from manipulating it. This means no one else can manipulate that record until the user releases the lock. The downside is that users can be locked out for a very long time, thereby slowing the overall system response and causing frustration.
Where to use pessimistic locking: this is mainly used in environments where data-contention (the degree of users request to the database system at any one time) is heavy; where the cost of protecting data through locks is less than the cost of rolling back transactions, if concurrency conflicts occur. Pessimistic concurrency is best implemented when lock times will be short, as in programmatic processing of records. Pessimistic concurrency requires a persistent connection to the database and is not a scalable option when users are interacting with data, because records might be locked for relatively large periods of time. It is not appropriate for use in Web application development.
Optimistic locking: this allows multiple concurrent users access to the database whilst the system keeps a copy of the initial-read made by each user. When a user wants to update a record, the application determines whether another user has changed the record since it was last read. The application does this by comparing the initial-read held in memory to the database record to verify any changes made to the record. Any discrepancies between the initial-read and the database record violates concurrency rules and hence causes the system to disregard any update request. An error message is generated and the user is asked to start the update process again. It improves database performance by reducing the amount of locking required, thereby reducing the load on the database server. It works efficiently with tables that require limited updates since no users are locked out. However, some updates may fail. The downside is constant update failures due to high volumes of update requests from multiple concurrent users - it can be frustrating for users.
Where to use optimistic locking: this is appropriate in environments where there is low contention for data, or where read-only access to data is required. Optimistic concurrency is used extensively in .NET to address the needs of mobile and disconnected applications, where locking data rows for prolonged periods of time would be infeasible. Also, maintaining record locks requires a persistent connection to the database server, which is not possible in disconnected applications.

## Lock compatibility table

Several variations and refinements of these major lock types exist, with respective variations of blocking behavior. If a first lock blocks another lock, the two locks are called incompatible; otherwise the locks are compatible. Often, lock types blocking interactions are presented in the technical literature by a Lock compatibility table. The following is an example with the common, major lock types:

✔ indicates compatibility
X indicates incompatibility, i.e., a case when a lock of the first type (in left column) on an object blocks a lock of the second type (in top row) from being acquired on the same object (by another transaction). An object typically has a queue of waiting requested (by transactions) operations with respective locks. The first blocked lock for operation in the queue is acquired as soon as the existing blocking lock is removed from the object, and then its respective operation is executed. If a lock for operation in the queue is not blocked by any existing lock (existence of multiple compatible locks on a same object is possible concurrently), it is acquired immediately.
Comment: In some publications, the table entries are simply marked "compatible" or "incompatible", or respectively "yes" or "no".

## Disadvantages

Lock-based resource protection and thread/process synchronization have many disadvantages:

Contention: some threads/processes have to wait until a lock (or a whole set of locks) is released. If one of the threads holding a lock dies, stalls, blocks, or enters an infinite loop, other threads waiting for the lock may wait indefinitely until the computer is power cycled.
Overhead: the use of locks adds overhead for each access to a resource, even when the chances for collision are very rare. (However, any chance for such collisions is a race condition.)
Debugging: bugs associated with locks are time dependent and can be very subtle and extremely hard to replicate, such as deadlocks.
Instability: the optimal balance between lock overhead and lock contention can be unique to the problem domain (application) and sensitive to design, implementation, and even low-level system architectural changes. These balances may change over the life cycle of an application and may entail tremendous changes to update (re-balance).
Composability: locks are only composable (e.g., managing multiple concurrent locks in order to atomically delete item X from table A and insert X into table B) with relatively elaborate (overhead) software support and perfect adherence by applications programming to rigorous conventions.
Priority inversion: a low-priority thread/process holding a common lock can prevent high-priority threads/processes from proceeding. Priority inheritance can be used to reduce priority-inversion duration. The priority ceiling protocol can be used on uniprocessor systems to minimize the worst-case priority-inversion duration, as well as prevent deadlock.
Convoying: all other threads have to wait if a thread holding a lock is descheduled due to a time-slice interrupt or page fault.
Some concurrency control strategies avoid some or all of these problems. For example, a funnel or serializing tokens can avoid the biggest problem: deadlocks. Alternatives to locking include non-blocking synchronization methods, like lock-free programming techniques and transactional memory. However, such alternative methods often require that the actual lock mechanisms be implemented at a more fundamental level of the operating software. Therefore, they may only relieve the application level from the details of implementing locks, with the problems listed above still needing to be dealt with beneath the application.
In most cases, proper locking depends on the CPU providing a method of atomic instruction stream synchronization (for example, the addition or deletion of an item into a pipeline requires that all contemporaneous operations needing to add or delete other items in the pipe be suspended during the manipulation of the memory content required to add or delete the specific item). Therefore, an application can often be more robust when it recognizes the burdens it places upon an operating system and is capable of graciously recognizing the reporting of impossible demands.

### Lack of composability

One of lock-based programming's biggest problems is that "locks don't compose": it is hard to combine small, correct lock-based modules into equally correct larger programs without modifying the modules or at least knowing about their internals. Simon Peyton Jones (an advocate of software transactional memory) gives the following example of a banking application: design a class Account that allows multiple concurrent clients to deposit or withdraw money to an account, and give an algorithm to transfer money from one account to another.
The lock-based solution to the first part of the problem is:

class Account:
    member balance: Integer
    member mutex: Lock

    method deposit(n: Integer)
           mutex.lock()
           balance ← balance + n
           mutex.unlock()

    method withdraw(n: Integer)
           deposit(−n)

The second part of the problem is much more complicated. A transfer routine that is correct for sequential programs would be

function transfer(from: Account, to: Account, amount: Integer)
    from.withdraw(amount)
    to.deposit(amount)

In a concurrent program, this algorithm is incorrect because when one thread is halfway through transfer, another might observe a state where amount has been withdrawn from the first account, but not yet deposited into the other account: money has gone missing from the system. This problem can only be fixed completely by putting locks on both accounts prior to changing either one, but then the locks have to be placed according to some arbitrary, global ordering to prevent deadlock:

function transfer(from: Account, to: Account, amount: Integer)
    if from < to    // arbitrary ordering on the locks
        from.lock()
        to.lock()
    else
        to.lock()
        from.lock()
    from.withdraw(amount)
    to.deposit(amount)
    from.unlock()
    to.unlock()

This solution gets more complicated when more locks are involved, and the transfer function needs to know about all of the locks, so they cannot be hidden.

## Language support

Programming languages vary in their support for synchronization:

Ada provides protected objects that have visible protected subprograms or entries as well as rendezvous.
The ISO/IEC C standard provides a standard mutual exclusion (locks) application programming interface (API) since C11, in header <threads.h>, with various mutex-manipulating functions.
The OpenMP standard is supported by some compilers, and allows critical sections to be specified using pragmas.
The POSIX pthread API provides lock support. C and C++ can easily access any native operating system locking features.
The current ISO/IEC C++ standard supports threading facilities since C++11. In particular, it provides the class std::mutex, as well as various lock classes like std::lock_guard, std::unique_lock, and std::scoped_lock in header <mutex>.
Visual C++ provides the synchronize attribute of methods to be synchronized, but this is specific to COM objects in the Windows architecture and Visual C++ compiler.
C# provides the lock keyword on a thread to ensure its exclusive access to a resource, as well as the System.Threading.Lock class.
Visual Basic (.NET) provides a SyncLock keyword like C#'s lock keyword.
Java provides the keyword synchronized to lock code blocks, methods or objects and libraries featuring concurrency-safe data structures. Java also features the interface java.util.concurrent.locks.Lock.
Objective-C provides the keyword @synchronized to put locks on blocks of code and also provides the classes NSLock, NSRecursiveLock, and NSConditionLock along with the NSLocking protocol for locking as well.
PHP provides a file-based locking  as well as a Mutex class in the pthreads extension.
Python provides a low-level mutex mechanism with class threading.Lock.
The ISO/IEC Fortran standard (ISO/IEC 1539-1:2010) provides the lock_type derived type in the intrinsic module iso_fortran_env and the lock/unlock statements since Fortran 2008.
Ruby provides a low-level mutex object and no keyword.
Rust provides the std::sync::Mutex<T> struct.
x86 assembly language provides the LOCK prefix on certain operations to guarantee their atomicity.
Haskell implements locking via a mutable data structure called an MVar, which can either be empty or contain a value, typically a reference to a resource. A thread that wants to use the resource ‘takes’ the value of the MVar, leaving it empty, and puts it back when it is finished. Attempting to take a resource from an empty MVar results in the thread blocking until the resource is available. As an alternative to locking, an implementation of software transactional memory also exists.
Go provides a low-level Mutex object, sync.Mutex in standard's library sync package. It can be used for locking code blocks, methods or objects.

## Mutexes vs. semaphores
