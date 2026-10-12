"""Formula-based OS numericals (v3.0).

The seven simulator kinds cover the classic trace problems. Exams (GATE, university
papers, Silberschatz end-of-chapter exercises) also ask a large family of
FORMULA problems that v2.x never trained on: effective access time with a TLB or
with page faults, address-bit and page-table sizing, multi-level paging depth,
disk access time, the minimum resources that make deadlock impossible, fork()
counting, semaphore values, internal fragmentation and multiprogramming CPU
utilisation.

Each kind has a generator with several wordings, a renderer that writes the
formula first and then ONE arithmetic operation per line (the v2.x error audit
found chained operations were where the model slipped), and exact expected
answers for the grader. Every value is computed with Fractions and only rounded
for display, so a rendered number can never disagree with the grader.
"""
import math
from fractions import Fraction as F

KINDS = ("eat_tlb", "eat_pagefault", "paging_bits", "multilevel_paging", "disk_access",
         "deadlock_min", "fork_count", "semaphore", "internal_frag", "cpu_util",
         "cache_eat")

OPEN = ["", "", "Question: ", "Solve: ", "Here is an exam question. ", "Q. "]


def fmt(x, dp=4):
    """Exact where possible, otherwise rounded - never '0.30000000000000004'."""
    x = F(x)
    if x.denominator == 1:
        return str(x.numerator)
    s = f"{float(x):.{dp}f}".rstrip("0").rstrip(".")
    return s


def _size(nbytes):
    for unit, p in (("GB", 30), ("MB", 20), ("KB", 10)):
        if nbytes >= 1 << p and nbytes % (1 << p) == 0:
            return f"{nbytes >> p} {unit}"
    return f"{nbytes} bytes"


# ======================================================================= generators
def gen(kind, rng):
    return GEN[kind](rng)


def g_eat_tlb(rng):
    t = rng.choice([0, 2, 5, 10, 20, 20, 30])
    m = rng.choice([50, 80, 100, 100, 120, 150, 200])
    h = rng.choice([F(80, 100), F(85, 100), F(90, 100), F(95, 100), F(98, 100), F(99, 100)])
    levels = rng.choice([1, 1, 1, 2, 3])
    inverse = rng.random() < 0.25
    lvl = ("a single-level page table" if levels == 1 else f"a {levels}-level page table")
    tl = ("TLB lookup time is negligible" if t == 0 else f"a TLB lookup takes {t} ns")
    v = dict(kind="eat_tlb", t=t, m=m, levels=levels, h=str(h), inverse=inverse)
    if inverse:
        hit, miss = t + m, t + (levels + 1) * m
        target = hit * h + miss * (1 - h)
        v["target"] = str(target)
        q = rng.choice([
            f"A paged system uses {lvl}; {tl} and a memory access takes {m} ns. What TLB "
            f"hit ratio is needed for an effective access time of {fmt(target)} ns?",
            f"With {lvl}, memory access time {m} ns and {tl}, find the minimum TLB hit "
            f"ratio that gives an effective memory access time of {fmt(target)} ns."])
    else:
        hp = rng.choice([f"{fmt(h * 100)}%", fmt(h)])
        q = rng.choice([
            f"A system uses {lvl}. {tl[0].upper() + tl[1:]}, a memory access takes {m} ns, "
            f"and the TLB hit ratio is {hp}. What is the effective memory access time?",
            f"Memory access time = {m} ns, TLB access time = {t} ns, hit ratio = {hp}, "
            f"{lvl}. Calculate the effective access time (EAT).",
            f"If the TLB hit rate is {hp}, {tl}, and main memory takes {m} ns per access "
            f"with {lvl}, what is the EAT?"])
    return v, rng.choice(OPEN) + q


