# Threads

## Threads versus processes
A thread is a unit of CPU execution inside a process. Threads of one process share its code, data, heap and open files, but each thread has its own program counter, registers and stack. Creating a thread is cheaper than creating a process, and switching between threads of the same process is cheaper than a process context switch because the address space does not change.

## Why threads help
Threads improve responsiveness, because one thread can keep serving a user while another waits for I/O. They allow resource sharing without explicit inter-process communication. On a multicore machine they let one program use several cores at once, which is parallelism; on a single core they still give concurrency, which is interleaving.

## Threading models
In the many-to-one model, many user threads map onto one kernel thread, so one blocking system call blocks them all and they cannot run in parallel. The one-to-one model maps each user thread to its own kernel thread; Linux and Windows use it. The many-to-many model multiplexes many user threads onto a smaller or equal number of kernel threads.
