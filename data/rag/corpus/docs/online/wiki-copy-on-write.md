# Copy-on-write

Copy-on-write (COW), also called implicit sharing or shadowing, is a resource-management technique used in programming to manage shared data efficiently. Instead of copying data right away when multiple programs use it, the same data is shared between programs until one tries to modify it. If no changes are made, no private copy is created, saving resources. A copy is only made when needed, ensuring each program has its own version when modifications occur. This technique is commonly applied to memory, files, and data structures.

## In virtual memory management

Copy-on-write finds its main use in operating systems, sharing the physical memory of computers running multiple processes, in the implementation of the fork() system call. Typically, the new process does not modify any memory and immediately executes a new process, replacing the address space entirely. It would waste processor time and memory to copy all of the old process's memory during the fork only to immediately discard the copy.
Copy-on-write can be implemented efficiently using the page table by marking certain pages of memory as read-only and keeping a count of the number of references to the page. When data is written to these pages, the operating-system kernel intercepts the write attempt and allocates a new physical page, initialized with the copy-on-write data, although the allocation can be skipped if there is only one reference. The kernel then updates the page table with the new (writable) page, decrements the number of references, and performs the write. The new allocation ensures that a change in the memory of one process is not visible in another's.
The copy-on-write technique can be extended to support efficient memory allocation by keeping one page of physical memory filled with zeros. When the memory is allocated, all the pages returned refer to the page of zeros and are all marked copy-on-write. This way, physical memory is not allocated for the process until data is written, allowing processes to reserve more virtual memory than physical memory and use memory sparsely, at the risk of running out of virtual address space. The combined algorithm is similar to demand paging.
Copy-on-write pages are also used in the Linux kernel's same-page merging feature.

## In software

COW is also used in library, application, and system code.

### Examples

The string class provided by the C++ standard library was specifically designed to allow copy-on-write implementations in the initial C++98 standard, but not in the newer C++11 standard:

In the PHP programming language, all types except references are implemented as copy-on-write. For example, strings and arrays are passed by reference, but when modified, they are duplicated if they have non-zero reference counts. This allows them to act as value types without the performance problems of copying on assignment or making them immutable.
In the Qt framework, many types are copy-on-write ("implicitly shared" in Qt's terms). Qt uses atomic compare-and-swap operations to increment or decrement the internal reference counter. Since the copies are cheap, Qt types can often be safely used by multiple threads without the need of locking mechanisms such as mutexes. The benefits of COW are thus valid in both single- and multithreaded systems.
Rust's standard library provides a Cow<T> ("clone-on-write") smart pointer type that wraps either borrowed or owned data. It allows a function to return borrowed data without cloning it when no modification is needed, but automatically clones the data into an owned, mutable value the first time it is written to.
In Docker, a set of software for implementing operating-system level virtualization, docker images are built in a layered format, with lower layers being read-only and the upper layer available for editing. Creating a new image which shares the same base layers as another image does not copy the layers, but instead follows COW principles and allows the two images to share layers until one is edited.

## In computer storage

COW is used as the underlying mechanism in file systems like ZFS, Btrfs, ReFS, APFS, and Bcachefs, as well as in logical volume management and database servers such as Microsoft SQL Server.
In traditional file systems, modifying a file overwrites the original data blocks in place. In a copy-on-write (COW) file system, the original blocks remain unchanged. When part of a file is modified, only the affected blocks are written to new locations, and metadata is updated to point to them, preserving the original version until it's no longer needed. This approach enables features like snapshots, which capture the state of a file at a specific time without consuming much additional space. Snapshots typically store only the modified data and are kept close to the original. However, they are considered a weak form of incremental backup and cannot replace a full backup.
In order to create and start new containers quickly,
container engines doing
OS-level virtualization often perform copy-on-write in storage,
either block-level copy-on-write (as described above) or file-level copy-on-write.
Some but not all filesystems support file-level copy-on-write as part of union mounting,
including OverlayFS, aufs, GlusterFS, and UnionFS.
