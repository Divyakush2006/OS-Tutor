"""Test the model the way a user does: through Open WebUI's own chat API
(browser -> Open WebUI :3000 -> gateway -> llama-server).

    serve/.venv-webui/Scripts/python serve/ui_test.py [--only NAME]

Numerical questions are written in free student wording (not the training
templates) with textbook numbers, and graded by the simulators. Concept, tutoring
and edge-case answers are saved for review. Everything goes to
reports/ui_test.json and reports/UI_TEST.md.
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ostutor.evaluation.harness import grade  # noqa: E402

UI = "http://localhost:3000"
SIL = [["P1", 0, 8, 1], ["P2", 1, 4, 1], ["P3", 2, 9, 1], ["P4", 3, 5, 1]]
REF = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]
BK = dict(avail=[3, 3, 2], names=["P0", "P1", "P2", "P3", "P4"],
          alloc=[[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]],
          maxm=[[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]])
DQ = [98, 183, 37, 122, 14, 124, 65, 67]

SOLVE = [
    ("srtf_textbook", "I have four processes. P1 arrives at time 0 and needs 8 ms, P2 arrives at 1 "
     "and needs 4 ms, P3 arrives at 2 and needs 9 ms, P4 arrives at 3 and needs 5 ms. What is the "
     "average waiting time with SRTF (preemptive SJF)?",
     dict(kind="scheduling", algo="SRTF", quantum=2, procs=SIL)),
    ("rr_q4", "Three processes all arrive at time 0: P1 with a burst of 24 ms, P2 with 3 ms and P3 "
     "with 3 ms. Using Round Robin with a time quantum of 4 ms, find the average waiting time and "
     "the average turnaround time.",
     dict(kind="scheduling", algo="RR", quantum=4,
          procs=[["P1", 0, 24, 1], ["P2", 0, 3, 1], ["P3", 0, 3, 1]])),
    ("priority_np", "Five processes arrive at time 0 in the order P1..P5 with burst times 10, 1, 2, "
     "1, 5 and priorities 3, 1, 4, 5, 2 (a smaller number means higher priority). Using "
     "non-preemptive priority scheduling, what is the average waiting time?",
     dict(kind="scheduling", algo="PRIORITY", quantum=2,
          procs=[["P1", 0, 10, 3], ["P2", 0, 1, 1], ["P3", 0, 2, 4], ["P4", 0, 1, 5],
                 ["P5", 0, 5, 2]])),
    ("fifo_paging", "For the reference string 7 0 1 2 0 3 0 4 2 3 0 3 2 1 2 0 1 7 0 1 with 3 frames, "
     "how many page faults does FIFO replacement cause?",
     dict(kind="paging", refs=REF, frames=3, policy="FIFO")),
    ("lru_paging", "Same reference string 7 0 1 2 0 3 0 4 2 3 0 3 2 1 2 0 1 7 0 1 and 3 frames: how "
     "many page faults with LRU?",
     dict(kind="paging", refs=REF, frames=3, policy="LRU")),
    ("opt_paging", "How many page faults does the optimal (OPT) algorithm give for 7 0 1 2 0 3 0 4 2 "
     "3 0 3 2 1 2 0 1 7 0 1 with 3 frames?",
     dict(kind="paging", refs=REF, frames=3, policy="OPT")),
    ("banker_safe", "A system has resources A, B, C with Available = (3, 3, 2). Allocation: P0 (0,1,0), "
     "P1 (2,0,0), P2 (3,0,2), P3 (2,1,1), P4 (0,0,2). Max: P0 (7,5,3), P1 (3,2,2), P2 (9,0,2), "
     "P3 (2,2,2), P4 (4,3,3). Is the system in a safe state? If so, give a safe sequence.",
     dict(kind="banker_safety", **BK)),
    ("banker_request", "In that same system (Available (3,3,2); Allocation P0 (0,1,0), P1 (2,0,0), "
     "P2 (3,0,2), P3 (2,1,1), P4 (0,0,2); Max P0 (7,5,3), P1 (3,2,2), P2 (9,0,2), P3 (2,2,2), "
     "P4 (4,3,3)), P1 requests (1,0,2). Can the request be granted immediately?",
     dict(kind="banker_request", pid=1, req=[1, 0, 2], **BK)),
    ("disk_sstf", "The disk head is at cylinder 53 on a 200-cylinder disk (0-199). The queue is 98, "
     "183, 37, 122, 14, 124, 65, 67. What is the total head movement with SSTF?",
     dict(kind="disk", reqs=DQ, head=53, policy="SSTF", size=200, direction="up")),
    ("disk_scan", "Same queue 98, 183, 37, 122, 14, 124, 65, 67 with the head at 53 on a 0-199 disk, "
     "moving towards 0. What is the total head movement with SCAN?",
     dict(kind="disk", reqs=DQ, head=53, policy="SCAN", size=200, direction="down")),
    ("disk_clook", "Head at 53 on a 0-199 disk, moving towards higher cylinders, queue 98, 183, 37, "
     "122, 14, 124, 65, 67. Give the service order and total head movement for C-LOOK.",
     dict(kind="disk", reqs=DQ, head=53, policy="CLOOK", size=200, direction="up")),
    ("translate", "Pages are 4 KB (4096 bytes). The page table maps page 0 to frame 5, page 1 to "
     "frame 6, page 2 to frame 1 and page 3 to frame 2. What physical address does logical "
     "address 9000 map to?",
     dict(kind="translate", logical=9000, page_size=4096, table=[5, 6, 1, 2])),
    ("best_fit", "Memory partitions are 100 KB, 500 KB, 200 KB, 300 KB and 600 KB, in that order. "
     "Processes of 212 KB, 417 KB, 112 KB and 426 KB arrive in that order. Where does best-fit "
     "place each one?",
     dict(kind="freespace", holes=[100, 500, 200, 300, 600], reqs=[212, 417, 112, 426],
          policy="BEST")),
    ("worst_fit", "Same partitions 100, 500, 200, 300, 600 KB and processes 212, 417, 112, 426 KB. "
     "Where does worst-fit place each process?",
     dict(kind="freespace", holes=[100, 500, 200, 300, 600], reqs=[212, 417, 112, 426],
          policy="WORST")),
]

REVIEW = [
    ("explain_thrashing", "ostutor-explain", ["What is thrashing and how can an OS prevent it?"]),
    ("explain_deadlock", "ostutor-explain",
     ["What are the four necessary conditions for deadlock? Give an example of each."]),
    ("explain_paging_vs_seg", "ostutor-explain",
     ["Compare paging and segmentation. When would you prefer each?"]),
    ("tutor_fcfs", "ostutor-tutor",
     ["I calculated the FCFS average waiting time for bursts 24, 3, 3 (all arriving at 0) as 17. "
      "Is that right?"]),
    ("edge_missing_input", "ostutor-solve",
     ["Apply first-fit to memory holes of 100, 500, 200 and 300 KB. Which hole serves each request?"]),
]


def token():
    req = urllib.request.Request(f"{UI}/api/v1/auths/signin", method="POST",
                                 data=b'{"email":"","password":""}',
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))["token"]


def chat(tok, model, messages):
    req = urllib.request.Request(f"{UI}/api/chat/completions", method="POST",
                                 data=json.dumps(dict(model=model, messages=messages,
                                                      stream=False)).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {tok}"})
    t0 = time.time()
    d = json.load(urllib.request.urlopen(req, timeout=1800))
    return d["choices"][0]["message"]["content"], round(time.time() - t0, 1), \
        (d.get("usage") or {}).get("completion_tokens")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--models", default="ostutor-solve,qwen3-4b-base")
    a = ap.parse_args()
    tok = token()
    out = dict(solve=[], review=[])
    models = a.models.split(",")
    for name, q, v in SOLVE:
        if a.only and a.only not in name:
            continue
        for m in models:
            text, secs, n = chat(tok, m, [dict(role="user", content=q)])
            g = grade(dict(verify=v), text)
            out["solve"].append(dict(name=name, model=m, correct=g["final_correct"],
                                     expected=g.get("expected"), got=g.get("got"),
                                     detail=g.get("detail"), seconds=secs, tokens=n,
                                     question=q, answer=text))
            print(f"{name:16s} {m:15s} {'OK ' if g['final_correct'] else 'BAD'} "
                  f"exp={g.get('expected')} got={g.get('got')} {secs}s {n} tok", flush=True)
    for name, m, turns in REVIEW:
        if a.only and a.only not in name:
            continue
        text, secs, n = chat(tok, m, [dict(role="user", content=turns[0])])
        out["review"].append(dict(name=name, model=m, seconds=secs, tokens=n,
                                  question=turns[0], answer=text))
        print(f"{name:22s} {m:15s} {secs}s {n} tok", flush=True)

    (ROOT / "reports" / "ui_test.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    md = ["# UI test (through Open WebUI)", ""]
    for m in models:
        rows = [r for r in out["solve"] if r["model"] == m]
        if rows:
            md.append(f"- **{m}**: {sum(r['correct'] for r in rows)}/{len(rows)} correct")
    md += ["", "| question | model | correct | expected | got | seconds |", "|---|---|---|---|---|---|"]
    md += [f"| {r['name']} | {r['model']} | {'yes' if r['correct'] else 'no'} | {r['expected']} "
           f"| {r['got']} | {r['seconds']} |" for r in out["solve"]]
    for r in out["solve"] + out["review"]:
        md += ["", f"## {r['name']} - {r['model']}", "", f"**Q:** {r['question']}", "", r["answer"]]
    (ROOT / "reports" / "UI_TEST.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("written -> reports/UI_TEST.md")


if __name__ == "__main__":
    main()
