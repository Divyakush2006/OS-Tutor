# UI test (through Open WebUI)

- **ostutor-solve**: 4/14 correct

| question | model | correct | expected | got | seconds |
|---|---|---|---|---|---|
| srtf_textbook | ostutor-solve | no | 6.5 | 9.0 | 17.7 |
| rr_q4 | ostutor-solve | no | 5.67 | 8.0 | 16.0 |
| priority_np | ostutor-solve | no | 8.2 | 2.4 | 16.8 |
| fifo_paging | ostutor-solve | no | 15 | 8 | 10.8 |
| lru_paging | ostutor-solve | no | 12 | 13 | 14.4 |
| opt_paging | ostutor-solve | no | 9 | 8 | 15.1 |
| banker_safe | ostutor-solve | yes | None | None | 20.8 |
| banker_request | ostutor-solve | yes | True | True | 18.4 |
| disk_sstf | ostutor-solve | no | 236 | 208.0 | 11.3 |
| disk_scan | ostutor-solve | no | 236 | 331.0 | 13.3 |
| disk_clook | ostutor-solve | yes | 322 | 322.0 | 12.7 |
| translate | ostutor-solve | yes | 4904 | 4904.0 | 5.4 |
| best_fit | ostutor-solve | no | [3, 1, 2, 4] | [None, 1, None, 4] | 11.6 |
| worst_fit | ostutor-solve | no | [4, 1, 4, None] | [None, None, 600, None] | 7.2 |

## srtf_textbook - ostutor-solve

**Q:** I have four processes. P1 arrives at time 0 and needs 8 ms, P2 arrives at 1 and needs 4 ms, P3 arrives at 2 and needs 9 ms, P4 arrives at 3 and needs 5 ms. What is the average waiting time with SRTF (preemptive SJF)?

**Algorithm: SRTF (preemptive SJF)**

**Step 1 - build the schedule**
- t=0: ready P1(8) -> run P1
- t=1: ready P1(7) P2(4) -> keep P1 (7 > 4)
- t=2: ready P1(6) P2(4) P3(9) -> keep P1 (6 > 4)
- t=3: ready P1(5) P2(4) P3(9) P4(5) -> keep P1 (5 > 4)
- t=4: ready P1(4) P2(4) P3(9) P4(5) -> keep P1 (4 == 4)
- t=5: ready P2(4) P1(3) P3(9) P4(5) -> PREEMPT P1 -> run P2
- t=9: P2 completes
- t=9: ready P1(3) P3(9) P4(5) -> run P1
- t=12: P1 completes
- t=12: ready P3(9) P4(5) -> run P3
- t=21: P3 completes
- t=21: ready P4(5) -> run P4
- t=26: P4 completes

**Step 2 - Gantt chart:** P1[0-5] P2[5-9] P1[9-12] P3[12-21] P4[21-26]

**Step 3 - per-process times** (Turnaround = Completion - Arrival; Waiting = Turnaround - Burst)

| Process | Arrival | Burst | Completion | Turnaround | Waiting |
|----------|----------|--------|-------------|--------------|-------------|
| P1 | 0 | 8 | 12 | 12 - 0 = 12 | 12 - 8 = 4 |
| P2 | 1 | 4 | 9 | 9 - 1 = 8 | 8 - 4 = 4 |
| P3 | 2 | 9 | 21 | 21 - 2 = 19 | 19 - 9 = 10 |
| P4 | 3 | 5 | 26 | 26 - 3 = 23 | 23 - 5 = 18 |

**Step 4 - averages**

- Sum of waiting times: 4 + 4 = 8, 8 + 10 = 18, 18 + 18 = 36
- Average waiting time = 36 / 4 = **9.0**
- Sum of turnaround times: 12 + 8 = 20, 20 + 19 = 39, 39 + 23 = 62
- Average turnaround time = 62 / 4 = **15.5**

## rr_q4 - ostutor-solve

**Q:** Three processes all arrive at time 0: P1 with a burst of 24 ms, P2 with 3 ms and P3 with 3 ms. Using Round Robin with a time quantum of 4 ms, find the average waiting time and the average turnaround time.

**Algorithm: Round Robin (quantum = 4)**