def g_eat_pagefault(rng):
    ma = rng.choice([100, 120, 150, 200, 250])
    pf = rng.choice([5, 8, 10, 20, 25])
    inverse = rng.random() < 0.3
    v = dict(kind="eat_pagefault", ma=ma, pf=pf, inverse=inverse)
    if inverse:
        slow = rng.choice([10, 20, 5, 40])
        v["slow"] = slow
        q = rng.choice([
            f"Memory access time is {ma} ns and servicing a page fault takes {pf} ms. "
            f"What is the largest page-fault rate that keeps the slowdown below {slow}%?",
            f"With a {ma} ns memory access and an average page-fault service time of {pf} "
            f"ms, how small must the fault probability p be for the effective access time "
            f"to stay within {slow}% of {ma} ns?"])
    else:
        k = rng.choice([1000, 10000, 100000, 1000000, 2000, 5000])
        v["p"] = str(F(1, k))
        pw = rng.choice([f"1 in {k:,} accesses causes a page fault",
                         f"the page-fault rate is p = {fmt(F(1, k), 7)}",
                         f"one access out of every {k:,} causes a page fault"])
        q = rng.choice([
            f"Memory access time is {ma} ns, the page-fault service time is {pf} ms, and "
            f"{pw}. What is the effective access time?",
            f"Assume demand paging with ma = {ma} ns and a {pf} ms fault service time. If "
            f"{pw}, find the effective memory access time in nanoseconds."])
    return v, rng.choice(OPEN) + q


def g_paging_bits(rng):
    k = rng.choice([9, 10, 11, 12, 12, 13, 14])
    la = rng.choice([16, 20, 24, 32, 32, 36, 40, 48])
    pa = rng.choice([b for b in (16, 20, 24, 28, 30, 32, 34, 36) if b > k + 2])
    pte = rng.choice([2, 4, 4, 8])
    v = dict(kind="paging_bits", la=la, k=k, pa=pa, pte=pte)
    as_size = la <= 40 and rng.random() < 0.5
    v["la_as_size"] = as_size
    las = (f"a logical address space of {_size(1 << la)}" if as_size
           else f"a {la}-bit logical address")
    q = rng.choice([
        f"A system has {las}, a page size of {_size(1 << k)}, and {_size(1 << pa)} of "
        f"physical memory. Each page-table entry is {pte} bytes. Find the number of bits "
        f"in the page offset, the page number and the frame number, the number of pages, "
        f"and the size of the page table.",
        f"Consider paging with {_size(1 << k)} pages, {las} and {_size(1 << pa)} of RAM. "
        f"How many entries does the page table have, and how big is it with {pte}-byte "
        f"entries? Also give the offset and frame-number bits."])
    return v, rng.choice(OPEN) + q


def g_multilevel(rng):
    va = rng.choice([32, 32, 39, 40, 46, 48, 48, 57, 64])
    k = rng.choice([12, 12, 13, 14, 16])
    pte = rng.choice([4, 8, 8])
    v = dict(kind="multilevel_paging", va=va, k=k, pte=pte)
    q = rng.choice([
        f"A system has {va}-bit virtual addresses, {_size(1 << k)} pages and {pte}-byte "
        f"page-table entries. If every page table must fit in one page, how many levels "
        f"of paging are needed?",
        f"With a {va}-bit virtual address space, page size {_size(1 << k)} and PTE size "
        f"{pte} bytes, where each level's table occupies exactly one page, find the "
        f"number of page-table levels."])
    return v, rng.choice(OPEN) + q


def g_disk_access(rng):
    rpm = rng.choice([5400, 7200, 7200, 10000, 12000, 15000])
    seek = rng.choice([3, 4, 5, 6, 8, 9, 10, 12])
    rate = rng.choice([40, 50, 80, 100, 125, 128, 200, 256])
    kb = rng.choice([4, 8, 16, 32, 64, 128, 512])
    ctrl = rng.choice([0, 0, 0, F(1, 10), F(1, 2), 1])
    v = dict(kind="disk_access", rpm=rpm, seek=seek, rate=rate, kb=kb, ctrl=str(ctrl))
    ov = f" plus a controller overhead of {fmt(ctrl)} ms" if ctrl else ""
    q = rng.choice([
        f"A disk spins at {rpm:,} RPM with an average seek time of {seek} ms and a transfer "
        f"rate of {rate} MB/s (1 MB = 1024 KB). What is the average time to read a {kb} KB "
        f"block{ov}?",
        f"Average seek time {seek} ms, rotation speed {rpm:,} RPM, transfer rate {rate} MB/s "
        f"(take 1 MB = 1024 KB). Find the average access time for a {kb} KB transfer{ov}."])
    return v, rng.choice(OPEN) + q


