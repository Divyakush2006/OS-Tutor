# Readers–writers problem

In computer science, the readers–writers problems are examples of a common computing problem in concurrency. There are at least three variations of the problems, which deal with situations in which many concurrent threads of execution try to access the same shared resource at one time.
Some threads may read and some may write, with the constraint that no thread may access the shared resource for either reading or writing while another thread is in the act of writing to it. (In particular, we want to prevent more than one thread modifying the shared resource simultaneously and allow for two or more readers to access the shared resource at the same time). A readers–writer lock is a data structure that solves one or more of the readers–writers problems.
The basic reader–writers problem was first formulated and solved by Courtois et al.

## First readers–writers problem

Suppose we have a shared memory area (critical section) with the basic constraints detailed above. It is possible to protect the shared data behind a mutual exclusion mutex, in which case no two threads can access the data at the same time. However, this solution is sub-optimal, because it is possible that a reader R1 might have the lock, and then another reader R2 requests access. It would be foolish for R2 to wait until R1 was done before starting its own read operation; instead, R2 should be allowed to read the resource alongside R1 because reads don't modify data, so concurrent reads are safe. This is the motivation for the first readers–writers problem, in which the constraint is added that no reader shall be kept waiting if the share is currently opened for reading.  This is also called readers-preference, with its solution:

In this solution of the readers/writers problem, the first reader must lock the resource (shared file) if such is available. Once the file is locked from writers, it may be used by many subsequent readers without having them to re-lock it again.
Before entering the critical section, every new reader must go through the entry section. However, there may only be a single reader in the entry section at a time. This is done to avoid race conditions on the readers (in this context, a race condition is a condition in which two or more threads are waking up simultaneously and trying to enter the critical section; without further constraint, the behavior is nondeterministic.  E.g. two readers increment the readcount at the same time, and both try to lock the resource, causing one reader to block).  To accomplish this, every reader which enters the <ENTRY Section> will lock the <ENTRY Section> for themselves until they are done with it. At this point the readers are not locking the resource. They are only locking the entry section so no other reader can enter it while they are in it. Once the reader is done executing the entry section, it will unlock it by signaling the mutex. Signaling it is equivalent to: mutex.V() in the above code. Same is valid for the <EXIT Section>. There can be no more than a single reader in the exit section at a time, therefore, every reader must claim and lock the Exit section for themselves before using it.
Once the first reader is in the entry section, it will lock the resource. Doing this will prevent any writers from accessing it. Subsequent readers can just utilize the locked (from writers) resource. The reader to finish last (indicated by the readcount variable) must unlock the resource, thus making it available to writers.
In this solution, every writer must claim the resource individually. This means that a stream of readers can subsequently lock all potential writers out and starve them. This is so, because after the first reader locks the resource, no writer can lock it, before it gets released. And it will only be released by the last reader. Hence, this solution does not satisfy fairness.

## Second readers–writers problem

The first solution has a downside in that it can result in resource starvation, where it becomes impossible to write to a file if it is constantly being read from. If a reader R1 has the lock while a writer W is waiting for the lock, and then a reader R2 requests access, it could be considered "unfair" for R2 to jump in immediately, ahead of W. This is the motivation for the second readers–writers problem, in which the constraint is added that no writer, once added to the queue, shall be kept waiting longer than absolutely necessary. This is also called writers-preference.
A solution to the writers-preference scenario is:

In this solution, preference is given to the writers. This is accomplished by forcing every reader to lock and release the readTry semaphore individually. Thus, only one reader will be able to signify that it is trying to read at a given time by attempting to acquire the reader_mutex semaphore. At this point, if one or more writers have declared themselves, the first one will have already acquired the reader_mutex semaphore, causing the reader to block. Only once there are no other writers will that reader be able to proceed. Since readcount is modified in multiple places, access to it must be locked behind readcount_mutex.
Multiple writers can declare themselves by incrementing writecount; however, only the first writer will lock the reader_mutex to prevent readers from proceeding. Subsequent writers then use the resource sequentially by acquiring the writer_mutex before the write operation and releasing it after. The very last writer must release the reader_mutex semaphore, thus opening the gate for readers to try reading.
Note that if and only if there are no writers, the readTry and reader_mutex semaphores are redundant with readcount_mutex, serving only to prevent race conditions on the readcount variable. Multiple readers will thus be allowed to declare themselves and read the shared data simultaneously.

## Third readers–writers problem

In fact, the solutions implied by both problem statements can result in starvation — the first one may starve writers in the queue, and the second one may starve readers. Therefore, the third readers–writers problem is sometimes proposed, which adds the constraint that no thread shall be allowed to starve; that is, the operation of obtaining a lock on the shared data will always terminate in a bounded amount of time.
A solution with fairness for both readers and writers might be as follows:

This solution can only satisfy the condition that "no thread shall be allowed to starve" if and only if semaphores preserve first-in first-out ordering when blocking and releasing threads. Otherwise, a blocked writer, for example, may remain blocked indefinitely with a cycle of other writers decrementing the semaphore before it can.

### Simplest reader writer problem

The simplest reader writer problem which uses only two semaphores and doesn't need an array of readers to read the data in buffer.
Please notice that this solution gets simpler than the general case because it is made equivalent to the Bounded buffer problem, and therefore only N readers are allowed to enter in parallel, N being the size of the buffer. The initial value of read and write semaphores are 0 and N respectively.

#### Reader

#### Writer

#### Algorithm

Reader will run after Writer because of read semaphore.
Writer will stop writing when the write semaphore has reached 0.
Reader will stop reading when the read semaphore has reached 0.
In writer, the value of write semaphore is given to read semaphore and in reader, the value of read is given to write on completion of the loop.
