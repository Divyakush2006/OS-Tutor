"""Re-render worked solutions for existing procedural problems (v2.0 -> v2.1).

    python tools/rerender_procedural.py

Only the `solution` field changes. Problem text, parameters (`verify`), answers,
seeds and fingerprints are untouched, so decontamination and the evaluation suites
stay directly comparable across versions. Every re-rendered record is re-verified
against the simulator, and the run fails if any answer disagrees.

The previous files are kept under data/raw/_v2_0_solutions/ (never deleted).
"""
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ostutor.simulators.generate import render_solution, reverify  # noqa: E402

FILES = [ROOT / "data" / "raw" / "procedural_simulated.jsonl",
         ROOT / "data" / "raw" / "procedural_ood_holdout.jsonl",
         ROOT / "data" / "eval" / "os_solve_indist.jsonl",
         ROOT / "data" / "eval" / "os_solve_ood.jsonl"]
BACKUP = ROOT / "data" / "raw" / "_v2_0_solutions"


def main():
    BACKUP.mkdir(parents=True, exist_ok=True)
    for path in FILES:
        bak = BACKUP / f"{path.parent.name}__{path.name}"
        if not bak.exists():
            shutil.copy2(path, bak)
        rows = [json.loads(l) for l in open(bak, encoding="utf-8") if l.strip()]
        changed = 0
        for r in rows:
            new = render_solution(r["verify"])
            if new != r["solution"]:
                changed += 1
            r["solution"] = new
            if not reverify(r):
                sys.exit(f"answer mismatch after re-render in {path.name}: {r['verify']}")
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        os.replace(tmp, path)
        print(f"{path.parent.name}/{path.name}: {len(rows)} rows, {changed} re-rendered")


if __name__ == "__main__":
    main()
