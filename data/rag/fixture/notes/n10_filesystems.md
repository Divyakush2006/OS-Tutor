# File-system implementation

## Allocation methods
Contiguous allocation stores a file in consecutive blocks; it gives fast sequential and direct access but suffers external fragmentation and makes growth hard. Linked allocation chains blocks with pointers; it has no external fragmentation but direct access is slow and one lost pointer loses the rest of the file. The file allocation table (FAT) keeps the chain in a separate table. Indexed allocation gives each file an index block listing its blocks, supporting direct access without external fragmentation.

## Inodes
UNIX file systems keep each file's metadata in an inode: owner, permissions, size, timestamps and block pointers. A typical inode has twelve direct pointers, then one single-indirect, one double-indirect and one triple-indirect pointer, so small files are reached quickly and large files are still supported. The file name is not stored in the inode; it lives in the directory entry, which is why one inode can have several hard links.

## Free-space management
Free blocks can be tracked with a bit vector, one bit per block, which makes finding contiguous free space easy; with a linked list of free blocks; or by grouping and counting runs of free blocks.
