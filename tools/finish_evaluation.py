"""Run the remaining v3.0 measurements, in order, once the GPU is free.

    python tools/finish_evaluation.py

The v3 free-form run is started separately (it is the headline number and worth
having first). This finishes the comparison: the SAME 57 hand-written items on the
base model and on v2.2, then the forgetting checks for all three, then the table.

Order matters. The free-form suite is the number that predicted real behaviour, so
it comes first. The forgetting checks are logit-scored and cheap, so a broken
adapter would already have shown up in the free-form run.
"""
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V3 = ROOT / "outputs" / "ostutor-lora-v3" / "ostutor-lora"
V22 = ROOT / "outputs" / "ostutor-lora"
PY = sys.executable


def step(msg):
    print(f"\n=== {msg} ({datetime.now():%H:%M}) ===", flush=True)


def gpu_busy():
    """True while another run_eval/run_forgetting_eval process holds the GPU."""
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" "
         "| Select-Object -ExpandProperty CommandLine"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = r.stdout or ""
    return any(k in out for k in ("run_eval.py", "run_forgetting_eval.py",
                                  "clarify_probe.py"))


def sh(cmd, tail=25):
    print("$ " + " ".join(str(c) for c in cmd), flush=True)
    r = subprocess.run([str(c) for c in cmd], cwd=ROOT, text=True, capture_output=True,
                       encoding="utf-8", errors="replace")
    raw = ((r.stdout or "") + "\n" + (r.stderr or "")).replace("\r", "\n")
    lines = [l for l in raw.splitlines()
             if l.strip() and "it/s]" not in l and "Loading weights" not in l]
    print("\n".join(lines[-(200 if r.returncode else tail):]), flush=True)
    if r.returncode:
        print(f"!! FAILED (exit {r.returncode}) - continuing so the rest still runs",
              flush=True)
    return r.returncode


def main():
    step("waiting for the GPU")
    while gpu_busy():
        time.sleep(60)
    print("GPU free", flush=True)

    ff = ["--4bit", "--limit", "57", "--max-new", "4096", "--suites", "os_freeform"]

    step("free-form suite: base model")
    sh([PY, "tools/run_eval.py", *ff, "--out", "reports/eval_baseline_v3.json"])

    step("free-form suite: v2.2")
    sh([PY, "tools/run_eval.py", *ff, "--adapter", V22,
        "--out", "reports/eval_finetuned_v2.2_v3suite.json"])

    step("forgetting + OS theory MCQ: base")
    sh([PY, "tools/run_forgetting_eval.py", "--4bit",
        "--out", "reports/forgetting_base_v3.json"])

    step("forgetting + OS theory MCQ: v2.2")
    sh([PY, "tools/run_forgetting_eval.py", "--4bit", "--adapter", V22,
        "--compare", "reports/forgetting_base_v3.json",
        "--out", "reports/forgetting_finetuned_v2.2.json"])

    step("forgetting + OS theory MCQ: v3.0")
    sh([PY, "tools/run_forgetting_eval.py", "--4bit", "--adapter", V3,
        "--compare", "reports/forgetting_base_v3.json",
        "--out", "reports/forgetting_finetuned_v3.json"])

    step("comparison table")
    sh([PY, "tools/compare_runs.py"], tail=60)

    step("error audit on the remaining v3 failures")
    sh([PY, "tools/error_audit.py", "reports/eval_finetuned_v3.json"], tail=40)

    print(f"\nEVALUATION DONE {datetime.now():%H:%M}", flush=True)


if __name__ == "__main__":
    main()
