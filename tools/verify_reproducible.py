"""Reproducibility check: rebuild and require byte-identical artifacts.

    python tools/verify_reproducible.py

Reads the artifact SHA-256 values recorded in reports/manifest.json by the previous
build, runs the full build again, and compares. Any difference means some step
depends on something other than code + config + data (set iteration order, GPU
non-determinism, wall-clock) and the dataset cannot be audited or regenerated.

Note: the SuRe surprise scores are cached in data/build/surprise_cache.json on the
first build and read back on the second. The cache is part of the build state, just
like the shell-syntax results; delete it to re-measure from the base model.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "reports" / "manifest.json"


def artifacts():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return m["artifacts"], m["gates_passed"]


def main():
    before, ok_before = artifacts()
    log = ROOT / "reports" / "build_repro.log"
    with open(log, "w", encoding="utf-8") as f:
        rc = subprocess.run([sys.executable, "-m", "ostutor.build"], cwd=ROOT,
                            stdout=f, stderr=subprocess.STDOUT).returncode
    after, ok_after = artifacts()
    print(f"build exit code {rc} | gates passed: before {ok_before}, after {ok_after}")
    same = True
    for name in sorted(set(before) | set(after)):
        a, b = before.get(name), after.get(name)
        flag = "IDENTICAL" if a == b else "DIFFERENT"
        same &= a == b
        print(f"  {flag:9s} {name:12s} {str(a)[:16]}  {str(b)[:16]}")
    print("REPRODUCIBLE" if same else "NOT REPRODUCIBLE")
    sys.exit(0 if same else 1)


if __name__ == "__main__":
    main()
