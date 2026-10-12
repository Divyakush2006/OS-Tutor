# Disk scheduling

## Why the order of requests matters
On a hard disk the dominant cost of a request is seek time, the time for the head to move to the right cylinder. Disk scheduling reorders pending requests to reduce total head movement. On solid-state drives there is no seek, so simple FCFS ordering is usually used.

## The algorithms
FCFS serves requests in arrival order; it is fair but can make the head sweep back and forth. SSTF serves the closest request next; it reduces head movement but can starve requests far from the head. SCAN, the elevator algorithm, moves the head to one end of the disk serving requests on the way, then reverses. C-SCAN serves requests in one direction only and jumps back to the start, giving more uniform waiting times. LOOK and C-LOOK are variants that turn around at the last request instead of travelling to the end of the disk.
