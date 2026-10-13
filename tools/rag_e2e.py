"""End-to-end RAG evaluation on the served model over one corpus (G2).

    python tools/rag_e2e.py data/rag/corpus          (GPU must be free; ~40 min)
    python tools/rag_e2e.py data/rag/open

Phases (each resumable: finished rows are kept in <run>/<phase>.partial.jsonl):

  mcq        The 200-item theory MCQ (data/eval_theory/os_theory_mcq_200.jsonl) under
             base and v3, each with retrieval off and on: explain-mode system prompt, the
             question and its four options, "answer with the letter only". Retrieval uses
             the question text alone, as a student would type it, through the calibrated
             gate. One adapter per server; base runs on a server with no adapter.
             Generated-letter protocol - NOT the logit protocol behind the earlier 90.00% /
             85.71%, so base is re-measured here and compared like for like.
  short      The 144 short-answer questions (data/eval_rag/os_short_answer.jsonl) under
             base and v3, retrieval off and on: "answer in a few words". Correct when the
             reply contains an accepted answer (word-bounded; the rule of rag_compare.py).
             Reported on the test split (the corpus was chosen on dev) and on all 144.
  explain    v3 with retrieval on, test-split questions: for the course corpus the in-scope
             questions of data/rag/eval/corpus_questions.jsonl, for any other corpus the
             short-answer questions. Citation rate, invented citations, answer length,
             time and decode speed (brief: >= 20 tok/s).
  judge      Faithfulness. Every sentence of an explain answer that cites [Sn] is put to
             the untuned base model (LoRA scale 0) with passage Sn: "Does the passage
             support the sentence? yes/no". Faithfulness = supported / cited sentences.
             A sample is exported for a human check (judge_sample.md).

Prompt cache off (D-005), greedy decoding. Writes reports/rag/e2e-<timestamp>/.
"""
from __future__ import annotations

import argparse
import json
import random
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
MCQ = ROOT / "data" / "eval_theory" / "os_theory_mcq_200.jsonl"
QUESTIONS = ROOT / "data" / "rag" / "eval" / "corpus_questions.jsonl"
SHORT_QA = ROOT / "data" / "eval_rag" / "os_short_answer.jsonl"
SHORT_TOKENS = 64
SHORT_ASK = "Answer in a few words only: the name or term asked for, no explanation."
EXPLAIN_TOKENS = 1500
JUDGE = ("You check whether a sentence is supported by a passage. Answer with exactly one "
         "word: yes if everything the sentence states is supported by the passage, no otherwise.")


