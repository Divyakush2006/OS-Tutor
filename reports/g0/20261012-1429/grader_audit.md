# Grader audit — 20261012-1429

Items graded wrong whose concluding lines still contain the expected value. Each needs a human read; this file changes no grade.

| Configuration | Graded wrong | Suspects |
|---|---|---|
| base+solver | 8 | 0 |
| base | 32 | 6 |
| v2.2+solver | 14 | 0 |
| v2.2 | 38 | 6 |
| v3+solver | 0 | 0 |
| v3 | 23 | 6 |

### base · lru_classic (paging) — expected 12, grader read 15, finish=stop

```
- Step12: 3 → no
- Step13: 2 → no
- Step14: 1 → fault (11)
- Step15: 2 → fault (12)
- Step16: 0 → no
- Step17: 1 → no
- Step18: 7 → fault (13)
- Step19: 0 → fault (14)
- Step20: 1 → fault (15)
✅ Total page faults = **15**
---
### ✅ Final Answer:
**15** page faults occur when using LRU with 3 frames.
--- 
✅ **Answer: 15**
```

### base · lru_4f (paging) — expected 10, grader read 18, finish=stop

```
12. Page 3 → fault  
13. Page 7 → fault  
14. Page 6 → fault  
15. Page 3 → no  
16. Page 2 → no  
17. Page 1 → fault  
18. Page 2 → no  
19. Page 3 → no  
20. Page 6 → no  
So faults at:  
- 1, 2, 3, 4, 7, 8, 12, 13, 14, 17 → total of **10**
✅ Final answer: **10 page faults**
---
### ✅ Final Answer:
**10**
```

### base · scan_down (disk) — expected 236, grader read 53.0, finish=stop

```
- Head starts at 53  
- Moves down to 37 → 16  
- Then to 14 → 23  
- Then to 0 → 14  
- Total down: 16 + 23 + 14 = 53  
- Then moves up to 98 → 98  
- To 122 → 24  
- To 124 → 2  
- To 183 → 59  
- Total up: 98 + 24 + 2 + 59 = 183  
- Total: 53 + 183 = **236**
All requests are served.
---
### ✅ Final Answer:
**236**
```

### base · fcfs_disk (disk) — expected 7081, grader read None, finish=stop

```
Total seek distance =  
57 + 1384 + 557 + 861 + 826 + 561 + 487 + 728 + 1620
Let’s compute step by step:
- 57 + 1384 = 1441  
- 1441 + 557 = 1998  
- 1998 + 861 = 2859  
- 2859 + 826 = 3685  
- 3685 + 561 = 4246  
- 4246 + 487 = 4733  
- 4733 + 728 = 5461  
- 5461 + 1620 = **7081**
6. **Final answer**:  
The total seek distance using FCFS is **7081**.
✅ All steps are auditable, no assumptions made, and the input is fully provided.
**Final Answer: 7081**
```

### base · sstf_2 (disk) — expected 208, grader read None, finish=stop

```
- 170 → 190: 20  
**Total seek distance = 7 + 19 + 8 + 66 + 58 + 30 + 20**
Let’s compute:
- 7 + 19 = 26  
- 26 + 8 = 34  
- 34 + 66 = 100  
- 100 + 58 = 158  
- 158 + 30 = 188  
- 188 + 20 = **208**
---
### ✅ Final Answer:
**208 cylinders**
This is the total number of cylinders the head moves under SSTF.
---
**Answer: 208** ✅
```

### base · translate_4k (translate) — expected 4904, grader read 4.0, finish=stop

```
So, **Page number = 2**
---
### Step 3: Use the page table to find the frame number
From the page table:
- Page 2 → Frame 1
So, the **frame number** is **1**
---
### Step 4: Compute the physical address
Physical address = (Frame number × page size) + offset  
= (1 × 4096) + 808  
= 4096 + 808  
= **4904**
---
### ✅ Final Answer:
**4904**
```

### v2.2 · sjf_np_ties (scheduling) — expected 4.0, grader read 4.75, finish=stop

