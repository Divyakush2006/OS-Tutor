"""Fetch the openly licensed OS sources that supplement the course notes (G2, D-007).

    python tools/fetch_open_os_sources.py            (needs network; CPU only)

Writes Markdown into data/rag/corpus/docs/online/ and a source record per document into
data/rag/corpus/docs/online/sources.json, which tools/build_rag_manifest.py turns into
manifest entries. Every document is pinned: Hailperin at a git commit, Wikipedia at a
revision id, so a rebuild fetches exactly the same text.

Only text whose licence allows reuse with attribution is fetched:
  * Max Hailperin, "Operating Systems and Middleware: Supporting Controlled Interaction",
    revised edition 1.3.1 - CC BY-SA 3.0 (stated in the book source and README).
  * English Wikipedia articles on OS topics - CC BY-SA 4.0.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "rag" / "corpus" / "docs" / "online"
HAIL_SRC = ROOT / "data" / "rag" / "corpus" / "src" / "hailperin" / "tex"
WIKI_SRC = ROOT / "data" / "rag" / "corpus" / "src" / "wikipedia"     # raw API replies, cached
HAIL_REPO = "Max-Hailperin/Operating-Systems-and-Middleware--Supporting-Controlled-Interaction"
HAIL_COMMIT = "3567f8f83eafec7c2238271bbd18bea5e0c4f22f"
HAIL_CHAPTERS = {  # file -> chapter title (the OS chapters; the middleware ones are left out)
    "intro": "Introduction", "threads": "Threads", "scheduling": "Scheduling",
    "synchronization": "Synchronization and Deadlocks", "vm": "Virtual Memory",
    "processes": "Processes and Protection", "persistence": "Files and Other Persistent Storage",
    "security": "Security",
}
UA = "OSTutor-RAG/1.0 (course project; contact via repository owner)"

WIKI = [
    "Operating system", "Kernel (operating system)", "System call", "Process (computing)",
    "Process state", "Process control block", "Context switch", "Thread (computing)",
    "Scheduling (computing)", "Round-robin scheduling", "Shortest job next",
    "Shortest remaining time", "Multilevel feedback queue", "Fixed-priority pre-emptive scheduling",
    "Lottery scheduling", "Starvation (computer science)", "Aging (scheduling)",
    "Inter-process communication", "Race condition", "Critical section", "Mutual exclusion",
    "Lock (computer science)", "Spinlock", "Semaphore (programming)", "Monitor (synchronization)",
    "Peterson's algorithm", "Dining philosophers problem", "Readers–writers problem",
    "Producer–consumer problem", "Deadlock (computer science)", "Banker's algorithm",
    "Memory management", "Memory paging", "Page table", "Translation lookaside buffer",
    "Virtual memory", "Demand paging", "Page fault", "Page replacement algorithm",
    "Bélády's anomaly", "Thrashing (computer science)", "Memory segmentation",
    "Fragmentation (computing)", "Memory management unit", "Copy-on-write", "Fork (system call)",
    "File system", "Inode", "File Allocation Table", "Hard link", "I/O scheduling",
    "Elevator algorithm", "Shortest seek first", "Direct memory access", "Interrupt",
]
DROP_SECTIONS = {"see also", "references", "external links", "notes", "further reading",
                 "bibliography", "sources", "citations", "footnotes"}


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(6):
        try:
            return urllib.request.urlopen(req, timeout=60).read()
        except urllib.error.HTTPError as e:
            if attempt == 5 or e.code not in (429, 500, 502, 503, 504):
                raise
            time.sleep(float(e.headers.get("Retry-After") or 0) or 5 * 2 ** attempt)
        except OSError:
            if attempt == 5:
                raise
            time.sleep(2 ** attempt)


def slug(title: str) -> str:
    import unicodedata
    title = re.sub("[‐-―]", "-", title)        # en/em dashes separate words
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")


# ---------------------------------------------------------------- Hailperin (LaTeX -> Markdown)

def strip_command(tex: str, name: str) -> str:
    """Remove every \\name{...} including its argument, matching nested braces."""
    out, i, pat = [], 0, "\\" + name + "{"
    while True:
        j = tex.find(pat, i)
        if j < 0:
            return "".join(out) + tex[i:]
        out.append(tex[i:j])
        k, depth = j + len(pat), 1
        while k < len(tex) and depth:
            depth += {"{": 1, "}": -1}.get(tex[k], 0)
            k += 1
        i = k


# The book's own vocabulary macros (os-book.tex), so pandoc expands defined terms instead
# of dropping them ("a mechanism, , that ...").
MACROS = r"""
\newcommand{\vocab}[1]{\emph{#1}}
\newcommand{\vocabs}[1]{\emph{#1s}}
\newcommand{\vocabes}[1]{\emph{#1es}}
\newcommand{\vocabing}[1]{\emph{#1ing}}
\newcommand{\vocabion}[1]{\emph{#1ion}}
\newcommand{\vocabyies}[1]{\emph{#1ies}}
\newcommand{\foldvocab}[2]{\emph{#1 #2}}
\newcommand{\foldvocabs}[2]{\emph{#1 #2s}}
\newcommand{\foldvocabes}[2]{\emph{#1 #2es}}
\newcommand{\foldvocabyies}[2]{\emph{#1 #2ies}}
\newcommand{\vocabindex}[2]{\emph{#1}}
\newcommand{\foldindex}[2]{}
"""


def latex_to_md(tex: str) -> str:
    import pypandoc
    tex = re.sub(r"\\(begin|end)\{chapterEnumerate\}", r"\\\1{enumerate}", tex)
    # figures, index entries and labels carry no prose; pandoc would leave stubs
    tex = re.sub(r"\\begin\{figure\*?\}.*?\\end\{figure\*?\}", "", tex, flags=re.S)
    for cmd in ("index", "label", "nocite"):
        tex = strip_command(tex, cmd)
    md = pypandoc.convert_text(MACROS + tex, "gfm", format="latex", extra_args=["--wrap=none"])
    md = re.sub(r"<[^>]+>", "", md)                       # html leftovers (anchors, spans)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip() + "\n"


def hailperin() -> list[dict]:
    recs = []
    for name, title in HAIL_CHAPTERS.items():
        path = HAIL_SRC / f"{name}.tex"
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(get(f"https://raw.githubusercontent.com/{HAIL_REPO}/{HAIL_COMMIT}/{name}.tex"))
        md = latex_to_md(path.read_text(encoding="utf-8"))
        # pandoc maps \chapter to "#" and \section to "##"; make sure the chapter heading exists
        if not md.lstrip().startswith("# "):
            md = f"# {title}\n\n" + md
        out = OUT / f"hailperin-{name}.md"
        out.write_text(md, encoding="utf-8")
        recs.append(dict(id=f"hail-{name}", title=f"Hailperin, Operating Systems and Middleware — {title}",
                         path=f"docs/online/{out.name}",
                         source=f"https://github.com/{HAIL_REPO}/blob/{HAIL_COMMIT}/{name}.tex",
                         owner="Max Hailperin", licence="CC BY-SA 3.0",
                         permission="open licence; attribution: Max Hailperin, Operating Systems and "
                                    "Middleware: Supporting Controlled Interaction, rev. ed. 1.3.1",
                         kind="online", converted="LaTeX -> Markdown (pandoc), figures removed"))
        print(f"  hailperin {name}: {len(md.split())} words", flush=True)
    return recs


# ---------------------------------------------------------------- Wikipedia (plain-text extract)

def wiki_md(title: str) -> tuple[str, int, str]:
    q = urllib.parse.urlencode(dict(action="query", format="json", prop="extracts|revisions",
                                    explaintext=1, exsectionformat="wiki", rvprop="ids",
                                    redirects=1, titles=title))
    cache = WIKI_SRC / f"{slug(title)}.json"
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(get(f"https://en.wikipedia.org/w/api.php?{q}"))
        time.sleep(1.5)
    d = json.loads(cache.read_text(encoding="utf-8"))
    page = next(iter(d["query"]["pages"].values()))
    text, revid, real = page["extract"], page["revisions"][0]["revid"], page["title"]
    out, keep = [f"# {real}", ""], True
    for line in text.splitlines():
        m = re.match(r"^(=+)\s*(.*?)\s*=+$", line)
        if m:
            level = len(m.group(1))
            if level == 2:
                keep = m.group(2).lower() not in DROP_SECTIONS
            if keep:
                out += ["", "#" * level + " " + m.group(2), ""]
            continue
        if keep:
            out.append(line)
    md = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip() + "\n"
    return md, revid, real


def wikipedia() -> list[dict]:
    recs = []
    for title in WIKI:
        md, revid, real = wiki_md(title)
        out = OUT / f"wiki-{slug(real)}.md"
        out.write_text(md, encoding="utf-8")
        recs.append(dict(id=f"wiki-{slug(real)}", title=f"Wikipedia — {real}", path=f"docs/online/{out.name}",
                         source=f"https://en.wikipedia.org/w/index.php?oldid={revid}",
                         owner="Wikipedia contributors", licence="CC BY-SA 4.0",
                         permission=f"open licence; attribution: Wikipedia contributors, \"{real}\", "
                                    f"revision {revid}",
                         kind="online", converted="MediaWiki plain-text extract -> Markdown headings; "
                                                  "references and link sections removed"))
        print(f"  wikipedia {real}: rev {revid}, {len(md.split())} words", flush=True)
    return recs


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    recs = hailperin() + wikipedia()
    (OUT / "sources.json").write_text(json.dumps(recs, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(recs)} documents -> {OUT}")


if __name__ == "__main__":
    sys.exit(main())