def g_deadlock_min(rng):
    mode = rng.choice(["min", "min", "maxn", "list"])
    v = dict(kind="deadlock_min", mode=mode)
    if mode == "min":
        n, k = rng.randint(2, 12), rng.randint(2, 8)
        v.update(n=n, k=k)
        q = rng.choice([
            f"{n} processes share a resource type, and each process needs at most {k} "
            f"instances. What is the minimum number of instances that guarantees deadlock "
            f"can never occur?",
            f"A system has {n} processes, each requiring up to {k} units of the same "
            f"resource. Find the minimum number of units needed so the system is "
            f"deadlock-free."])
    elif mode == "maxn":
        k, r = rng.randint(2, 6), rng.randint(6, 40)
        v.update(k=k, r=r)
        q = (f"A system has {r} identical tape drives. Each process needs at most {k} drives. "
             f"What is the maximum number of processes that can share them without any "
             f"possibility of deadlock?")
    else:
        need = [rng.randint(2, 7) for _ in range(rng.randint(3, 5))]
        v.update(need=need)
        q = (f"Processes {', '.join(f'P{i + 1}' for i in range(len(need)))} need at most "
             f"{', '.join(map(str, need))} instances of a resource respectively. What is the "
             f"minimum number of instances that makes deadlock impossible?")
    return v, rng.choice(OPEN) + q


def g_fork(rng):
    mode = rng.choice(["total", "children", "print_after", "print_loop"])
    n = rng.randint(1, 6)
    v = dict(kind="fork_count", mode=mode, n=n)
    if mode in ("total", "children"):
        code = "\n".join(["fork();"] * n) if rng.random() < 0.5 else \
            f"for (int i = 0; i < {n}; i++)\n    fork();"
        ask = ("How many processes exist in total (including the original)?"
               if mode == "total" else "How many child processes are created?")
    elif mode == "print_after":
        code = "\n".join(["fork();"] * n) + '\nprintf("hello\\n");'
        ask = 'How many times is "hello" printed?'
    else:
        code = f'for (int i = 0; i < {n}; i++) {{\n    fork();\n    printf("x");\n}}'
        ask = 'How many times is "x" printed in total?'
    q = f"Consider this C code (assume every fork() succeeds):\n\n```c\n{code}\n```\n\n{ask}"
    return v, rng.choice(OPEN) + q


def g_semaphore(rng):
    s0 = rng.randint(0, 12)
    p, vv = rng.randint(0, 15), rng.randint(0, 15)
    v = dict(kind="semaphore", s0=s0, p=p, v=vv)
    q = rng.choice([
        f"A counting semaphore S is initialised to {s0}. Then {p} P (wait) operations and "
        f"{vv} V (signal) operations are performed on it. What is the final value of S?",
        f"S = {s0} initially. After {p} wait() and {vv} signal() calls, what is S? (Use the "
        f"convention that S may go negative; a negative value counts blocked processes.)"])
    return v, rng.choice(OPEN) + q


def g_internal_frag(rng):
    k = rng.choice([9, 10, 11, 12, 13])
    size = rng.randint(3 * (1 << k), 40 * (1 << k))
    if size % (1 << k) == 0:
        size += rng.randint(1, 100)
    v = dict(kind="internal_frag", k=k, size=size)
    q = rng.choice([
        f"A process of {size:,} bytes is loaded into a paged system with {1 << k}-byte pages. "
        f"How many pages does it need, and how much internal fragmentation results?",
        f"Page size = {_size(1 << k)}. A program needs {size:,} bytes. Find the number of "
        f"pages allocated and the internal fragmentation in the last page."])
    return v, rng.choice(OPEN) + q


