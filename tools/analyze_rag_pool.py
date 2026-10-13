"""Analyse the candidate pool and compile the open OS corpus from it (G2; D-009).

    python tools/analyze_rag_pool.py            (after tools/fetch_rag_pool.py)

Reads every source in data/rag/pool/ plus Hailperin's book, cuts it into the same chunks
the retriever uses, and measures each chunk:

  quality     words, share of letters, share of code lines, stub documents
  relevance   cosine to the nearest of 40 OS syllabus topics (ACM CS2013 OS knowledge area,
              one description each), with all-MiniLM-L6-v2 - the retriever's own embedder
  topic       which syllabus topic it is nearest to
  duplicates  MinHash LSH over word 5-shingles, Jaccard >= 0.7, within and across sources;
              the copy from the higher-priority source is kept (book > Wikipedia >
              Wikibooks > Stack Exchange)
  coverage    topics x sources, and which short-answer questions (data/eval_rag/
              os_short_answer.jsonl, DEV half only) each source contains an answer to

Selection rules are written below as constants and fixed BEFORE the end-to-end runs. The
relevance floor is placed from the measured distributions: it keeps 95% of the chunks of
the two OS textbooks (the positive reference) and is reported with how much of each other
source it removes. The kept chunks are written back as documents, section by section,
into data/rag/open/docs/<source>/, and every document gets a manifest entry with its
licence and attribution. Report: reports/rag/open_pool_analysis.md (+ .json, + figures).
"""
from __future__ import annotations

import json
import re
import shutil
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ostutor.rag.corpus import MIN_WORDS, _sections, _windows, sha256  # noqa: E402
from ostutor.rag.ingest import add  # noqa: E402

POOL = ROOT / "data" / "rag" / "pool"
OPEN = ROOT / "data" / "rag" / "open"
QA = ROOT / "data" / "eval_rag" / "os_short_answer.jsonl"
REPORT = ROOT / "reports" / "rag"
FIGS = ROOT / "docs" / "shots"
SOURCES = ["hailperin", "csbu", "wikipedia", "wikibooks", "stackexchange"]
PRIORITY = {s: i for i, s in enumerate(SOURCES)}
TEXTBOOKS = ("hailperin", "csbu")

# ---- selection rules (fixed before any end-to-end measurement)
MIN_ALPHA = 0.60          # share of characters that are letters
MAX_CODE = 0.50           # share of lines that look like code
MIN_DOC_WORDS = 120       # stub documents are dropped whole
KEEP_TEXTBOOK = 0.95      # relevance floor keeps this share of textbook chunks
DUP_JACCARD = 0.70

# how passages from this corpus are named to the model and the student (not "course notes")
LABEL = dict(noun="reference passages",
             sources_heading="Sources (openly licensed references, not your course notes)",
             not_found="\n\n---\n> **Not found in the reference corpus.** This answer comes from the "
                       "tutor's general knowledge; check it against your textbook or ask your instructor.")

