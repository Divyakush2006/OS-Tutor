# I/O scheduling

Input/output (I/O) scheduling is the method that computer operating systems use to decide in which order I/O operations will be submitted to storage volumes. I/O scheduling is sometimes called disk scheduling.

## Purpose

I/O scheduling usually has to work with hard disk drives that have long access times for requests placed far away from the current position of the disk head (this operation is called a seek). To minimize the effect this has on system performance, most I/O schedulers implement a variant of the  elevator algorithm that reorders the incoming randomly ordered requests so the associated data would be accessed with minimal head movement.
I/O schedulers can have many purposes depending on the goals; common purposes include the following

To minimize time wasted by hard disk seeks
To prioritize a certain processes' I/O requests
To give a share of the disk bandwidth to each running process
To guarantee that certain requests will be issued before a particular deadline

## Disciplines

Common scheduling disciplines include the following:

Random scheduling (RSS)
First In, First Out (FIFO), also known as First Come First Served (FCFS)
Last In, First Out (LIFO)
Shortest seek first, also known as Shortest Seek / Service Time First (SSTF)
Elevator algorithm, also known as SCAN (including its variants, C-SCAN, LOOK, and C-LOOK)
N-Step-SCAN SCAN of N records at a time
FSCAN, N-Step-SCAN where N equals queue size at start of the SCAN cycle
mClock scheduler
In Linux kernel:
anticipatory (until 2.6.32)
noop (until 4.20) 🠊 none (since 4.11)
deadline (until 4.20) 🠊 mq-deadline (since 4.11)
cfq (Completely Fair Queuing) (until 4.20) 🠊 bfq (Budget Fair Queueing) (since 4.12)
kyber (since 4.12)
