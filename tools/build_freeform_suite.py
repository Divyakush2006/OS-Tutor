"""Hand-written free-form evaluation suite (v3.0) - the release gate v2.2 lacked.

    python tools/build_freeform_suite.py

v2.2 scored 65% on generator-shaped questions and 4/14 on questions typed the way
students type them. Both of its test suites came from the training generator, so
the gap was invisible until the model was used through a chat UI.

Every question here is WRITTEN BY HAND in wording no generator produces (story
problems, abbreviations, messy formatting, trick cases, textbook classics) and
graded by the simulators from the parameters in `verify`. The file lives in
data/eval/, so the build's decontamination removes any training row that
overlaps it.

Writes data/eval/os_freeform.jsonl.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ostutor.evaluation.harness import grade  # noqa: E402
from ostutor.simulators.generate import render_solution  # noqa: E402

SIL = [["P1", 0, 8, 1], ["P2", 1, 4, 1], ["P3", 2, 9, 1], ["P4", 3, 5, 1]]
REF = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]
BK = dict(avail=[3, 3, 2], names=["P0", "P1", "P2", "P3", "P4"],
          alloc=[[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]],
          maxm=[[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]])
DQ = [98, 183, 37, 122, 14, 124, 65, 67]


def S(algo, procs, q=2):
    return dict(kind="scheduling", algo=algo, quantum=q, procs=procs)


ITEMS = [
    # ------------------------------------------------------------- scheduling
    ("srtf_classic", "Four jobs: P1 comes at t=0 needing 8ms, P2 at t=1 needing 4ms, P3 at t=2 "
     "needing 9ms, P4 at t=3 needing 5ms. What's the avg waiting time under SRTF?", S("SRTF", SIL)),
    ("rr_classic", "three procs all show up at time zero - P1 burst 24, P2 burst 3, P3 burst 3. "
     "RR with q=4. avg waiting time and avg turnaround time?",
     S("RR", [["P1", 0, 24, 1], ["P2", 0, 3, 1], ["P3", 0, 3, 1]], 4)),
    ("prio_classic", "Five processes, all arriving at 0, in order P1-P5. Bursts: 10, 1, 2, 1, 5. "
     "Priorities: 3, 1, 4, 5, 2 (1 = highest). Non-preemptive priority. Average waiting time?",
     S("PRIORITY", [["P1", 0, 10, 3], ["P2", 0, 1, 1], ["P3", 0, 2, 4], ["P4", 0, 1, 5],
                    ["P5", 0, 5, 2]])),
    ("fcfs_idle", "A lab machine gets job A at t=2 (3 units), job B at t=10 (4 units) and job C at "
     "t=11 (2 units). The CPU is idle until something arrives. Using first come first served, "
     "what is the average turnaround time?",
     S("FCFS", [["A", 2, 3, 1], ["B", 10, 4, 1], ["C", 11, 2, 1]])),
    ("sjf_np_ties", "Non-preemptive shortest job first. T1 arrives 0 burst 7; T2 arrives 2 burst 4; "
     "T3 arrives 4 burst 1; T4 arrives 5 burst 4. Compute the average waiting time.",
     S("SJF", [["T1", 0, 7, 1], ["T2", 2, 4, 1], ["T3", 4, 1, 1], ["T4", 5, 4, 1]])),
    ("srtf_gate", "GATE-style: processes P0, P1, P2 arrive at 0, 2 and 6 with CPU bursts 10, 20 "
     "and 30. With shortest-remaining-time-first, find the average waiting time.",
     S("SRTF", [["P0", 0, 10, 1], ["P1", 2, 20, 1], ["P2", 6, 30, 1]])),
    ("rr_q2_arrivals", "Round robin, time slice 2 ms. Arrivals/bursts: A 0/5, B 1/3, C 2/1, D 3/2, "
     "E 4/3. If a process arrives exactly when a slice ends, put the new arrival in the queue "
     "first. Give the average waiting time.",
     S("RR", [["A", 0, 5, 1], ["B", 1, 3, 1], ["C", 2, 1, 1], ["D", 3, 2, 1], ["E", 4, 3, 1]], 2)),
    ("prio_preempt", "Preemptive priority (smaller number wins). P1: arrival 0, burst 5, priority 3. "
     "P2: arrival 1, burst 3, priority 1. P3: arrival 2, burst 8, priority 4. P4: arrival 3, "
     "burst 2, priority 2. Average turnaround and average waiting?",
     S("PRIORITY_P", [["P1", 0, 5, 3], ["P2", 1, 3, 1], ["P3", 2, 8, 4], ["P4", 3, 2, 2]])),
    ("hrrn", "Using HRRN: process A arrives at 0 and needs 3, B at 2 needs 6, C at 4 needs 4, "
     "D at 6 needs 5, E at 8 needs 2. What is the average waiting time?",
     S("HRRN", [["A", 0, 3, 1], ["B", 2, 6, 1], ["C", 4, 4, 1], ["D", 6, 5, 1], ["E", 8, 2, 1]])),
    ("sjf_all_zero", "My OS homework: bursts of 5, 9, 2, 7 ms for P1..P4, everyone arrives at time 0. "
     "SJF please - what's the average wait?",
     S("SJF", [["P1", 0, 5, 1], ["P2", 0, 9, 1], ["P3", 0, 2, 1], ["P4", 0, 7, 1]])),
    ("rr_q3_long", "Round-robin with quantum 3. Six processes: P1 (arrives 0, needs 7), P2 (1, 4), "
     "P3 (3, 9), P4 (4, 2), P5 (6, 5), P6 (8, 3). Find average turnaround time.",
     S("RR", [["P1", 0, 7, 1], ["P2", 1, 4, 1], ["P3", 3, 9, 1], ["P4", 4, 2, 1], ["P5", 6, 5, 1],
              ["P6", 8, 3, 1]], 3)),
    ("srtf_idle", "SRTF. J1 arrives at 0 with 2 units of work, J2 arrives at 5 with 4 units, J3 "
     "arrives at 6 with 1 unit. What's the average waiting time?",
     S("SRTF", [["J1", 0, 2, 1], ["J2", 5, 4, 1], ["J3", 6, 1, 1]])),
    # ------------------------------------------------------------- paging
    ("fifo_classic", "ref string 7 0 1 2 0 3 0 4 2 3 0 3 2 1 2 0 1 7 0 1, 3 frames, FIFO. how many "
     "page faults?", dict(kind="paging", refs=REF, frames=3, policy="FIFO")),
    ("lru_classic", "Same string (7,0,1,2,0,3,0,4,2,3,0,3,2,1,2,0,1,7,0,1) but LRU with three "
     "frames - number of faults?", dict(kind="paging", refs=REF, frames=3, policy="LRU")),
    ("opt_classic", "Optimal replacement, 3 empty frames, pages requested: 7,0,1,2,0,3,0,4,2,3,0,3,"
     "2,1,2,0,1,7,0,1. Page faults?", dict(kind="paging", refs=REF, frames=3, policy="OPT")),
    ("belady_3", "FIFO with 3 frames on 3 2 1 0 3 2 4 3 2 1 0 4 - how many faults?",
     dict(kind="paging", refs=[3, 2, 1, 0, 3, 2, 4, 3, 2, 1, 0, 4], frames=3, policy="FIFO")),
    ("belady_4", "Now the same string 3 2 1 0 3 2 4 3 2 1 0 4 with FOUR frames under FIFO. Faults?",
     dict(kind="paging", refs=[3, 2, 1, 0, 3, 2, 4, 3, 2, 1, 0, 4], frames=4, policy="FIFO")),
    ("lru_4f", "A process touches pages 1, 2, 3, 4, 2, 1, 5, 6, 2, 1, 2, 3, 7, 6, 3, 2, 1, 2, 3, 6 "
     "in that order. Memory has 4 frames and uses LRU. Count the page faults.",
     dict(kind="paging", refs=[1, 2, 3, 4, 2, 1, 5, 6, 2, 1, 2, 3, 7, 6, 3, 2, 1, 2, 3, 6],
          frames=4, policy="LRU")),
    ("clock_small", "Second-chance (clock) replacement with 3 frames on the reference string "
     "2 3 2 1 5 2 4 5 3 2 5 2. How many page faults?",
     dict(kind="paging", refs=[2, 3, 2, 1, 5, 2, 4, 5, 3, 2, 5, 2], frames=3, policy="CLOCK")),
    ("opt_4f", "OPT page replacement, 4 frames, sequence 3 2 1 0 3 2 4 3 2 1 0 4. Faults?",
     dict(kind="paging", refs=[3, 2, 1, 0, 3, 2, 4, 3, 2, 1, 0, 4], frames=4, policy="OPT")),
    # ------------------------------------------------------------- banker
    ("banker_classic", "Banker's question from my textbook: Available (3,3,2). Allocation - P0 (0,1,0), "
     "P1 (2,0,0), P2 (3,0,2), P3 (2,1,1), P4 (0,0,2). Max - P0 (7,5,3), P1 (3,2,2), P2 (9,0,2), "
     "P3 (2,2,2), P4 (4,3,3). Safe or not? Give a safe sequence if safe.",
     dict(kind="banker_safety", **BK)),
    ("banker_req_grant", "Same system (Available 3 3 2; Alloc P0 0 1 0, P1 2 0 0, P2 3 0 2, P3 2 1 1, "
     "P4 0 0 2; Max P0 7 5 3, P1 3 2 2, P2 9 0 2, P3 2 2 2, P4 4 3 3). P1 asks for (1,0,2). "
     "Grant immediately?", dict(kind="banker_request", pid=1, req=[1, 0, 2], **BK)),
    ("banker_req_deny", "Using the textbook state Available=(3,3,2) with Allocation P0=(0,1,0), "
     "P1=(2,0,0), P2=(3,0,2), P3=(2,1,1), P4=(0,0,2) and Max P0=(7,5,3), P1=(3,2,2), P2=(9,0,2), "
     "P3=(2,2,2), P4=(4,3,3): can P0's request (0,2,0) be granted right away?",
     dict(kind="banker_request", pid=0, req=[0, 2, 0], **BK)),
    ("banker_total", "A system has 10 A, 5 B and 7 C in total. Current allocation: P0 (0,1,0), "
     "P1 (2,0,0), P2 (3,0,2), P3 (2,1,1), P4 (0,0,2). Maximum demand: P0 (7,5,3), P1 (3,2,2), "
     "P2 (9,0,2), P3 (2,2,2), P4 (4,3,3). Is it in a safe state?",
     dict(kind="banker_safety", total=[10, 5, 7], **BK)),
    ("banker_unsafe", "Resources R1 R2 R3, available 1 0 0. Process A holds 1 1 0 and could need "
     "up to 3 2 1. Process B holds 0 1 1, max 1 3 2. Process C holds 1 0 1, max 2 1 3. "
     "Does a safe sequence exist?",
     dict(kind="banker_safety", avail=[1, 0, 0], names=["A", "B", "C"],
          alloc=[[1, 1, 0], [0, 1, 1], [1, 0, 1]], maxm=[[3, 2, 1], [1, 3, 2], [2, 1, 3]])),
    ("banker_need_given", "Need matrix is given directly: P1 (1,2,2), P2 (0,1,1), P3 (4,3,1), "
     "P4 (1,0,0). Allocation: P1 (1,0,0), P2 (2,1,1), P3 (0,0,2), P4 (1,1,0). Available = (1,1,1). "
     "Check safety with the Banker's algorithm.",
     dict(kind="banker_safety", avail=[1, 1, 1], names=["P1", "P2", "P3", "P4"], given="need",
          alloc=[[1, 0, 0], [2, 1, 1], [0, 0, 2], [1, 1, 0]],
          maxm=[[2, 2, 2], [2, 2, 2], [4, 3, 3], [2, 1, 0]])),
    # ------------------------------------------------------------- disk
    ("sstf_classic", "Disk queue: 98, 183, 37, 122, 14, 124, 65, 67. Head starts at 53. SSTF - "
     "total head movement?", dict(kind="disk", reqs=DQ, head=53, policy="SSTF", size=200, direction="up")),
    ("scan_down", "Cylinders 0..199, head at 53 heading toward cylinder 0, queue 98 183 37 122 14 "
     "124 65 67. SCAN total movement?", dict(kind="disk", reqs=DQ, head=53, policy="SCAN", size=200,
                                             direction="down")),
    ("cscan_up", "C-SCAN on a 200-cylinder disk (0-199), head at 53 moving up, requests 98, 183, "
     "37, 122, 14, 124, 65, 67 (count the return sweep as movement). Total?",
     dict(kind="disk", reqs=DQ, head=53, policy="CSCAN", size=200, direction="up")),
    ("look_prev", "The arm is at 143 and just served a request at 125. Pending: 86, 1470, 913, 1774, "
     "948, 1509, 1022, 1750, 130 on a 5000-cylinder disk (0-4999). Using LOOK, how far does the "
     "head travel in total?",
     dict(kind="disk", reqs=[86, 1470, 913, 1774, 948, 1509, 1022, 1750, 130], head=143,
          policy="LOOK", size=5000, direction="up", prev=125)),
    ("fcfs_disk", "FCFS disk scheduling, head at 143, requests 86, 1470, 913, 1774, 948, 1509, "
     "1022, 1750, 130. Total seek distance?",
     dict(kind="disk", reqs=[86, 1470, 913, 1774, 948, 1509, 1022, 1750, 130], head=143,
          policy="FCFS", size=5000, direction="up")),
    ("clook_down", "C-LOOK, head at 50 moving towards lower numbers, pending requests 82, 170, 43, "
     "140, 24, 16, 190 (disk 0-199). Total head movement including the jump?",
     dict(kind="disk", reqs=[82, 170, 43, 140, 24, 16, 190], head=50, policy="CLOOK", size=200,
          direction="down")),
    ("sstf_2", "Head position 50. Requests: 82, 170, 43, 140, 24, 16, 190. Shortest seek time "
     "first. How many cylinders does the head move?",
     dict(kind="disk", reqs=[82, 170, 43, 140, 24, 16, 190], head=50, policy="SSTF", size=200,
          direction="up")),
    # ------------------------------------------------------------- translation
    ("translate_4k", "Page size 4 KB. Page table: page 0 -> frame 5, page 1 -> frame 6, page 2 -> "
     "frame 1, page 3 -> frame 2. Logical address 9000 maps to what physical address?",
     dict(kind="translate", logical=9000, page_size=4096, table=[5, 6, 1, 2])),
    ("translate_hex", "1 KB pages; the page table is [3, 7, 2, 9, 0]. What is the physical address "
     "for virtual address 0x0A2C?",
     dict(kind="translate", logical=0x0A2C, page_size=1024, table=[3, 7, 2, 9, 0], hex=True)),
    ("translate_2k", "With 2048-byte pages and page table 8, 1, 14, 3, 6, 11 (for pages 0 to 5), "
     "translate logical address 10000.",
     dict(kind="translate", logical=10000, page_size=2048, table=[8, 1, 14, 3, 6, 11])),
    # ------------------------------------------------------------- fit
    ("best_fit_classic", "Partitions (in order): 100 KB, 500 KB, 200 KB, 300 KB, 600 KB. Processes "
     "212 KB, 417 KB, 112 KB, 426 KB arrive in that order. Best fit placement?",
     dict(kind="freespace", holes=[100, 500, 200, 300, 600], reqs=[212, 417, 112, 426], policy="BEST")),
    ("worst_fit_classic", "Same memory holes 100K 500K 200K 300K 600K and requests 212K 417K 112K "
     "426K. Where does worst fit put each one?",
     dict(kind="freespace", holes=[100, 500, 200, 300, 600], reqs=[212, 417, 112, 426], policy="WORST")),
    ("first_fit_classic", "First fit: free blocks 100, 500, 200, 300, 600 KB; allocate 212, 417, "
     "112, 426 KB in order. Which ones cannot be allocated?",
     dict(kind="freespace", holes=[100, 500, 200, 300, 600], reqs=[212, 417, 112, 426], policy="FIRST")),
    ("best_fit_2", "Holes of 40 KB, 25 KB, 90 KB, 30 KB and 60 KB. Requests come for 28, 55, 35 and "
     "20 KB. Using best-fit, which hole does each request use?",
     dict(kind="freespace", holes=[40, 25, 90, 30, 60], reqs=[28, 55, 35, 20], policy="BEST")),
    # ------------------------------------------------------------- formulas
    ("eat_tlb_1", "TLB lookup 20 ns, memory access 100 ns, 80% TLB hit ratio, single-level page "
     "table. Effective access time?",
     dict(kind="eat_tlb", t=20, m=100, levels=1, h="4/5", inverse=False)),
    ("eat_tlb_2", "A system with a two-level page table has a TLB hit rate of 98%. Memory takes "
     "120 ns and a TLB search takes 10 ns. What is the EAT?",
     dict(kind="eat_tlb", t=10, m=120, levels=2, h="49/50", inverse=False)),
    ("eat_pf", "Memory access = 200 ns, page fault service = 8 ms, and 1 access in 1,000 causes a "
     "fault. Effective access time in ns?",
     dict(kind="eat_pagefault", ma=200, pf=8, p="1/1000", inverse=False)),
    ("paging_bits_1", "32-bit logical addresses, 4 KB pages, 4-byte page-table entries, 1 GB of "
     "physical memory. How many entries in the page table and how big is it? Also offset and "
     "frame bits.", dict(kind="paging_bits", la=32, k=12, pa=30, pte=4)),
    ("multilevel_1", "RISC-V Sv39-style paging: 39-bit virtual addresses, 4 KB pages, 8-byte PTEs, "
     "each table fits in one page. How many levels of page tables?",
     dict(kind="multilevel_paging", va=39, k=12, pte=8)),
    ("disk_time", "7200 RPM disk, 9 ms average seek, 100 MB/s transfer rate (1 MB = 1024 KB). "
     "Average time to read one 4 KB block?",
     dict(kind="disk_access", rpm=7200, seek=9, rate=100, kb=4, ctrl="0")),
    ("deadlock_min_1", "Six processes each need at most 3 tape drives. What's the minimum number of "
     "drives that guarantees no deadlock?", dict(kind="deadlock_min", mode="min", n=6, k=3)),
    ("deadlock_list", "Three processes need at most 3, 4 and 5 printers. Minimum printers so "
     "deadlock can never happen?", dict(kind="deadlock_min", mode="list", need=[3, 4, 5])),
    ("fork_1", "How many times does this print?\n\n```c\nint main() {\n  fork();\n  fork();\n  "
     "fork();\n  fork();\n  fork();\n  printf(\"hi\\n\");\n}\n```", dict(kind="fork_count", mode="print_after", n=5)),
    ("fork_loop", "for(i = 0; i < 4; i++) { fork(); } - how many child processes get created?",
     dict(kind="fork_count", mode="children", n=4)),
    ("semaphore_1", "Counting semaphore starts at 7. Then 20 P operations and 15 V operations happen. "
     "Final value?", dict(kind="semaphore", s0=7, p=20, v=15)),
    ("frag_1", "Page size 2048 bytes, process size 72,766 bytes. Pages needed and internal "
     "fragmentation?", dict(kind="internal_frag", k=11, size=72766)),
    ("cpu_util_1", "Processes wait for I/O 80% of the time. CPU utilisation with 4 processes in "
     "memory?", dict(kind="cpu_util", pct=80, mode="util", n=4)),
    ("cache_1", "Cache 5 ns, RAM 60 ns, cache hit rate 95%; a miss checks the cache first. Average "
     "access time?", dict(kind="cache_eat", c=5, m=60, h="19/20")),
    # ------------------------------------------------------------- clarify
    ("clarify_fit", "Use best fit on holes of 120, 300, 80 and 500 KB and tell me where each "
     "process ends up.", dict(kind="clarify", missing="fit_reqs", given="", need="request sizes",
                               why="", example="")),
    ("clarify_rr", "P1, P2, P3 all arrive at 0 with bursts 5, 3, 8. What is the average waiting time "
     "under round robin?", dict(kind="clarify", missing="rr_quantum", given="", need="time quantum",
                                why="", example="")),
    ("clarify_frames", "How many page faults does LRU give for 1 2 3 4 1 2 5 1 2 3 4 5?",
     dict(kind="clarify", missing="paging_frames", given="", need="number of frames", why="",
          example="")),
]


def main():
    out = []
    for name, q, v in ITEMS:
        ref = render_solution(v) if v["kind"] != "clarify" else "Please provide the missing value?"
        assert grade(dict(verify=v), ref)["final_correct"], f"reference fails grading: {name}"
        out.append(dict(id=name, topic=name, problem=q, verify=v, freeform=True))
    path = ROOT / "data" / "eval" / "os_freeform.jsonl"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    kinds = {}
    for r in out:
        kinds[r["verify"]["kind"]] = kinds.get(r["verify"]["kind"], 0) + 1
    print(f"{len(out)} hand-written items -> {path.relative_to(ROOT)}  {kinds}")


if __name__ == "__main__":
    main()
