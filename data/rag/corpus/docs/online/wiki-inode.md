# Inode

An inode (index node) is a data structure in a Unix-style file system that describes a file-system object such as a file or a directory. Each inode stores the attributes and disk block locations of the object's data. File-system object attributes may include metadata (times of last change, access, modification), as well as owner and permission data.
A directory is a list of inodes with their assigned names. The list includes an entry for itself, its parent, and each of its children.

## Etymology

There has been uncertainty on the Linux kernel mailing list about the reason for the "i" in "inode". In 2002, the question was brought to Unix pioneer Dennis Ritchie, who replied: In truth, I don't know either. It was just a term that we started to use. "Index" is my best guess, because of the slightly unusual file system structure that stored the access information of files as a flat array on the disk, with all the hierarchical directory information living aside from this. Thus the i-number is an index in this array, the i-node is the selected element of the array. (The "i-" notation was used in the 1st edition manual; its hyphen was gradually dropped.)

A 1978 paper by Ritchie and Ken Thompson bolsters the notion of "index" being the etymological origin of inodes. They wrote: […] a directory entry contains only a name for the associated file and a pointer to the file itself. This pointer is an integer called the i-number (for index number) of the file.  When the file is accessed, its i-number is used as an index into a system table (the i-list) stored in a known part of the device on which the directory resides.  The entry found thereby (the file's i-node) contains the description of the file.
 Additionally, Maurice J. Bach wrote that the word inode "is a contraction of the term index node and is commonly used in literature on the UNIX system".

## Details

A file system relies on data structures about the files, as opposed to the contents of those files. The former are called metadata—data that describes data.  Each file is associated with an inode, which is identified by an integer, often referred to as an i-number or inode number.
Inodes store information about files and directories (folders), such as file ownership, access mode (read, write, execute permissions), and file type. The data may be called stat data, in reference to the stat system call that provides the data to programs.
The inode number indexes a table of inodes on the file system. From the inode number, the kernel's file system driver can access the inode contents, including the location of the file, thereby allowing access to the file. A file's inode number can be found using the ls -i command, which prints the inode number in the first column of  its output.
On many older file systems, inodes are stored in one or more fixed-size areas that are set up at file system creation time, so the maximum number of inodes is fixed at file system creation, limiting the maximum number of files the file system can hold.  A typical allocation heuristic for inodes in a file system is one inode for every 2K bytes contained in the filesystem.
Some Unix-style file systems such as JFS, XFS, ZFS, OpenZFS, ReiserFS, btrfs, and APFS omit a fixed-size inode table, but must store equivalent data in order to provide equivalent capabilities. Common alternatives to the fixed-size table include B-trees and the derived B+ trees.
File names and directory implications:

Inodes do not contain their hard link names, only other file metadata.
Unix directories are lists of association structures, each of which contains one filename and one inode number.
The file system driver must search a directory for a particular filename and then convert the filename to the correct corresponding inode number.
The operating system kernel's in-memory representation of this data is called struct inode in Linux. Systems derived from BSD use the term vnode (the "v" refers to the kernel's virtual file system layer).

## POSIX inode description

The POSIX standard mandates file-system behavior that is strongly influenced by traditional UNIX file systems.  An inode is denoted by the phrase "file serial number", defined as a per-file system unique identifier for a file. That file serial number, together with the device ID of the device containing the file, uniquely identify the file within the whole system.
Within a POSIX system, a file has the following attributes which may be retrieved by the stat system call:

Device ID (this identifies the device containing the file; that is, the scope of uniqueness of the serial number).
File serial numbers.
The file mode, which determines the file type and how the file's owner, users who are members of the file's group, and users who are neither the owner nor a member of the file's group can access the file.
A link count telling how many hard links point to the inode.
The User ID of the file's owner.
The Group ID of the file.
The device ID of the file if it is a device file.
The size of the file in bytes.
Timestamps telling when the inode itself was last modified (ctime, inode change time), the file content last modified (mtime, modification time), and last accessed (atime, access time).
The preferred I/O block size.
The number of blocks allocated to this file.

## Implications

Filesystems designed with inodes will have the following administrative characteristics:

### Multi-named files and hard links

Files can have multiple names. If multiple names hard link to the same inode then the names are equivalent; i.e., the first to be created has no special status. This is unlike symbolic links, which depend on the original name, not the inode (number).

### inode persistence and unlinked files

An inode may have no links. An inode without links represents a file with no remaining directory entries or paths leading to it in the filesystem. A file that has been deleted or lacks directory entries pointing to it is termed an 'unlinked' file. 
Such files are removed from the filesystem, freeing the occupied disk space for reuse. An inode without links remains in the filesystem until the resources (disk space and blocks) freed by the unlinked file are deallocated or the file system is modified.
Although an unlinked file becomes invisible in the filesystem, its deletion is deferred until all processes with access to the file have finished using it, including executable files which are implicitly held open by the processes executing them.

