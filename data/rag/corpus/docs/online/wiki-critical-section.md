# Critical section

In concurrent programming, concurrent accesses to shared resources can lead to unexpected or erroneous behavior. Thus, the parts of the program where the shared resource is accessed need to be protected in ways that avoid the concurrent access. One way to do so is known as a critical section or critical region. This protected section cannot be entered by more than one process or thread at a time; others are suspended until the first leaves the critical section. Typically, the critical section accesses a shared resource, such as a data structure, peripheral device, or network connection, that would not operate correctly in the context of multiple concurrent accesses.

## Need for critical sections

Different code or processes may consist of the same variable or other resources that must be read or written but whose results depend on the order in which the actions occur. For example, if a variable x is to be read by process A, and process B must write to the variable x at the same time, process A might get either the old or new value of x.

Process A:

Process B:

In cases where a locking mechanism with finer granularity is not needed, a critical section is important. In the above case, if A needs to read the updated value of x, executing process A, and process B at the same time may not give required results. To prevent this, variable x is protected by a critical section. First, B gets the access to the section. Once B finishes writing the value, A gets the access to the critical section, and variable x can be read.
By carefully controlling which variables are modified inside and outside the critical section, concurrent access to the shared variable is prevented. A critical section is typically used when a multi-threaded program must update multiple related variables without a separate thread making conflicting changes to that data. In a related situation, a critical section may be used to ensure that a shared resource, for example, a printer, can only be accessed by one process at a time.

## Implementation of critical sections

The implementation of critical sections vary among different operating systems.
A critical section will usually terminate in finite time, and a thread, task, or process must wait for a fixed time to enter it (bounded waiting). To ensure exclusive use of critical sections, some synchronization mechanism is required at the entry and exit of the program.
A critical section is a piece of a program that requires mutual exclusion of access.

As shown in the figure, in the case of mutual exclusion (mutex), one thread blocks a critical section by using locking techniques when it needs to access the shared resource, and other threads must wait their turn to enter the section. This prevents conflicts when two or more threads share the same memory space and want to access a common resource.

The simplest method to prevent any change of processor control inside the critical section is implementing a semaphore. In uniprocessor systems, this can be done by disabling interrupts on entry into the critical section, avoiding system calls that can cause a context switch while inside the section, and restoring interrupts to their previous state on exit. With this implementation, any execution thread entering any critical section in the system will prevent any other thread, including an interrupt, from being granted processing time on the CPU until the original thread leaves its critical section.
This brute-force approach can be improved by using semaphores. To enter a critical section, a thread must obtain a semaphore, which it releases on leaving the section. Other threads are prevented from entering the critical section at the same time as the original thread, but are free to gain control of the CPU and execute other code, including other critical sections that are protected by different semaphores. Semaphore locking also has a time limit to prevent a deadlock condition in which a lock is acquired by a single process for an infinite time, stalling the other processes that need to use the shared resource protected by the critical section.

## Uses of critical sections

### Kernel-level critical sections

Typically, critical sections prevent thread and process migration between processors and the preemption of processes and threads by interrupts and other processes and threads.
Critical sections often allow nesting. Nesting allows multiple critical sections to be entered and exited at little cost.
If the scheduler interrupts the current process or thread in a critical section, the scheduler will either allow the currently executing process or thread to run to completion of the critical section, or it will schedule the process or thread for another complete quantum. The scheduler will not migrate the process or thread to another processor, and it will not schedule another process or thread to run while the current process or thread is in a critical section.
Similarly, if an interrupt occurs in a critical section, the interrupt information is recorded for future processing, and execution is returned to the process or thread in the critical section. Once the critical section is exited, and in some cases the scheduled quantum completed, the pending interrupt will be executed. The concept of scheduling quantum applies to "round-robin" and similar scheduling policies.
Since critical sections may execute only on the processor on which they are entered, synchronization is only required within the executing processor. This allows critical sections to be entered and exited at almost no cost. No inter-processor synchronization is required. Only instruction stream synchronization is needed. Most processors provide the required amount of synchronization by interrupting the current execution state. This allows critical sections in most cases to be nothing more than a per processor count of critical sections entered.
Performance enhancements include executing pending interrupts at the exit of all critical sections and allowing the scheduler to run at the exit of all critical sections. Furthermore, pending interrupts may be transferred to other processors for execution.
Critical sections should not be used as a long-lasting locking primitive. Critical sections should be kept short enough so they can be entered, executed, and exited without any interrupts occurring from the hardware and the scheduler.
Kernel-level critical sections are the base of the software lockout issue.

### Critical sections in data structures

In parallel programming, the code is divided into threads. The read-write conflicting variables are split between threads and each thread has a copy of them. Data structures such as linked lists, trees, and hash tables have data variables that are linked and cannot be split between threads; hence, implementing parallelism is very difficult. To improve the efficiency of implementing data structures, multiple operations such as insertion, deletion, and search can be executed in parallel. While performing these operations, there may be scenarios where the same element is being searched by one thread and is being deleted by another. In such cases, the output may be erroneous. The thread searching the element may have a hit, whereas the other thread may subsequently delete it. These scenarios will cause issues in the program running by providing false data. To prevent this, one method is to keep the entire data structure under critical section so that only one operation is handled at a time. Another method is locking the node in use under critical section, so that other operations do not use the same node. Using critical section, thus, ensures that the code provides expected outputs.

### Critical sections in relation to peripherals

Critical sections also occur in code which manipulates external peripherals, such as I/O devices. The registers of a peripheral must be programmed with certain values in a certain sequence. If two or more processes control a device simultaneously, neither process will have the device in the state it requires and incorrect behavior will ensue.
When a complex unit of information must be produced on an output device by issuing multiple output operations, exclusive access is required so that another process does not corrupt the datum by interleaving its own bits of output.
In the input direction, exclusive access is required when reading a complex datum via multiple separate input operations. This prevents another process from consuming some of the pieces, causing corruption.
Storage devices provide a form of memory. The concept of critical sections is equally relevant to storage devices as to shared data structures in main memory. A process which performs multiple access or update operations on a file is executing a critical section that must be guarded with an appropriate file locking mechanism.
