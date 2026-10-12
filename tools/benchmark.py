"""Benchmark every model configuration on the 57 hand-written OS questions.

    python tools/benchmark.py                      # all configurations
    python tools/benchmark.py --only v3 v3+solver

WARNING - do not use the two-adapter mode. Loading v2.2 and v3 together and selecting
between them with per-request `lora` scales does NOT isolate them. Measured 2026-09-21:
v3 scored 17/57 with both adapters resident and 36/57 with only v3 resident, on the same
weights, prompts and grader; the transformers reference is 37/57. Every number from a
two-adapter run is therefore void, including the base and v2.2 columns. Run one adapter
at a time with --single (or --raw), restarting the server between configurations.

    llama-server -m qwen3-4b-instruct-2507-Q8_0.gguf \\
        --lora ostutor-v3-lora-f16.gguf -np 1 ...      # then: benchmark.py --single

Why one server rather than three runs of tools/run_eval.py: the transformers path takes
76 minutes per model and loads different quantisation (NF4 rather than Q8_0), so the
numbers would not be comparable with each other OR with what the chat stack actually
serves. Here a configuration is just a pair of LoRA scales, the weights never change,
and a full pass takes about three minutes.

CONFIGURATIONS
  base       both adapters off - what fine-tuning was measured against
  v2.2       the previous adapter, same suite
  v3         this adapter, answering entirely by itself
  v3+solver  this adapter with verified-solver delegation (ostutor/solver.py)

Grading is ostutor.evaluation.harness.grade for every configuration, the same simulator-
exact grader used throughout.
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ostutor import config as C  # noqa: E402
from ostutor.evaluation.harness import grade  # noqa: E402
from ostutor.solver import solve  # noqa: E402

SERVER = "http://127.0.0.1:8081/v1/chat/completions"

# (label, v2.2 scale, v3 scale, delegate to the simulator)
CONFIGS = {
    "base":      (0.0, 0.0, False),
    "v2.2":      (1.0, 0.0, False),
    "v3":        (0.0, 1.0, False),
    "v3+solver": (0.0, 1.0, True),
}


SINGLE = False   # --single: one adapter loaded (the serving layout), v3 is id 0


def post(system, user, v22, v3, max_tokens):
    # With --single the server has ONLY the v3 adapter, so v3 addresses id 0 and the
    # v2.2 scale is meaningless. This exists because the four-configuration run above
    # needs two adapters loaded, and two adapters is itself a variable worth ruling out.
    scales = [dict(id=0, scale=v3)] if SINGLE else \
        [dict(id=0, scale=v22), dict(id=1, scale=v3)]
    body = dict(messages=[dict(role="system", content=system),
                          dict(role="user", content=user)],
                temperature=0, max_tokens=max_tokens, lora=scales)
    req = urllib.request.Request(SERVER, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=900))
    c = d["choices"][0]
    return c["message"]["content"], c.get("finish_reason")


def run(label, suite):
    v22, v3, delegate = CONFIGS[label]
    system = C.system_for("solve", "os")
    rows, by_kind, delegated, truncated, t0, items = [], {}, 0, 0, time.time(), []
    for i, rec in enumerate(suite):
        q = rec["problem"]
        text, fin, meta = None, "stop", {}
        if delegate:
            # Extraction always runs on the untuned base: measured 84% against the
            # adapter's 79%, because the adapter is biased toward solving not reading.
            text, meta = solve(q, lambda s, u: post(s, u, 0.0, 0.0, 900)[0])
            if text is not None:
                delegated += 1
        if text is None:
            text, fin = post(system, q, v22, v3, 4096)
        truncated += int(fin == "length")
        g = grade(rec, text)
        rows.append(g)
        b = by_kind.setdefault(rec["verify"]["kind"], [0, 0])
        b[1] += 1
        b[0] += int(g["final_correct"])
        # Kept so a disagreement between two runs can be read item by item rather than
        # guessed at from the per-kind totals.
        items.append(dict(index=i, kind=rec["verify"]["kind"],
                          final_correct=g["final_correct"],
                          delegated=bool(meta.get("delegated")),
                          reason=meta.get("reason"), finish=fin, output=text))
        if (i + 1) % 20 == 0:
            acc = sum(r["final_correct"] for r in rows) / len(rows)
            print(f"    {label}: {i+1}/{len(suite)}  running {acc:.3f}", flush=True)
    n = len(rows)
    correct = sum(r["final_correct"] for r in rows)
    return dict(label=label, n=n, correct=correct, accuracy=round(correct / n, 4),
                delegated=delegated, truncated=truncated,
                seconds=round(time.time() - t0, 1),
                by_kind={k: dict(correct=v[0], n=v[1]) for k, v in by_kind.items()},
                items=items)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=list(CONFIGS))
    ap.add_argument("--single", action="store_true",
                    help="server has only the v3 adapter loaded (the serving layout)")
    ap.add_argument("--out", default=str(ROOT / "reports" / "benchmark_v3.json"))
    a = ap.parse_args()
    global SINGLE
    SINGLE = a.single

    suite = [json.loads(l) for l in open(ROOT / "data/eval/os_freeform.jsonl",
                                         encoding="utf-8")]
    print(f"57-item hand-written OS suite, {len(suite)} items, identical weights "
          f"(Q8_0) for every configuration\n")
    results = []
    for label in a.only:
        print(f"  running {label} ...", flush=True)
        results.append(run(label, suite))
        r = results[-1]
        print(f"  {label:<10} {r['correct']}/{r['n']} = {r['accuracy']:.1%}  "
              f"({r['seconds']:.0f}s, delegated {r['delegated']}, "
              f"truncated {r['truncated']})\n", flush=True)

    kinds = sorted({k for r in results for k in r["by_kind"]},
                   key=lambda k: -max(r["by_kind"].get(k, {}).get("n", 0) for r in results))
    w = max(len(k) for k in kinds) + 2
    print("\n" + "=" * 78)
    print(f"{'question kind':<{w}}" + "".join(f"{r['label']:>12}" for r in results))
    print("-" * 78)
    for k in kinds:
        line = f"{k:<{w}}"
        for r in results:
            b = r["by_kind"].get(k)
            line += f"{(str(b['correct']) + '/' + str(b['n'])) if b else '-':>12}"
        print(line)
    print("-" * 78)
    print(f"{'TOTAL':<{w}}" + "".join(f"{r['correct']}/{r['n']:>8}" for r in results))
    print(f"{'accuracy':<{w}}" + "".join(f"{r['accuracy']:>11.1%}" for r in results))
    Path(a.out).write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(f"\nwritten to {a.out}")


if __name__ == "__main__":
    main()