def g_cpu_util(rng):
    pct = rng.choice([50, 60, 70, 75, 80, 80, 90])
    mode = rng.choice(["util", "util", "min_n"])
    v = dict(kind="cpu_util", pct=pct, mode=mode)
    if mode == "util":
        n = rng.randint(1, 8)
        v["n"] = n
        q = (f"Each process spends {pct}% of its time waiting for I/O. With {n} processes in "
             f"memory, what is the CPU utilisation (assume independent waits)?")
    else:
        target = rng.choice([80, 90, 95, 99])
        v["target"] = target
        q = (f"Processes spend {pct}% of their time in I/O wait. What is the minimum degree of "
             f"multiprogramming needed for at least {target}% CPU utilisation?")
    return v, rng.choice(OPEN) + q


def g_cache_eat(rng):
    c = rng.choice([1, 2, 5, 10, 20])
    m = rng.choice([50, 60, 100, 120, 200])
    h = rng.choice([F(80, 100), F(90, 100), F(95, 100), F(97, 100), F(99, 100)])
    v = dict(kind="cache_eat", c=c, m=m, h=str(h))
    q = rng.choice([
        f"A cache has an access time of {c} ns and main memory {m} ns. The hit ratio is "
        f"{fmt(h * 100)}%. On a miss the cache is checked first, then memory is accessed. "
        f"What is the average memory access time?",
        f"Cache access = {c} ns, memory access = {m} ns, hit ratio = {fmt(h)}. Assuming a "
        f"miss costs the cache lookup plus the memory access, find the effective access time."])
    return v, rng.choice(OPEN) + q


GEN = dict(eat_tlb=g_eat_tlb, eat_pagefault=g_eat_pagefault, paging_bits=g_paging_bits,
           multilevel_paging=g_multilevel, disk_access=g_disk_access,
           deadlock_min=g_deadlock_min, fork_count=g_fork, semaphore=g_semaphore,
           internal_frag=g_internal_frag, cpu_util=g_cpu_util, cache_eat=g_cache_eat)


