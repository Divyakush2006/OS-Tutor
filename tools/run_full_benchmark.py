"""Everything that is still unmeasured, in one unattended run.

    python tools/run_full_benchmark.py

Waits for tools/benchmark.py (the 57-item suite, four configurations on one llama-server)
to finish, frees the GPU, then runs the checks that need logit scoring through
transformers and cannot share the GPU with llama-server:

  * MMLU on subjects unrelated to operating systems, plus adjacent CS subjects, for the
    base model, v2.2 and v3.0. Reported as accuracy AND paired flips, because an
    unchanged mean can hide many cancelling right->wrong and wrong->right changes - the
    flips are the actual signature of forgetting.
  * The 70 hand-written OS theory MCQs, same scoring, which is the conceptual number the
    free-form suite does not capture.

The dataset carries 16% replay on a spaced schedule specifically to protect general
ability. Until this runs, that protection is a design intention rather than a result.
"""
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
V3 = ROOT / "outputs" / "ostutor-lora-v3" / "ostutor-lora"
V22 = ROOT / "outputs" / "ostutor-lora"


def step(msg):
    print(f"\n=== {msg} ({datetime.now():%H:%M}) ===", flush=True)


def busy(*needles):
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process | Select-Object -ExpandProperty CommandLine"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = r.stdout or ""
    return any(n in out for n in needles)


def sh(cmd, tail=30):
    print("$ " + " ".join(str(c) for c in cmd), flush=True)
    r = subprocess.run([str(c) for c in cmd], cwd=ROOT, text=True, capture_output=True,
                       encoding="utf-8", errors="replace")
    raw = ((r.stdout or "") + "\n" + (r.stderr or "")).replace("\r", "\n")
    lines = [l for l in raw.splitlines()
             if l.strip() and "it/s]" not in l and "Loading weights" not in l]
    print("\n".join(lines[-(200 if r.returncode else tail):]), flush=True)
    if r.returncode:
        print(f"!! exit {r.returncode} - continuing", flush=True)
    return r.returncode


def main():
    step("waiting for the 57-item benchmark to finish")
    # "benchmark.py" alone also matches THIS script's own command line
    # (run_full_benchmark.py), so the wait never ended. Match the path as invoked.
    while busy("tools/benchmark.py", "tools\\benchmark.py"):
        time.sleep(60)
    print("benchmark done", flush=True)

    step("freeing the GPU (the forgetting check needs it through transformers)")
    subprocess.run(["taskkill", "/F", "/IM", "llama-server.exe"], capture_output=True)
    time.sleep(6)
    sh(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader"], tail=3)

    base = "reports/forgetting_base_v3.json"
    step("MMLU + OS theory MCQ: base model")
    sh([PY, "tools/run_forgetting_eval.py", "--4bit", "--out", base])

    step("MMLU + OS theory MCQ: v2.2")
    sh([PY, "tools/run_forgetting_eval.py", "--4bit", "--adapter", V22,
        "--compare", base, "--out", "reports/forgetting_finetuned_v2.2.json"])

    step("MMLU + OS theory MCQ: v3.0")
    sh([PY, "tools/run_forgetting_eval.py", "--4bit", "--adapter", V3,
        "--compare", base, "--out", "reports/forgetting_finetuned_v3.json"])

    step("comparison table")
    sh([PY, "tools/compare_runs.py"], tail=80)
    print(f"\nFULL BENCHMARK DONE {datetime.now():%H:%M}", flush=True)


if __name__ == "__main__":
    main()
