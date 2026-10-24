"""Before/after measurements for the final-review fixes, on the live model server.

    serve/.venv-webui/Scripts/python tools/final_review_eval.py [--phases disk tutor offtopic]

  disk      The 80 disk items of the OOD holdout through the solver, with the range fix in
            ostutor/solver.py, against the same items in reports/g0/20261012-1429/ood.json.
  tutor     30 student attempts (24 wrong, 6 right) over paging, scheduling, disk and
            address translation. BEFORE is the old tutor path (trained prompt, reply shown
            as written); AFTER is gateway.tutor_reply (private simulator check, reply rules,
            redraft, safe hint). Every reply is saved for reading by hand.
  offtopic  The classifier's "offtopic" verdict, which now declines a question, on the 124
            in-scope retrieval questions, the 144 short-answer questions, the 40 questions
            the corpora do not cover, and 20 everyday questions.

Writes reports/final_review/<phase>.json and summary.md. Needs llama-server on :8081 with
the v3 adapter, as served.
"""
import argparse
import asyncio
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "serve"))
import gateway  # noqa: E402
from ostutor.evaluation.extraction import fields_match  # noqa: E402
from ostutor.evaluation.harness import grade  # noqa: E402
from ostutor.theory_filter import _AFFIRM, _reveals  # noqa: E402
from tools import g0_ablation as g  # noqa: E402

OUT = ROOT / "reports" / "final_review"
OLD_OOD = ROOT / "reports" / "g0" / "20261012-1429" / "ood.json"


# ------------------------------------------------------------------ disk
def run_disk():
    old = {x["id"]: x for x in json.loads(OLD_OOD.read_text(encoding="utf-8"))["items"]}
    recs = [r for r in g._ood_records() if r["verify"]["kind"] == "disk"]
    items = []
    for i, rec in enumerate(recs, 1):
        r = g._answer(rec["problem"], True, 0.0, 1.0)
        gr = grade(rec, r["text"])
        accepted = next((e["params"] for e in r["trace"] if e["outcome"] == "ok"), None)
        exact, wrong = fields_match(accepted, rec["verify"])
        o = old[rec["id"]]
        items.append(dict(id=rec["id"], correct=bool(gr["final_correct"]), extraction_exact=exact,
                          wrong_fields=wrong, delegated=r["delegated"],
                          before_correct=o["correct"], before_extraction_exact=o["extraction_exact"]))
        if i % 20 == 0:
            print(f"  disk {i}/{len(recs)}", flush=True)
    n = len(items)
    s = lambda k: sum(x[k] for x in items)  # noqa: E731
    lost = sum(x["before_correct"] and not x["correct"] for x in items)
    won = sum(x["correct"] and not x["before_correct"] for x in items)
    return dict(n=n, before_correct=s("before_correct"), after_correct=s("correct"),
                before_extraction_exact=s("before_extraction_exact"),
                after_extraction_exact=s("extraction_exact"), right_to_wrong=lost,
                wrong_to_right=won, items=items)


# ------------------------------------------------------------------ tutor
def _right(question, params):
    text, meta = gateway.solve(question, lambda s, u: json.dumps(params))
    line = next(l for l in text.splitlines() if l.startswith("**Answer:"))
    return [float(x) for x in gateway._NUM.findall(line)]


