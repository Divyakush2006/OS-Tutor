"""Page replacement, address translation and disk scheduling.

Disk scheduling is a documented gap: OSTEP's disk.py implements FIFO/SSTF/SATF/
BSATF, which are realistic but non-standard for exams. SCAN, C-SCAN, LOOK and
C-LOOK - the four every syllabus asks for - are absent. They are implemented here.

Every routine returns a step trace alongside the answer, so the target teaches the
procedure rather than just the number.
"""

# --------------------------------------------------------------- page replacement
def page_replacement(refs, frames, policy="LRU"):
    """FIFO / LRU / OPT / CLOCK. Returns dict with faults and a per-reference trace."""
    policy = policy.upper()
    mem, steps, faults = [], [], 0
    last_used, load_order = {}, []
    ref_bit, hand = {}, 0

    def nxt(p, t):
        try:
            return refs.index(p, t + 1)
        except ValueError:
            return 10 ** 9

    def at(p, t):
        return "never" if nxt(p, t) >= 10 ** 9 else "#" + str(nxt(p, t) + 1)

    for t, page in enumerate(refs):
        hit = page in mem
        victim = None
        opt_note = "-"
        # v3.0: every eviction carries its REASON as an explicit comparison
        # (LRU "last used 7@#1 < 0@#2 < 1@#3 -> least recent = 7"). v2.2 showed only
        # the resulting frames, and on free-worded questions the model evicted the
        # wrong page or never evicted at all.
        why = "-"
        if hit:
            if policy == "CLOCK":
                ref_bit[page] = 1
                why = f"hit, set bit of {page} to 1"
            else:
                why = f"{page} already in frames"
        else:
            faults += 1
            if len(mem) < frames:
                mem.append(page)
                load_order.append(page)
                ref_bit[page] = 1
                why = f"free frame ({len(mem)}/{frames} used)"
            else:
                if policy == "FIFO":
                    queue = " ".join(map(str, load_order))
                    victim = load_order.pop(0)
                    why = f"frames full; load order {queue} -> oldest = {victim}"
                elif policy == "LRU":
                    lu = sorted(mem, key=lambda p: last_used.get(p, -1))
                    victim = lu[0]
                    why = ("frames full; last used "
                           + " < ".join(f"{p}@#{last_used[p] + 1}" for p in lu)
                           + f" -> least recent = {victim}")
                elif policy == "OPT":
                    far = sorted(mem, key=lambda p: (-nxt(p, t), mem.index(p)))
                    victim = far[0]
                    why = ("frames full; next use " + " > ".join(f"{p}@{at(p, t)}" for p in far)
                           + f" -> farthest = {victim}")
                    opt_note = "next use " + ", ".join(f"{p}@{at(p, t)}" for p in mem)
                elif policy == "CLOCK":
                    sweep = []
                    while True:
                        cand = mem[hand % frames]
                        if ref_bit.get(cand, 0) == 0:
                            victim = cand
                            sweep.append(f"{cand}(0) evict")
                            hand = (hand + 1) % frames
                            break
                        sweep.append(f"{cand}(1) clear")
                        ref_bit[cand] = 0
                        hand = (hand + 1) % frames
                    why = "frames full; hand " + ", ".join(sweep)
                else:
                    raise ValueError(policy)
                mem[mem.index(victim)] = page
                if policy == "FIFO":
                    load_order.append(page)
                ref_bit[page] = 1
        last_used[page] = t
        # The frames are listed IN POLICY ORDER: FIFO oldest first, LRU least-recent
        # first, OPT in frame order, CLOCK with each reference bit and the hand.
        if policy == "FIFO":
            state = " ".join(map(str, load_order))
        elif policy == "LRU":
            state = " ".join(map(str, sorted(mem, key=lambda p: last_used.get(p, -1))))
        elif policy == "OPT":
            state = " ".join(map(str, mem))
        else:
            state = (" ".join(f"{p}({ref_bit.get(p, 0)})" for p in mem)
                     + (f", hand {mem[hand % frames]}" if len(mem) == frames else ""))
        steps.append(dict(t=t, page=page, hit=hit, victim=victim, frames=mem[:],
                          faults_so_far=faults, state=state, why=why, opt_note=opt_note,
                          text=(f"ref {page}: HIT, frames={mem}" if hit else
                                (f"ref {page}: FAULT, load into free frame, frames={mem}"
                                 if victim is None else
                                 f"ref {page}: FAULT, evict {victim}, frames={mem}"))))
    return dict(policy=policy, frames=frames, refs=refs, faults=faults,
                hits=len(refs) - faults,
                hit_ratio=round((len(refs) - faults) / len(refs), 4), steps=steps)


