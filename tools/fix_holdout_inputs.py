"""Restore the inputs the v2.2.0 OOD reframing deleted.

    python tools/fix_holdout_inputs.py

_reframe_holdout replaced the question's first paragraph with a held-out framing,
and for Banker's (Available) and free-space (the request list) that paragraph also
carried inputs - so those OOD questions were unsolvable. This re-inserts the data
sentence (held-out wording) into the first paragraph. Parameters, solutions and
answers are untouched; every patched record is re-checked with missing_inputs().
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ostutor.simulators.generate import holdout_data_sentence, missing_inputs  # noqa: E402

FILES = [ROOT / "data" / "eval" / "os_solve_ood.jsonl",
         ROOT / "data" / "raw" / "procedural_ood_holdout.jsonl",
         ROOT / "data" / "raw" / "_v2_0_solutions" / "eval__os_solve_ood.jsonl",
         ROOT / "data" / "raw" / "_v2_0_solutions" / "raw__procedural_ood_holdout.jsonl"]


def main():
    for f in FILES:
        rows = [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
        fixed = 0
        for i, r in enumerate(rows):
            if not missing_inputs(r):
                continue
            head, rest = r["problem"].split("\n\n", 1)
            rng = random.Random(f"{r.get('seed', i)}-holdout-data")
            r["problem"] = head + holdout_data_sentence(r["verify"], rng) + "\n\n" + rest
            assert not missing_inputs(r), (f.name, i, missing_inputs(r))
            fixed += 1
        with open(f, "w", encoding="utf-8", newline="\n") as out:
            for r in rows:
                out.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"{f.relative_to(ROOT)}: fixed {fixed} of {len(rows)}")


if __name__ == "__main__":
    main()
