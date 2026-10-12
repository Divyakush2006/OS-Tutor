# Thrashing and the working set

## What thrashing is
Thrashing happens when processes do not have enough frames to hold the pages they are actively using. They fault constantly, the paging device becomes the bottleneck, and the CPU sits idle waiting for pages. A naive scheduler sees low CPU utilisation and admits more processes, which makes the shortage of frames worse.

## The working-set model
The working set of a process is the set of pages it referenced in its most recent window of delta references. If the sum of the working-set sizes of all processes exceeds the number of frames, thrashing will occur, and the system should suspend a process rather than admit another. A window that is too small misses part of the locality; one that is too large spans several localities.

## Page-fault frequency
A simpler control measures each process's page-fault rate directly. If the rate rises above an upper bound, the process is given another frame; if it falls below a lower bound, a frame is taken away.
