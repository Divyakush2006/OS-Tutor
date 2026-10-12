"""Self-distilled theory and tutoring data (v3.0).

    python tools/generate_theory_sdft.py [--only theory|tutor] [--limit N]

Requires llama-server on :8081 with the base GGUF (+ any LoRA, applied at scale 0,
so answers come from the UNTUNED base model).

THEORY. Every question in ostutor/simulators/theory_bank.py is asked twice: once
as written and once with a style request (exam revision, beginner, concise, with
an example). Targets are the base model's own greedy answers - self-distillation
(SDFT, Yang et al., ACL 2024) - so training on them anchors the explanation
behaviour the adapter must not damage. Answers are later sanitised and fact-checked
by ostutor/theory_filter.py; nothing here is trusted blindly.

TUTOR. A simulator-verified problem plus a student's WRONG attempt built from a
real misconception (non-preemptive SJF numbers for an SRTF question, FIFO faults
for LRU, forgetting the return jump, ...). The base model answers as a Socratic
tutor; the filter rejects any reply that reveals the correct final answer.

Output: data/raw/theory_sdft.jsonl, data/raw/tutor_sdft.jsonl (resumable: already
answered prompts are skipped).
"""
import argparse
import hashlib
import json
import random
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ostutor.config import SYSTEM_PROMPTS  # noqa: E402
from ostutor.simulators import generate as G  # noqa: E402
from ostutor.simulators.theory_bank import questions  # noqa: E402

SERVER = "http://127.0.0.1:8081/v1/chat/completions"
STYLES = [
    ("plain", ""),
    ("exam", " I'm revising for an exam, so please cover the key points I should remember."),
    ("beginner", " Please explain it simply; I'm new to operating systems."),
    ("example", " Please include a concrete example."),
    ("concise", " Keep it concise."),
]


def ask(system, user, max_tokens):
    body = dict(messages=[dict(role="system", content=system), dict(role="user", content=user)],
                temperature=0, max_tokens=max_tokens, lora=[dict(id=0, scale=0.0)])
    req = urllib.request.Request(SERVER, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=1200))
    c = d["choices"][0]
    return c["message"]["content"], c.get("finish_reason"), d.get("usage", {}).get("completion_tokens")


def every_style_prompts():
    """Every question in every style - the full cross product.

    The base pass asks 2 wordings per question and --extra-styles adds 2 more, which
    left one of the five styles unused. Conceptual supply turned out to be the second
    tightest category in the build (72% of it was needed), and total dataset size is
    proportional to the scarcest supply, so the last wording is worth having. A
    superset of both earlier passes, so resuming re-asks only what is missing.
    """
    return [dict(area=q["area"], question=q["question"], style=name,
                 user=q["question"] + suffix)
            for q in questions() for name, suffix in STYLES]


def theory_prompts(seed=20260920, extra=False):
    """Two wordings per question (plain + one style). `extra` adds two MORE styles
    per question: theory volume also sets the row budget for every other category
    (MIX is proportional), so more accepted theory answers mean more procedural
    skill rows can ship."""
    rng = random.Random(seed)
    out = []
    for q in questions():
        chosen = [STYLES[0], rng.choice(STYLES[1:])]
        if extra:
            rest = [s for s in STYLES[1:] if s not in chosen]
            rng.shuffle(rest)
            chosen = rest[:2]
        for name, suffix in chosen:
            out.append(dict(area=q["area"], question=q["question"], style=name,
                            user=q["question"] + suffix))
    return out


MISCONCEPTIONS = {
    "SRTF": ("SJF", "I used shortest job first"),
    "RR": ("FCFS", "I ran them in arrival order"),
    "PRIORITY": ("FCFS", "I scheduled them in the order they arrived"),
    "SJF": ("FCFS", "I just used arrival order"),
    "LRU": ("FIFO", "I evicted the page that came in first"),
    "OPT": ("LRU", "I evicted the least recently used page"),
    "FIFO": ("LRU", "I replaced the least recently used page"),
    "BEST": ("FIRST", "I put each process in the first hole that fits"),
    "WORST": ("BEST", "I picked the smallest hole that fits"),
}


def tutor_prompts(n, seed=424242):
    """A problem plus a wrong attempt that comes from a named misconception."""
    from ostutor.simulators.memory import fit_allocation, page_replacement
    from ostutor.simulators.scheduling import ALGORITHMS, Proc
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        g = rng.choice([G.gen_scheduling, G.gen_paging, G.gen_freespace])
        rec = g(random.Random(rng.randrange(1 << 30)), "normal")
        v = rec["verify"]
        if v["kind"] == "scheduling":
            wrong_algo, story = MISCONCEPTIONS.get(v["algo"], (None, None))
            if not wrong_algo:
                continue
            procs = [Proc(p, a, b, pr) for p, a, b, pr in v["procs"]]
            right = ALGORITHMS[v["algo"]](procs, quantum=v["quantum"]).avg_waiting
            wrong = ALGORITHMS[wrong_algo](procs, quantum=v["quantum"]).avg_waiting
            what = "average waiting time"
        elif v["kind"] == "paging":
            wrong_algo, story = MISCONCEPTIONS.get(v["policy"], (None, None))
            if not wrong_algo:
                continue
            right = page_replacement(v["refs"], v["frames"], v["policy"])["faults"]
            wrong = page_replacement(v["refs"], v["frames"], wrong_algo)["faults"]
            what = "number of page faults"
        else:
            wrong_algo, story = MISCONCEPTIONS.get(v["policy"], (None, None))
            if not wrong_algo:
                continue
            right = fit_allocation(v["holes"], v["reqs"], v["policy"])["placement"]
            wrong = fit_allocation(v["holes"], v["reqs"], wrong_algo)["placement"]
            what = "placement (hole numbers, in request order)"
        if right == wrong:
            continue
        user = (f"{rec['problem']}\n\nMy attempt: {story}, and I got {what} = {wrong}. "
                f"{rng.choice(['Is that right?', 'Can you check my answer?', 'Where did I go wrong?', 'Am I correct?'])}")
        out.append(dict(kind=v["kind"], problem=rec["problem"], verify=v, right=right,
                        wrong=wrong, user=user))
    return out


