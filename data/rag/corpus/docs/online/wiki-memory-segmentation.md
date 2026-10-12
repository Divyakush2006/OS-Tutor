# Memory segmentation

Memory segmentation is an operating system memory management technique of dividing a computer's primary memory into segments or sections. In a computer system using segmentation, a reference to a memory location includes a value that identifies a segment and an offset (memory location) within that segment. Segments or sections are also used in object files of compiled programs when they are linked together into a program image and when the image is loaded into memory.
Segments usually correspond to natural divisions of a program such as individual routines or data tables, so segmentation is generally more visible to the programmer than paging alone. Segments may be created for program modules, or for classes of memory usage such as code segments and data segments. Certain segments may be shared between programs.
Segmentation was originally invented as a method by which system software could isolate software processes (tasks) and data they are using. It was intended to increase reliability of the systems running multiple processes simultaneously.

## Hardware implementation

In a system using segmentation, computer memory addresses consist of a segment id and an offset within the segment. A hardware memory management unit (MMU) is responsible for translating the segment and offset into a physical address, and for performing checks to make sure the translation can be done and that the reference to that segment and offset is permitted.
Each segment has a length and set of permissions (for example, read, write, execute) associated with it. A process is only allowed to make a reference into a segment if the type of reference is allowed by the permissions, and if the offset within the segment is within the range specified by the length of the segment. Otherwise, a hardware exception such as a segmentation fault is raised.
Segments may also be used to implement virtual memory. In this case each segment has an associated flag indicating whether it is present in main memory or not. If a segment is accessed that is not present in main memory, a "segment not present" exception is raised, and the operating system will read the segment into memory from secondary storage.
Segmentation is one method of implementing memory protection. Paging is another, and they can be combined. The size of a memory segment is generally not fixed and may be as small as a single byte.
Segmentation has been implemented several ways on various hardware, with or without paging. Intel x86 memory segmentation does not fit either model and is discussed separately below, and also in greater detail in a separate article.

### Segmentation without paging

Associated with each segment is information that indicates where the segment is located in memory— the segment base. When a program references a memory location, the offset is added to the segment base to generate a physical memory address.
An implementation of virtual memory on a system using segmentation without paging requires that entire segments be swapped back and forth between main memory and secondary storage. When a segment is swapped in, the operating system has to allocate enough contiguous free memory to hold the entire segment. Often memory fragmentation results if there is not enough contiguous memory even though there may be enough in total.

### Segmentation with paging

Instead of a memory location, the segment information includes the address of a page table for the segment.
When a program references a memory location the offset is translated to a memory address using the page table. A segment can be extended by allocating another memory page and adding it to the segment's page table.
An implementation of virtual memory on a system using segmentation with paging usually only moves individual pages back and forth between main memory and secondary storage, similar to a paged non-segmented system. Pages of the segment can be located anywhere in main memory and need not be contiguous. This usually results in a reduced amount of input/output between primary and secondary storage and reduced memory fragmentation.

## History

The Burroughs Corporation B5000 computer was one of the first to implement segmentation, and "perhaps the first commercial computer to provide virtual memory" based on segmentation. The B5000 is equipped with a segment information table called the Program Reference Table (PRT) which is used to indicate whether the corresponding segment resides in the main memory, to maintain the base address and the size of the segment. The later B6500 computer also implemented segmentation; a version of its architecture is still in use today on the Unisys ClearPath Libra servers.
The GE 645 computer, a modification of the GE-635 with segmentation and paging support added, was designed in 1964 to support Multics.
The Intel iAPX 432, begun in 1975, attempted to implement a true segmented architecture with memory protection on a microprocessor.
The 960MX version of the Intel i960 processors supported load and store instructions with the source or destination being an "access descriptor" for an object, and an offset into the object, with the access descriptor being in a 32-bit register and with the offset computed from a base offset in the next register and from an additional offset and, optionally, an index register specified in the instruction. An access descriptor contains permission bits and a 26-bit object index; the object index is an index into a table of object descriptors, giving an object type, an object length, and a physical address for the object's data, a page table for the object, or the top-level page table for a two-level page table for the object, depending on the object type.
Prime, Stratus, Apollo, IBM System/38, and IBM AS/400 (including IBM i) computers use memory segmentation.

## Examples

### Burroughs large system architectures

Burroughs introduced segmentation on the B5000, followed by the compatible B5500 and B5700.
The later B6500 replaced the Program Reference Table (PRT) with a Saguaro stack, changed control word formats, changed descriptor formats and changed the mechanism for referring to a control word or descriptor.