```
- t=11: ready={T3(1)} -> pick T3 (shortest burst 1), completes at 11 + 1 = 12
- t=12: ready={T4(4)} -> pick T4 (shortest burst 4), completes at 12 + 4 = 16
**Step 2 - Gantt chart:** T1[0-7] T2[7-11] T3[11-12] T4[12-16]
**Step 3 - per-process times** (Turnaround = Completion - Arrival; Waiting = Turnaround - Burst)
| Process | Arrival | Burst | Completion | Turnaround | Waiting |
|---------|---------|-------|------------|-------------|------------|
| T1 | 0 | 7 | 7 | 7 - 0 = 7 | 7 - 7 = 0 |
| T2 | 2 | 4 | 11 | 11 - 2 = 9 | 9 - 4 = 5 |
| T3 | 4 | 1 | 12 | 12 - 4 = 8 | 8 - 1 = 7 |
| T4 | 5 | 4 | 16 | 16 - 5 = 11 | 11 - 4 = 7 |
**Step 4 - averages**
- Sum of waiting times: 0 + 5 = 5, 5 + 7 = 12, 12 + 7 = 19
- Average waiting time = 19 / 4 = **4.75**
- Sum of turnaround times: 7 + 9 = 16, 16 + 8 = 24, 24 + 11 = 35
- Average turnaround time = 35 / 4 = **8.75**
```

### v2.2 · hrrn (scheduling) — expected 4.0, grader read 4.6, finish=stop

```
**Step 2 - Gantt chart:** A[0-3] B[3-9] C[9-13] D[13-18] E[18-20]
**Step 3 - per-process times**
| Process | Arrival | Burst | Completion | Turnaround (Completion - Arrival) | Waiting (Turnaround - Burst) |
|---------|---------|-------|------------|------------------------|------------------------|
| A | 0 | 3 | 3 | 3 - 0 = 3 | 3 - 3 = 0 |
| B | 2 | 6 | 9 | 9 - 2 = 7 | 7 - 6 = 1 |
| C | 4 | 4 | 13 | 13 - 4 = 9 | 9 - 4 = 5 |
| D | 6 | 5 | 18 | 18 - 6 = 12 | 12 - 5 = 7 |
| E | 8 | 2 | 20 | 20 - 8 = 12 | 12 - 2 = 10 |
**Step 4 - average**
- Sum of waiting times: 0 + 1 = 1, 1 + 5 = 6, 6 + 7 = 13, 13 + 10 = 23
- Average waiting time = 23 / 5 = 4.6
- Sum of turnaround times: 3 + 7 = 10, 10 + 9 = 19, 19 + 12 = 31, 31 + 12 = 43
- Average turnaround time = 43 / 5 = 8.6
**Conclusion:** Average waiting time = 4.6; Average turnaround time = 8.6
```

### v2.2 · fifo_classic (paging) — expected 15, grader read 16, finish=stop

```
- 3: miss, evict 0, faults = 10, frames {4, 2, 3}
- 0: miss, evict 4, faults = 11, frames {2, 3, 0}
- 3: hit, frames {2, 3, 0}
- 2: hit, frames {2, 3, 0}
- 1: miss, evict 2, faults = 12, frames {3, 0, 1}
- 2: miss, evict 3, faults = 13, frames {0, 1, 2}
- 0: hit, frames {0, 1, 2}
- 1: hit, frames {0, 1, 2}
- 7: miss, evict 0, faults = 14, frames {1, 2, 7}
- 0: miss, evict 1, faults = 15, frames {2, 7, 0}
- 1: miss, evict 2, faults = 16, frames {7, 0, 1}
- 7: hit, frames {7, 0, 1}
- 0: hit, frames {7, 0, 1}
- 1: hit, frames {7, 0, 1}
**Total page faults = 16**
```

### v2.2 · belady_3 (paging) — expected 9, grader read 2, finish=stop

```
**Step-by-step simulation.** FIFO means the oldest page is evicted first.
- t 0: 3 not in memory, evict 3, fault 3 -> 3 2 1 0 3 2 4 3 2 1 0 4
- t 1: 2 in memory, good
- t 2: 1 in memory, good
- t 3: 0 in memory, good
- t 4: 3 in memory, good
- t 5: 2 in memory, good
- t 6: 4 not in memory, evict 3, fault 4 -> 3 2 1 0 4 3 2 4 3 2 1 0
- t 7: 3 in memory, good
- t 8: 2 in memory, good
- t 9: 1 in memory, good
- t 10: 0 in memory, good
- t 11: 4 in memory, good
**Total page faults = 2.**
```

### v2.2 · clock_small (paging) — expected 8, grader read 12, finish=stop

```
**Policy: Second-chance (clock) with 3 frames**
- t 0: 2 not in memory, evict 2, faults = 1; clock = 2
- t 1: 3 not in memory, evict 3, faults = 2; clock = 3
- t 2: 2 not in memory, evict 2, faults = 3; clock = 2
- t 3: 1 not in memory, evict 1, faults = 4; clock = 1
- t 4: 5 not in memory, evict 5, faults = 5; clock = 5
- t 5: 2 not in memory, evict 2, faults = 6; clock = 2
- t 6: 4 not in memory, evict 4, faults = 7; clock = 4
- t 7: 5 not in memory, evict 5, faults = 8; clock = 5
- t 8: 3 not in memory, evict 3, faults = 9; clock = 3
- t 9: 2 not in memory, evict 2, faults = 10; clock = 2
- t 10: 5 not in memory, evict 5, faults = 11; clock = 5
- t 11: 2 not in memory, evict 2, faults = 12; clock = 2
**Total page faults = 12** (hits = 12 - 12 = 0, hit ratio = 0 / 12 = 0.000)
```

