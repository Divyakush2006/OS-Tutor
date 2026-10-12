# Page replacement

## Demand paging and page faults
With demand paging, a page is loaded only when it is first referenced. A reference to a page that is not in memory causes a page fault: the operating system finds a free frame, or chooses a victim page to evict, reads the needed page from disk, updates the page table and restarts the instruction. A dirty victim must be written back to disk first, which roughly doubles the cost of the fault.

## Replacement algorithms
FIFO evicts the page that has been in memory longest. The optimal algorithm (OPT) evicts the page that will not be used for the longest time; it cannot be implemented, but it is the yardstick for others. LRU evicts the page that has not been used for the longest time. The clock (second-chance) algorithm approximates LRU with one reference bit per frame.

## Belady's anomaly
Belady's anomaly is the counter-intuitive case in which giving a process more frames produces more page faults. FIFO can suffer from it. LRU and OPT cannot, because they are stack algorithms: the set of pages kept with n frames is always a subset of the set kept with n plus one frames.
