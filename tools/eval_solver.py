"""Measure the 57 hand-written items with verified-solver delegation.

    python tools/eval_solver.py [--no-delegate]

Uses the running llama-server (serve/start_tutor.ps1), so it measures the stack a
student actually talks to. Extraction runs on the UNTUNED base (LoRA scale 0), which
measured 84% against 79% for the adapter; the adapter is biased toward solving rather
than reading. Everything is graded by the same ostutor.evaluation.harness as before,
so the number is comparable with reports/eval_finetuned_v3*.json.

--no-delegate reproduces the plain model path through the same code, for a like-for-like
control.
"""
import argparse
import json
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ostutor import config as C  # noqa: E402
from ostutor.evaluation.harness import grade  # noqa: E402
from ostutor.solver import solve  # noqa: E402

SERVER = "http://127.0.0.1:8081/v1/chat/completions"


def _post(system, user, scale, max_tokens):
    body = dict(messages=[dict(role="system", content=system),
                          dict(role="user", content=user)],
                temperature=0, max_tokens=max_tokens, lora=[dict(id=0, scale=scale)])
    req = urllib.request.Request(SERVER, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=900))["choices"][0]["message"]["content"]


def base_ask(system, user):
    """Extraction: untuned base, short reply."""
    return _post(system, user, 0.0, 900)


def tuned_ask(system, user):
    """Teaching: the fine-tuned adapter, full worked answer."""
    return _post(system, user, 1.0, 4096)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-delegate", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "reports" / "eval_solver_v3.json"))
    a = ap.parse_args()

    suite = [json.loads(l) for l in open(ROOT / "data/eval/os_freeform.jsonl",
                                         encoding="utf-8")]
    results, items, by_kind, t0 = [], [], {}, time.time()
    delegated = Counter()

    for i, rec in enumerate(suite):
        q = rec["problem"]
        text, meta = (None, dict(delegated=False, reason="disabled")) \
            if a.no_delegate else solve(q, base_ask)
        if text is None:
            # Not a solver kind, or extraction could not be grounded: the model answers.
            text = tuned_ask(C.system_for("solve", "os"), q)
        delegated[bool(meta.get("delegated"))] += 1
        g = grade(rec, text)
        results.append(g)
        k = rec["verify"]["kind"]
        b = by_kind.setdefault(k, [0, 0, 0])
        b[1] += 1
        b[0] += int(g["final_correct"])
        b[2] += int(bool(meta.get("delegated")))
        items.append(dict(index=i, kind=k, final_correct=g["final_correct"],
                          delegated=bool(meta.get("delegated")),
                          reason=meta.get("reason"), output=text))
        if (i + 1) % 10 == 0:
            acc = sum(r["final_correct"] for r in results) / len(results)
            print(f"  {i+1}/{len(suite)}  running acc {acc:.3f}", flush=True)

    n = len(results)
    acc = sum(r["final_correct"] for r in results) / n
    print(f"\n{'SOLVER-DELEGATED' if not a.no_delegate else 'PLAIN MODEL'}: "
          f"{sum(r['final_correct'] for r in results)}/{n} = {acc:.1%}  "
          f"({time.time()-t0:.0f}s)")
    print(f"delegated to the simulator: {delegated[True]}/{n}\n")
    print(f"{'kind':<18}{'correct':>9}{'delegated':>11}")
    for k, (c, tot, dele) in sorted(by_kind.items(), key=lambda x: -x[1][1]):
        print(f"{k:<18}{c}/{tot:<7}{dele}/{tot}")

    Path(a.out).write_text(json.dumps(
        dict(mode="plain" if a.no_delegate else "solver", n=n, accuracy=round(acc, 4),
             delegated=delegated[True],
             by_kind={k: dict(correct=v[0], n=v[1], delegated=v[2])
                      for k, v in by_kind.items()},
             items=items), indent=1), encoding="utf-8")
    print(f"\nwritten to {a.out}")


if __name__ == "__main__":
    main()