### v2.2 · opt_4f (paging) — expected 6, grader read 10, finish=stop

```
| # | Ref | Result | Evicted | Frames (next use shown at each eviction) | Faults |
|---|-----|--------|---------|--------|--------|
| 1 | 3 | miss | - | 3 | 1 |
| 2 | 2 | miss | - | 3 2 | 2 |
| 3 | 1 | miss | - | 3 2 1 | 3 |
| 4 | 0 | miss | 3 | 0 2 1 (next use 3@never) | 4 |
| 5 | 3 | miss | 2 | 0 3 1 (next use 2@never) | 5 |
| 6 | 2 | miss | 0 | 2 3 1 (next use 0@never) | 6 |
| 7 | 4 | miss | 3 | 2 4 1 (next use 3@never) | 7 |
| 8 | 3 | miss | 2 | 3 4 1 (next use 2@never) | 8 |
| 9 | 2 | miss | 3 | 2 4 1 (next use 3@never) | 9 |
| 10 | 1 | hit | - | 2 4 1 | 9 |
| 11 | 0 | miss | 2 | 0 4 1 (next use 2@never) | 10 |
| 12 | 4 | hit | - | 0 4 1 | 10 |
**Total page faults = 10** (hits = 12 - 10 = 2, hit ratio = 2 / 12 = 0.1667)
```

### v3 · hrrn (scheduling) — expected 4.0, grader read -2.2, finish=stop

```
**Step 2 - Gantt chart:** A[0-3] B[3-6] C[6-6] D[6-6] E[6-8]
**Step 3 - per-process times** (Turnaround = Completion - Arrival; Waiting = Turnaround - Burst)
| Process | Arrival | Burst | Completion | Turnaround | Waiting |
|---------|---------|-------|------------|-------------|--------------|
| A | 0 | 3 | 3 | 3 - 0 = 3 | 3 - 3 = 0 |
| B | 2 | 6 | 6 | 6 - 2 = 4 | 4 - 6 = -2 |
| C | 4 | 4 | 6 | 6 - 4 = 2 | 2 - 4 = -2 |
| D | 6 | 5 | 6 | 6 - 6 = 0 | 0 - 5 = -5 |
| E | 8 | 2 | 8 | 8 - 8 = 0 | 0 - 2 = -2 |
**Step 4 - averages**
- Sum of waiting times: 0 + (-2) = -2, -2 + (-2) = -4, -4 + (-5) = -9, -9 + (-2) = -11
- Average waiting time = -11 / 5 = **-2.2**
- Sum of turnaround times: 3 + 4 = 7, 7 + 2 = 9, 9 + 0 = 9, 9 + 0 = 9
- Average turnaround time = 9 / 5 = **1.8**
**Answer: average waiting time = -2.2**
```

### v3 · fifo_classic (paging) — expected 15, grader read 20, finish=stop

```
ames full; oldest (3) evicted |
| 10 | 3 | miss | 4 | 9 | frames full; oldest (4) evicted |
| 11 | 0 | miss | 2 | 10 | frames full; oldest (2) evicted |
| 12 | 3 | miss | 0 | 11 | frames full; oldest (0) evicted |
| 13 | 2 | miss | 3 | 12 | frames full; oldest (3) evicted |
| 14 | 1 | miss | 2 | 13 | frames full; oldest (2) evicted |
| 15 | 2 | miss | 1 | 14 | frames full; oldest (1) evicted |
| 16 | 0 | miss | 2 | 15 | frames full; oldest (2) evicted |
| 17 | 1 | miss | 0 | 16 | frames full; oldest (0) evicted |
| 18 | 7 | miss | 1 | 17 | frames full; oldest (1) evicted |
| 19 | 0 | miss | 7 | 18 | frames full; oldest (7) evicted |
| 20 | 1 | miss | 0 | 19 | frames full; oldest (0) evicted |
| 21 | 3 | miss | 1 | 20 | frames full; oldest (1) evicted |
**Total page faults = 20** (hits = 21 - 20 = 1, hit ratio = 1 / 21 = 0.0476, fault ratio = 20 / 21 = 0.9524)
**Answer: page faults = 20**
```

### v3 · opt_classic (paging) — expected 9, grader read 12, finish=stop

