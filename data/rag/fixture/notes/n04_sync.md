# Process synchronisation

## The critical-section problem
A race condition occurs when the outcome depends on the order in which threads access shared data. The code that touches the shared data is the critical section. A correct solution must guarantee mutual exclusion (at most one thread inside), progress (if nobody is inside, a waiting thread can enter without indefinite postponement) and bounded waiting (there is a limit on how many times others can enter ahead of a waiting thread).

## Mutex locks and semaphores
A mutex lock is acquired before the critical section and released after it. A spinlock busy-waits while the lock is held, which wastes CPU but avoids a context switch, so it suits short critical sections on multiprocessors. A semaphore is an integer accessed only through wait (P) and signal (V). A binary semaphore behaves like a mutex. A counting semaphore initialised to N allows up to N threads to use a pool of N identical resources.

## Monitors and condition variables
A monitor is a language construct in which only one thread may be active at a time. Inside it, condition variables let a thread wait until a condition holds; signal wakes one waiting thread. Unlike a semaphore's signal, a condition variable's signal has no effect if no thread is waiting.
