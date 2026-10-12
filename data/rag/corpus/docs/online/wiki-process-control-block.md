# Process control block

A process control block (PCB), also sometimes called a process descriptor, is a data structure used by a computer operating system to store all the information about a  process.
When a process is created (initialized or installed), the operating system creates a corresponding process control block, which specifies and tracks the process state (i.e. new, ready, running, waiting or terminated). Since it is used to track process information, the PCB plays a key role in context switching.
An operating system kernel stores PCBs in a process table.
The current working directory of a process is one of the properties that the kernel stores in the process's PCB.

## Role

The role of the PCBs is central in process management: they are accessed and/or modified by most utilities, particularly those involved with scheduling and resource management.

## Structure

In multitasking operating systems, the PCB stores data needed for correct and efficient process management. Though the details of these structures are system-dependent, common elements fall in three main categories:

Process identification
Process state
Process control
Status tables exist for each relevant entity, like describing memory, I/O devices, files and processes.
Memory tables, for example, contain information about the allocation of main and secondary (virtual) memory for each process, authorization attributes for accessing memory areas shared among different processes, etc. I/O tables may have entries stating the availability of a device or its assignment to a process, the status of I/O operations, the location of memory buffers used for them, etc.
Process identification data include a unique identifier for the process (almost invariably an integer) and, in a multiuser-multitasking system, data such as the identifier of the parent process, user identifier, user group identifier, etc. The process id is particularly relevant since it is often used to cross-reference the tables defined above, e.g. showing which process is using which I/O devices, or memory areas.
Process state data define the status of a process when it is suspended, allowing the OS to restart it later. This always includes the content of general-purpose CPU registers, the CPU process status word, stack and frame pointers, etc. During context switch, the running process is stopped and another process runs. The kernel must stop the execution of the running process, copy out the values in hardware registers to its PCB, and update the hardware registers with the values from the PCB of the new process.
Process control information is used by the OS to manage the process itself. This includes:

Process scheduling state – The state of the process in terms of "ready", "suspended", etc., and other scheduling information as well, such as priority value, the amount of time elapsed since the process gained control of the CPU or since it was suspended. Also, in case of a suspended process, event identification data must be recorded for the event the process is waiting for;
Process structuring information – the process's children id's, or the id's of other processes related to the current one in some functional way, which may be represented as a queue, a ring or other data structures;
Interprocess communication information – flags, signals and messages associated with the communication among independent processes;
Process Privileges – allowed/disallowed access to system resources;
Process State – new, ready, running, waiting, dead;
Process Number (PID) – unique identification number for each process (also known as Process ID);
Program Counter (PC) – a pointer to the address of the next instruction to be executed for this process;
CPU Registers – register set where process needs to be stored for execution for running state;
CPU Scheduling Information – information scheduling CPU time;
Memory Management Information – page table, memory limits, segment table;
Accounting Information – amount of CPU used for process execution, time limits, execution ID etc.;
I/O Status Information – list of I/O devices allocated to the process.

## Location

The PCB must be kept in an area of memory protected from normal process access. In some operating systems the PCB is placed at the bottom of the process stack.
