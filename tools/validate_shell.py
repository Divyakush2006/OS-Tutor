"""Syntax-validate every candidate shell command with `bash -n`, in parallel.

Replaces tools/validate_shell.sh, which had two real problems:
  * it wrote JSON from bash, and two concurrent runs interleaved into an
    unparseable file that crashed the build;
  * it spawned one process per command serially under Git Bash on Windows and
    stalled for over two hours without progress.

This version calls Git Bash's bash.exe EXPLICITLY. A bare `bash` on this machine
resolves to C:\\Windows\\system32\\bash.exe (WSL), which is why the first Python
attempt reported every command as failing. Commands are checked on a thread pool
and results are written atomically (temp file + rename), one failing id per line.

    python tools/validate_shell.py
"""
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ostutor import config as C
from ostutor.sources import ingest_shell

CANDIDATES = [r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe",
              "/usr/bin/bash", "/bin/bash"]
BASH = next((p for p in CANDIDATES if os.path.exists(p)), None)
OUT = C.BUILD / "shell_syntax_fail.txt"


def check(item):
    rid, cmd = item
    if "\x00" in cmd:
        return rid, True                     # -print0 payloads: not a defect
    fd, path = tempfile.mkstemp(suffix=".sh")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(cmd + "\n")
        r = subprocess.run([BASH, "-n", path], capture_output=True, timeout=10)
        return rid, r.returncode == 0
    except subprocess.TimeoutExpired:
        return rid, False
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def main():
    if not BASH:
        sys.exit("Git Bash not found; cannot run bash -n")
    # sanity: the interpreter must accept valid syntax and reject invalid syntax
    assert check(("ok", "ls -la | grep foo"))[1], f"{BASH} rejects valid syntax"
    assert not check(("bad", "echo 'unterminated"))[1], f"{BASH} accepts invalid syntax"

    rows = ingest_shell()
    items = [(r["id"], r["messages"][-1]["content"]) for r in rows]
    t0, fails = time.time(), []
    with ThreadPoolExecutor(max_workers=max(4, (os.cpu_count() or 4))) as ex:
        for i, (rid, ok) in enumerate(ex.map(check, items, chunksize=32)):
            if not ok:
                fails.append(rid)
            if (i + 1) % 2000 == 0:
                print(f"  {i+1}/{len(items)}  failures so far {len(fails)}  "
                      f"({time.time()-t0:.0f}s)", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text("\n".join(fails) + ("\n" if fails else ""), encoding="utf-8")
    tmp.replace(OUT)                          # atomic
    print(f"bash -n via {BASH}: {len(fails)}/{len(items)} fail "
          f"({100*len(fails)/len(items):.2f}%) in {time.time()-t0:.0f}s -> {OUT}")


if __name__ == "__main__":
    main()
