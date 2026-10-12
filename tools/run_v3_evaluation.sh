#!/usr/bin/env bash
# Full v3.0 measurement: base vs v2.2 vs v3.0 on identical suites.
#
#   bash tools/run_v3_evaluation.sh [v3_adapter_dir]
#
# Order matters: the forgetting checks are cheap (logit scoring) and run first, so a
# broken adapter is caught in minutes rather than hours. Nothing here needs the
# chat stack; stop it first (serve/stop_tutor.ps1) so the GPU is free.
set -u
cd "$(dirname "$0")/.."
V3="${1:-outputs/ostutor-lora-v3}"
V22="outputs/ostutor-lora"
E="--4bit --limit 57 --max-new 4096 --suites os_freeform"
G="--limit 60 --max-new 4096 --suites os_solve_indist,os_solve_ood --update"

step() { echo; echo "=== $* ($(date +%H:%M)) ==="; }

step "forgetting + OS theory: base"
python tools/run_forgetting_eval.py --4bit --out reports/forgetting_base_v3.json 2>&1 | grep -E "accuracy|written|Error"
step "forgetting + OS theory: v2.2"
python tools/run_forgetting_eval.py --4bit --adapter $V22 --compare reports/forgetting_base_v3.json \
  --out reports/forgetting_finetuned_v2.2.json 2>&1 | grep -E "accuracy|delta|written|Error"
step "forgetting + OS theory: v3.0"
python tools/run_forgetting_eval.py --4bit --adapter $V3 --compare reports/forgetting_base_v3.json \
  --out reports/forgetting_finetuned_v3.json 2>&1 | grep -E "accuracy|delta|written|Error"

step "free-form suite: v3.0"
python tools/run_eval.py $E --adapter $V3 --out reports/eval_finetuned_v3.json 2>&1 | grep -E ":|written|Error"
step "free-form suite: v2.2"
python tools/run_eval.py $E --adapter $V22 --out reports/eval_finetuned_v2.2_v3suite.json 2>&1 | grep -E ":|written|Error"
step "free-form suite: base"
python tools/run_eval.py $E --out reports/eval_baseline_v3.json 2>&1 | grep -E ":|written|Error"

python tools/compare_runs.py
step "generator-shaped suites (secondary), 60 items each"
python tools/run_eval.py --4bit $G --adapter $V3 --out reports/eval_finetuned_v3.json 2>&1 | grep -E ":|written"
python tools/run_eval.py --4bit $G --adapter $V22 --out reports/eval_finetuned_v2.2_v3suite.json 2>&1 | grep -E ":|written"
python tools/run_eval.py --4bit $G --out reports/eval_baseline_v3.json 2>&1 | grep -E ":|written"

python tools/compare_runs.py
step "error audit: which failures remain"
python tools/error_audit.py reports/eval_finetuned_v3.json
echo "ALL DONE $(date +%H:%M)"