TOPICS = {
    "OS overview": "what an operating system is, its roles as resource manager and abstraction layer, kernel versus user programs",
    "OS structure": "monolithic kernels, microkernels, layered and modular kernel design, loadable kernel modules",
    "dual mode": "user mode and kernel mode, privileged instructions, the mode bit, protection rings",
    "system calls": "system calls, the trap instruction, system call numbers, the C library wrappers, the POSIX API",
    "interrupts": "hardware interrupts, exceptions, traps, interrupt handlers, interrupt vector table, the timer interrupt",
    "booting": "booting a computer, the bootloader, BIOS and UEFI, loading the kernel, the init process",
    "processes": "the process abstraction, process states, the process control block, process creation and termination",
    "process API": "fork, exec, wait and exit, zombie and orphan processes, parent and child processes",
    "context switch": "context switching between processes or threads, saving and restoring registers, dispatch latency",
    "threads": "threads versus processes, user-level and kernel-level threads, threading models, pthreads",
    "IPC": "inter-process communication: pipes, message queues, shared memory, sockets, message passing",
    "signals": "UNIX signals, signal handlers, SIGKILL, SIGTERM, SIGCHLD, sending and catching signals",
    "CPU scheduling": "CPU scheduling criteria, turnaround time, waiting time, response time, throughput, preemption",
    "scheduling algorithms": "FCFS, shortest job first, shortest remaining time, round robin, priority scheduling, aging",
    "MLFQ and fair share": "multilevel feedback queue, lottery and stride scheduling, proportional share, Linux CFS",
    "multiprocessor scheduling": "multiprocessor and multicore scheduling, processor affinity, load balancing",
    "real-time scheduling": "real-time systems, hard and soft deadlines, rate monotonic and earliest deadline first",
    "race conditions": "race conditions, critical sections, mutual exclusion, atomicity, the critical section problem",
    "locks": "locks, mutexes, spinlocks, test-and-set, compare-and-swap, ticket locks, Peterson's algorithm",
    "semaphores": "semaphores, counting and binary semaphores, wait and signal, P and V operations",
    "monitors and condition variables": "monitors, condition variables, wait and signal, Mesa and Hoare semantics",
    "classic sync problems": "producer-consumer bounded buffer, readers-writers, dining philosophers problems",
    "concurrency bugs": "concurrency bugs, atomicity violations, order violations, priority inversion, livelock",
    "deadlock": "deadlock, the four necessary conditions, resource allocation graphs, prevention, avoidance, detection, Banker's algorithm",
    "memory basics": "address spaces, logical and physical addresses, address binding, base and limit registers, swapping",
    "memory allocation": "contiguous memory allocation, first fit, best fit, worst fit, fragmentation, buddy and slab allocators, malloc",
    "segmentation": "segmentation, segment tables, segment base and bounds, segmentation with paging",
    "paging": "paging, pages and frames, page tables, address translation, page table entries, valid and dirty bits",
    "TLB and page tables": "translation lookaside buffer, TLB hits and misses, multi-level, hashed and inverted page tables",
    "virtual memory": "virtual memory, demand paging, page faults, swap space, copy-on-write, memory-mapped files",
    "page replacement": "page replacement algorithms FIFO, LRU, optimal, clock, second chance, Belady's anomaly",
    "thrashing and working set": "thrashing, the working set model, page fault frequency, frame allocation",
    "storage devices": "hard disks, seek time, rotational latency, solid state drives, flash memory, wear leveling",
    "disk scheduling": "disk scheduling algorithms FCFS, SSTF, SCAN, C-SCAN, LOOK, I/O scheduling",
    "RAID": "RAID levels, striping, mirroring, parity, reliability of storage",
    "I/O systems": "I/O devices, device drivers, polling, interrupt-driven I/O, direct memory access, buffering",
    "file system interface": "files, directories, paths, file descriptors, open, read, write, hard and symbolic links, permissions",
    "file system implementation": "inodes, file allocation methods, contiguous, linked, indexed, FAT, free space management, extents",
    "crash consistency": "file system consistency, journaling, fsck, log-structured file systems, crash recovery",
    "protection and security": "protection, access control lists, capabilities, least privilege, authentication, buffer overflow attacks",
    "virtualisation": "virtual machines, hypervisors, containers, namespaces, cgroups, trap and emulate",
}


def load_pool() -> list[dict]:
    docs = []
    for src in SOURCES:
        if src == "hailperin":
            recs = json.loads((ROOT / "data/rag/corpus/docs/online/sources.json").read_text(encoding="utf-8"))
            for r in recs:
                if r["id"].startswith("hail-"):
                    p = ROOT / "data/rag/corpus" / r["path"]
                    docs.append(dict(id=r["id"], source=src, title=r["title"], text=p.read_text(encoding="utf-8"),
                                     url=r["source"], licence=r["licence"], owner=r["owner"],
                                     attribution=r["permission"].replace("open licence; attribution: ", "")))
            continue
        pj = POOL / src / "pool.jsonl"
        if not pj.is_file():
            print(f"  (no pool for {src} yet)")
            continue
        for l in open(pj, encoding="utf-8"):
            r = json.loads(l)
            docs.append(dict(r, source=src, text=(POOL / r["path"]).read_text(encoding="utf-8")))
    return docs


def chunks_of(doc: dict) -> list[dict]:
    out = []
    for heading, body in _sections(doc["text"]):
        for win in _windows(body.split()):
            if len(win) >= MIN_WORDS:
                out.append(dict(doc=doc["id"], source=doc["source"], section=heading, text=" ".join(win),
                                raw=body))
    return out


def code_share(text: str) -> float:
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return 0.0
    codey = sum(bool(re.search(r"[;{}]\s*$|^\s*(#include|int |void |\$ |```|for \(|if \(|return )", l)) for l in lines)
    return codey / len(lines)


