"""Follow-up checks on a G0 run.

    python tools/g0_diagnostics.py reports/g0/<run>

Two questions the G0 numbers raised, answered on one v3 server:

1. DETERMINISM. v3 alone scored 36/57 on 2026-09-21 and 34/57 on 2026-10-12 with the
   same weights and greedy decoding; only 23/57 outputs were identical. Hypothesis:
   llama-server's prompt cache reuses the KV of a shared prefix (the system prompt) from
   whatever request came before, which changes how the prompt is batched and so the
   logits. Test: replay the six items whose verdict flipped, each three times —
   twice with cache_prompt=false (an unrelated request in between) and once with the
   cache warmed by a different prompt — and compare the outputs byte for byte.

2. DISK SIZE. Nine OOD disk items were delegated with the disk size misread. Hypothesis:
   "device spans 0-299" is extracted as size=299 (the last cylinder) instead of 300.
   Test: re-extract those items and record the size the model returns.

Writes diagnostics.json into the run directory. Changes nothing else.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import g0_ablation as g  # noqa: E402
from ostutor import config as C  # noqa: E402
from ostutor.solver import solve  # noqa: E402

FLIPPED = ["rr_classic", "prio_classic", "belady_3", "clock_small", "banker_req_deny", "cscan_up"]
UNRELATED = "Explain in two sentences what a page fault is."


def ask(system, user, cache, max_tokens=g.ANSWER_TOKENS):
    import urllib.request
    body = dict(messages=[dict(role="system", content=system), dict(role="user", content=user)],
                temperature=0, max_tokens=max_tokens, cache_prompt=cache,
                lora=[dict(id=0, scale=1.0)])
    req = urllib.request.Request(g.SERVER + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=1800))["choices"][0]["message"]["content"]


def main() -> None:
    run = Path(sys.argv[1])
    suite = {json.loads(l)["id"]: json.loads(l) for l in open(g.SUITE, encoding="utf-8")}
    solve_sys = C.system_for("solve", "os")
    proc = g.start_server("v3", ROOT / "serve" / "logs" / "g0-diagnostics.log")
    try:
        det = []
        for iid in FLIPPED:
            q = suite[iid]["problem"]
            a = ask(solve_sys, q, cache=False)
            ask(solve_sys, UNRELATED, cache=True, max_tokens=60)    # disturb the cache
            b = ask(solve_sys, q, cache=False)
            ask("You are a helpful assistant.", UNRELATED, cache=True, max_tokens=60)
            c = ask(solve_sys, q, cache=True)                       # warmed by a different prefix
            det.append(dict(id=iid, nocache_repeat_identical=a == b, cached_equals_nocache=c == a))
            print(f"  {iid:<18} no-cache repeat identical: {a == b}   cached == no-cache: {c == a}",
                  flush=True)

        ood = json.loads((run / "ood.json").read_text(encoding="utf-8"))
        recs = {r["id"]: r for r in g._ood_records()}
        sizes = []
        for x in ood["items"]:
            if x["delegated"] and "size" in x["wrong_fields"]:
                trace: list = []
                solve(recs[x["id"]]["problem"],
                      lambda s, u: g.chat(s, u, g.EXTRACT_TOKENS, 0.0)["text"], trace=trace)
                got = next((e["params"].get("size") for e in trace if e["outcome"] == "ok"), None)
                want = recs[x["id"]]["verify"]["size"]
                sizes.append(dict(id=x["id"], truth=want, extracted=got, off_by_one=got == want - 1))
                print(f"  {x['id']}  truth {want}  extracted {got}", flush=True)
    finally:
        g.stop_server(proc)
    res = dict(determinism=det, disk_size=sizes)
    (run / "diagnostics.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({"nocache_repeat_identical": sum(d["nocache_repeat_identical"] for d in det),
                      "cached_equals_nocache": sum(d["cached_equals_nocache"] for d in det),
                      "n": len(det),
                      "disk_off_by_one": sum(s["off_by_one"] for s in sizes), "disk_n": len(sizes)}))


if __name__ == "__main__":
    main()
