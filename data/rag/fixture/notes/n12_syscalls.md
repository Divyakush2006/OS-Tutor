# System calls and protection

## Dual-mode operation
Hardware provides at least two modes: user mode and kernel mode, recorded by a mode bit. Privileged instructions, such as those that control I/O, set the timer or change memory-management registers, can execute only in kernel mode. If a user program attempts one, the hardware traps to the operating system instead.

## System calls
A system call is the interface through which a user program asks the kernel for a service. The program places a system-call number and parameters in registers or a memory block and executes a trap instruction; the hardware switches to kernel mode and jumps to a handler, which dispatches on the number. Library functions such as printf may wrap system calls such as write, but not every library call makes a system call.

## Interrupts and the timer
A timer interrupt guarantees that the operating system regains control even if a user program never makes a system call, which is what makes preemptive scheduling possible.
