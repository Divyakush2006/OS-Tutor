"""End-to-end RAG check on the served model: the same questions with retrieval off and on.

    python tools/rag_e2e.py [corpus_dir]          (default data/rag/fixture; GPU must be free)

Starts llama-server with the v3 adapter only (the serving configuration), then:

  A. THEORY MCQ (data/eval_theory, 70 items). Explain-mode system prompt, the question
     and its options, "answer with the letter only". Retrieval uses the question text
     alone, as a student would type it. Paired exact McNemar, off vs on. This is a
     generated-letter protocol, NOT the logit-scored one behind the 85.71% forgetting
     number, so the two are not comparable; only off-vs-on here is.
  B. EXPLAIN ANSWERS for the corpus's labelled queries (in-scope and out-of-scope):
     citation rate, invented citations, abstention, fact-checker flags, prompt tokens,
     time to answer and generation speed (the brief requires >= 20 tok/s).

Prompt cache off on every request (D-005), greedy decoding. Writes
reports/rag/e2e-<timestamp>/{results.json, summary.md}.
"""
from __future__ import annotations

import json
import re
import statistics
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import g0_ablation as g  # noqa: E402
from ostutor import config as C  # noqa: E402
from ostutor.evaluation.stats import paired  # noqa: E402
from ostutor.rag.retrieve import Retriever, augment, cited  # noqa: E402
from ostutor.theory_filter import fact_flags  # noqa: E402

EXPLAIN = C.SYSTEM_PROMPTS[("explain", "os")]
EXPLAIN_TOKENS = 700


