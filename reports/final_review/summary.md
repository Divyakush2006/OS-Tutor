# Final-review fixes: before and after

Measured 2026-10-24 08:56 on the live llama-server (v3 adapter, as served).

## Disk range fix (OOD holdout, disk items)

| | Before | After |
|---|---|---|
| Correct | 74/80 | 80/80 |
| Extraction exact | 71/80 | 80/80 |
| Right to wrong / wrong to right | | 0 / 6 |

## Verified tutoring (30 attempts, 24 wrong)

| Reply | Before | After |
|---|---|---|
| reveals_answer | 5 | 0 |
| asserts_other_result | 6 | 0 |
| works_it_out | 9 | 0 |
| affirms_wrong | 0 | 0 |
| asks_question | 30 | 30 |
| confirms_right | 0 | 6 |

After paths: {'tutor-redrafted': 3, 'tutor-checked': 21, 'tutor-confirmed': 6}. Private verdict right: 28/30.

## Off-topic refusal (classifier verdict)

| Set | Declined |
|---|---|
| in_scope_retrieval | 1/124 |
| short_answer | 0/144 |
| not_covered_by_corpora | 5/40 |
| everyday | 17/20 |
