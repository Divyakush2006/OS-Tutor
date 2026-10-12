# System call

In computing, a system call (syscall) is the programmatic way in which a computer program requests a service from the operating system on which it is executed. This may include hardware-related services (for example, accessing a hard disk drive or accessing the device's camera), creation and execution of new processes, and communication with integral kernel services such as process scheduling.  System calls provide an essential interface between a process and the operating system.
In most systems, system calls can only be made from userspace processes, while in some systems, OS/360 and successors for example, privileged system code also issues system calls.
For embedded systems, system calls typically do not change the privilege mode of the CPU.

## Privileges

The architecture of most modern processors, with the exception of some embedded systems, involves a security model. For example, the rings model specifies multiple privilege levels under which software may be executed: a program is usually limited to its own address space so that it cannot access or modify other running programs or the operating system itself, and is usually prevented from directly manipulating hardware devices (e.g. the frame buffer or network devices).
However, many applications need access to these components, so system calls are made available by the operating system to provide well-defined, safe implementations for such operations. The operating system executes at the highest level of privilege, and allows applications to request services via system calls, which are often initiated via interrupts. An interrupt automatically puts the CPU into some elevated privilege level and then passes control to the kernel, which determines whether the calling program should be granted the requested service. If the service is granted, the kernel executes a specific set of instructions over which the calling program has no direct control, returns the privilege level to that of the calling program, and then returns control to the calling program.

## The library as an intermediary

Generally, systems provide a library or API that sits between normal programs and the operating system.  On Unix-like systems, that API is usually part of an implementation of the C library (libc), such as glibc, that provides wrapper functions for the system calls, often named the same as the system calls they invoke. On Windows NT, that API is part of the Native API, in the ntdll.dll library; this is an undocumented API used by implementations of the regular Windows API and directly used by some system programs on Windows.  The library's wrapper functions expose an ordinary function calling convention (a subroutine call on the assembly level) for using the system call, as well as making the system call more modular. Here, the primary function of the wrapper is to place all the arguments to be passed to the system call in the appropriate processor registers (and maybe on the call stack as well), and also setting a unique system call number for the kernel to call. In this way the library, which exists between the OS and the application, increases portability.
The call to the library function itself does not cause a switch to kernel mode and is usually a normal subroutine call (using, for example, a "CALL" assembly instruction in some Instruction set architectures (ISAs)). The actual system call does transfer control to the kernel (and is more implementation-dependent and platform-dependent than the library call abstracting it). For example, in Unix-like systems, fork and execve are C library functions that in turn execute instructions that invoke the fork and exec system calls. Making the system call directly in the application code is more complicated and may require embedded assembly code to be used (in C and C++), as well as requiring knowledge of the low-level binary interface for the system call operation, which may be subject to change over time and thus not be part of the application binary interface; the library functions are meant to abstract this away.
On exokernel based systems, the library is especially important as an intermediary. On exokernels, libraries shield user applications from the very low level kernel API, and provide abstractions and resource management.
IBM's OS/360, DOS/360 and TSS/360 implement most system calls through a library of assembly language macros, although there are a few services with a call linkage. This reflects their origin at a time when programming in assembly language was more common than high-level language usage.  IBM system calls were therefore not directly executable by high-level language programs, but required a callable assembly language wrapper subroutine. Since then, IBM has added many services that can be called from high level languages in, e.g., z/OS and z/VSE. In more recent release of MVS/SP and in all later MVS versions, some system call macros generate Program Call (PC).

## Examples and tools

On Unix, Unix-like and other POSIX-compliant operating systems, popular system calls are open, read, write, close, wait, exec, fork, exit, and kill. Many modern operating systems have hundreds of system calls. For example, Linux and OpenBSD each have over 300 different calls, NetBSD has close to 500, FreeBSD has over 500, Windows has close to 2000, divided between win32k (graphical) and ntdll (core) system calls while Plan 9 has 54.
Tools such as strace, ftrace and truss allow a process to execute from start and report all system calls the process invokes, or can attach to an already running process and intercept any system call made by the said process if the operation does not violate the permissions of the user. This special ability of the program is usually also implemented with system calls such as ptrace or system calls on files in procfs.

## Typical implementations

Implementing system calls requires a transfer of control from user space to kernel space, which involves some sort of architecture-specific feature. A typical way to implement this is to use a software interrupt or trap. Interrupts transfer control to the operating system kernel, so software simply needs to set up some register with the system call number needed, and execute the software interrupt.
This is the only technique provided for many RISC processors, but CISC architectures such as x86 support additional techniques. For example, the x86 instruction set contains the instructions SYSCALL/SYSRET and SYSENTER/SYSEXIT (these two mechanisms were independently created by AMD and Intel, respectively, but in essence they do the same thing). These are "fast" control transfer instructions that are designed to quickly transfer control to the kernel for a system call without the overhead of an interrupt. Linux 2.5 began using this on the x86, where available; formerly it used the INT instruction, where the system call number was placed in the EAX register before interrupt 0x80 was executed.
An older mechanism is the call gate; originally used in Multics and later, for example, see call gate on the Intel x86. It allows a program to call a kernel function directly using a safe control transfer mechanism, which the operating system sets up in advance. This approach has been unpopular on x86, presumably due to the requirement of a far call (a call to a procedure located in a different segment than the current code segment) which uses x86 memory segmentation and the resulting lack of portability it causes, and the existence of the faster instructions mentioned above.
For IA-64 architecture, EPC (Enter Privileged Code) instruction is used. The first eight system call arguments are passed in registers, and the rest are passed on the stack.
In the IBM System/360 mainframe family, and its successors, a Supervisor Call instruction (SVC), with the number in the instruction rather than in a register, implements a system call for legacy facilities in most of IBM's own operating systems, and for all system calls in Linux.  In later versions of MVS, IBM uses the Program Call (PC) instruction for many newer facilities. In particular, PC is used when the caller might be in Service Request Block (SRB) mode.
The PDP-11 minicomputer used the EMT, TRAP and IOT instructions, which, similar to the IBM System/360 SVC and x86 INT, put the code in the instruction; they generate interrupts to specific addresses, transferring control to the operating system.  The VAX 32-bit successor to the PDP-11 series used the CHMK, CHME, and CHMS instructions to make system calls to privileged code at various levels; the code is an argument to the instruction.
Within the RISC-V privileged architecture, the instruction ECALL (after environment call) is designed to enter a more privileged level and therefore this instruction performs the functionalities related to system calls. ECALL events are then handled in a similar fashion to other types of synchronous traps, including the same return mechanism. In the related Linux implementations, the system call number is placed into the a7 (x17) register before ECALL is executed, function arguments are listed in accordance to the RISC-V ABI (a0, a1, ...) while the return value is put in a0.

## Categories of system calls

System calls can be grouped roughly into six major categories:

Process control
create process (for example, fork on Unix-like systems, or NtCreateProcess in the Windows NT Native API)
terminate process
load, execute
get/set process attributes
wait for time, wait event, signal event
allocate and free memory
File management
create file, delete file
open, close
read, write, reposition
get/set file attributes
Device management
request device, release device
read, write, reposition
get/set device attributes
logically attach or detach devices
Information maintenance
get/set total system information (including time, date, computer name, enterprise etc.)
get/set process, file, or device metadata (including author, opener, creation time and date, etc.)
Communication
create, delete communication connection
send, receive messages
transfer status information
attach or detach remote devices
Protection
get/set file permissions

## Processor mode and context switching

System calls in most Unix-like systems are processed in kernel mode, which is accomplished by changing the processor execution mode to a more privileged one, but no process context switch is necessary –  although a privilege context switch does occur. The hardware sees the world in terms of the execution mode according to the processor status register, and processes are an abstraction provided by the operating system. A system call does not generally require a context switch to another process; instead, it is processed in the context of whichever process invoked it.
In a multithreaded process, system calls can be made from multiple threads. The handling of such calls is dependent on the design of the specific operating system kernel and the application runtime environment. The following list shows typical models followed by operating systems:

Many-to-one model: All system calls from any user thread in a process are handled by a single kernel-level thread. This model has a serious drawback –  any blocking system call (like awaiting input from the user) can freeze all the other threads. Also, since only one thread can access the kernel at a time, this model cannot utilize multiple cores of processors.
One-to-one model: Every user thread gets attached to a distinct kernel-level thread during a system call. This model solves the above problem of blocking system calls. It is found in all major Linux distributions, macOS, iOS, recent Windows and Solaris versions.
Many-to-many model: In this model, a pool of user threads is mapped to a pool of kernel threads. All system calls from a user thread pool are handled by the threads in their corresponding kernel thread pool.
Hybrid model: This model implements both many-to-many and one-to-one models depending upon the choice made by the kernel. This is found in old versions of IRIX, HP-UX and Solaris.
