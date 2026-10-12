"""The catastrophic-forgetting check for v3.0, all three models, freshly paired.

    python tools/run_forgetting_chain.py

Runs tools/run_forgetting_eval.py for the base model, v2.2 and v3.0 back to back on
one GPU, then prints the comparison. The earlier base/v2.2 runs on disk are from
2026-09-19 and predate data/eval_theory/os_theory_mcq.jsonl, so they carry 700 items
rather than 770 and cannot be paired item-for-item against a v3.0 run that includes the
theory block. Re-running all three costs about an hour and makes every number on the
table come from the same item set, which is what a flip count requires.

Why flips and not just the mean: an unchanged average can hide a large number of
cancelling right->wrong and wrong->right changes. Only the right->wrong count measures
what was actually lost.
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
BASE = "reports/forgetting_base_v3.json"

RUNS = [
    ("base model", [], BASE),
    ("v2.2", ["--adapter", "outputs/ostutor-lora", "--compare", BASE],
     "reports/forgetting_v2.2_paired.json"),
    ("v3.0", ["--adapter", "outputs/ostutor-lora-v3/ostutor-lora", "--compare", BASE],
     "reports/forgetting_v3_paired.json"),
]


def sh(cmd, tail=60):
    print("$ " + " ".join(str(c) for c in cmd), flush=True)
    r = subprocess.run([str(c) for c in cmd], cwd=ROOT, text=True, capture_output=True,
                       encoding="utf-8", errors="replace")
    raw = ((r.stdout or "") + "\n" + (r.stderr or "")).replace("\r", "\n")
    lines = [l for l in raw.splitlines()
             if l.strip() and "it/s]" not in l and "Loading checkpoint" not in l]
    print("\n".join(lines[-(200 if r.returncode else tail):]), flush=True)
    if r.returncode:
        print(f"!! exit {r.returncode}", flush=True)
    return r.returncode


def main():
    for label, extra, out in RUNS:
        print(f"\n=== forgetting check: {label} ({datetime.now():%H:%M}) ===", flush=True)
        sh([PY, "-X", "utf8", "tools/run_forgetting_eval.py", "--4bit",
            *extra, "--out", out])
    print(f"\n=== comparison table ({datetime.now():%H:%M}) ===", flush=True)
    sh([PY, "-X", "utf8", "tools/compare_runs.py"], tail=100)
    print(f"\nFORGETTING CHAIN DONE {datetime.now():%H:%M}", flush=True)


if __name__ == "__main__":
    main()
