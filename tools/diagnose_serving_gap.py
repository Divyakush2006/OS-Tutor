"""Why does v3.0 score 64.9% through transformers and 29.8% through llama.cpp?

    python tools/diagnose_serving_gap.py

Same 57 items, same grader, same adapter. The transformers run (reports/
eval_finetuned_v3.json) scored 37/57. The four-configuration llama.cpp run
(reports/benchmark_v3.json) scored 17/57 for the same adapter. Half the adapter's
ability disappears somewhere between the two, and the llama.cpp path is the one a
student actually talks to, so this matters more than either score.

Three variables differ between those runs, and they are tested one at a time:

  A  two adapters loaded vs one. benchmark.py needed both v2.2 and v3 resident so that
     every configuration shared one set of weights. Per-request scales on a multi-LoRA
     server are the least-exercised path in the whole stack, so it is ruled out first
     by re-running with only v3 loaded, addressed as id 0.
  B  -np 4 vs -np 1. Four parallel slots divide the KV cache into quarters; the serving
     stack uses one slot.
  C  quantisation: NF4 base + fp16 PEFT adapter, against Q8_0 base + f16 GGUF adapter
     applied at runtime. If A and B come back clean, this is what is left, and the fix
     is to merge the adapter into the base weights before quantising rather than
     applying it at runtime.

Each stage prints its score against the two reference numbers, so whichever stage moves
17/57 back toward 37/57 is the culprit.
"""
import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
SERVER_EXE = ROOT / "serve" / "llama.cpp" / "bin" / "llama-server.exe"
BASE_GGUF = ROOT / "models" / "gguf" / "qwen3-4b-instruct-2507-Q8_0.gguf"
V3_GGUF = ROOT / "models" / "gguf" / "ostutor-v3-lora-f16.gguf"
LOG = ROOT / "serve" / "logs"

# (label, extra llama-server args, out file) - one variable changed at a time.
STAGES = [
    ("one adapter, -np 1  (exactly the serving stack)",
     ["-c", "20480", "-np", "1"], "reports/benchmark_v3_single_np1.json"),
    ("one adapter, -np 4  (isolates the parallel slots)",
     ["-c", "24576", "-np", "4"], "reports/benchmark_v3_single_np4.json"),
]


def wait_for(*needles, gone=True, clear_polls=4):
    """Wait until none of `needles` is running, and STAYS gone for clear_polls checks.

    A chain like run_forgetting_chain.py has a gap of a few seconds between one child
    exiting and the next starting. A single poll landing in that gap reads the GPU as
    free, and the server started here then fights the next child for VRAM - which is
    exactly how the first v3.0 forgetting run died with `CUDA error: unknown error`.
    """
    clear = 0
    while clear < clear_polls:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process | Select-Object -ExpandProperty CommandLine"],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        present = any(n in (r.stdout or "") for n in needles)
        clear = 0 if present == gone else clear + 1
        if clear < clear_polls:
            time.sleep(30)


def server_up(timeout=240):
    for _ in range(timeout):
        try:
            urllib.request.urlopen("http://127.0.0.1:8081/health", timeout=3).read()
            return True
        except Exception:
            time.sleep(1)
    return False


def kill_server():
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-Process llama-server -ErrorAction SilentlyContinue "
                    "| Stop-Process -Force"], capture_output=True)
    time.sleep(5)


def main():
    print(f"waiting for the forgetting chain to free the GPU ({datetime.now():%H:%M})",
          flush=True)
    wait_for("run_forgetting_chain.py", "run_forgetting_eval.py")
    kill_server()
    LOG.mkdir(parents=True, exist_ok=True)

    for label, extra, out in STAGES:
        print(f"\n=== {label} ({datetime.now():%H:%M}) ===", flush=True)
        args = [str(SERVER_EXE), "-m", str(BASE_GGUF), "--lora", str(V3_GGUF),
                "-ngl", "99", *extra, "-fa", "on", "-ctk", "q8_0", "-ctv", "q8_0",
                "--jinja", "--host", "127.0.0.1", "--port", "8081"]
        with open(LOG / "diag-server.log", "w", encoding="utf-8") as lf:
            proc = subprocess.Popen(args, cwd=ROOT, stdout=lf, stderr=subprocess.STDOUT)
        if not server_up():
            print("!! server did not come up - see serve/logs/diag-server.log", flush=True)
            proc.kill()
            continue
        adapters = json.load(urllib.request.urlopen("http://127.0.0.1:8081/lora-adapters"))
        print(f"loaded adapters: {[(a.get('id'), Path(a.get('path','')).name) for a in adapters]}",
              flush=True)
        r = subprocess.run([PY, "-X", "utf8", "tools/benchmark.py", "--single",
                            "--only", "v3", "v3+solver", "--out", out],
                           cwd=ROOT, text=True, capture_output=True,
                           encoding="utf-8", errors="replace")
        print(((r.stdout or "") + (r.stderr or "")).replace("\r", ""), flush=True)
        proc.kill()
        time.sleep(5)

    print("\n" + "=" * 70)
    print("reference: v3 through transformers (NF4 + PEFT)  37/57 = 64.9%")
    print("reference: v3 through llama.cpp, two adapters    17/57 = 29.8%")
    for _, _, out in STAGES:
        p = ROOT / out
        if not p.exists():
            continue
        for cfg in json.loads(p.read_text(encoding="utf-8")):
            print(f"{cfg['label']:<12} {cfg['correct']}/{cfg['n']} = "
                  f"{cfg['accuracy']:.1%}   <- {out}")
    print(f"\nDIAGNOSIS RUN DONE {datetime.now():%H:%M}", flush=True)


if __name__ == "__main__":
    main()