**Step 1 - build the schedule**
- t=0-4: P1 runs, 24 - 4 = 20 left; queue [P1, P2, P3]
- t=4-7: P2 runs, 3 - 3 = 0 left; done at 7; queue [P1, P3]
- t=7-11: P1 runs, 20 - 4 = 16 left; queue [P1, P3]
- t=11-15: P3 runs, 3 - 3 = 0 left; done at 15; queue [P1]
- t=15-20: P1 runs, 16 - 4 = 12 left; queue [P1]
- t=20-24: P1 runs, 12 - 4 = 8 left; queue [P1]
- t=24-28: P1 runs, 8 - 4 = 4 left; queue [P1]
- t=28-32: P1 runs, 4 - 4 = 0 left; done at 32; queue []

**Step 2 - Gantt chart:** P1[0-4] P2[4-7] P1[7-11] P3[11-15] P1[15-20] P1[20-24] P1[24-28] P1[28-32]

**Step 3 - per-process times** (Turnaround = Completion - Arrival; Waiting = Turnaround - Burst)

| Process | Arrival | Burst | Completion | Turnaround | Waiting |
|---------|---------|-------|------------|-------------|------------|
| P1 | 0 | 24 | 32 | 32 - 0 = 32 | 32 - 24 = 8 |
| P2 | 0 | 3 | 7 | 7 - 0 = 7 | 7 - 3 = 4 |
| P3 | 0 | 3 | 15 | 15 - 0 = 15 | 15 - 3 = 12 |

**Step 4 - averages**

- Sum of waiting times: 8 + 4 = 12, 12 + 12 = 24
- Average waiting time = 24 / 3 = **8.0**
- Sum of turnaround times: 32 + 7 = 39, 39 + 15 = 54
- Average turnaround time = 54 / 3 = **18.0**

## priority_np - ostutor-solve

**Q:** Five processes arrive at time 0 in the order P1..P5 with burst times 10, 1, 2, 1, 5 and priorities 3, 1, 4, 5, 2 (a smaller number means higher priority). Using non-preemptive priority scheduling, what is the average waiting time?

**Algorithm: non-preemptive priority scheduling**

**Step 1 - build the schedule**
- t=0: ready P2(p1) P5(p2) P3(p4) P4(p5) P1(p3) -> run P2 (burst 1, arrival 0, completed at 0 + 1 = 1)
- t=1: ready P5(p2) P3(p4) P4(p5) P1(p3) -> run P5 (burst 1, arrival 0, completed at 1 + 1 = 2)
- t=2: ready P3(p4) P4(p5) P1(p3) -> run P3 (burst 2, arrival 0, completed at 2 + 2 = 4)
- t=4: ready P4(p5) P1(p3) -> run P4 (burst 1, arrival 0, completed at 4 + 1 = 5)
- t=5: ready P1(p3) -> run P1 (burst 10, arrival 0, completed at 5 + 10 = 15)

**Step 2 - Gantt chart:** P2[0-1] P5[1-2] P3[2-4] P4[4-5] P1[5-15]

**Step 3 - per-process times** (Turnaround = Completion - Arrival; Waiting = Turnaround - Burst)

| Process | Arrival | Burst | Completion | Turnaround | Waiting |
|----------|----------|--------|-------------|--------------|-------------|
| P1 | 0 | 10 | 15 | 15 - 0 = 15 | 15 - 10 = 5 |
| P2 | 0 | 1 | 1 | 1 - 0 = 1 | 1 - 1 = 0 |
| P3 | 0 | 2 | 4 | 4 - 0 = 4 | 4 - 2 = 2 |
| P4 | 0 | 1 | 5 | 5 - 0 = 5 | 5 - 1 = 4 |
| P5 | 0 | 1 | 2 | 2 - 0 = 2 | 2 - 1 = 1 |

**Step 4 - averages**

- Sum of waiting times: 5 + 0 = 5, 5 + 2 = 7, 7 + 4 = 11, 11 + 1 = 12
- Average waiting time = 12 / 5 = **2.4**
- Sum of turnaround times: 15 + 1 = 16, 16 + 4 = 20, 20 + 5 = 25, 25 + 2 = 27
- Average turnaround time = 27 / 5 = **5.4**

## fifo_paging - ostutor-solve

**Q:** For the reference string 7 0 1 2 0 3 0 4 2 3 0 3 2 1 2 0 1 7 0 1 with 3 frames, how many page faults does FIFO replacement cause?

**Policy: FIFO, 3 frames**