def alpha_share(text: str) -> float:
    t = re.sub(r"\s", "", text)
    return sum(c.isalpha() for c in t) / max(1, len(t))


def contains(text: str, answers: list[str]) -> bool:
    low = text.lower()
    for a in answers:
        if len(a) < 3 or a.isdigit():
            continue
        if re.search(r"(?<![a-z0-9])" + re.escape(a.lower()) + r"(?![a-z0-9])", low):
            return True
    return False


def histogram_svg(series: dict[str, list[float]], floor: float, path: Path) -> None:
    colours = {"hailperin": "#4472c4", "csbu": "#5b9bd5", "wikipedia": "#ed7d31", "wikibooks": "#ffc000",
               "stackexchange": "#70ad47"}
    W, H, L, R, T, B = 640, 280, 50, 16, 34, 58
    bins = np.linspace(0.0, 0.9, 46)
    X = lambda v: L + (W - L - R) * v / 0.9                                 # noqa: E731
    dens = {s: np.histogram(v, bins=bins)[0] / max(1, len(v)) for s, v in series.items() if v}
    ymax = max(d.max() for d in dens.values()) * 1.1
    Y = lambda v: T + (H - T - B) * (1 - v / ymax)                          # noqa: E731
    g = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Calibri, Carlito, Arial" font-size="11">',
         f'<rect width="{W}" height="{H}" fill="#fff" stroke="#d9d9d9"/>',
         f'<text x="{W / 2}" y="22" text-anchor="middle" font-size="14" fill="#595959">Relevance to the OS syllabus, by source</text>']
    for k in range(0, 10):
        v = k / 10
        g.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{T}" y2="{H - B}" stroke="#eeeeee"/>'
                 f'<text x="{X(v):.1f}" y="{H - B + 15}" text-anchor="middle" fill="#595959">{v:.1f}</text>')
    g.append(f'<text x="{(L + W - R) / 2}" y="{H - B + 31}" text-anchor="middle" fill="#595959">cosine to the nearest syllabus topic</text>')
    g.append(f'<line x1="{X(floor):.1f}" x2="{X(floor):.1f}" y1="{T}" y2="{H - B}" stroke="#c00000" stroke-dasharray="4 3"/>'
             f'<text x="{X(floor) + 4:.1f}" y="{T + 12}" fill="#c00000">floor {floor:.2f}</text>')
    centres = (bins[:-1] + bins[1:]) / 2
    for s, d in dens.items():
        pts = " ".join(f"{X(c):.1f},{Y(v):.1f}" for c, v in zip(centres, d))
        g.append(f'<polyline points="{pts}" fill="none" stroke="{colours[s]}" stroke-width="2"/>')
    x = L + 10
    for s in dens:
        g.append(f'<line x1="{x}" x2="{x + 18}" y1="{H - 10}" y2="{H - 10}" stroke="{colours[s]}" stroke-width="2.5"/>'
                 f'<text x="{x + 22}" y="{H - 6}" fill="#595959">{s}</text>')
        x += 112
    g.append("</svg>")
    path.write_text("".join(g), encoding="utf-8")


