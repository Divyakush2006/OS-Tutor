#!/usr/bin/env bash
# Re-score every model on the repaired OOD suite (v2.2.1: 169 questions had lost
# Available / the request list). Only the OOD suite is re-run; the replaced
# results stay in each report under "superseded" for audit.
set -u
cd "$(dirname "$0")/.."
F="--4bit --suites os_solve_ood --update"
run() { echo "== $* ($(date +%H:%M))"; python tools/run_eval.py $F "$@" 2>&1 \
          | grep --line-buffered -E "os_solve_ood:|written|Error|Traceback"; }

# primary budget, 3,072 tokens, 20 items (same items as before)
run --limit 20 --max-new 3072 --adapter outputs/ostutor-lora      --out reports/eval_finetuned_v2.2_3072.json
run --limit 20 --max-new 3072 --adapter outputs/ostutor-lora-v2.0 --out reports/eval_finetuned_v2.0_long.json
run --limit 20 --max-new 3072                                      --out reports/eval_baseline_3072.json
python tools/compare_runs.py
python tools/error_audit.py reports/eval_finetuned_v2.2_3072.json
# The 1,100-token continuity budget is not re-run on the repaired OOD suite:
# 3,072 is the primary measure. Its standard-suite results remain valid.
echo "ALL DONE $(date +%H:%M)"