- 7: miss, evict 7, faults = 1; frames[0]=7, frames[1]=0, frames[2]=1
- 0: hit
- 1: hit
- 2: miss, evict 7, faults = 2; frames[0]=2, frames[1]=0, frames[2]=1
- 0: hit
- 3: miss, evict 2, faults = 3; frames[0]=3, frames[1]=0, frames[2]=1
- 0: hit
- 4: miss, evict 3, faults = 4; frames[0]=4, frames[1]=0, frames[2]=1
- 2: miss, evict 4, faults = 5; frames[0]=2, frames[1]=0, frames[2]=1
- 3: miss, evict 2, faults = 6; frames[0]=3, frames[1]=0, frames[2]=1
- 0: hit
- 3: hit
- 2: miss, evict 3, faults = 7; frames[0]=2, frames[1]=0, frames[2]=1
- 1: hit
- 2: hit
- 0: hit
- 1: hit
- 7: miss, evict 2, faults = 8; frames[0]=7, frames[1]=0, frames[2]=1
- 0: hit
- 1: hit
- 7: hit
- 0: hit
- 1: hit

**Total page faults = 8**

## lru_paging - ostutor-solve

**Q:** Same reference string 7 0 1 2 0 3 0 4 2 3 0 3 2 1 2 0 1 7 0 1 and 3 frames: how many page faults with LRU?

**Policy: LRU, 3 frames**

| # | Ref | Result | Evicted | Frames (least recently used first) | Faults |
|---|-----|--------|---------|--------|--------|
| 1 | 7 | miss | - | 7 | 1 |
| 2 | 0 | miss | - | 7 0 | 2 |
| 3 | 1 | miss | - | 7 0 1 | 3 |
| 4 | 2 | miss | 7 | 0 1 2 | 4 |
| 5 | 0 | hit | - | 0 1 2 | 4 |
| 6 | 3 | miss | 0 | 1 2 3 | 5 |
| 7 | 0 | miss | 1 | 2 3 0 | 6 |
| 8 | 4 | miss | 2 | 3 0 4 | 7 |
| 9 | 2 | miss | 3 | 0 4 2 | 8 |
| 10 | 3 | miss | 0 | 4 2 3 | 9 |
| 11 | 0 | miss | 4 | 2 3 0 | 10 |
| 12 | 3 | hit | - | 2 0 3 | 10 |
| 13 | 2 | hit | - | 0 3 2 | 10 |
| 14 | 1 | miss | 0 | 3 2 1 | 11 |
| 15 | 2 | hit | - | 3 1 2 | 11 |
| 16 | 0 | miss | 3 | 1 2 0 | 12 |
| 17 | 1 | hit | - | 2 0 1 | 12 |
| 18 | 7 | miss | 2 | 0 1 7 | 13 |
| 19 | 0 | hit | - | 1 7 0 | 13 |
| 20 | 1 | hit | - | 7 0 1 | 13 |

**Total page faults = 13** (hits = 20 - 13 = 7, hit ratio = 7 / 20 = 0.35)

## opt_paging - ostutor-solve

**Q:** How many page faults does the optimal (OPT) algorithm give for 7 0 1 2 0 3 0 4 2 3 0 3 2 1 2 0 1 7 0 1 with 3 frames?

**Policy: OPT, 3 frames**

- t 0: evict nothing, 7 not in memory -> miss, evict nothing, 7@7; faults = 1
- t 1: evict nothing, 0 not in memory -> miss, evict nothing, 0@0; faults = 2
- t 2: evict nothing, 1 not in memory -> miss, evict nothing, 1@1; faults = 3
- t 3: evict nothing, 2 not in memory -> miss, evict nothing, 2@2; faults = 4
- t 4: evict nothing, 0 is in memory -> hit; faults = 4
- t 5: evict nothing, 3 not in memory -> miss, evict nothing, 3@3; faults = 5
- t 6: evict nothing, 0 is in memory -> hit; faults = 5
- t 7: evict nothing, 4 not in memory -> miss, evict nothing, 4@4; faults = 6
- t 8: evict nothing, 2 is in memory -> hit; faults = 6
- t 9: evict nothing, 3 is in memory -> hit; faults = 6
- t 10: evict nothing, 0 is in memory -> hit; faults = 6
- t 11: evict nothing, 3 is in memory -> hit; faults = 6
- t 12: evict nothing, 2 is in memory -> hit; faults = 6
- t 13: evict nothing, 1 not in memory -> miss, evict nothing, 1@1; faults = 7
- t 14: evict nothing, 2 is in memory -> hit; faults = 7
- t 15: evict nothing, 0 is in memory -> hit; faults = 7
- t 16: evict nothing, 1 is in memory -> hit; faults = 7
- t 17: evict nothing, 7 not in memory -> miss, evict nothing, 7@7; faults = 8
- t 18: evict nothing, 0 is in memory -> hit; faults = 8
- t 19: evict nothing, 1 is in memory -> hit; faults = 8

