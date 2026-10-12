# Paging and address translation

## Pages and frames
Paging divides logical memory into fixed-size pages and physical memory into frames of the same size. Any page can be placed in any free frame, so paging has no external fragmentation. It still has internal fragmentation: on average half of the last page of each process is unused.

## Translating an address
A logical address is split into a page number and an offset. The page number indexes the page table, which gives the frame number; the physical address is the frame number times the page size plus the offset. The offset is never translated.

## The translation look-aside buffer
Without help, every memory reference would need two memory accesses: one for the page-table entry and one for the data. The translation look-aside buffer (TLB) is a small, fast associative cache of recent page-table entries. On a TLB hit the frame number is available at once. The effective access time is the hit ratio times the hit cost plus the miss ratio times the miss cost, so a high hit ratio is essential.

## Large address spaces
A single flat page table for a 64-bit address space would be enormous. Hierarchical (multi-level) page tables page the page table itself; hashed and inverted page tables are alternatives that keep one entry per physical frame or per hash bucket.