def _git(*a: str) -> str:
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def ask(system: str, user: str, max_tokens: int, scale: float | None) -> dict:
    body = dict(messages=[dict(role="system", content=system), dict(role="user", content=user)],
                temperature=0, max_tokens=max_tokens, cache_prompt=False)
    if scale is not None:
        body["lora"] = [dict(id=0, scale=scale)]
    req = urllib.request.Request(g.SERVER + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t = time.perf_counter()
    d = json.load(urllib.request.urlopen(req, timeout=1800))
    tm = d.get("timings", {})
    return dict(text=d["choices"][0]["message"]["content"] or "", seconds=round(time.perf_counter() - t, 3),
                finish=d["choices"][0].get("finish_reason"),
                prompt_tokens=d.get("usage", {}).get("prompt_tokens"),
                completion_tokens=d.get("usage", {}).get("completion_tokens"),
                tok_s=tm.get("predicted_per_second"))


def letter(text: str) -> int | None:
    m = re.search(r"\b([ABCD])\b", text.strip().upper())
    return "ABCD".index(m.group(1)) if m else None


class Partial:
    """Append-only row store so an interrupted phase resumes where it stopped."""

    def __init__(self, path: Path):
        self.path = path
        self.rows = {}
        if path.is_file():
            for l in open(path, encoding="utf-8"):
                r = json.loads(l)
                self.rows[r["key"]] = r

    def add(self, row: dict) -> None:
        self.rows[row["key"]] = row
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def sentences(text: str) -> list[str]:
    text = re.sub(r"\n+", " ", text)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\[*(])", text) if s.strip()]


def run_mcq(out: Path, r: Retriever) -> None:
    items = [json.loads(l) for l in open(MCQ, encoding="utf-8")]
    store = Partial(out / "mcq.partial.jsonl")
    notes = {}
    for q in items:
        notes[q["id"]] = r.retrieve(q["question"])
    for server, adapter, scale in (("base", None, None), ("v3", "v3", 1.0)):
        todo = [q for q in items for arm in ("off", "on") if f"{server}|{arm}|{q['id']}" not in store.rows]
        if not todo:
            continue
        proc = g.start_server(adapter, ROOT / "serve" / "logs" / f"rag-e2e-{server}.log")
        try:
            for q in items:
                opts = "\n".join(f"{'ABCD'[k]}. {c}" for k, c in enumerate(q["choices"]))
                user = f"{q['question']}\n\n{opts}\n\nAnswer with the letter of the correct option only."
                for arm, system in (("off", EXPLAIN), ("on", augment(EXPLAIN, notes[q["id"]], r.noun))):
                    key = f"{server}|{arm}|{q['id']}"
                    if key in store.rows:
                        continue
                    a = ask(system, user, 8, scale)
                    store.add(dict(key=key, server=server, arm=arm, id=q["id"], answer=q["answer"],
                                   text=a["text"], pred=letter(a["text"]), correct=letter(a["text"]) == q["answer"],
                                   notes=[h["chunk"].chunk_id for h in notes[q["id"]]],
                                   status=q.get("status")))
                print(f"  mcq {server} {q['id']}", flush=True)
        finally:
            g.stop_server(proc)


def contains(text: str, answers: list[str]) -> bool:
    low = text.lower()
    return any(re.search(r"(?<![a-z0-9])" + re.escape(a.lower()) + r"(?![a-z0-9])", low)
               for a in answers if len(a) >= 3 and not a.isdigit())


def run_short(out: Path, r: Retriever) -> None:
    items = [json.loads(l) for l in open(SHORT_QA, encoding="utf-8")]
    store = Partial(out / "short.partial.jsonl")
    notes = {q["id"]: r.retrieve(q["question"]) for q in items}
    for server, adapter, scale in (("base", None, None), ("v3", "v3", 1.0)):
        if all(f"{server}|{arm}|{q['id']}" in store.rows for q in items for arm in ("off", "on")):
            continue
        proc = g.start_server(adapter, ROOT / "serve" / "logs" / f"rag-e2e-short-{server}.log")
        try:
            for q in items:
                user = f"{q['question']}\n\n{SHORT_ASK}"
                for arm, system in (("off", EXPLAIN), ("on", augment(EXPLAIN, notes[q["id"]], r.noun))):
                    key = f"{server}|{arm}|{q['id']}"
                    if key in store.rows:
                        continue
                    a = ask(system, user, SHORT_TOKENS, scale)
                    store.add(dict(key=key, server=server, arm=arm, id=q["id"], split=q["split"],
                                   answers=q["answers"], text=a["text"], correct=contains(a["text"], q["answers"]),
                                   notes=[h["chunk"].chunk_id for h in notes[q["id"]]],
                                   answer_in_notes=any(contains(h["chunk"].text, q["answers"])
                                                       for h in notes[q["id"]])))
                print(f"  short {server} {q['id']}", flush=True)
        finally:
            g.stop_server(proc)


def explain_questions(corpus: Path) -> list[dict]:
    if corpus.name == "corpus":
        qs = [json.loads(l) for l in open(QUESTIONS, encoding="utf-8")]
        return [q for q in qs if q["doc"] and q["split"] == "test"]
    return [dict(id=q["id"], query=q["question"], doc=None, answers=q["answers"])
            for q in map(json.loads, open(SHORT_QA, encoding="utf-8")) if q["split"] == "test"]


def run_explain(out: Path, r: Retriever, corpus: Path) -> None:
    qs = explain_questions(corpus)
    store = Partial(out / "explain.partial.jsonl")
    if all(q["id"] in store.rows for q in qs):
        return
    proc = g.start_server("v3", ROOT / "serve" / "logs" / "rag-e2e-explain.log")
    try:
        for q in qs:
            if q["id"] in store.rows:
                continue
            hits = r.retrieve(q["query"])
            a = ask(augment(EXPLAIN, hits, r.noun), q["query"], EXPLAIN_TOKENS, 1.0)
            valid, invented = cited(a["text"], len(hits))
            store.add(dict(key=q["id"], id=q["id"], query=q["query"], doc=q["doc"], **a,
                           notes=[dict(n=n, chunk=h["chunk"].chunk_id, doc=h["chunk"].doc_id,
                                       citation=h["chunk"].citation(), text=h["chunk"].text)
                                  for n, h in enumerate(hits, 1)],
                           gold_doc_given=(any(h["chunk"].doc_id == q["doc"] for h in hits) if q["doc"]
                                           else any(contains(h["chunk"].text, q["answers"]) for h in hits)),
                           valid_citations=sorted(valid), invented_citations=sorted(invented),
                           fact_flags=sorted({n for n, _ in fact_flags(a["text"])})))
            print(f"  explain {q['id']} notes={len(hits)} cites={sorted(valid)} {a['tok_s']:.1f} tok/s", flush=True)
    finally:
        g.stop_server(proc)


def run_judge(out: Path) -> None:
    ex = list(Partial(out / "explain.partial.jsonl").rows.values())
    store = Partial(out / "judge.partial.jsonl")
    todo = []
    for row in ex:
        notes = {n["n"]: n for n in row["notes"]}
        for k, s in enumerate(sentences(row["text"])):
            for n in sorted({int(m) for m in re.findall(r"\[S(\d+)\]", s)}):
                if n in notes:
                    todo.append((f"{row['id']}|{k}|{n}", row["id"], s, n, notes[n]))
    if all(t[0] in store.rows for t in todo):
        return
    proc = g.start_server(None, ROOT / "serve" / "logs" / "rag-e2e-judge.log")
    try:
        for key, qid, s, n, note in todo:
            if key in store.rows:
                continue
            clean = re.sub(r"\s*\[S\d+\]", "", s)
            a = ask(JUDGE, f"Passage:\n{note['text']}\n\nSentence:\n{clean}\n\nIs the sentence supported "
                            "by the passage? Answer yes or no.", 3, None)
            store.add(dict(key=key, id=qid, sentence=s, cited=n, passage=note["text"],
                           citation=note["citation"], verdict=a["text"].strip().lower().startswith("yes")))
        print(f"  judged {len(todo)} cited sentences", flush=True)
    finally:
        g.stop_server(proc)


def summarise(out: Path, meta: dict) -> None:
    res = dict(meta)
    mcq = list(Partial(out / "mcq.partial.jsonl").rows.values())
    if mcq:
        by = {}
        for row in mcq:
            by.setdefault(f"{row['server']}+{'rag' if row['arm'] == 'on' else 'norag'}", {})[row["id"]] = row["correct"]
        res["mcq"] = {k: dict(correct=sum(v.values()), n=len(v), accuracy=round(sum(v.values()) / len(v), 4))
                      for k, v in by.items()}
        pairs = [("v3+rag", "base+norag"), ("v3+rag", "v3+norag"), ("base+rag", "base+norag"),
                 ("v3+norag", "base+norag")]
        res["mcq_paired"] = {f"{b} -> {a}": paired(by[b], by[a], b, a) for a, b in pairs if a in by and b in by}
        new = {r["id"] for r in mcq if r.get("status") == "unreviewed"}
        res["mcq_new_items_only"] = {k: sum(v[i] for i in new if i in v) for k, v in by.items()}
        res["mcq_items_with_notes"] = sum(1 for r in mcq if r["server"] == "v3" and r["arm"] == "on" and r["notes"])
    sh = list(Partial(out / "short.partial.jsonl").rows.values())
    if sh:
        res["short"] = {}
        for split in ("test", "all"):
            by = {}
            for row in sh:
                if split == "all" or row["split"] == split:
                    by.setdefault(f"{row['server']}+{'rag' if row['arm'] == 'on' else 'norag'}", {})[row["id"]] = row["correct"]
            pairs = [("v3+rag", "v3+norag"), ("base+rag", "base+norag"), ("v3+rag", "base+norag"),
                     ("v3+norag", "base+norag")]
            res["short"][split] = dict(
                accuracy={k: dict(correct=sum(v.values()), n=len(v), accuracy=round(sum(v.values()) / len(v), 4))
                          for k, v in by.items()},
                paired={f"{b} -> {a}": paired(by[b], by[a], b, a) for a, b in pairs if a in by and b in by},
                answer_in_notes=sum(1 for row in sh if row["server"] == "v3" and row["arm"] == "on"
                                    and (split == "all" or row["split"] == split) and row["answer_in_notes"]))
    ex = list(Partial(out / "explain.partial.jsonl").rows.values())
    if ex:
        given = [x for x in ex if x["notes"]]
        res["explain"] = dict(
            n=len(ex), given_notes=len(given), gold_doc_given=sum(x["gold_doc_given"] for x in ex),
            cited_at_least_once=sum(bool(x["valid_citations"]) for x in given),
            invented_citations=sum(len(x["invented_citations"]) for x in ex),
            truncated=sum(x["finish"] == "length" for x in ex),
            fact_flags=sum(bool(x["fact_flags"]) for x in ex),
            prompt_tokens_median=statistics.median(x["prompt_tokens"] for x in ex),
            completion_tokens_median=statistics.median(x["completion_tokens"] for x in ex),
            seconds_median=round(statistics.median(x["seconds"] for x in ex), 2),
            tok_s_median=round(statistics.median(x["tok_s"] for x in ex), 2),
            tok_s_min=round(min(x["tok_s"] for x in ex), 2))
    jd = list(Partial(out / "judge.partial.jsonl").rows.values())
    if jd:
        sent_total = sum(len(sentences(x["text"])) for x in ex)
        res["faithfulness"] = dict(cited_sentence_checks=len(jd), supported=sum(x["verdict"] for x in jd),
                                   share_supported=round(sum(x["verdict"] for x in jd) / len(jd), 4),
                                   sentences_total=sent_total,
                                   sentences_with_citation=len({(x["id"], x["key"].split("|")[1]) for x in jd}),
                                   judge="untuned base model (Qwen3-4B-Instruct-2507), one yes/no per cited sentence")
        rng = random.Random(30)
        sample = rng.sample(jd, min(40, len(jd)))
        lines = ["# Faithfulness: sample for a human check", "",
                 "For each row: does the passage support everything the sentence states? Mark the "
                 "`human` column yes/no. `judge` is the base model's verdict.", ""]
        for k, x in enumerate(sample, 1):
            lines += [f"## {k}. `{x['key']}` — judge: **{'yes' if x['verdict'] else 'no'}** — human: ____", "",
                      f"**Sentence:** {x['sentence']}", "", f"**Passage [S{x['cited']}] {x['citation']}:** {x['passage']}", ""]
        (out / "judge_sample.md").write_text("\n".join(lines), encoding="utf-8")
        (out / "judge_sample.json").write_text(json.dumps([x["key"] for x in sample], indent=1), encoding="utf-8")
    (out / "results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    md = [f"# RAG end to end — `{res['corpus']}`", "",
          f"Commit `{res['commit'][:10]}` (dirty: {res['dirty']}) · corpus `{res['corpus_sha256'][:12]}` · "
          "greedy · prompt cache off · one adapter per server", ""]
    if "mcq" in res:
        md += ["## Theory MCQ, 200 items (generated letter)", "",
               "| Configuration | Correct | Accuracy |", "|---|---|---|"]
        md += [f"| {k} | {v['correct']}/{v['n']} | {v['accuracy']:.2%} |" for k, v in sorted(res["mcq"].items())]
        md += ["", "| Comparison | Right→wrong | Wrong→right | exact McNemar p |", "|---|---|---|---|"]
        md += [f"| {k} | {p['right_to_wrong']} | {p['wrong_to_right']} | {p['mcnemar_p']:.4f} |"
               for k, p in res["mcq_paired"].items()]
        md += ["", f"Items given notes by the gate: {res['mcq_items_with_notes']}/200. "
               f"Correct on the 130 new (unreviewed) items only: {res['mcq_new_items_only']}"]
    if "short" in res:
        for split, x in res["short"].items():
            n = next(iter(x["accuracy"].values()))["n"]
            md += ["", f"## Short-answer questions, {split} ({n} items; correct = an accepted answer in the reply)", "",
                   "| Configuration | Correct | Accuracy |", "|---|---|---|"]
            md += [f"| {k} | {v['correct']}/{v['n']} | {v['accuracy']:.2%} |" for k, v in sorted(x["accuracy"].items())]
            md += ["", "| Comparison | Right→wrong | Wrong→right | exact McNemar p |", "|---|---|---|---|"]
            md += [f"| {k} | {p['right_to_wrong']} | {p['wrong_to_right']} | {p['mcnemar_p']:.4f} |"
                   for k, p in x["paired"].items()]
            md += ["", f"Notes given to v3 contained an accepted answer for {x['answer_in_notes']}/{n} items."]
    if "explain" in res:
        e = res["explain"]
        md += ["", f"## Explain answers ({e['n']} test-split questions, v3 + RAG)", "",
               f"- given notes: {e['given_notes']}/{e['n']}; notes included the labelled document "
               f"(other corpora: an accepted answer): {e['gold_doc_given']}",
               f"- answers citing at least one note: **{e['cited_at_least_once']}/{e['given_notes']}**",
               f"- invented citations: **{e['invented_citations']}**",
               f"- truncated at {EXPLAIN_TOKENS} tokens: {e['truncated']}; fact-checker flags: {e['fact_flags']}",
               f"- median prompt {e['prompt_tokens_median']} tokens, answer {e['completion_tokens_median']} tokens, "
               f"{e['seconds_median']} s; decode median {e['tok_s_median']} tok/s, slowest {e['tok_s_min']} tok/s"]
    if "faithfulness" in res:
        f = res["faithfulness"]
        md += ["", "## Faithfulness", "",
               f"- cited-sentence checks: {f['cited_sentence_checks']}; judged supported: **{f['supported']} "
               f"({f['share_supported']:.1%})**",
               f"- sentences carrying a citation: {f['sentences_with_citation']} of {f['sentences_total']}",
               f"- judge: {f['judge']}; human-check sample: `judge_sample.md`"]
    (out / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(md))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus", nargs="?", default=str(ROOT / "data/rag/corpus"))
    ap.add_argument("--run", help="resume this run directory")
    ap.add_argument("--phases", default="mcq,short,explain,judge")
    a = ap.parse_args()
    corpus = Path(a.corpus).resolve()
    out = Path(a.run) if a.run else ROOT / "reports" / "rag" / time.strftime("e2e-%Y%m%d-%H%M")
    out.mkdir(parents=True, exist_ok=True)
    r = Retriever(corpus)
    meta = dict(corpus=str(corpus.relative_to(ROOT)).replace("\\", "/"), corpus_sha256=r.manifest["chunks_sha256"],
                commit=_git("rev-parse", "HEAD"), dirty=bool(_git("status", "--porcelain", "--untracked-files=no")),
                gate=dict(strong_cosine=r.strong_cosine, min_bm25=r.min_bm25), server_args=g.SERVER_ARGS,
                cache_prompt=False, temperature=0)
    (out / "provenance.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    phases = a.phases.split(",")
    if "mcq" in phases:
        run_mcq(out, r)
    if "short" in phases:
        run_short(out, r)
    if "explain" in phases:
        run_explain(out, r, corpus)
    if "judge" in phases:
        run_judge(out)
    summarise(out, meta)


if __name__ == "__main__":
    main()