**Total page faults = 8** (hits = 20, hit ratio = 20 / 20 = 1.0)

## banker_safe - ostutor-solve

**Q:** A system has resources A, B, C with Available = (3, 3, 2). Allocation: P0 (0,1,0), P1 (2,0,0), P2 (3,0,2), P3 (2,1,1), P4 (0,0,2). Max: P0 (7,5,3), P1 (3,2,2), P2 (9,0,2), P3 (2,2,2), P4 (4,3,3). Is the system in a safe state? If so, give a safe sequence.

**Step 1 - compute Need = Max - Allocation** (row by row)

- P0: (7, 5, 3) - (0, 1, 0) = (7, 4, 3)
- P1: (3, 2, 2) - (2, 0, 0) = (1, 2, 2)
- P2: (9, 0, 2) - (3, 0, 2) = (6, 0, 0)
- P3: (2, 2, 2) - (2, 1, 1) = (0, 1, 1)
- P4: (4, 3, 3) - (0, 0, 2) = (4, 3, 1)

**Step 2 - run the safety algorithm**

- Work = Available = (3, 3, 2)
- P0: Need (7, 4, 3) vs Work (3, 3, 2): 7>3, 4>3, 3<=2 -> cannot run yet
- P1: Need (1, 2, 2) vs Work (3, 3, 2): 1<=3, 2<=3, 2<=2 -> all fit, run it. Work = (3, 3, 2) + Allocation (2, 0, 0) = (5, 3, 2)
- P0: Need (7, 4, 3) vs Work (5, 3, 2): 7>5, 4>3, 3>2 -> cannot run yet
- P2: Need (6, 0, 0) vs Work (5, 3, 2): 6>5, 0<=3, 0<=2 -> cannot run yet
- P3: Need (0, 1, 1) vs Work (5, 3, 2): 0<=5, 1<=3, 1<=2 -> all fit, run it. Work = (5, 3, 2) + Allocation (2, 1, 1) = (7, 4, 3)
- P0: Need (7, 4, 3) vs Work (7, 4, 3): 7<=7, 4<=4, 3<=3 -> all fit, run it. Work = (7, 4, 3) + Allocation (0, 1, 0) = (7, 5, 3)
- P2: Need (6, 0, 0) vs Work (7, 5, 3): 6<=7, 0<=5, 0<=3 -> all fit, run it. Work = (7, 5, 3) + Allocation (3, 0, 2) = (10, 5, 5)
- P4: Need (4, 3, 1) vs Work (10, 5, 5): 4<=10, 3<=5, 1<=5 -> all fit, run it. Work = (10, 5, 5) + Allocation (0, 0, 2) = (10, 5, 7)

**Step 3 - conclusion**

All 5 processes can complete, so the system is in a **SAFE state**.
A safe sequence is **< P1, P3, P0, P2, P4 >**.

_Safe sequences are not unique: any ordering in which each process's Need is met by the running Work vector is equally correct._

## banker_request - ostutor-solve

**Q:** In that same system (Available (3,3,2); Allocation P0 (0,1,0), P1 (2,0,0), P2 (3,0,2), P3 (2,1,1), P4 (0,0,2); Max P0 (7,5,3), P1 (3,2,2), P2 (9,0,2), P3 (2,2,2), P4 (4,3,3)), P1 requests (1,0,2). Can the request be granted immediately?

**Step-by-step simulation.**