def tutor_items():
    """(question, params, claim) for 30 attempts (12 paging, 9 scheduling, 6 disk, 3 translation); claims are wrong by a typical slip
    except the six marked right."""
    P = []
    pages = [([7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2], 3), ([1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5], 3),
             ([1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5], 4), ([2, 3, 2, 1, 5, 2, 4, 5, 3, 2, 5, 2], 3),
             ([4, 7, 0, 7, 1, 0, 1, 2, 1, 2, 7, 1, 2], 3), ([1, 3, 0, 3, 5, 6, 3], 3)]
    for k, (refs, f) in enumerate(pages):
        for pol in ("FIFO", "LRU"):
            P.append(("paging", dict(kind="paging", policy=pol, frames=f, refs=refs),
                      f"For the reference string {' '.join(map(str, refs))} with {f} frames I used "
                      f"{pol} page replacement and got {{claim}} page faults. Is that right?"))
    procs = [[["P1", 0, 5, 1], ["P2", 1, 3, 1], ["P3", 2, 1, 1], ["P4", 3, 2, 1]],
             [["P1", 0, 8, 1], ["P2", 1, 4, 1], ["P3", 2, 9, 1], ["P4", 3, 5, 1]],
             [["P1", 0, 6, 1], ["P2", 2, 2, 1], ["P3", 4, 8, 1], ["P4", 5, 3, 1]]]
    for pr in procs:
        desc = ", ".join(f"{n} arrives at {a} with burst {b}" for n, a, b, _ in pr)
        for algo in ("FCFS", "SJF", "RR"):
            q = " with a time quantum of 2" if algo == "RR" else ""
            P.append(("scheduling", dict(kind="scheduling", algo=algo, quantum=2, procs=pr),
                      f"{desc}. Using {algo} scheduling{q}, I got an average waiting time of "
                      f"{{claim}}. Is that right?"))
    disks = [(53, [98, 183, 37, 122, 14, 124, 65, 67]), (50, [82, 170, 43, 140, 24, 16, 190])]
    for head, reqs in disks:
        for pol in ("FCFS", "SSTF", "SCAN"):
            P.append(("disk", dict(kind="disk", policy=pol, head=head, reqs=reqs, size=200,
                                   direction="up"),
                      f"The disk has cylinders 0 to 199 and the head is at {head}, moving up. "
                      f"Requests: {', '.join(map(str, reqs))}. Using {pol} I got a total head "
                      f"movement of {{claim}} cylinders. Am I correct?"))
    for L, ps, table in [(1234, 512, [5, 2, 7]), (3000, 1024, [4, 9, 1, 6]), (700, 256, [3, 8, 2])]:
        P.append(("translate", dict(kind="translate", logical=L, page_size=ps, table=table),
                  f"The page size is {ps} bytes and the page table maps pages 0, 1, 2... to frames "
                  f"{', '.join(map(str, table))}. I translated logical address {L} and got "
                  f"physical address {{claim}}. Is that right?"))
    items = []
    right_ids = {0, 7, 13, 18, 22, 28}               # six attempts that are correct
    for i, (kind, params, tmpl) in enumerate(P[:30]):
        q0 = tmpl.format(claim="X")
        right = _right(q0, params)
        r = right[0]
        claim = r if i in right_ids else (r + 3 if kind != "translate" else r + params["page_size"])
        c = int(claim) if float(claim) == int(claim) else claim
        items.append(dict(id=f"t{i + 1:02d}", kind=kind, question=tmpl.format(claim=c),
                          right=right, claim=float(claim), correct_attempt=i in right_ids))
    return items


def judge(reply, item):
    right = set(item["right"])
    claimed = {item["claim"]}
    wrong = not item["correct_attempt"]
    steps = sum(bool(gateway._STEP.search(l)) for l in reply.splitlines())
    rows = sum(l.lstrip().startswith("|") for l in reply.splitlines())
    asserted = [x for x in gateway._RESULT.findall(reply) if float(x) not in claimed]
    return dict(
        reveals_answer=wrong and any(_reveals(reply, int(r) if r == int(r) else r) for r in right),
        asserts_other_result=bool(asserted),
        works_it_out=steps >= gateway.TRACE_STEPS or rows >= 5,
        affirms_wrong=wrong and bool(_AFFIRM.search(reply)),
        asks_question="?" in reply,
        confirms_right=(not wrong) and bool(re.search(r"\b(?:correct|right|yes|well done)\b",
                                                       reply[:300], re.I))
        and not re.search(r"\b(?:not|isn't|incorrect)\s+(?:quite\s+)?(?:correct|right)\b",
                          reply[:300], re.I),
    )


async def run_tutor():
    items = tutor_items()
    out = []
    for i, it in enumerate(items, 1):
        raw = dict(model="ostutor-tutor", cache_prompt=False,
                   messages=[dict(role="user", content=it["question"])])
        body = gateway.prepare(raw, prompt_override=gateway.SYSTEM_PROMPTS[("tutor", "os")])
        body.update(stream=False, lora=[dict(id=0, scale=1.0)])
        r = await gateway.client.post("/v1/chat/completions", json=body)
        before = gateway.scrub(r.json()["choices"][0]["message"]["content"] or "")
        t = time.time()
        after, path = await gateway.tutor_reply(raw, it["question"])
        kind, right, verdict = gateway.tutor_truth(it["question"])
        out.append(dict(it, before=before, after=after, after_path=path,
                        verdict=verdict, verdict_ok=verdict == ("correct" if it["correct_attempt"]
                                                                else "incorrect"),
                        after_seconds=round(time.time() - t, 1),
                        before_judged=judge(before, it), after_judged=judge(after, it)))
        print(f"  tutor {i}/{len(items)} {path}", flush=True)
    keys = list(out[0]["before_judged"])
    tot = {side: {k: sum(x[f"{side}_judged"][k] for x in out) for k in keys}
           for side in ("before", "after")}
    paths = {p: sum(x["after_path"] == p for x in out) for p in {x["after_path"] for x in out}}
    return dict(n=len(out), wrong_attempts=sum(not x["correct_attempt"] for x in out),
                totals=tot, after_paths=paths, verdict_ok=sum(x["verdict_ok"] for x in out),
                items=out)