def beladys_anomaly(refs, f_small, f_large):
    """FIFO can fault MORE with more frames. A favourite exam trap."""
    a = page_replacement(refs, f_small, "FIFO")["faults"]
    b = page_replacement(refs, f_large, "FIFO")["faults"]
    return dict(small=f_small, large=f_large, faults_small=a, faults_large=b,
                anomaly=b > a)


# ------------------------------------------------------------ address translation
def translate(logical, page_size, page_table, phys_frames=None):
    """Single-level translation with full working shown."""
    page = logical // page_size
    offset = logical % page_size
    # Every product and difference is written out. The v2.0 form
    # "physical = 9 x 1024 + 118 = 9334" did the multiply-add in one jump, and the
    # fine-tuned model reproduced the pattern with wrong digits (9374).
    base = page * page_size
    steps = [f"page number = floor({logical} / {page_size}) = {page}  "
             f"(check: {page} x {page_size} = {base} <= {logical} < {base + page_size})",
             f"page offset = {logical} - {base} = {offset}"]
    if page >= len(page_table) or page_table[page] is None:
        steps.append(f"page {page} is not in the page table -> PAGE FAULT")
        return dict(logical=logical, page=page, offset=offset, frame=None,
                    physical=None, fault=True, steps=steps)
    frame = page_table[page]
    phys = frame * page_size + offset
    fbase = frame * page_size
    steps.append(f"page table[{page}] = frame {frame}")
    steps.append(f"frame base = {frame} x {page_size} = {fbase}")
    steps.append(f"physical address = {fbase} + {offset} = {phys}")
    return dict(logical=logical, page=page, offset=offset, frame=frame,
                physical=phys, fault=False, steps=steps)


def multilevel_translate(logical, page_size, bits_l1, bits_l2, addr_bits=32):
    offset_bits = page_size.bit_length() - 1
    off = logical & (page_size - 1)
    rest = logical >> offset_bits
    l2 = rest & ((1 << bits_l2) - 1)
    l1 = rest >> bits_l2
    return dict(logical=logical, offset_bits=offset_bits, l1_index=l1,
                l2_index=l2, offset=off,
                steps=[f"offset bits = log2({page_size}) = {offset_bits}",
                       f"offset      = {logical} & {page_size - 1} = {off}",
                       f"L2 index    = ({logical} >> {offset_bits}) & "
                       f"{(1 << bits_l2) - 1} = {l2}",
                       f"L1 index    = {logical} >> {offset_bits + bits_l2} = {l1}"])