def main() -> None:
    from datasketch import MinHash, MinHashLSH
    from sentence_transformers import SentenceTransformer

    docs = load_pool()
    by_id = {d["id"]: d for d in docs}
    stub = {d["id"] for d in docs if len(d["text"].split()) < MIN_DOC_WORDS}
    ch = [c for d in docs if d["id"] not in stub for c in chunks_of(d)]
    print(f"pool: {len(docs)} documents ({len(stub)} stubs), {len(ch)} chunks", flush=True)

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu", local_files_only=True)
    temb = model.encode([f"{k}: {v}" for k, v in TOPICS.items()], normalize_embeddings=True)
    cemb = model.encode([c["section"] + ". " + c["text"] for c in ch], normalize_embeddings=True, batch_size=64,
                        show_progress_bar=False)
    sims = cemb @ temb.T
    names = list(TOPICS)
    for c, row in zip(ch, sims):
        c["relevance"] = float(row.max())
        c["topic"] = names[int(row.argmax())]
        c["alpha"] = alpha_share(c["text"])
        c["code"] = code_share(c["raw"])

    # relevance floor from the positive reference (the two OS textbooks)
    ref = sorted(c["relevance"] for c in ch if c["source"] in TEXTBOOKS)
    floor = round(ref[int((1 - KEEP_TEXTBOOK) * len(ref))], 3)

    # near-duplicates: keep the higher-priority source's copy
    lsh = MinHashLSH(threshold=DUP_JACCARD, num_perm=64)
    order = sorted(range(len(ch)), key=lambda i: (PRIORITY[ch[i]["source"]], i))
    dup_of = {}
    for i in order:
        words = ch[i]["text"].lower().split()
        m = MinHash(num_perm=64)
        for k in range(max(1, len(words) - 4)):
            m.update(" ".join(words[k:k + 5]).encode())
        hit = lsh.query(m)
        if hit:
            dup_of[i] = int(hit[0])
        else:
            lsh.insert(str(i), m)
    for i, c in enumerate(ch):
        reasons = []
        if c["alpha"] < MIN_ALPHA:
            reasons.append("low letter share")
        if c["code"] > MAX_CODE:
            reasons.append("mostly code")
        if c["relevance"] < floor:
            reasons.append("off-syllabus")
        if i in dup_of:
            reasons.append(f"duplicate of {ch[dup_of[i]]['source']}")
        c["drop"] = reasons
    kept = [c for c in ch if not c["drop"]]

    # ---- coverage of the dev short-answer questions, per source and in total
    qa = [json.loads(l) for l in open(QA, encoding="utf-8")]
    dev = [q for q in qa if q["split"] == "dev"]
    cover = {}
    for label, rows in [("pool (all chunks)", ch), ("kept", kept)] + \
            [(f"kept: {s}", [c for c in kept if c["source"] == s]) for s in SOURCES]:
        cover[label] = sum(any(contains(c["text"], q["answers"]) for c in rows) for q in dev)
    course_chunks = []
    try:
        from ostutor.rag.corpus import load_corpus
        cc, _ = load_corpus(ROOT / "data" / "rag" / "corpus")
        course_chunks = [c.text for c in cc]
        cover["course corpus (for comparison)"] = sum(any(contains(t, q["answers"]) for t in course_chunks) for q in dev)
    except Exception as e:                                    # the course corpus is optional here
        print("  course corpus not loaded:", e)

    # ---- per-source table
    rows = []
    for s in SOURCES:
        cs = [c for c in ch if c["source"] == s]
        if not cs:
            continue
        ks = [c for c in cs if not c["drop"]]
        drops = Counter(r.split(" of ")[0] for c in cs for r in c["drop"][:1])
        rows.append(dict(source=s, documents=sum(1 for d in docs if d["source"] == s),
                         stubs=sum(1 for d in docs if d["source"] == s and d["id"] in stub),
                         chunks=len(cs), kept=len(ks), words_kept=sum(len(c["text"].split()) for c in ks),
                         relevance_median=round(statistics.median(c["relevance"] for c in cs), 3),
                         drop_reasons=dict(drops)))
    topics = defaultdict(Counter)
    for c in kept:
        topics[c["topic"]][c["source"]] += 1

    # ---- write the compiled corpus: kept chunks regrouped into their sections
    if (OPEN / "docs").exists():
        shutil.rmtree(OPEN / "docs")
    (OPEN / "docs").mkdir(parents=True)
    keep_sections = defaultdict(list)
    for c in kept:
        if c["section"] not in keep_sections[c["doc"]]:
            keep_sections[c["doc"]].append(c["section"])
    man = OPEN / "manifest.json"
    man.write_text(json.dumps(dict(
        corpus="ostutor-open-os",
        note="Openly licensed OS texts only, compiled by tools/analyze_rag_pool.py (D-009). No course "
             "material. Each document keeps only the sections that passed the quality, relevance and "
             "duplicate filters.", label=LABEL, documents=[]), indent=1) + "\n", encoding="utf-8")
    written = []
    for doc_id, secs in keep_sections.items():
        d = by_id[doc_id]
        parts = [f"# {d['title']}"]
        for heading, body in _sections(d["text"]):
            if heading in secs:
                parts.append(f"\n## {heading}\n" if heading else "")
                parts.append(body)
        out = OPEN / "docs" / d["source"] / f"{doc_id}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(parts).strip() + "\n", encoding="utf-8")
        written.append((out, d))
    for out, d in written:
        add(OPEN, [str(out)], owner=d.get("owner", ""), source=d["url"], licence=d["licence"],
            permission=f"open licence; attribution: {d['attribution']}", id_prefix=d["source"])
    m = json.loads(man.read_text(encoding="utf-8"))
    for e in m["documents"]:
        d = by_id[Path(e["path"]).stem]
        e["id"], e["title"], e["kind"] = d["id"], d["title"], d["source"]
    man.write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    # ---- the same pool with NO filtering (stubs aside), as a control for the filters
    allc = OPEN.parent / "open_all"
    if (allc / "docs").exists():
        shutil.rmtree(allc / "docs")
    (allc / "docs").mkdir(parents=True)
    (allc / "manifest.json").write_text(json.dumps(dict(
        corpus="ostutor-open-os-unfiltered", note="Control corpus: every non-stub pool document, unfiltered "
        "(tools/analyze_rag_pool.py). Not for serving.", documents=[]), indent=1) + "\n", encoding="utf-8")
    for d in docs:
        if d["id"] in stub:
            continue
        out = allc / "docs" / d["source"] / f"{d['id']}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(d["text"], encoding="utf-8")
        add(allc, [str(out)], owner=d.get("owner", ""), source=d["url"], licence=d["licence"],
            permission=f"open licence; attribution: {d['attribution']}", id_prefix=d["source"])
    m = json.loads((allc / "manifest.json").read_text(encoding="utf-8"))
    for e in m["documents"]:
        d = by_id[Path(e["path"]).stem]
        e["id"], e["title"], e["kind"] = d["id"], d["title"], d["source"]
    (allc / "manifest.json").write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    # ---- report
    REPORT.mkdir(parents=True, exist_ok=True)
    FIGS.mkdir(parents=True, exist_ok=True)
    histogram_svg({s: [c["relevance"] for c in ch if c["source"] == s] for s in SOURCES}, floor,
                  FIGS / "pool_relevance.svg")
    res = dict(pool_documents=len(docs), pool_chunks=len(ch), stubs=len(stub), relevance_floor=floor,
               rules=dict(min_alpha=MIN_ALPHA, max_code=MAX_CODE, min_doc_words=MIN_DOC_WORDS,
                          keep_textbook=KEEP_TEXTBOOK, dup_jaccard=DUP_JACCARD),
               kept_chunks=len(kept), kept_documents=len(written), sources=rows,
               dev_answer_coverage=dict(n=len(dev), **cover),
               topics={t: dict(topics[t]) for t in TOPICS},
               thin_topics=[t for t in TOPICS if sum(topics[t].values()) < 15])
    (REPORT / "open_pool_analysis.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    md = ["# Open OS corpus: pool analysis", "",
          f"Pool: {len(docs)} documents, {len(ch):,} chunks after dropping {len(stub)} stub documents "
          f"(< {MIN_DOC_WORDS} words). Kept: **{len(kept):,} chunks in {len(written)} documents**.", "",
          f"Relevance floor **{floor}** = the {int((1 - KEEP_TEXTBOOK) * 100)}th percentile of the two OS "
          "textbooks' chunks (it keeps 95% of them).", "",
          "| Source | Documents | Stubs | Chunks | Kept | Words kept | Median relevance | Main drop reasons |",
          "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['source']} | {r['documents']:,} | {r['stubs']} | {r['chunks']:,} | {r['kept']:,} | "
                  f"{r['words_kept']:,} | {r['relevance_median']} | "
                  f"{', '.join(f'{k} {v}' for k, v in sorted(r['drop_reasons'].items(), key=lambda x: -x[1])) or '—'} |")
    md += ["", f"## Answer coverage (dev short-answer questions, n = {len(dev)})", "",
           "Questions for which at least one chunk contains an accepted answer — the ceiling for retrieval.", "",
           "| Chunks | Questions covered |", "|---|---|"]
    md += [f"| {k} | {v}/{len(dev)} |" for k, v in cover.items()]
    md += ["", "## Kept chunks per syllabus topic", "", "| Topic | " + " | ".join(SOURCES) + " | Total |",
           "|---|" + "---|" * (len(SOURCES) + 1)]
    for t in TOPICS:
        c = topics[t]
        md.append(f"| {t} | " + " | ".join(str(c.get(s, 0)) for s in SOURCES) + f" | {sum(c.values())} |")
    md += ["", f"Topics with fewer than 15 kept chunks: {', '.join(res['thin_topics']) or 'none'}"]
    (REPORT / "open_pool_analysis.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
