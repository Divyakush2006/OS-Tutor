# Demand paging

In computer operating systems, demand paging (as opposed to anticipatory paging) is a method of virtual memory management. In a system that uses demand paging, the operating system copies a disk page into physical memory only when an attempt is made to access it and that page is not already in memory (i.e., if a page fault occurs). It follows that a process begins execution with none of its pages in physical memory, and triggers many page faults until most of its working set of pages are present in physical memory. This is an example of a lazy loading technique.

## Basic concept

Demand paging only brings pages into memory when an executing process demands them. This is often referred to as lazy loading, as only those pages demanded by the process are swapped from secondary storage to main memory. Contrast this to pure swapping, where all memory for a process is swapped from secondary storage to main memory when the process starts up or resumes execution.
Commonly, to achieve this process a memory management unit is used. The memory management unit maps logical memory to physical memory. Entries in the memory management unit include a bit that indicates whether a page is valid or invalid. A valid page is one that currently resides in main memory. An invalid page is one that currently resides in secondary memory. When a process tries to access a page, the following steps are generally followed:

Attempt to access page.
If page is valid (in memory) then continue processing instruction as normal.
If page is invalid then a page-fault trap occurs.
Check if the memory reference is a valid reference to a location on secondary memory. If so, we have to page in the required page. Otherwise, the process is terminated (illegal memory access).
Schedule disk operation to read the desired page into main memory.
Restart the instruction that was interrupted by the operating system trap.

## Advantages

Demand paging, as opposed to loading all pages immediately:

Only loads pages that are demanded by the executing process.
As there is more space in main memory, more processes can be loaded, reducing the context switching time, which utilizes large amounts of resources.
Less loading latency occurs at program startup, as less information is accessed from secondary storage and less information is brought into main memory.
As main memory is expensive compared to secondary memory, this technique helps significantly reduce the bill of material (BOM) cost in smart phones for example. Symbian OS had this feature.

## Disadvantages

Individual programs face extra latency when they access a page for the first time.
Low-cost, low-power embedded systems may not have a memory management unit that supports page replacement.
Memory management with page replacement algorithms becomes slightly more complex.
Possible security risks, including vulnerability to timing attacks; see Percival, Colin (2005-05-13). Cache missing for fun and profit (PDF). BSDCan 2005. (specifically the virtual memory attack in section 2).
Thrashing which may occur due to repeated page faults.
