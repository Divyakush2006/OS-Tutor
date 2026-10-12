# Processes

## What a process is
A process is a program in execution. The program is a passive file on disk; the process is the active entity with a program counter, a stack, a heap, a data section and a set of open resources. Two processes can run the same program and still be separate processes, each with its own address space.

## Process states
A process moves between five states. New: it is being created. Ready: it could run and is waiting for a CPU. Running: its instructions are executing. Waiting (also called blocked): it cannot continue until some event happens, such as an I/O completion. Terminated: it has finished. Only one process per core is in the running state at any instant. A running process that issues an I/O request moves to waiting, not to ready; when the I/O completes it moves to ready and must be scheduled again.

## The process control block
The kernel represents each process with a process control block (PCB). It records the process state, the saved program counter and registers, scheduling information such as priority, memory-management information such as the page-table base, accounting data, and the list of open files. A context switch saves the running process's registers into its PCB and loads the registers of the next process from its PCB. Context switching is pure overhead: no user work is done while it happens.