```
ready in frames | 2 3 1 | 7 |
| 10 | 3 | hit | - | 3 already in frames | 2 3 1 | 7 |
| 11 | 0 | miss | 3 | next use 3@12 > 1@14 > 2@13 -> farthest | 2 0 1 | 8 |
| 12 | 3 | miss | 0 | next use 0@16 > 1@14 > 2@13 -> farthest | 2 3 1 | 9 |
| 13 | 2 | hit | - | 2 already in frames | 2 3 1 | 9 |
| 14 | 1 | hit | - | 1 already in frames | 2 3 1 | 9 |
| 15 | 2 | hit | - | 2 already in frames | 2 3 1 | 9 |
| 16 | 0 | miss | 2 | next use 2@never > 3@never > 1@17 -> farthest | 0 3 1 | 10 |
| 17 | 1 | hit | - | 1 already in frames | 0 3 1 | 10 |
| 18 | 7 | miss | 0 | next use 0@never > 3@never > 1@never -> farthest | 7 3 1 | 11 |
| 19 | 0 | miss | 7 | next use 7@never > 3@never > 1@never -> farthest | 0 3 1 | 12 |
| 20 | 1 | hit | - | 1 already in frames | 0 3 1 | 12 |
**Total page faults = 12** (hits = 20 - 12 = 8, hit ratio = 8 / 20 = 0.4, fault ratio = 12 / 20 = 0.6)
**Answer: page faults = 12**
```

### v3 · belady_3 (paging) — expected 9, grader read 12, finish=stop

```
| 3 | 1 | miss | - | free frame 2 load 1 |
| 4 | 0 | miss | 3 | frames full evict oldest 3 |
| 5 | 3 | miss | 2 | frames full evict oldest 2 |
| 6 | 2 | miss | 1 | frames full evict oldest 1 |
| 7 | 4 | miss | 0 | frames full evict oldest 0 |
| 8 | 3 | miss | 3 | frames full evict oldest 3 |
| 9 | 2 | miss | 2 | frames full evict oldest 2 |
| 10 | 1 | miss | 1 | frames full evict oldest 1 |
| 11 | 0 | miss | 0 | frames full evict oldest 0 |
| 12 | 4 | hit | - | 4 already in frames |
**Total page faults = 12**
 Hits = 12 - 12 = 0
 Hit ratio = 0 / 12 = 0 (0%)
 Fault ratio = 12 / 12 = 1 (100%)
**Answer: page faults = 12**
```

### v3 · opt_4f (paging) — expected 6, grader read 8, finish=stop

```
| 3 | 1 | fault | - | no frame holds 1 frame 1 loaded |
| 4 | 0 | fault | - | no frame holds 0 frame 0 loaded |
| 5 | 3 | hit | - | 3 already in frame 3 |
| 6 | 2 | hit | - | 2 already in frame 2 |
| 7 | 4 | fault | 0 | frames: 3,2,1,4 not used 0@#11, 1@#10, 2@#8, 3@#9, 4@#7 0 not used again 11 > 10 > 9 > 8 0 will be used in 11 > 10 > 9 > 8 evict 0 |
| 8 | 3 | hit | - | 3 already in frame 3 |
| 9 | 2 | hit | - | 2 already in frame 2 |
| 10 | 1 | hit | - | 1 already in frame 1 |
| 11 | 0 | fault | 1 | frames: 3,2,4,1 not used 1@#10, 2@#9, 3@#8, 4@#7 1 not used again 2@#9, 3@#8, 4@#7 9 > 8 > 7 1 will be used in 10 > 9 > 8 > 7 evict 1 |
| 12 | 4 | hit | - | 4 already in frame 4 |
**Total page faults = 8**
*Hits = 12 - 8 = 4*
*Hit ratio = 4 / 12 = 0.3333*
*Fault ratio = 8 / 12 = 0.6667*
**Answer: page faults = 8**
```

### v3 · translate_hex (translate) — expected 2604, grader read 7724.0, finish=stop

```
**Step-by-step translation**
- convert 0x0A2C to decimal: 0 x 4096 = 0; 10 x 256 = 2560; 2 x 16 = 32; 12 x 1 = 12
- sum: 0 + 2560 = 2560, 2560 + 32 = 2592, 2592 + 12 = 2604 -> 0x0A2C = 2604
- page number = floor(2604 / 1024) = 2 (check: 2 x 1024 = 2048 <= 2604 < 3072)
- page offset = 2604 - 2048 = 556
- page table[2] = frame 7
- frame base = 7 x 1024 = 7168
- physical address = 7168 + 556 = 7724
**Physical address = 7724**
- in hexadecimal: 7724 = 0x1e2c
**Answer: physical address = 0x1e2c**
```