# --------------------------------------------------------------- disk scheduling
def disk_schedule(requests, head, policy="SCAN", disk_size=200, direction="up"):
    """FCFS, SSTF, SCAN, C-SCAN, LOOK, C-LOOK.

    SCAN/C-SCAN/LOOK/C-LOOK are the four missing from OSTEP and required by
    essentially every syllabus.
    """
    policy = policy.upper()
    reqs = list(requests)
    order, steps, cur = [], [], head

    if policy == "FCFS":
        order = reqs[:]
    elif policy == "SSTF":
        pending = reqs[:]
        while pending:
            nxt = min(pending, key=lambda r: (abs(r - cur), r))
            below = [r for r in pending if r < cur]
            above = [r for r in pending if r >= cur]
            cands, dist = [], []
            if below:
                b = max(below); cands.append(f"below {b} ({cur} - {b} = {cur - b})"); dist.append(cur - b)
            if above:
                a = min(above); cands.append(f"above {a} ({a} - {cur} = {a - cur})"); dist.append(a - cur)
            if len(dist) == 2:
                if dist[0] == dist[1]:
                    cmpx = f"{dist[0]} = {dist[1]}, tie -> lower cylinder"
                else:
                    cmpx = f"{min(dist)} < {max(dist)}"
                steps.append(f"at {cur}: nearest {' vs '.join(cands)}; {cmpx} -> {nxt}")
            else:
                steps.append(f"at {cur}: only requests {'below' if below else 'above'} "
                             f"remain; nearest {cands[0]} -> {nxt}")
            order.append(nxt)
            pending.remove(nxt)
            cur = nxt
    else:
        up = sorted(r for r in reqs if r >= head)
        down = sorted((r for r in reqs if r < head), reverse=True)
        # State the split explicitly before the order: the fine-tuned model
        # produced non-monotonic SCAN orders (49 -> 32 -> 55) without it.
        steps.append(f"sorted requests: {sorted(reqs)}; below head {head}: "
                     f"{sorted(r for r in reqs if r < head)}; at/above head: {up}")
        way = ("UP, towards higher cylinders" if direction == "up"
               else "DOWN, towards cylinder 0")
        first, second = (up, down) if direction == "up" else (down, up)
        edge = disk_size - 1 if direction == "up" else 0
        other_edge = 0 if direction == "up" else disk_size - 1
        if policy == "SCAN":
            order = first + [edge] + second
            steps.append(f"SCAN, head moving {way}: service {first}, continue to the "
                         f"disk edge {edge}, reverse, then service {second}")
        elif policy == "LOOK":
            order = first + second
            steps.append(f"LOOK, head moving {way}: service {first}, reverse at the last "
                         f"request (not the edge), then service {second}")
        elif policy == "CSCAN":
            wrap = sorted(second) if direction == "up" else sorted(second, reverse=True)
            order = first + [edge, other_edge] + wrap
            steps.append(f"C-SCAN, head moving {way}: service {first}, go to the edge "
                         f"{edge}, jump to {other_edge}, continue {direction} through {wrap}")
        elif policy == "CLOOK":
            wrap = sorted(second) if direction == "up" else sorted(second, reverse=True)
            order = first + wrap
            steps.append(f"C-LOOK, head moving {way}: service {first}, jump to the "
                         f"farthest pending request, continue {direction} through {wrap}")
        else:
            raise ValueError(policy)

    cur, total, path = head, 0, [head]
    for tgt in order:
        d = abs(tgt - cur)
        steps.append(f"{cur} -> {tgt}: {max(cur, tgt)} - {min(cur, tgt)} = {d}; "
                     f"running total {total} + {d} = {total + d}")
        total += d
        cur = tgt
        path.append(tgt)
    serviced = [p for p in path[1:] if p in reqs]
    return dict(policy=policy, head=head, requests=reqs, order=order,
                path=path, total_head_movement=total, steps=steps,
                serviced=serviced)


# ----------------------------------------------------------- contiguous allocation
def fit_allocation(holes, requests, policy="FIRST"):
    """FIRST / BEST / WORST fit over a hole list."""
    policy = policy.upper()
    holes = [dict(id=i + 1, size=s, free=s) for i, s in enumerate(holes)]  # 1-based, as students number partitions
    steps, placed = [], []
    for req in requests:
        # v3.0: every hole is checked against the request in writing ("hole 2=200 <
        # 212 no"). v2.2 listed only the fitting holes and the model, on a free-worded
        # question, "fitted" 212 KB into a 200 KB hole.
        checks, cands = [], []
        for h in holes:
            if h["free"] >= req:
                cands.append(h)
                checks.append(f"hole {h['id']}={h['free']} >= {req} fits")
                if policy == "FIRST":
                    break
            else:
                checks.append(f"hole {h['id']}={h['free']} < {req} no")
        if not cands:
            steps.append(f"request {req}: {'; '.join(checks)} -> no hole fits -> must WAIT")
            placed.append(None)
            continue
        if policy == "FIRST":
            h = cands[0]
            choice = f"first fitting hole = hole {h['id']}"
        else:
            desc = policy == "WORST"
            order = sorted(cands, key=lambda x: ((-x["free"] if desc else x["free"]), x["id"]))
            h = order[0]
            chain = (" > " if desc else " < ").join(str(c["free"]) for c in order)
            choice = (f"{'largest' if desc else 'smallest'} fitting: {chain} -> hole {h['id']}")
        steps.append(f"request {req}: {'; '.join(checks)} -> {choice}; "
                     f"{h['free']} - {req} = {h['free'] - req}")
        h["free"] -= req
        placed.append(h["id"])
    return dict(policy=policy, placement=placed,
                remaining=[h["free"] for h in holes], steps=steps,
                external_fragmentation=sum(h["free"] for h in holes))