def _git(*a: str) -> str:
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def ask(system: str, user: str, max_tokens: int) -> dict:
    body = dict(messages=[dict(role="system", content=system), dict(role="user", content=user)],
                temperature=0, max_tokens=max_tokens, cache_prompt=False,
                lora=[dict(id=0, scale=1.0)])
    req = urllib.request.Request(g.SERVER + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t = time.perf_counter()
    d = json.load(urllib.request.urlopen(req, timeout=1800))
    tm = d.get("timings", {})
    return dict(text=d["choices"][0]["message"]["content"] or "",
                seconds=round(time.perf_counter() - t, 3),
                prompt_tokens=d.get("usage", {}).get("prompt_tokens"),
                completion_tokens=d.get("usage", {}).get("completion_tokens"),
                tok_s=tm.get("predicted_per_second"))


def letter(text: str) -> int | None:
    m = re.search(r"\b([ABCD])\b", text.strip().upper())
    return "ABCD".index(m.group(1)) if m else None


def main() -> None:
    corpus = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "data/rag/fixture").resolve()
    out = ROOT / "reports" / "rag" / time.strftime("e2e-%Y%m%d-%H%M")
    out.mkdir(parents=True, exist_ok=True)
    r = Retriever(corpus)
    mcq = [json.loads(l) for l in open(g.THEORY, encoding="utf-8")]
    queries = [json.loads(l) for l in open(corpus / "queries.jsonl", encoding="utf-8")]
    res = dict(corpus=str(corpus.relative_to(ROOT)).replace("\\", "/"),
               corpus_sha256=r.manifest["chunks_sha256"], provenance=dict(
                   commit=_git("rev-parse", "HEAD"), dirty=bool(_git("status", "--porcelain", "--untracked-files=no")),
                   adapter="v3", server_args=g.SERVER_ARGS, cache_prompt=False, temperature=0),
               mcq=[], explain=[])
    proc = g.start_server("v3", ROOT / "serve" / "logs" / "rag-e2e.log")
    try:
        for i, q in enumerate(mcq):
            opts = "\n".join(f"{'ABCD'[k]}. {c}" for k, c in enumerate(q["choices"]))
            user = f"{q['question']}\n\n{opts}\n\nAnswer with the letter of the correct option only."
            hits = r.retrieve(q["question"])
            row = dict(id=f"mcq{i:02d}", answer=q["answer"], notes=[h["chunk"].chunk_id for h in hits])
            for arm, system in (("off", EXPLAIN), ("on", augment(EXPLAIN, hits))):
                a = ask(system, user, 8)
                row[arm] = dict(text=a["text"], pred=letter(a["text"]),
                                correct=letter(a["text"]) == q["answer"])
            res["mcq"].append(row)
            print(f"  mcq {i:02d} notes={len(hits)} off={row['off']['correct']} on={row['on']['correct']}",
                  flush=True)

        for q in queries:
            hits = r.retrieve(q["query"])
            row = dict(id=q["id"], in_scope=bool(q["doc"]), notes=[h["chunk"].chunk_id for h in hits],
                       gold_retrieved=any(h["chunk"].doc_id == q["doc"] for h in hits))
            for arm, system in (("off", EXPLAIN), ("on", augment(EXPLAIN, hits))):
                a = ask(system, q["query"], EXPLAIN_TOKENS)
                valid, invented = cited(a["text"], len(hits))
                row[arm] = dict(a, valid_citations=sorted(valid), invented_citations=sorted(invented),
                                fact_flags=sorted({n for n, _ in fact_flags(a["text"])}))
            res["explain"].append(row)
            print(f"  {q['id']} notes={len(hits)} cites={row['on']['valid_citations']} "
                  f"{row['on']['tok_s']:.1f} tok/s", flush=True)
    finally:
        g.stop_server(proc)

    # ---------------------------------------------------------------- summary
    off = {x["id"]: x["off"]["correct"] for x in res["mcq"]}
    on = {x["id"]: x["on"]["correct"] for x in res["mcq"]}
    covered = [x for x in res["mcq"] if x["notes"]]
    p_all = paired(off, on, "off", "on")
    p_cov = paired({x["id"]: off[x["id"]] for x in covered}, {x["id"]: on[x["id"]] for x in covered},
                   "off", "on") if covered else None
    ins = [x for x in res["explain"] if x["in_scope"] and x["notes"]]
    oos = [x for x in res["explain"] if not x["in_scope"]]
    ex = res["explain"]

    def med(rows, arm, key):
        v = [x[arm][key] for x in rows if x[arm][key] is not None]
        return round(statistics.median(v), 2) if v else None

    res["summary"] = dict(
        mcq_all=p_all, mcq_with_notes=p_cov, mcq_items_with_notes=len(covered),
        explain=dict(
            in_scope_with_notes=len(ins),
            cited_at_least_once=sum(bool(x["on"]["valid_citations"]) for x in ins),
            invented_citations=sum(len(x["on"]["invented_citations"]) for x in ex),
            out_of_scope=len(oos), out_of_scope_given_notes=sum(bool(x["notes"]) for x in oos),
            fact_flags_off=sum(bool(x["off"]["fact_flags"]) for x in ex),
            fact_flags_on=sum(bool(x["on"]["fact_flags"]) for x in ex),
            prompt_tokens_median=dict(off=med(ins, "off", "prompt_tokens"), on=med(ins, "on", "prompt_tokens")),
            seconds_median=dict(off=med(ins, "off", "seconds"), on=med(ins, "on", "seconds")),
            completion_tokens_median=dict(off=med(ins, "off", "completion_tokens"),
                                          on=med(ins, "on", "completion_tokens")),
            tok_s_median=dict(off=med(ex, "off", "tok_s"), on=med(ex, "on", "tok_s")),
            tok_s_min_on=round(min(x["on"]["tok_s"] for x in ex), 2)))
    (out / "results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    s, e = res["summary"], res["summary"]["explain"]
    md = [f"# RAG end to end — `{res['corpus']}`", "",
          f"Commit `{res['provenance']['commit'][:10]}` (dirty: {res['provenance']['dirty']}) · v3 adapter, "
          "one adapter per server · greedy · prompt cache off", "",
          "## A. Theory MCQ (70 items, generated letter; not comparable to the logit-scored 85.71%)", "",
          "| Items | Off | On | Right→wrong | Wrong→right | exact McNemar p |", "|---|---|---|---|---|---|",
          f"| all 70 | {p_all['correct_a']}/{p_all['n']} | {p_all['correct_b']}/{p_all['n']} | "
          f"{p_all['right_to_wrong']} | {p_all['wrong_to_right']} | {p_all['mcnemar_p']:.4f} |"]
    if p_cov:
        md.append(f"| {len(covered)} with notes retrieved | {p_cov['correct_a']}/{p_cov['n']} | "
                  f"{p_cov['correct_b']}/{p_cov['n']} | {p_cov['right_to_wrong']} | "
                  f"{p_cov['wrong_to_right']} | {p_cov['mcnemar_p']:.4f} |")
    md += ["", "## B. Explain answers", "",
           f"- in-scope questions given notes: {e['in_scope_with_notes']}; answers citing at least one note: "
           f"**{e['cited_at_least_once']}/{e['in_scope_with_notes']}**",
           f"- invented citations (a [S*n*] with no such note), all answers: **{e['invented_citations']}**",
           f"- out-of-scope questions given notes: {e['out_of_scope_given_notes']}/{e['out_of_scope']}",
           f"- answers flagged by the fact checker: off {e['fact_flags_off']}, on {e['fact_flags_on']} (of {len(ex)})",
           f"- median prompt tokens (in-scope): off {e['prompt_tokens_median']['off']}, on {e['prompt_tokens_median']['on']}",
           f"- median answer length, tokens: off {e['completion_tokens_median']['off']}, on {e['completion_tokens_median']['on']}",
           f"- median time to full answer, s: off {e['seconds_median']['off']}, on {e['seconds_median']['on']}",
           f"- generation speed, median tok/s: off {e['tok_s_median']['off']}, on {e['tok_s_median']['on']}; "
           f"slowest answer with RAG {e['tok_s_min_on']} tok/s (brief: >= 20)"]
    (out / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