# ------------------------------------------------------------------ off-topic
EVERYDAY = ["What is the best way to cook biryani?", "Who won the 2011 Cricket World Cup?",
            "What is the capital of Australia?", "How do I improve my running stamina?",
            "Write a poem about the monsoon.", "What is the plot of Hamlet?",
            "How many calories are in a banana?", "Recommend a good fantasy novel.",
            "How do vaccines train the immune system?", "What causes inflation?",
            "Translate 'good morning' into French.", "How do I tie a tie?",
            "What is photosynthesis?", "Who painted the Mona Lisa?",
            "How do I make cold brew coffee?", "What is the tallest mountain in Africa?",
            "Explain the offside rule in football.", "How do I learn to play guitar?",
            "What is the boiling point of water at high altitude?", "Plan a 3-day trip to Goa."]


def run_offtopic():
    rq = [json.loads(l) for l in open(ROOT / "data/rag/eval/corpus_questions.jsonl", encoding="utf-8")]
    sa = [json.loads(l) for l in open(ROOT / "data/eval_rag/os_short_answer.jsonl", encoding="utf-8")]
    sets = {"in_scope_retrieval": [x["query"] for x in rq if x["doc"]],
            "short_answer": [x["question"] for x in sa],
            "not_covered_by_corpora": [x["query"] for x in rq if not x["doc"]],
            "everyday": EVERYDAY}
    res = {}
    for name, qs in sets.items():
        kinds = [gateway._classify(q) for q in qs]
        declined = [q for q, k in zip(qs, kinds) if k == "offtopic"]
        res[name] = dict(n=len(qs), declined=len(declined), declined_questions=declined)
        print(f"  offtopic {name}: {len(declined)}/{len(qs)} declined", flush=True)
    return res


# ------------------------------------------------------------------ main
def summary(results):
    L = ["# Final-review fixes: before and after", "",
         f"Measured {time.strftime('%Y-%m-%d %H:%M')} on the live llama-server (v3 adapter, as served).", ""]
    if "disk" in results:
        d = results["disk"]
        L += ["## Disk range fix (OOD holdout, disk items)", "",
              "| | Before | After |", "|---|---|---|",
              f"| Correct | {d['before_correct']}/{d['n']} | {d['after_correct']}/{d['n']} |",
              f"| Extraction exact | {d['before_extraction_exact']}/{d['n']} | {d['after_extraction_exact']}/{d['n']} |",
              f"| Right to wrong / wrong to right | | {d['right_to_wrong']} / {d['wrong_to_right']} |", ""]
    if "tutor" in results:
        t = results["tutor"]
        L += ["## Verified tutoring (30 attempts, 24 wrong)", "", "| Reply | Before | After |", "|---|---|---|"]
        for k in t["totals"]["before"]:
            L.append(f"| {k} | {t['totals']['before'][k]} | {t['totals']['after'][k]} |")
        L += ["", f"After paths: {t['after_paths']}. Private verdict right: {t['verdict_ok']}/{t['n']}.", ""]
    if "offtopic" in results:
        L += ["## Off-topic refusal (classifier verdict)", "", "| Set | Declined |", "|---|---|"]
        for k, v in results["offtopic"].items():
            L.append(f"| {k} | {v['declined']}/{v['n']} |")
        L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phases", nargs="*", default=["disk", "tutor", "offtopic"])
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    results = {}
    for ph in ("disk", "tutor", "offtopic"):
        f = OUT / f"{ph}.json"
        if ph in a.phases:
            print(ph, flush=True)
            res = asyncio.run(run_tutor()) if ph == "tutor" else (run_disk() if ph == "disk" else run_offtopic())
            f.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
        if f.exists():
            results[ph] = json.loads(f.read_text(encoding="utf-8"))
    (OUT / "summary.md").write_text(summary(results), encoding="utf-8")
    print(summary(results))


if __name__ == "__main__":
    main()