- Request (1,0,2) vs Need (1,2,2): 1<=1, 0<=2, 2<=2 -> OK
- Request (1,0,2) vs Available (3,3,2): 1<=3, 0<=3, 2<=2 -> OK
- Simulation continues; resources are granted
- Allocation P1 = Allocation P1 + Request = (2,0,0) + (1,0,2) = (3,0,2)
- Available = Available - Request = (3,3,2) - (1,0,2) = (2,3,0)
- Now run the safety algorithm
- Work = Available = (2,3,0)
- P0: Need (7,4,3) vs Work (2,3,0): 7>2, 4>3, 3>0 -> cannot run yet
- P1: Need (0,2,0) vs Work (2,3,0): 0<=2, 2<=3, 0<=0 -> all fit, run it. Work = Work + Allocation = (2,3,0) + (3,0,2) = (5,3,2)
- P0: Need (7,4,3) vs Work (5,3,2): 7>5, 4>3, 3>2 -> cannot run yet
- P2: Need (6,0,0) vs Work (5,3,2): 6>5, 0<=3, 0<=2 -> cannot run yet
- P3: Need (0,2,0) vs Work (5,3,2): 0<=5, 2<=3, 0<=2 -> all fit, run it. Work = Work + Allocation = (5,3,2) + (2,1,1) = (7,4,3)
- P0: Need (7,4,3) vs Work (7,4,3): 7<=7, 4<=4, 3<=3 -> all fit, run it. Work = Work + Allocation = (7,4,3) + (0,1,0) = (7,5,3)
- P2: Need (6,0,0) vs Work (7,5,3): 6<=7, 0<=5, 0<=3 -> all fit, run it. Work = Work + Allocation = (7,5,3) + (3,0,2) = (10,5,5)
- P4: Need (4,3,1) vs Work (10,5,5): 4<=10, 3<=5, 1<=5 -> all fit, run it. Work = Work + Allocation = (10,5,5) + (0,0,2) = (10,5,7)
- SAFE. Safe sequence: < P1, P3, P0, P2, P4 >
- Resulting state is SAFE (sequence < P1, P3, P0, P2, P4 >)

**Conclusion: the request is GRANTED.**

## disk_sstf - ostutor-solve

**Q:** The disk head is at cylinder 53 on a 200-cylinder disk (0-199). The queue is 98, 183, 37, 122, 14, 124, 65, 67. What is the total head movement with SSTF?

**Policy: SSTF**

- sorted requests: [14, 37, 65, 67, 98, 122, 124, 183]; below head 53: [14, 37]; at/after head: [65, 67, 98, 122, 124, 183]
- 53 -> 37: 53 - 37 = 16; running total 0 + 16 = 16
- 37 -> 14: 37 - 14 = 23; running total 16 + 23 = 39
- 14 -> 65: 65 - 14 = 51; running total 39 + 51 = 90
- 65 -> 67: 67 - 65 = 2; running total 90 + 2 = 92
- 67 -> 98: 98 - 67 = 31; running total 92 + 31 = 123
- 98 -> 122: 122 - 98 = 24; running total 123 + 24 = 147
- 122 -> 124: 124 - 122 = 2; running total 147 + 2 = 149
- 124 -> 183: 183 - 124 = 59; running total 149 + 59 = 208

**Total head movement = 208 cylinders**

## disk_scan - ostutor-solve

**Q:** Same queue 98, 183, 37, 122, 14, 124, 65, 67 with the head at 53 on a 0-199 disk, moving towards 0. What is the total head movement with SCAN?

**Policy: SCAN (up then down)**

- sorted requests: [14, 37, 65, 67, 98, 122, 124, 183]; below head 53: [14, 37]; at/above head: [65, 67, 98, 122, 124, 183]
- SCAN up: service [65, 67, 98, 122, 124, 183], go to the end of the disk, then reverse
- 53 -> 65: 65 - 53 = 12; running total 0 + 12 = 12
- 65 -> 67: 67 - 65 = 2; running total 12 + 2 = 14
- 67 -> 98: 98 - 67 = 31; running total 14 + 31 = 45
- 98 -> 122: 122 - 98 = 24; running total 45 + 24 = 69
- 122 -> 124: 124 - 122 = 2; running total 69 + 2 = 71
- 124 -> 183: 183 - 124 = 59; running total 71 + 59 = 130
- 183 -> 199: 199 - 183 = 16; running total 130 + 16 = 146
- 199 -> 37: 199 - 37 = 162; running total 146 + 162 = 308
- 37 -> 14: 37 - 14 = 23; running total 308 + 23 = 331

**Total head movement = 331 cylinders**

## disk_clook - ostutor-solve

**Q:** Head at 53 on a 0-199 disk, moving towards higher cylinders, queue 98, 183, 37, 122, 14, 124, 65, 67. Give the service order and total head movement for C-LOOK.

**Policy: C-LOOK**

