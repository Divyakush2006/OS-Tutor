"""What the self-distillation filter accepted, and why it rejected the rest.

    python tools/sdft_report.py

Run after tools/generate_theory_sdft.py. Accepted THEORY volume sets the row budget
for every other category (MIX is proportional), so this number is worth watching;
rejection reasons say whether a pass was limited by quality or by a token budget.
"""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ostutor.theory_filter import accept_theory, accept_tutor  # noqa: E402


def report(path, fn, label):
    if not path.exists():
        print(f"{label}: not generated yet")
        return
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    reasons = collections.Counter()
    lens, by_area = [], collections.Counter()
    for r in rows:
        text, why = fn(r)
        reasons[why] += 1
        if text:
            lens.append(len(text))
            by_area[r.get("area") or r.get("kind") or "?"] += 1
    ok = reasons["ok"]
    print(f"\n{label}: {len(rows)} answers, accepted {ok} "
          f"({ok / max(1, len(rows)):.1%})")
    for why, n in reasons.most_common():
        if why != "ok":
            print(f"    rejected {n:5d}  {why}")
    if lens:
        s = sorted(lens)
        print(f"    accepted length in characters: median {s[len(s) // 2]}, "
              f"p95 {s[int(len(s) * 0.95)]}, max {s[-1]}")
        print(f"    coverage: {len(by_area)} areas, "
              f"min {min(by_area.values())} / max {max(by_area.values())} per area")
    return ok


def main():
    raw = ROOT / "data" / "raw"
    t = report(raw / "theory_sdft.jsonl", accept_theory, "theory (conceptual)")
    report(raw / "tutor_sdft.jsonl", accept_tutor, "tutoring (Socratic)")
    if t:
        from ostutor.config import MIX
        print(f"\naccepted theory {t} + 36 hand-written gold at {MIX['conceptual']:.0%} "
              f"of the mix implies a training set of about "
              f"{round((t + 36) / MIX['conceptual'], -2):,.0f} rows, before dedup and "
              f"diversity selection trim the supply.")


if __name__ == "__main__":
    main()
