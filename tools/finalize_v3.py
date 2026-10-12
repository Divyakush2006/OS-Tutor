"""v3.0 end game, driven from one process.

    python tools/finalize_v3.py [--skip-generation]

Runs the whole tail of the pipeline in order and stops at the first failure:

    llama-server up -> generate (theory, tutoring, retries) -> report -> free the
    GPU -> unit tests -> build -> build again and compare hashes -> dataset card
    -> bundle

The Kaggle launch stays a separate step (tools/kaggle_launch.py), so the release
gates are read by a human before any GPU quota is spent.

WHY THIS OWNS THE GENERATORS. The first two versions of this driver polled the
process table to find out whether generation was still running, and both got it
wrong: the shell version could not see the generators at all (tasklist /V does not
print command lines, and msys ps does not see Windows ones), and the Python version
treated an empty query result as "nothing is running". Both then killed
llama-server underneath a generator that was still working. A driver that starts
its own children and waits for them cannot make that mistake.
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SERVER_EXE = ROOT / "serve" / "llama.cpp" / "bin" / "llama-server.exe"
BASE_GGUF = ROOT / "models" / "gguf" / "qwen3-4b-instruct-2507-Q8_0.gguf"
LORA_GGUF = ROOT / "models" / "gguf" / "ostutor-v2.2-lora-f16.gguf"
HEALTH = "http://127.0.0.1:8081/health"
# Tutoring supply is what bounds the WHOLE dataset: the build reported "achievable
# total 9250 (ceiling 12000), bound by 'tutoring'", and tutoring used 100% of its
# distinct supply, so the diversity selector had no choice to make. Every extra
# distinct tutoring row lifts the total by 1/0.08 = 12.5 rows, most of them
# procedural. 1800 prompts takes tutoring past the 12,000 ceiling with room to select.
TUTOR_N = 1800


def step(msg):
    print(f"\n=== {msg} ({datetime.now():%H:%M}) ===", flush=True)


_NOISE = ("it/s]", "it/s,", "s/it]", "Loading weights")


def sh(cmd, tail=None, check=True):
    """Run a step. Progress-bar lines are dropped: a tqdm bar writing 400 lines of
    "Loading weights" pushed a real traceback out of the tail, and the first build
    failure of v3.0 was reported as nothing but progress bars. On failure the tail is
    widened, because that is exactly when the output matters."""
    print("$ " + " ".join(str(c) for c in cmd), flush=True)
    r = subprocess.run([str(c) for c in cmd], cwd=ROOT, text=True, capture_output=True,
                       encoding="utf-8", errors="replace")
    raw = ((r.stdout or "") + "\n" + (r.stderr or "")).replace("\r", "\n")
    out = [l for l in raw.splitlines()
           if l.strip() and not any(n in l for n in _NOISE)]
    n = 200 if r.returncode else tail
    print("\n".join(out[-n:] if n else out), flush=True)
    if check and r.returncode:
        sys.exit(f"FAILED (exit {r.returncode}): {' '.join(str(c) for c in cmd)}")
    return r.returncode


def server_up():
    try:
        with urllib.request.urlopen(HEALTH, timeout=3) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError):
        return False


def start_server():
    """The generators need the BASE model's own answers, so the LoRA is loaded but
    every request sends scale 0. -np 4 gives four slots; -c 24576 across them leaves
    6,144 tokens per slot, well above the largest prompt plus a 3,400-token reply."""
    if server_up():
        print("llama-server already up", flush=True)
        return
    logs = ROOT / "serve" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    cmd = [SERVER_EXE, "-m", BASE_GGUF, "--lora", LORA_GGUF, "-ngl", "99",
           "-c", "24576", "-np", "4", "-fa", "on", "-ctk", "q8_0", "-ctv", "q8_0",
           "--jinja", "--host", "127.0.0.1", "--port", "8081", "--alias", "ostutor"]
    print("$ " + " ".join(str(c) for c in cmd), flush=True)
    out = open(logs / "llama-server.out.log", "ab")
    err = open(logs / "llama-server.log", "ab")
    subprocess.Popen([str(c) for c in cmd], cwd=ROOT, stdout=out, stderr=err)
    for _ in range(180):
        if server_up():
            print("llama-server ready", flush=True)
            return
        time.sleep(1)
    sys.exit("llama-server did not come up in 180 s - see serve/logs/llama-server.log")


def stop_server():
    subprocess.run(["taskkill", "/F", "/IM", "llama-server.exe"],
                   capture_output=True, text=True)
    time.sleep(5)
    sh(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader"], check=False)


def counts():
    def n(p):
        return sum(1 for _ in open(p, encoding="utf-8")) if p.exists() else 0
    return n(RAW / "theory_sdft.jsonl"), n(RAW / "tutor_sdft.jsonl")


GEN = [sys.executable, "tools/generate_theory_sdft.py"]


def generate():
    start_server()
    t, u = counts()
    print(f"starting from theory {t}, tutoring {u}", flush=True)

    # Each pass is resumable: prompts already answered are skipped, so re-running
    # one costs nothing and a killed pass loses only its in-flight requests.
    step("theory: every wording (resumes; no-op if complete)")
    sh(GEN + ["--only", "theory", "--all-styles"], tail=6)

    step(f"tutoring: {TUTOR_N} prompts (resumes)")
    sh(GEN + ["--only", "tutor", "--tutor-n", str(TUTOR_N)], tail=6)

    # The original 1,600-token cap cut off 4.6% of theory answers and 60% of
    # tutoring answers mid-sentence. They were being discarded as "truncated" - a
    # token-budget artefact, not a quality signal. Re-ask exactly those.
    step("re-asking the answers the token limit cut off (theory)")
    sh(GEN + ["--only", "theory", "--all-styles", "--retry-truncated"], tail=6)

    step("re-asking the answers the token limit cut off (tutoring)")
    sh(GEN + ["--only", "tutor", "--tutor-n", str(TUTOR_N), "--retry-truncated"], tail=6)

    step("self-distillation acceptance report")
    sh([sys.executable, "tools/sdft_report.py"], check=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-generation", action="store_true")
    a = ap.parse_args()

    if not a.skip_generation:
        generate()

    step("freeing the GPU (the build needs it for embeddings and replay ranking)")
    stop_server()

    step("unit tests")
    sh([sys.executable, "tools/test_pipeline.py"], tail=3)

    step("build")
    sh([sys.executable, "-m", "ostutor.build"], tail=60)

    step("reproducibility (build again, compare hashes)")
    sh([sys.executable, "tools/verify_reproducible.py"], tail=20)

    # Generated from the manifest, so every figure in it is a figure the build
    # actually produced. package_kaggle.py ships it as the bundle's README.
    step("dataset card")
    sh([sys.executable, "tools/write_dataset_card.py"])

    step("bundle")
    sh([sys.executable, "tools/package_kaggle.py"], tail=8)

    m = json.loads((ROOT / "dist" / "ostutor-sft" / "manifest.json").read_text(encoding="utf-8"))
    print(f"\ngates_passed={m['gates_passed']}  version={m['pipeline_version']}  "
          f"train_sha256={m['artifacts']['train.jsonl'][:16]}", flush=True)
    print(f"FINALIZE DONE {datetime.now():%H:%M}", flush=True)


if __name__ == "__main__":
    main()