#### B5000, B5500 and B5700

Words in the B5000, B5500 and B5700 are 48 bits long. Descriptors have the uppermost bit set in the word. They reside in either the Program Reference Table (PRT) or the stack, and contain a presence bit indicating whether the data are present in memory. There are distinct data and program descriptors.

#### B6500, B7500 and successors

Words in the B6500 and its successors have 48 bits of data and 3 tag bits. The tag bits indicate the type of data contained in the word; there are several descriptor types, indicated by different tag bit values. Control words and descriptors reside in the Saguaro stack. Array segments may be paged.
The line includes the B6500, B6700, B7700, B6800, B6900, B5900, the A-series Burroughs and Unisys machines, and the current Clearpath MCP systems (Libra). While there have been a few enhancements over the years, particularly hardware advances, the architecture has changed little. The segmentation scheme has remained the same, see Segmented memory.

### Multics architectures

### S/370 architecture

In the IBM System/370 models with virtual storage (DAT) and 24-bit addresses, control register 0 specifies a segment size of either 64 KiB or 1 MiB and a page size of either 2 KiB or 4 KiB; control register 1 contains a Segment Table Designator (STD), which specifies the length and real address of the segment table. Each segment table entry contains a page table location, a page table length and an invalid bit. IBM later expanded the address size to 31 bits and added two bits to the segment table entries:

Segment-protection bit
Segment is read-only
Common-segment bit
The segment is shared between address spaces; this bit is set to optimize TLB use
Each of IBM's DAT implementations includes a translation cache, which IBM called a Translation Lookaside Buffer (TLB). While Principles of Operation discusses the TLB in general terms, the details are not part of the architecture and vary from model to model.
Starting with the 3031, 3032, and 3033 processor complexes, IBM offered a feature called Dual-address Space (DAS), which allows a program to switch between the translation tables for two address spaces, referred to as primary address space (CR1) and secondary address space (CR7), and to move data between the address spaces subject to protection key. DAS supports a translation table to convert a 16-bit address space number (ASN) to an STD, with privileged instructions to load the STD into CR1 (primary) or CR7 (secondary).

### x86 architecture

Early x86 processors, beginning with the Intel 8086, provide crude memory segmentation and no memory protection (every byte of each segment is always available to any program.) The 16-bit segment registers allow for 65,536 segments; each segment begins at a fixed offset equal to 16 times the segment number; the segment starting address granularity is 16 bytes. Each segment grants read-write access to 64 KiB (65,536 bytes) of address space (this limit is set by the 16-bit PC and SP registers; the processor does no bounds checking). Offset+address exceeding 0xFFFFF wraps around to 0x00000. Each 64 KiB segment overlaps the next 4,095 segments; each physical address can be denoted by 4,096 segment–offset pairs. This scheme can address only 1 MiB (1024 KiB) of physical memory (and memory-mapped i/o). (Optional expanded memory hardware can add bank-switched memory under software control.) Intel retroactively named the sole operating mode of these x86 CPU models "real mode".
The Intel 80286 and later processors add "286 protected mode", which retains 16-bit addressing, and adds segmentation (without paging) and per-segment memory protection. For backward compatibility, all x86 CPUs start up in "real mode", with the same fixed overlapping 64 KiB segments, no memory protection, only 1 MiB physical address space, and some subtle differences (high memory area, unreal mode). In order to use its full 24-bit (16 MiB) physical address space and advanced MMU features, an 80286 or later processor must be switched into "protected mode" by software, usually the operating system or a DOS extender. If a program does not use the segment registers, or only puts values into them that it receives from the operating system, then identical code can run in real mode or protected mode, but most real-mode software computes new values for the segment registers, breaking this compatibility.
The Intel i386 and later processors add "386 protected mode", which uses 32-bit addressing, retains segmentation, and adds memory paging. In these processors, the segment table, rather than pointing to a page table for the segment, contains the segment address in linear memory. When paging is enabled, addresses in linear memory are then mapped to physical addresses using a separate page table. Most operating systems did not use the segmentation capability, opting to keep the base address in all segment registers equal to 0 at all times and provide per-page memory protection and swapping using only paging.  Some use the CS register to provide executable-space protection on processors lacking the NX bit or use the FS or GS registers to access thread-local storage.
The x86-64 architecture does not support segmentation in "long mode" (64-bit mode). Four of the segment registers: CS, SS, DS, and ES are forced to 0, and the limit to 264. The segment registers FS and GS can still have a nonzero base address. This allows operating systems to use these segments for special purposes such as thread-local storage.
