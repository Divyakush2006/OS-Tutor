"""Regenerate the own-authored OS content in data/raw from the knowledge base.

    python tools/generate_os_content.py

Writes:
  data/raw/conceptual_misconceptions.jsonl   misconception explanations + capped comparisons
  data/raw/tutoring_os_dialogues.jsonl       Socratic OS tutoring dialogues

Fully deterministic (fixed seeds, no wall-clock input): the same knowledge base always
produces byte-identical files. The draw count scales with the number of concepts so
each concept gets the same expected number of framings as the original 122-concept
build (1,400 draws, 11.5 per concept); rows with identical answers are dropped here
because they would be removed by exact dedup anyway.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ostutor.config import RAW  # noqa: E402
from ostutor.simulators import conceptual, conceptual_compare, os_dialogues  # noqa: E402

DRAWS_PER_CONCEPT = 1400 / 122


def _unique(rows, key="answer"):
    seen, out = set(), []
    for r in rows:
        if r[key] not in seen:
            seen.add(r[key])
            out.append(r)
    return out


def _write(path, rows):
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def main():
    n = round(DRAWS_PER_CONCEPT * len(conceptual.KB))
    mis = _unique(conceptual.generate(n, seed=42))
    cmp_ = _unique(conceptual_compare.generate(5000, seed=7))
    dlg = os_dialogues.generate(3)
    _write(RAW / "conceptual_misconceptions.jsonl", mis + cmp_)
    _write(RAW / "tutoring_os_dialogues.jsonl", dlg)
    print(f"concepts {len(conceptual.KB)} | draws {n} | misconception {len(mis)} | "
          f"comparison {len(cmp_)} | dialogues {len(dlg)}")


if __name__ == "__main__":
    main()