### inode number conversion and file directory path retrieval

It is typically not possible to map from an open file to the filename that was used to open it. When a program opens a file, the operating system converts the filename to an inode number and then discards the filename. As a result, functions like getcwd() and getwd()which retrieve the current working directory of the process, cannot directly access the filename.
Beginning with the current directory, these functions search up to its parent directory, then to the parent's parent, and so on, until reaching the root directory. At each level, the function looks for a directory entry whose inode matches that of the directory it just moved up from. Because the child directory's inode still exists as an entry in its parent directory, it allows the function to reconstruct the absolute path of the current working directory.
Some operating systems maintain extra information to make this operation run faster. For example, in the Linux VFS, directory entry cache, also known as dentry or dcache, are cache entries used by the kernel to speed up filesystem operations by storing information about directory links in RAM.

### Historical possibility of directory hard linking

Historically, it was possible to hard link directories. This made the directory structure an arbitrary directed graph contrary to a directed acyclic graph. It was even possible for a directory to be its own parent. Modern systems generally prohibit this confusing state, except that the parent of root is still defined as root. The most notable exception to this prohibition is found in Mac OS X (versions 10.5 and higher) which allows hard links of directories to be created on HFS+ file systems by the superuser.

### inode number stability and non-Unix file systems

When a file is relocated to a different directory on the same file system, or when a disk defragmentation alters its physical location, the file's inode number remains unchanged.
This unique characteristic permits the file to be moved or renamed even during read or write operations, thereby ensuring continuous access without disruptions.
This feature—having a file's metadata and data block locations persist in a central data structure, irrespective of file renaming or moving—cannot be fully replicated in many non-Unix file systems like FAT and its derivatives, as they lack a mechanism to maintain this invariant property when both the file's directory entry and its data are simultaneously relocated. In these file systems, moving or renaming a file might lead to more significant changes in the data structure representing the file, and the system does not keep a separate, central record of the file's data block locations and metadata as inodes do in Unix-like systems.

### Simplified library installation with inode file systems

inode file systems allow a running process to continue accessing a library file even as another process is replacing that same file.
This operation should be performed atomically, meaning it should appear as a single operation that is either entirely completed or not done at all, with no intermediate state visible to other processes.
During the replacement, a new inode is created for the new library file, establishing an entirely new mapping. Subsequently, future access requests for that library will retrieve the newly installed version.
When the operating system is replacing the file (and creating a new inode), it places a lock on the inode and possibly the containing directory. This prevents other processes from reading or writing to the file (inode) during the update operation, thereby avoiding data inconsistency or corruption.
Once the update operation is complete, the lock is released. Any subsequent access to the file (via the inode) by any processes will now point to the new version of the library. Thus, making it possible to perform updates even when the library is in use by another process.
One significant advantage of this mechanism is that it eliminates the need for a system reboot to replace libraries currently in use. Consequently, systems can update or upgrade software libraries seamlessly without interrupting running processes or operations.

### Potential for inode exhaustion and solutions

When a file system is created, some file systems allocate a fixed number of inodes. This means that it is possible to run out of inodes on a file system, even if there is free space remaining in the file system.  This situation often arises in use cases where there are many small files, such as on a server storing email messages, because each file, no matter how small, requires its own inode.
Other file systems avoid this limitation by using dynamic inode allocation. Dynamic inode allocation allows a file system to create more inodes as needed instead of relying on a fixed number created at the time of file system creation. This can "grow" the file system by increasing the number of inodes available for new files and directories, thus avoiding the problem of running out of inodes.

## Inlining

It can make sense to store very small files in the inode itself to save both space (no data block needed) and lookup time (no further disk access needed). This file system feature is called inlining. The strict separation of inode and file data thus can no longer be assumed when using modern file systems.
If the data of a file fits in the space allocated for pointers to the data, this space can conveniently be used. For example, ext2 and its successors store the data of symlinks (typically file names) in this way if the data is no more than 60 bytes ("fast symbolic links").
Ext4 has a file system option called inline_data that allows ext4 to perform inlining if enabled during file system creation. Because an inode's size is limited, this only works for very small files.

## In non-Unix systems

NTFS has a master file table (MFT) storing files in a B-tree. Each entry has a "fileID", analogous to the inode number, that uniquely refers to this entry. The three timestamps, a device ID, attributes, reference count, and file sizes are found in the entry, but unlike in POSIX the permissions are expressed through a different API. The on-disk layout is more complex. The earlier FAT file systems did not have such a table and were incapable of making hard links.
NTFS also has a concept of inlining small files into the MFT entry.
The derived ReFS has a homologous MFT. ReFS has a 128-bit file ID; this extension was also backported to NTFS, which originally had a 64-bit file ID.
The same stat-like GetFileInformationByHandle API can be used on Cluster Shared Volumes, so it presumably has a similar concept of a file ID.
