# Contiguous allocation and segmentation

## Contiguous allocation
In contiguous allocation each process occupies one block of physical memory. Placement strategies are first fit, best fit and worst fit. First fit is usually fastest; best fit leaves the smallest leftover hole; worst fit leaves the largest. All of them suffer from external fragmentation: there may be enough free memory in total but no single hole is large enough.

## Compaction
Compaction moves processes so that the free memory forms one large block. It is possible only when relocation is dynamic, done at execution time, and it is expensive because memory must be copied.

## Segmentation
Segmentation divides a program into variable-sized logical units such as code, stack and heap, each with a base and a limit in a segment table. Because segments are allocated exactly to size, segmentation has no internal fragmentation, but because segments vary in size it does suffer from external fragmentation. Combining segmentation with paging, as some architectures do, removes the external fragmentation.
