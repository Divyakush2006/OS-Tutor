"""Measure the auto-mode router against labelled questions.

    python tools/test_router.py            # needs llama-server on :8081

Routing is the first decision the tutor makes, and a wrong one is expensive: send a
student who showed their working to the solver and they get handed the answer they were
supposed to derive; send a solvable procedure to the explainer and they get prose
instead of a verified number. So it is measured, not assumed.

Each case is (question, expected_mode). The expectations encode the product decisions:
  * a shown attempt is ALWAYS tutoring, however solvable the problem looks;
  * anything a simulator covers goes to the solver, so the numbers are exact;
  * an underspecified question goes to the solver, whose prompt asks for what is missing;
  * "why / which / compare" is analysis, not explanation;
  * a command request is shell;
  * anything off-topic still answers, but with the scope note.
"""
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "serve"))

import gateway  # noqa: E402

CASES = [
    # --- shown attempt -> tutoring (outranks everything) ---
    ("P1(0,7) P2(1,4) P3(2,9) with SRTF. My attempt: I used SJF and got 5.0. Is that right?",
     "ostutor-tutor"),
    ("I calculated 12 page faults for LRU on 7 0 1 2 0 3 with 3 frames. Am I correct?",
     "ostutor-tutor"),
    ("Where did I go wrong? I think best fit puts the 212 KB request in the 300 KB hole.",
     "ostutor-tutor"),
    ("Check my answer: total head movement 640 for SSTF from 53.", "ostutor-tutor"),
    ("My working gives a safe sequence of P0 P1 P2. Did I get this right?", "ostutor-tutor"),

    # --- solvable procedures -> verified solver ---
    ("Four jobs: P1 at 0 needs 8ms, P2 at 1 needs 4ms, P3 at 2 needs 9ms. SRTF average "
     "waiting time?", "ostutor-solve"),
    ("Reference string 7 0 1 2 0 3 0 4 with 3 frames, FIFO. How many page faults?",
     "ostutor-solve"),
    ("Disk queue 98 183 37 122, head at 53, SSTF. Total head movement?", "ostutor-solve"),
    ("Available (3,3,2), Allocation P0 (0,1,0) P1 (2,0,0), Max P0 (7,5,3) P1 (3,2,2). "
     "Is the state safe?", "ostutor-solve"),
    ("Holes 100, 500, 200 KB. Requests 212, 417 KB. Best fit placement?", "ostutor-solve"),
    ("1 KB pages, page table [3, 7, 2, 9]. Physical address for logical 2604?",
     "ostutor-solve"),
    ("TLB lookup 20ns, memory 100ns, hit ratio 80%. Effective access time?",
     "ostutor-solve"),
    ("How many processes does fork() called three times in a loop create?",
     "ostutor-solve"),

    # --- underspecified -> solver, which asks for the missing input ---
    ("Use best fit on holes of 120, 300, 80 and 500 KB and tell me where each process "
     "ends up.", "ostutor-solve"),
    ("How many page faults does LRU give for 1 2 3 4 1 2 5 1 2 3 4 5?", "ostutor-solve"),

    # --- open / comparative -> analysis ---
    ("Which scheduler would you choose for an interactive desktop and why?",
     "ostutor-analyze"),
    ("Compare paging and segmentation for a workload with many small objects.",
     "ostutor-analyze"),
    ("Why does a system start thrashing, and how would you diagnose it on a real server?",
     "ostutor-analyze"),
    ("Is SSTF a better disk scheduler than SCAN? Justify your answer.", "ostutor-analyze"),
    ("What are the trade-offs of a very small time quantum?", "ostutor-analyze"),

    # --- concept -> explanation ---
    ("What is a page fault?", "ostutor-explain"),
    ("Explain what a semaphore is.", "ostutor-explain"),
    ("Does LRU suffer from Belady's anomaly?", "ostutor-explain"),
    ("What does the dispatcher do?", "ostutor-explain"),
    ("Define internal fragmentation.", "ostutor-explain"),

    # --- shell ---
    ("Which command shows the processes using the most memory?", "ostutor-shell"),
    ("How do I kill a process by name in bash?", "ostutor-shell"),
    ("Give me a one-liner to find files over 100 MB.", "ostutor-shell"),
]


def main():
    ok, by_expected, wrong = 0, Counter(), []
    for question, expected in CASES:
        mode, why = gateway.route(question)
        by_expected[expected] += 1
        if mode == expected:
            ok += 1
        else:
            wrong.append((question, expected, mode, why))
    n = len(CASES)
    print(f"router accuracy: {ok}/{n} = {ok / n:.1%}\n")
    if wrong:
        print("misrouted:")
        for q, exp, got, why in wrong:
            print(f"  expected {exp:<17} got {got:<17} ({why})")
            print(f"      {q[:96]}")
    # The tutoring cases are the ones that must never be wrong.
    tutor_wrong = [w for w in wrong if w[1] == "ostutor-tutor"]
    print(f"\nshown-attempt cases misrouted: {len(tutor_wrong)} "
          f"(must be 0 - these decide whether a student is taught or handed the answer)")
    sys.exit(1 if tutor_wrong or ok / n < 0.85 else 0)


if __name__ == "__main__":
    main()
