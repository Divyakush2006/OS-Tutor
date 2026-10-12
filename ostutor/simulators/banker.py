"""Banker's algorithm: safety check and resource-request grant/deny.

Absent from OSTEP entirely and from every other openly-licensed OS simulator, yet
present in essentially every OS syllabus and exam. It is also the hardest common
question for a language model to answer unaided, because it is an iterative
search over a matrix with backtracking-free but order-sensitive state.

Both routines emit the full working: the Need matrix, every Work vector after a
grant, the safe sequence, and for a request the three feasibility tests in order.
"""


def need_matrix(maxm, alloc):
    return [[maxm[i][j] - alloc[i][j] for j in range(len(maxm[0]))]
            for i in range(len(maxm))]


def _cmp(a, b):
    """Component-wise comparison, written out: "1<=6, 0<=6, 6>5".

    Error audit of the first fine-tune: 22 wrong Banker's answers came from
    comparing whole vectors in one step ("Need [1,0,6,2] <= Work [6,6,5,11]",
    false because 6 > 5). Writing each position removes the silent check."""
    return ", ".join(f"{x}<={y}" if x <= y else f"{x}>{y}" for x, y in zip(a, b))


def is_safe(avail, maxm, alloc, names=None):
    """Returns (safe, sequence, steps). Steps record every Work update."""
    n, m = len(alloc), len(avail)
    names = names or [f"P{i}" for i in range(n)]
    need = need_matrix(maxm, alloc)
    work = list(avail)
    finish = [False] * n
    seq, steps = [], []

    steps.append(dict(kind="need", need=[row[:] for row in need],
                      text="Need = Max - Allocation"))
    steps.append(dict(kind="work", work=work[:],
                      text=f"Work = Available = {work}"))

    progress = True
    while progress:
        progress = False
        for i in range(n):
            if finish[i]:
                continue
            if all(need[i][j] <= work[j] for j in range(m)):
                before = work[:]
                for j in range(m):
                    work[j] += alloc[i][j]
                finish[i] = True
                seq.append(names[i])
                progress = True
                steps.append(dict(
                    kind="grant", proc=names[i], need=need[i][:],
                    work_before=before, alloc=alloc[i][:], work_after=work[:],
                    text=(f"{names[i]}: Need {need[i]} vs Work {before}: "
                          f"{_cmp(need[i], before)} -> all fit, run it. "
                          f"Work = {before} + Allocation {alloc[i]} = {work}")))
                break
            else:
                steps.append(dict(
                    kind="skip", proc=names[i], need=need[i][:], work=work[:],
                    text=(f"{names[i]}: Need {need[i]} vs Work {work}: "
                          f"{_cmp(need[i], work)} -> cannot run yet")))

    safe = all(finish)
    steps.append(dict(kind="verdict", safe=safe, sequence=seq[:],
                      text=("SAFE. Safe sequence: < " + ", ".join(seq) + " >") if safe
                      else ("UNSAFE - no safe sequence exists; processes "
                            + ", ".join(names[i] for i in range(n) if not finish[i])
                            + " can never finish")))
    return safe, seq, steps


def request(avail, maxm, alloc, pid, req, names=None):
    """Resource-request algorithm. Returns (granted, steps)."""
    n, m = len(alloc), len(avail)
    names = names or [f"P{i}" for i in range(n)]
    need = need_matrix(maxm, alloc)
    steps = []

    # Test 1: Request <= Need
    if any(req[j] > need[pid][j] for j in range(m)):
        steps.append(dict(kind="deny", test=1,
                          text=(f"Test 1 FAILS: Request {req} vs Need {need[pid]}: "
                                f"{_cmp(req, need[pid])} -> request exceeds Need "
                                f"for {names[pid]} -> error, the "
                                f"process has exceeded its declared maximum")))
        return False, steps
    steps.append(dict(kind="test", test=1,
                      text=(f"Test 1: Request {req} vs Need {need[pid]}: "
                            f"{_cmp(req, need[pid])} -> OK")))

    # Test 2: Request <= Available
    if any(req[j] > avail[j] for j in range(m)):
        steps.append(dict(kind="deny", test=2,
                          text=(f"Test 2 FAILS: Request {req} vs Available {avail}: "
                                f"{_cmp(req, avail)} -> {names[pid]} must WAIT (resources "
                                f"not currently free)")))
        return False, steps
    steps.append(dict(kind="test", test=2,
                      text=(f"Test 2: Request {req} vs Available {avail}: "
                            f"{_cmp(req, avail)} -> OK")))

    # Test 3: pretend to allocate, then check safety
    new_avail = [avail[j] - req[j] for j in range(m)]
    new_alloc = [row[:] for row in alloc]
    new_max = [row[:] for row in maxm]
    for j in range(m):
        new_alloc[pid][j] += req[j]
    steps.append(dict(kind="pretend", avail=new_avail, alloc=new_alloc[pid][:],
                      text=(f"Test 3: pretend to grant. Available = {avail} - "
                            f"{req} = {new_avail}; Allocation[{names[pid]}] = "
                            f"{new_alloc[pid]}. Now run the safety algorithm.")))

    safe, seq, safety_steps = is_safe(new_avail, new_max, new_alloc, names)
    steps += safety_steps
    if safe:
        steps.append(dict(kind="grant_final", sequence=seq,
                          text=(f"Resulting state is SAFE (sequence < {', '.join(seq)} >) "
                                f"-> GRANT the request")))
    else:
        steps.append(dict(kind="deny", test=3,
                          text=("Resulting state is UNSAFE -> DENY the request; "
                                f"{names[pid]} must wait and the old state is restored")))
    return safe, steps


def verify_sequence(seq, avail, maxm, alloc, names=None):
    """Validate ANY candidate safe sequence.

    Safe sequences are NOT unique. For the canonical Silberschatz state both
    < P1 P3 P4 P0 P2 > and < P1 P3 P0 P2 P4 > are correct. A grader that
    string-matches one published answer key will mark correct work wrong, so
    evaluation must replay the sequence and check feasibility at each step.

    Returns (valid, explanation).
    """
    n, m = len(alloc), len(avail)
    names = names or [f"P{i}" for i in range(n)]
    need = need_matrix(maxm, alloc)
    work = list(avail)
    if sorted(seq) != sorted(names):
        return False, f"sequence must contain each process exactly once: {seq}"
    for s in seq:
        i = names.index(s)
        if not all(need[i][j] <= work[j] for j in range(m)):
            return False, f"{s} cannot run: Need {need[i]} > Work {work}"
        work = [work[j] + alloc[i][j] for j in range(m)]
    return True, f"valid safe sequence; final Work = {work}"