def drop_truncated(out_path):
    """Remove answers the server cut off at the token limit, so the resume logic
    re-asks exactly those prompts (with a larger budget).

    The re-ask is not bit-identical to the original: temperature is 0, but under
    llama.cpp's continuous batching the floating-point reduction order depends on
    what else shares the batch, so a re-asked prompt can come back slightly
    reworded. Measured on 19 prompts that were answered twice, 17 differed. It is
    still the same model answering the same question, which is what a
    self-distilled target needs to be.

    Answers rejected on CONTENT (revealed answer, no question, misconception) are
    NOT re-asked: the model would very likely make the same choice again, and the
    GPU time is better spent on prompts with no answer at all."""
    if not out_path.exists():
        return
    rows = [json.loads(l) for l in open(out_path, encoding="utf-8")]
    keep = [r for r in rows if r.get("finish_reason") in (None, "stop")]
    if len(keep) == len(rows):
        print(f"{out_path.name}: no truncated answers", flush=True)
        return
    bak = out_path.with_suffix(".jsonl.truncated")
    with open(bak, "a", encoding="utf-8") as f:
        for r in rows:
            if r.get("finish_reason") not in (None, "stop"):
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(out_path, "w", encoding="utf-8") as f:
        for r in keep:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{out_path.name}: dropped {len(rows) - len(keep)} truncated answers "
          f"(kept in {bak.name}); they will be re-asked", flush=True)


def run(prompts, system, out_path, key, max_tokens):
    # Provenance: which system prompt produced this answer. A self-distilled target
    # is only a valid anchor for the behaviour the prompt asks for, and v3.0 found
    # that out the hard way - the tutor prompt said "do not reveal the answer UNTIL
    # they have attempted it", every example was a student who had attempted it, and
    # a quarter of the replies duly gave the answer away. Recording the hash makes a
    # prompt change visible in the data instead of silent.
    sys_sha = hashlib.blake2b(system.encode(), digest_size=6).hexdigest()
    done = set()
    if out_path.exists():
        rows = [json.loads(l) for l in open(out_path, encoding="utf-8")]
        stale = [r for r in rows if r.get("system_sha") not in (None, sys_sha)]
        if stale:
            sys.exit(f"{out_path.name}: {len(stale)} answers were generated under a "
                     f"different system prompt. Move the file aside (see "
                     f"data/raw/_pre_prompt_fix/) and regenerate, rather than mixing "
                     f"targets that were asked for different behaviour.")
        done = {r[key] for r in rows}
    todo, seen = [], set()
    for p in prompts:                      # de-duplicate: style sets can overlap
        if p[key] not in done and p[key] not in seen:
            seen.add(p[key])
            todo.append(p)
    print(f"{out_path.name}: {len(done)} done, {len(todo)} to go "
          f"(max_tokens={max_tokens})", flush=True)

    def work(p):
        text, fin, n = ask(system, p["user"], max_tokens)
        return dict(p, answer=text, finish_reason=fin, tokens=n, system_sha=sys_sha)

    with ThreadPoolExecutor(4) as ex, open(out_path, "a", encoding="utf-8") as f:
        for i, r in enumerate(ex.map(work, todo)):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            if (i + 1) % 25 == 0:
                print(f"  {i + 1}/{len(todo)}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--tutor-n", type=int, default=450)
    ap.add_argument("--extra-styles", action="store_true",
                    help="second pass: two further wordings per question")
    ap.add_argument("--all-styles", action="store_true",
                    help="both wording sets (use with --retry-truncated)")
    ap.add_argument("--retry-truncated", action="store_true",
                    help="re-ask only the answers the token limit cut off")
    # Measured: at 1600 tokens 4.6% of theory answers and 60% of tutoring answers were
    # cut off mid-sentence. Tutoring replies are the longest (a full Socratic
    # walk-through of a wrong attempt), hence the larger budget.
    ap.add_argument("--theory-max-tokens", type=int, default=2600)
    ap.add_argument("--tutor-max-tokens", type=int, default=3400)
    a = ap.parse_args()
    raw = ROOT / "data" / "raw"
    if a.only in (None, "theory"):
        tp = every_style_prompts() if a.all_styles \
            else theory_prompts(extra=a.extra_styles)
        out = raw / "theory_sdft.jsonl"
        if a.retry_truncated:
            drop_truncated(out)
        run(tp[: a.limit], SYSTEM_PROMPTS[("explain", "os")], out, "user",
            a.theory_max_tokens)
    if a.only in (None, "tutor"):
        up = tutor_prompts(a.tutor_n)[: a.limit]
        out = raw / "tutor_sdft.jsonl"
        if a.retry_truncated:
            drop_truncated(out)
        run(up, SYSTEM_PROMPTS[("tutor", "os")], out, "user", a.tutor_max_tokens)


if __name__ == "__main__":
    main()
