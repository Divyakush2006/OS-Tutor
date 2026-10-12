# Token budget per question type

Worst case over 40 random instances per size, measured with the model's tokenizer on the exact worked-solution format it was trained on. `budget` = worst case x 1.1 margin. Training covered answers up to 4,096 tokens (question + answer).

## CPU scheduling (any algorithm)
size = processes; evaluation suites use 4-10

| size | mean tokens | worst case | budget (+10%) |
|---|---|---|---|
| 4 | 601 | 1,000 | 1,100 |
| 6 | 865 | 1,382 | 1,520 |
| 8 | 1,140 | 1,914 | 2,105 |
| 10 | 1,498 | 2,731 | 3,004 |
| 15 | 2,510 | 5,749 | 6,323 |
| 20 | 3,738 | 7,577 | 8,334 |
| 30 | 5,897 | 14,164 | 15,580 |

## CPU scheduling, worst case (RR q=2, long bursts)
size = processes; evaluation suites use -

| size | mean tokens | worst case | budget (+10%) |
|---|---|---|---|
| 4 | 1,666 | 2,088 | 2,296 |
| 6 | 2,673 | 3,412 | 3,753 |
| 8 | 3,862 | 4,522 | 4,974 |
| 10 | 5,218 | 6,025 | 6,627 |
| 15 | 9,880 | 11,186 | 12,304 |
| 20 | 15,480 | 18,273 | 20,100 |

## Page replacement
size = references; evaluation suites use 12-24

| size | mean tokens | worst case | budget (+10%) |
|---|---|---|---|
| 10 | 337 | 452 | 497 |
| 15 | 482 | 632 | 695 |
| 20 | 674 | 903 | 993 |
| 30 | 990 | 1,352 | 1,487 |
| 50 | 1,627 | 2,273 | 2,500 |
| 75 | 2,535 | 3,419 | 3,760 |
| 100 | 3,277 | 4,562 | 5,018 |

## Disk scheduling
size = requests; evaluation suites use 5-10

| size | mean tokens | worst case | budget (+10%) |
|---|---|---|---|
| 5 | 347 | 474 | 521 |
| 8 | 498 | 688 | 756 |
| 10 | 607 | 904 | 994 |
| 15 | 918 | 1,325 | 1,457 |
| 20 | 1,120 | 1,724 | 1,896 |
| 30 | 1,742 | 2,530 | 2,783 |
| 50 | 2,894 | 4,353 | 4,788 |

## Contiguous allocation (fit)
size = holes = requests; evaluation suites use 3-6

| size | mean tokens | worst case | budget (+10%) |
|---|---|---|---|
| 3 | 252 | 287 | 315 |
| 5 | 455 | 537 | 590 |
| 8 | 787 | 1,000 | 1,100 |
| 10 | 1,039 | 1,246 | 1,370 |
| 15 | 1,847 | 2,376 | 2,613 |
| 20 | 2,811 | 3,664 | 4,030 |

## Banker's safety
size = processes; evaluation suites use 4-7

| size | mean tokens | worst case | budget (+10%) |
|---|---|---|---|
| 4 | 714 | 930 | 1,023 |
| 5 | 869 | 1,125 | 1,237 |
| 7 | 1,206 | 1,813 | 1,994 |
| 10 | 1,711 | 2,393 | 2,632 |
| 15 | 2,429 | 3,176 | 3,493 |
| 20 | 3,130 | 4,680 | 5,148 |

## Banker's request
size = processes; evaluation suites use 4-7

| size | mean tokens | worst case | budget (+10%) |
|---|---|---|---|
| 4 | 628 | 895 | 984 |
| 5 | 617 | 1,078 | 1,185 |
| 7 | 775 | 1,503 | 1,653 |
| 10 | 785 | 1,919 | 2,110 |
| 15 | 1,398 | 3,174 | 3,491 |
| 20 | 1,871 | 4,236 | 4,659 |

## Address translation
size = page-table rows; evaluation suites use 4-8

| size | mean tokens | worst case | budget (+10%) |
|---|---|---|---|
| 4 | 145 | 157 | 172 |
| 8 | 145 | 157 | 172 |
| 16 | 150 | 160 | 176 |
| 32 | 149 | 164 | 180 |