# ======================================================================= solving
def solve(v):
    """Returns (formula_line, steps, answers) - answers is {label: exact value}."""
    k = v["kind"]
    if k == "eat_tlb":
        t, m, L, h = v["t"], v["m"], v["levels"], F(v["h"])
        hit = t + m
        pt = L * m
        miss = t + pt + m
        steps = [f"TLB hit: TLB + one memory access = {t} + {m} = {hit} ns",
                 f"TLB miss: {L} page-table access{'es' if L > 1 else ''} = {L} x {m} = {pt} ns",
                 f"miss time = TLB + page tables + data = {t} + {pt} = {t + pt}, "
                 f"{t + pt} + {m} = {miss} ns"]
        if v["inverse"]:
            target = F(v["target"])
            num = miss - target
            den = miss - hit
            steps += [f"EAT = h x {hit} + (1 - h) x {miss} = {miss} - h x ({miss} - {hit})",
                      f"{miss} - {hit} = {den}",
                      f"{miss} - {fmt(target)} = {fmt(num)}",
                      f"h = {fmt(num)} / {den} = {fmt(num / den)}"]
            return ("EAT = h x (t + m) + (1 - h) x (t + (L + 1) x m); solve for h",
                    steps, {"hit ratio": num / den})
        a = h * hit
        q = 1 - h
        b = q * miss
        steps += [f"h x hit = {fmt(h)} x {hit} = {fmt(a)}",
                  f"1 - h = 1 - {fmt(h)} = {fmt(q)}",
                  f"(1 - h) x miss = {fmt(q)} x {miss} = {fmt(b)}",
                  f"EAT = {fmt(a)} + {fmt(b)} = {fmt(a + b)} ns"]
        return ("EAT = h x (t + m) + (1 - h) x (t + (L + 1) x m)", steps, {"EAT (ns)": a + b})
    if k == "eat_pagefault":
        ma, pf = v["ma"], v["pf"]
        pfns = pf * 1_000_000
        steps = [f"page-fault service time = {pf} ms = {pf} x 1,000,000 = {pfns:,} ns"]
        if v["inverse"]:
            limit = F(ma * (100 + v["slow"]), 100)
            steps += [f"allowed EAT = {ma} x (1 + {v['slow']}/100) = {fmt(limit)} ns",
                      f"EAT = (1 - p) x {ma} + p x {pfns} = {ma} + p x ({pfns} - {ma})",
                      f"{pfns} - {ma} = {pfns - ma}",
                      f"{fmt(limit)} - {ma} = {fmt(limit - ma)}",
                      f"p < {fmt(limit - ma)} / {pfns - ma} = {fmt((limit - ma) / (pfns - ma), 9)}"]
            p = (limit - ma) / (pfns - ma)
            return ("EAT = (1 - p) x ma + p x (page-fault time) <= allowed", steps,
                    {"max page-fault rate p": p})
        p = F(v["p"])
        a = (1 - p) * ma
        b = p * pfns
        steps += [f"1 - p = 1 - {fmt(p, 7)} = {fmt(1 - p, 7)}",
                  f"(1 - p) x {ma} = {fmt(a, 4)} ns",
                  f"p x {pfns:,} = {fmt(b, 4)} ns",
                  f"EAT = {fmt(a, 4)} + {fmt(b, 4)} = {fmt(a + b, 4)} ns"]
        return ("EAT = (1 - p) x ma + p x (page-fault service time)", steps,
                {"EAT (ns)": a + b})
    if k == "paging_bits":
        la, kk, pa, pte = v["la"], v["k"], v["pa"], v["pte"]
        pn = la - kk
        fb = pa - kk
        pages = 1 << pn
        size = pages * pte
        steps = ([f"logical address bits = log2({_size(1 << la)}) = log2({1 << la:,}) = {la}"]
                 if v.get("la_as_size") else [f"logical address = {la} bits"])
        steps += [f"physical address bits = log2({_size(1 << pa)}) = log2({1 << pa:,}) = {pa}",
                  f"offset bits = log2(page size) = log2({1 << kk}) = {kk}",
                 f"page-number bits = {la} - {kk} = {pn}",
                 f"number of pages = 2^{pn} = {pages:,}",
                 f"frame-number bits = {pa} - {kk} = {fb}",
                 f"number of frames = 2^{fb} = {1 << fb:,}",
                 f"page table size = pages x PTE size = {pages:,} x {pte} = {size:,} bytes"
                 + (f" = {_size(size)}" if _size(size) != f"{size} bytes" else "")]
        return ("offset = log2(page size); pages = 2^(logical bits - offset); "
                "table = pages x PTE size", steps,
                {"offset bits": kk, "page-number bits": pn, "frame-number bits": fb,
                 "pages": pages, "page table bytes": size})
    if k == "multilevel_paging":
        va, kk, pte = v["va"], v["k"], v["pte"]
        per = (1 << kk) // pte
        bits = per.bit_length() - 1
        rest = va - kk
        levels = math.ceil(rest / bits)
        steps = [f"offset bits = log2({1 << kk}) = {kk}",
                 f"bits left for page numbers = {va} - {kk} = {rest}",
                 f"entries per page-table page = {1 << kk} / {pte} = {per}",
                 f"bits resolved per level = log2({per}) = {bits}",
                 f"levels = ceil({rest} / {bits}) = ceil({fmt(F(rest, bits), 3)}) = {levels}"]
        return ("levels = ceil((VA bits - offset bits) / log2(page size / PTE size))",
                steps, {"levels": levels})
    if k == "disk_access":
        rpm, seek, rate, kb, ctrl = v["rpm"], v["seek"], v["rate"], v["kb"], F(v["ctrl"])
        rot = F(60_000, rpm)
        lat = rot / 2
        mb = F(kb, 1024)
        xfer = mb / rate * 1000
        total = seek + lat + xfer + ctrl
        steps = [f"one rotation = 60,000 ms / {rpm:,} = {fmt(rot)} ms",
                 f"average rotational latency = {fmt(rot)} / 2 = {fmt(lat)} ms",
                 f"block size = {kb} KB / 1024 = {fmt(mb, 6)} MB",
                 f"transfer time = {fmt(mb, 6)} / {rate} x 1000 = {fmt(xfer)} ms",
                 f"total = seek + latency = {seek} + {fmt(lat)} = {fmt(seek + lat)}",
                 f"{fmt(seek + lat)} + transfer {fmt(xfer)} = {fmt(seek + lat + xfer)}"]
        if ctrl:
            steps.append(f"{fmt(seek + lat + xfer)} + controller {fmt(ctrl)} = {fmt(total)} ms")
        return ("access time = seek + rotational latency (half a rotation) + transfer "
                "(+ controller overhead)", steps, {"access time (ms)": total})
    if k == "deadlock_min":
        if v["mode"] == "min":
            n, kk = v["n"], v["k"]
            worst = n * (kk - 1)
            steps = [f"worst case: every process holds {kk} - 1 = {kk - 1} and waits for one more",
                     f"instances held in that worst case = {n} x {kk - 1} = {worst}",
                     f"one extra instance lets some process finish: {worst} + 1 = {worst + 1}"]
            return ("minimum = n x (k - 1) + 1", steps, {"minimum instances": worst + 1})
        if v["mode"] == "maxn":
            kk, r = v["k"], v["r"]
            nmax = (r - 1) // (kk - 1)
            steps = [f"deadlock-free when n x ({kk} - 1) + 1 <= {r}, i.e. n x {kk - 1} <= {r - 1}",
                     f"n <= {r - 1} / {kk - 1} = {fmt(F(r - 1, kk - 1), 3)}",
                     f"largest whole n = {nmax}"]
            return ("n x (k - 1) + 1 <= R", steps, {"maximum processes": nmax})
        need = v["need"]
        less = [x - 1 for x in need]
        steps = [f"each process can hold one less than its maximum: "
                 + ", ".join(f"{x} - 1 = {x - 1}" for x in need),
                 f"sum of (max - 1) = {' + '.join(map(str, less))} = {sum(less)}",
                 f"minimum = {sum(less)} + 1 = {sum(less) + 1}"]
        return ("minimum = sum of (max_i - 1) + 1", steps, {"minimum instances": sum(less) + 1})
    if k == "fork_count":
        n, mode = v["n"], v["mode"]
        total = 1 << n
        steps = [f"each fork() doubles the number of processes: 1 -> "
                 + " -> ".join(str(1 << i) for i in range(1, n + 1)),
                 f"after {n} fork() call{'s' if n > 1 else ''}: 2^{n} = {total} processes"]
        if mode == "total":
            return ("processes = 2^n", steps, {"processes": total})
        if mode == "children":
            steps.append(f"children = total - original = {total} - 1 = {total - 1}")
            return ("children = 2^n - 1", steps, {"child processes": total - 1})
        if mode == "print_after":
            steps.append(f"every one of the {total} processes runs printf once -> {total}")
            return ("prints = 2^n", steps, {"prints": total})
        per = [1 << i for i in range(1, n + 1)]
        steps = [f"iteration i = {i}: after fork() there are 2^{i + 1} = {per[i]} processes, "
                 f"each prints once -> {per[i]}" for i in range(n)]
        steps.append(f"total = {_rs(per)}")
        return ("prints = 2^1 + 2^2 + ... + 2^n = 2^(n+1) - 2", steps,
                {"prints": sum(per)})
    if k == "semaphore":
        s0, p, vv = v["s0"], v["p"], v["v"]
        after_p = s0 - p
        final = after_p + vv
        steps = [f"each P subtracts 1: {s0} - {p} = {after_p}",
                 f"each V adds 1: {after_p} + {vv} = {final}"]
        if final < 0:
            steps.append(f"S = {final} < 0: {-final} process{'es are' if final < -1 else ' is'} "
                         f"blocked on S")
        return ("S_final = S_initial - (number of P) + (number of V)", steps,
                {"final value": final})
    if k == "internal_frag":
        ps, size = 1 << v["k"], v["size"]
        pages = -(-size // ps)
        alloc = pages * ps
        steps = [f"pages = ceil({size:,} / {ps}) = ceil({fmt(F(size, ps), 3)}) = {pages}",
                 f"memory allocated = {pages} x {ps} = {alloc:,} bytes",
                 f"internal fragmentation = {alloc:,} - {size:,} = {alloc - size:,} bytes"]
        return ("pages = ceil(size / page size); fragmentation = pages x page size - size",
                steps, {"pages": pages, "internal fragmentation (bytes)": alloc - size})
    if k == "cpu_util":
        p = F(v["pct"], 100)
        if v["mode"] == "util":
            n = v["n"]
            pn = p ** n
            steps = [f"probability all {n} are waiting = {fmt(p)}^{n} = {fmt(pn, 6)}",
                     f"CPU utilisation = 1 - {fmt(pn, 6)} = {fmt(1 - pn, 6)} = "
                     f"{fmt((1 - pn) * 100, 4)}%"]
            return ("utilisation = 1 - p^n", steps, {"utilisation (%)": (1 - pn) * 100})
        target = F(v["target"], 100)
        n = 1
        while p ** n > 1 - target:
            n += 1
        bound = math.log(float(1 - target)) / math.log(float(p))
        steps = [f"need 1 - {fmt(p)}^n >= {fmt(target)}, i.e. {fmt(p)}^n <= {fmt(1 - target)}",
                 f"n >= log({fmt(1 - target)}) / log({fmt(p)}) = {bound:.3f}, so n = {n}"]
        if n > 1:
            steps.append(f"check n = {n - 1}: {fmt(p)}^{n - 1} = {fmt(p ** (n - 1), 6)} > "
                         f"{fmt(1 - target)} (not enough)")
        steps.append(f"check n = {n}: {fmt(p)}^{n} = {fmt(p ** n, 6)} <= {fmt(1 - target)} (enough)")
        return ("utilisation = 1 - p^n >= target", steps, {"minimum processes": n})
    if k == "cache_eat":
        c, m, h = v["c"], v["m"], F(v["h"])
        a = h * c
        miss = c + m
        q = 1 - h
        b = q * miss
        steps = [f"hit cost = {c} ns; miss cost = {c} + {m} = {miss} ns",
                 f"h x hit = {fmt(h)} x {c} = {fmt(a)}",
                 f"1 - h = {fmt(q)}",
                 f"(1 - h) x miss = {fmt(q)} x {miss} = {fmt(b)}",
                 f"average access time = {fmt(a)} + {fmt(b)} = {fmt(a + b)} ns"]
        return ("T = h x c + (1 - h) x (c + m)", steps, {"access time (ns)": a + b})
    raise ValueError(k)


def _rs(vals):
    acc, parts = vals[0], []
    for x in vals[1:]:
        parts.append(f"{acc} + {x} = {acc + x}")
        acc += x
    return ", ".join(parts) if parts else str(vals[0])


def render(v):
    formula, steps, answers = solve(v)
    lines = [f"**Formula:** {formula}", "", "**Working**", ""]
    lines += [f"- {s}" for s in steps]
    ans = ", ".join(f"{k} = {fmt(x, 9 if isinstance(x, F) and abs(x) < F(1, 100) else 4)}"
                    for k, x in answers.items())
    lines += ["", f"**Answer: {ans}**"]
    return "\n".join(lines)


def expected(v):
    return solve(v)[2]
