# Bélády's anomaly

In computer storage, Bélády's anomaly is the phenomenon in which increasing the number of page frames results in an increase in the number of page faults for certain memory access patterns. This phenomenon is commonly experienced when using the first-in first-out (FIFO) page replacement algorithm. In FIFO, the page fault may or may not increase as the page frames increase, but in optimal and stack-based algorithms like Least Recently Used (LRU), as the page frames increase, the page fault decreases. László Bélády demonstrated this in 1969.

## Background

In common computer memory management, information is loaded in specific-sized chunks. Each chunk is referred to as a page. Main memory can hold only a limited number of pages at a time. It requires a frame for each page it can load. A page fault occurs when a page is not found, and might need to be loaded from disk into memory.
When a page fault occurs and all frames are in use, one must be cleared to make room for the new page (page replacement). A simple algorithm is FIFO: whichever page has been in the frames the longest is the one that is cleared. Until Bélády's anomaly was demonstrated, it was believed that an increase in the number of page frames would always result in the same number of, or fewer, page faults.

## Bélády's anomaly is unbounded

Bélády, Nelson and Shedler constructed reference strings for which the FIFO page replacement algorithm produced nearly twice as many page faults in a larger memory than in a smaller one and they conjectured that 2 is a general bound.
In 2010, Fornai and Iványi showed that the anomaly is in fact unbounded and that one can construct a reference string to any arbitrary page fault ratio.