- sorted requests: [14, 37, 65, 67, 98, 122, 124, 183]; below head 53: [14, 37]; at/above head: [65, 67, 98, 122, 124, 183]
- C-LOOK: service upward to the last request, jump to the lowest pending request, resume upward
- 53 -> 65: 65 - 53 = 12; running total 0 + 12 = 12
- 65 -> 67: 67 - 65 = 2; running total 12 + 2 = 14
- 67 -> 98: 98 - 67 = 31; running total 14 + 31 = 45
- 98 -> 122: 122 - 98 = 24; running total 45 + 24 = 69
- 122 -> 124: 124 - 122 = 2; running total 69 + 2 = 71
- 124 -> 183: 183 - 124 = 59; running total 71 + 59 = 130
- 183 -> 14: 183 - 14 = 169; running total 130 + 169 = 299
- 14 -> 37: 37 - 14 = 23; running total 299 + 23 = 322

**Service order:** 65 -> 67 -> 98 -> 122 -> 124 -> 183 -> 14 -> 37
**Total head movement = 322 cylinders**

## translate - ostutor-solve

**Q:** Pages are 4 KB (4096 bytes). The page table maps page 0 to frame 5, page 1 to frame 6, page 2 to frame 1 and page 3 to frame 2. What physical address does logical address 9000 map to?

**Step-by-step translation**

- page number = floor(9000 / 4096) = 2 (check: 2 x 4096 = 8192 <= 9000 < 12288)
- page offset = 9000 - 8192 = 808
- page table[2] = frame 1
- frame base = 1 x 4096 = 4096
- physical address = 4096 + 808 = 4904

**Physical address = 4904**

## best_fit - ostutor-solve

**Q:** Memory partitions are 100 KB, 500 KB, 200 KB, 300 KB and 600 KB, in that order. Processes of 212 KB, 417 KB, 112 KB and 426 KB arrive in that order. Where does best-fit place each one?

**Policy: best-fit**

- holes (free KB, by number): hole 0=100, hole 1=500, hole 2=200, hole 3=300, hole 4=600
- request 212: fitting holes [hole 1=500, hole 2=200, hole 3=300, hole 4=600] -> smallest fitting hole = hole 2; 200 - 212 = -12 -> none fit
- request 417: fitting holes [hole 1=500, hole 4=600] -> smallest fitting hole = hole 1; 500 - 417 = 83
- request 112: fitting holes [hole 0=100, hole 1=83, hole 2=200, hole 3=300, hole 4=600] -> smallest fitting hole = hole 0; 100 - 112 = -12 -> none fit
- request 426: fitting holes [hole 4=600] -> smallest fitting hole = hole 4; 600 - 426 = 174

**Placement:** [none, 1, none, 4]
**Remaining free space per hole:** [100, 83, 200, 300, 174]
- Sum of free space: 100 + 83 = 183, 183 + 200 = 383, 383 + 300 = 683, 683 + 174 = 857
**Total external fragmentation = 857 KB**

## worst_fit - ostutor-solve

**Q:** Same partitions 100, 500, 200, 300, 600 KB and processes 212, 417, 112, 426 KB. Where does worst-fit place each process?

**Step-by-step solution:**

- holes (free KB): [100, 500, 200, 300, 600]; sum = 1700
- fit[212]: none >= 212 -> None
- fit[417]: none >= 417 -> None
- fit[112]: holes [100, 500, 200, 300, 600] >= 112 -> largest fitting hole = 600; 600 - 112 = 488
- fit[426]: none >= 426 -> None
- placement = [None, None, 600, None]
- remaining free space = 1700 - 112 = 1588
- placement: [None, None, 600, None]
- remaining free space: 1588

## explain_thrashing - ostutor-explain

**Q:** What is thrashing and how can an OS prevent it?

They sit in the same area (memory) but answer different questions.

**What is thrashing?** Thrashing is a case of EXCESSIVE page-fault rate, caused by degree of multiprogramming exceeding available real memory. It is measured by the page-fault rate, not by how much memory is left.

**How can an OS prevent it?** The usual heuristic is to raise the threshold for swapping out memory processes, so the degree of multiprogramming never reaches the thrashing region. That is what the degree of multiprogramming must be kept below.

**Where students go wrong:** One common error is to think thrashing means the system has no free frames; another is to think swapping out a process is the same as taking it out of memory. Both come from the same habit of reasoning from the name rather than the mechanism.

