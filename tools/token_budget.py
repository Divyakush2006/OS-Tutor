"""Measure how many tokens a complete worked answer needs, per question type and size.

    python tools/token_budget.py

For each procedural kind, problem size is swept well past the evaluation sizes
(e.g. up to 30 processes, 100 page references). At every size, 40 random instances
are solved by the simulator, the worked solution is rendered exactly as the model
was trained to write it, and it is tokenised with the model's own tokenizer. The
MAX over instances is reported - a production budget must cover the worst case,
not the average. A 10% margin is added for the model's own wording variance.

Writes reports/token_budget.json and reports/TOKEN_BUDGET.md.
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from transformers import AutoTokenizer  # noqa: E402

from ostutor import config as C  # noqa: E402
from ostutor.simulators.banker import is_safe, need_matrix  # noqa: E402
from ostutor.simulators.generate import render_solution  # noqa: E402

N_SAMPLES = 40
MARGIN = 1.10
TRAIN_MAX = C.TRAIN_MAX_LENGTH


def names(n):
    return [f"P{i}" for i in range(n)]


def sched(rng, n):
    algo = rng.choice(["FCFS", "SJF", "SRTF", "RR", "PRIORITY", "PRIORITY_P"])
    t, procs = 0, []
    for i in range(n):
        t += rng.randint(0, 4)
        procs.append([f"P{i}", t, rng.randint(1, 12), rng.randint(1, 5)])
    return dict(kind="scheduling", algo=algo, quantum=rng.choice([2, 3, 4, 5]), procs=procs)


def sched_rr_long(rng, n):
    """Worst case: Round Robin, small quantum, long bursts - the most events."""
    t, procs = 0, []
    for i in range(n):
        t += rng.randint(0, 2)
        procs.append([f"P{i}", t, rng.randint(8, 20), 1])
    return dict(kind="scheduling", algo="RR", quantum=2, procs=procs)


def paging(rng, n):
    return dict(kind="paging", refs=[rng.randint(0, 9) for _ in range(n)],
                frames=rng.randint(3, 5), policy=rng.choice(["FIFO", "LRU", "OPT", "CLOCK"]))


def disk(rng, n):
    return dict(kind="disk", reqs=rng.sample(range(1, 199), n), head=rng.randint(0, 199),
                policy=rng.choice(["FCFS", "SSTF", "SCAN", "LOOK", "CSCAN", "CLOOK"]),
                size=200, direction=rng.choice(["up", "down"]))


def freespace(rng, n):
    return dict(kind="freespace", holes=[rng.randint(50, 600) for _ in range(n)],
                reqs=[rng.randint(40, 500) for _ in range(n)],
                policy=rng.choice(["FIRST", "BEST", "WORST"]))


def banker(rng, n, m=None):
    m = m or rng.randint(3, 4)
    for _ in range(500):
        maxm = [[rng.randint(0, 8) for _ in range(m)] for _ in range(n)]
        alloc = [[rng.randint(0, maxm[i][j]) for j in range(m)] for i in range(n)]
        avail = [rng.randint(1, 6) for _ in range(m)]
        if is_safe(avail, maxm, alloc)[0]:
            break
    return dict(kind="banker_safety", avail=avail, maxm=maxm, alloc=alloc, names=names(n))


def banker_req(rng, n):
    v = banker(rng, n)
    need = need_matrix(v["maxm"], v["alloc"])
    pid = rng.randrange(n)
    v.update(kind="banker_request", pid=pid,
             req=[rng.randint(0, max(x, 0)) for x in need[pid]])
    return v


def translate(rng, n):
    ps = rng.choice([512, 1024, 2048, 4096])
    table = [rng.randint(0, 63) for _ in range(n)]
    return dict(kind="translate", logical=rng.randrange(ps * n), page_size=ps, table=table)


SWEEPS = [
    # label, generator, sizes, what "size" means, size used in the eval suites
    ("CPU scheduling (any algorithm)", sched, [4, 6, 8, 10, 15, 20, 30], "processes", "4-10"),
    ("CPU scheduling, worst case (RR q=2, long bursts)", sched_rr_long, [4, 6, 8, 10, 15, 20],
     "processes", "-"),
    ("Page replacement", paging, [10, 15, 20, 30, 50, 75, 100], "references", "12-24"),
    ("Disk scheduling", disk, [5, 8, 10, 15, 20, 30, 50], "requests", "5-10"),
    ("Contiguous allocation (fit)", freespace, [3, 5, 8, 10, 15, 20], "holes = requests", "3-6"),
    ("Banker's safety", banker, [4, 5, 7, 10, 15, 20], "processes", "4-7"),
    ("Banker's request", banker_req, [4, 5, 7, 10, 15, 20], "processes", "4-7"),
    ("Address translation", translate, [4, 8, 16, 32], "page-table rows", "4-8"),
]


def main():
    tok = AutoTokenizer.from_pretrained(str(C.MODEL))
    ntok = lambda s: len(tok(s)["input_ids"])  # noqa: E731
    rng = random.Random(20260919)
    out, md = {}, []
    md += ["# Token budget per question type", "",
           f"Worst case over {N_SAMPLES} random instances per size, measured with the "
           "model's tokenizer on the exact worked-solution format it was trained on. "
           f"`budget` = worst case x {MARGIN} margin. Training covered answers up to "
           f"{TRAIN_MAX:,} tokens (question + answer).", ""]
    for label, gen, sizes, unit, eval_size in SWEEPS:
        rows = []
        for n in sizes:
            ans = [ntok(render_solution(gen(rng, n))) for _ in range(N_SAMPLES)]
            rows.append(dict(size=n, mean=round(sum(ans) / len(ans)), max=max(ans),
                             budget=int(max(ans) * MARGIN)))
        out[label] = dict(unit=unit, eval_size=eval_size, rows=rows)
        md += [f"## {label}", f"size = {unit}; evaluation suites use {eval_size}", "",
               "| size | mean tokens | worst case | budget (+10%) |", "|---|---|---|---|"]
        md += [f"| {r['size']} | {r['mean']:,} | {r['max']:,} | {r['budget']:,} |" for r in rows]
        md.append("")
        print(label, [(r["size"], r["max"]) for r in rows], flush=True)
    (C.REPORTS / "token_budget.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    (C.REPORTS / "TOKEN_BUDGET.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("written -> reports/TOKEN_BUDGET.md")


if __name__ == "__main__":
    main()