**Putting them together:** A system with 1 GB RAM and 10 processes each using 128 MB faults constantly - far more than it can service - is thrashing. Raising the threshold to 800 MB per process stops the fault rate from rising.

## explain_deadlock - ostutor-explain

**Q:** What are the four necessary conditions for deadlock? Give an example of each.

They sit in the same area (deadlock) but answer different questions.

**The four necessary conditions for deadlock.** Mutual exclusion, hold-and-wait, no preemption and circular wait must ALL hold simultaneously. Breaking any one breaks the cycle.

**An example of each.** A printer cannot be held by two processes at once (mutual exclusion); a process that has opened a file may wait for another file it did not open (hold-and-wait); a database transaction may roll back its own changes (no preemption); four processes each holding a resource held in circular fashion (circular wait).

**Where students go wrong.** One common error is to think deadlock can only happen when every process holds a resource; another is to think deadlock cannot happen with preemption. Both come from the same habit of reasoning from the name rather than the mechanism.

**Putting them together.** A process that opens a file and then waits for another file it never opened is in hold-and-wait. By contrast, a process that opens a file and then waits for another file it never opened is in hold-and-wait.

## explain_paging_vs_seg - ostutor-explain

**Q:** Compare paging and segmentation. When would you prefer each?

They sit in the same area (memory) but answer different questions.

**Paging.** Paging divides memory into fixed-size pages and uses a PAGE TABLE to map each page number to a frame number. It eliminates external fragmentation and enables demand paging, but the page table grows with address space and page-table misses are costly.

**Segmentation.** Segmentation divides memory into VARIABLE-SIZE segments, each identifying a logical unit (code, data, stack). A segment table maps each segment number to a base and limit, and protection is enforced per segment. It supports modular programming and relocatable code but suffers internal fragmentation and makes protection and paging more complex.

**Where students go wrong.** One common error is to think paging and segmentation solve the same problem - external fragmentation - so they are interchangeable; another is to think segmentation is just a fancy form of paging. Both come from the same area but answer different questions.

**Putting them together.** A 4 KB page table for a 1 GB address space requires about 1 MB of table entries. By contrast, a segment table for a small program can be kept entirely in registers.

## tutor_fcfs - ostutor-tutor

**Q:** I calculated the FCFS average waiting time for bursts 24, 3, 3 (all arriving at 0) as 17. Is that right?

Hi, can you walk me through your calculation?

## edge_missing_input - ostutor-solve

**Q:** Apply first-fit to memory holes of 100, 500, 200 and 300 KB. Which hole serves each request?

**Policy: first-fit**

- holes: [100@0, 500@1, 200@2, 300@3]; free KB = 100 + 500 + 200 + 300 = 1100
- request 100: fitting holes [100@0, 500@1, 200@2, 300@3] -> lowest-numbered fitting hole = 100@0; 100 - 100 = 0
- request 200: fitting holes [500@1, 200@2, 300@3] -> lowest-numbered fitting hole = 500@1; 500 - 200 = 300
- request 150: fitting holes [300@3] -> lowest-numbered fitting hole = 300@3; 300 - 150 = 150
- request 250: fitting holes [500@1] -> lowest-numbered fitting hole = 500@1; 300 - 250 = 50
- request 300: free sizes [0, 50, 200, 150], none >= 300 -> must WAIT
- request 350: free sizes [0, 50, 200, 150], none >= 350 -> must WAIT
- request 400: free sizes [0, 50, 200, 150], none >= 400 -> must WAIT
- request 500: free sizes [0, 50, 200, 150], none >= 500 -> must WAIT
- request 600: free sizes [0, 50, 200, 150], none >= 600 -> must WAIT
- request 700: free sizes [0, 50, 200, 150], none >= 700 -> must WAIT
- request 800: free sizes [0, 50, 200, 150], none >= 800 -> must WAIT
- request 900: free sizes [0, 50, 200, 150], none >= 900 -> must WAIT
- request 1000: free sizes [0, 50, 200, 150], none >= 1000 -> must WAIT
- request 1100: free sizes [0, 50, 200, 150], none >= 1100 -> must WAIT

**Placement:** [100, 500, 300, 500, None, None, None, None, None, None, None, None, None, None]
**Remaining free space per hole:** [0, 50, 200, 150]
- Sum of free space: 0 + 50 = 50, 50 + 200 = 250, 250 + 150 = 400
**Total external fragmentation = 400 KB**
