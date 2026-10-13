"""Fetch the CANDIDATE POOL for the open OS corpus (no course material; D-009).

    python tools/fetch_rag_pool.py [--sources csbu,wikibooks,wikipedia,stackexchange]

Everything lands in data/rag/pool/<source>/ as Markdown plus one pool.jsonl record per
document (title, url, licence, attribution, metadata). Nothing here is the corpus yet:
tools/analyze_rag_pool.py measures the pool and decides what goes in. Raw API replies are
cached in data/rag/pool/_cache/ so a rerun fetches nothing twice. Only openly licensed text:

  csbu           Ian Wienand, "Computer Science from the Bottom Up" - CC BY-SA 3.0 (front
                 matter of the book source), DocBook source pinned to a git commit
  wikibooks      Wikibooks "Operating System Design" - CC BY-SA 4.0
  wikipedia      every article in a set of OS categories plus the core list - CC BY-SA 4.0
  stackexchange  highest-voted Q&A on cs.stackexchange and unix.stackexchange for OS tags -
                 CC BY-SA 2.5 / 3.0 / 4.0 by post date (Stack Exchange's licensing page)
Hailperin's book, already fetched for the course corpus, is reused from
data/rag/corpus/docs/online/.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import html
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / "data" / "rag" / "pool"
CACHE = POOL / "_cache"
UA = "OSTutor-RAG/1.0 (university course project)"

CSBU_REPO, CSBU_COMMIT = "ianw/bottomupcs", "5ab2ce5c3bf39ed39b951add9e34a35f7bdbbec4"
CSBU_CHAPTERS = {"00": "General Unix and Advanced C", "01": "Binary and Number Representation",
                 "02": "Computer Architecture", "03": "The Operating System", "04": "The Process",
                 "05": "Virtual Memory", "06": "The Toolchain", "07": "Behind the process",
                 "08": "Dynamic Linking"}

WIKI_CATEGORIES = [
    "Operating system technology", "Process (computing)", "Processor scheduling algorithms",
    "Scheduling algorithms", "Memory management", "Virtual memory", "Memory management algorithms",
    "Concurrency control", "Concurrency (computer science)", "Inter-process communication",
    "Disk scheduling algorithms", "File system management", "Computer file systems",
    "Operating system security", "Interrupts", "Threads (computing)", "Deadlock",
    "Synchronization", "Real-time computing", "Operating system kernels", "Device drivers",
    "Computer memory", "Input/output", "Virtualization",
]

SE_TAGS = {
    "cs": ["operating-systems", "scheduling", "process-scheduling", "concurrency", "mutual-exclusion",
           "deadlocks", "virtual-memory", "memory-management", "memory-allocation", "paging",
           "synchronization", "semaphores", "cpu-cache", "file-systems", "threads", "parallel-computing"],
    "unix": ["process", "virtual-memory", "scheduling", "kernel", "signals", "fork", "inode",
             "filesystems", "swap", "linux-kernel", "ipc", "threads", "memory", "system-calls"],
}
SE_MIN_Q, SE_MIN_A = 3, 3          # question and best-answer score floors (votes as quality)


# ---------------------------------------------------------------- helpers

def get(url: str, cache_key: str | None = None) -> bytes:
    if cache_key:
        f = CACHE / cache_key
        if f.is_file():
            return f.read_bytes()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    for attempt in range(6):
        try:
            r = urllib.request.urlopen(req, timeout=60)
            data = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                data = gzip.decompress(data)
            break
        except urllib.error.HTTPError as e:
            if attempt == 5 or e.code not in (429, 500, 502, 503, 504):
                raise
            time.sleep(float(e.headers.get("Retry-After") or 0) or 5 * 2 ** attempt)
        except OSError:
            if attempt == 5:
                raise
            time.sleep(2 ** attempt)
    if cache_key:
        CACHE.mkdir(parents=True, exist_ok=True)
        (CACHE / cache_key).write_bytes(data)
    return data


def slug(title: str) -> str:
    title = re.sub("[‐-―]", "-", title)
    a = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", a.lower()).strip("-")[:80]


def key(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:16] + ".bin"


def html_to_md(h: str) -> str:
    """Stack Exchange post HTML to Markdown-ish text that keeps paragraphs, lists and code."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(h, "html.parser")
    for pre in soup.find_all("pre"):
        pre.replace_with("\n```\n" + pre.get_text() + "\n```\n")
    for li in soup.find_all("li"):
        li.insert_before("\n- ")
    for tag in soup.find_all(["p", "blockquote", "h1", "h2", "h3", "h4"]):
        tag.insert_after("\n\n")
    for img in soup.find_all("img"):
        img.replace_with("[image]")
    text = soup.get_text()
    return re.sub(r"\n{3,}", "\n\n", text).strip()


class Pool:
    def __init__(self, source: str):
        self.dir = POOL / source
        self.dir.mkdir(parents=True, exist_ok=True)
        self.source, self.rows = source, []

    def add(self, doc_id: str, title: str, md: str, **meta) -> None:
        path = self.dir / f"{doc_id}.md"
        path.write_text(md, encoding="utf-8")
        self.rows.append(dict(id=doc_id, source=self.source, title=title,
                              path=str(path.relative_to(POOL)).replace("\\", "/"), words=len(md.split()), **meta))

    def save(self) -> None:
        with open(self.dir / "pool.jsonl", "w", encoding="utf-8", newline="\n") as f:
            for r in self.rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"{self.source}: {len(self.rows)} documents, {sum(r['words'] for r in self.rows):,} words")


# ---------------------------------------------------------------- sources

def csbu() -> None:
    import pypandoc
    pool = Pool("csbu")
    for n, title in CSBU_CHAPTERS.items():
        url = f"https://raw.githubusercontent.com/{CSBU_REPO}/{CSBU_COMMIT}/input/chapter{n}/chapter{n}.xml"
        xml = get(url, key("csbu", n)).decode("utf-8")
        xml = re.sub(r"<xi:include[^>]*/>", "", xml)               # figures and code includes
        md = pypandoc.convert_text(xml, "gfm", format="docbook", extra_args=["--wrap=none"])
        md = re.sub(r"<[^>]+>", "", md)
        md = re.sub(r"\n{3,}", "\n\n", md).strip()
        if not md.startswith("# "):
            md = f"# {title}\n\n{md}"
        pool.add(f"csbu-{n}-{slug(title)}", f"Wienand, Computer Science from the Bottom Up — {title}", md,
                 url=f"https://github.com/{CSBU_REPO}/blob/{CSBU_COMMIT}/input/chapter{n}/chapter{n}.xml",
                 licence="CC BY-SA 3.0", owner="Ian Wienand",
                 attribution="Ian Wienand, Computer Science from the Bottom Up")
    pool.save()


def mediawiki_extract(api: str, title: str) -> tuple[str, int, str] | None:
    q = urllib.parse.urlencode(dict(action="query", format="json", prop="extracts|revisions", explaintext=1,
                                    exsectionformat="wiki", rvprop="ids", redirects=1, titles=title))
    d = json.loads(get(f"{api}?{q}", key(api, "x", title)))
    page = next(iter(d["query"]["pages"].values()))
    if "missing" in page or not page.get("extract"):
        return None
    out, keep = [f"# {page['title']}", ""], True
    drop = {"see also", "references", "external links", "notes", "further reading", "bibliography",
            "sources", "citations", "footnotes"}
    for line in page["extract"].splitlines():
        m = re.match(r"^(=+)\s*(.*?)\s*=+$", line)
        if m:
            if len(m.group(1)) == 2:
                keep = m.group(2).lower() not in drop
            if keep:
                out += ["", "#" * len(m.group(1)) + " " + m.group(2), ""]
            continue
        if keep:
            out.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip() + "\n", page["revisions"][0]["revid"], page["title"]


def wikibooks() -> None:
    api = "https://en.wikibooks.org/w/api.php"
    q = urllib.parse.urlencode(dict(action="query", format="json", list="allpages", apprefix="Operating System Design",
                                    aplimit=500, apnamespace=0))
    titles = [p["title"] for p in json.loads(get(f"{api}?{q}", key("wb", "pages")))["query"]["allpages"]]
    pool = Pool("wikibooks")
    for t in titles:
        r = mediawiki_extract(api, t)
        if not r:
            continue
        md, rev, real = r
        pool.add(f"wb-{slug(real)}", f"Wikibooks — {real}", md,
                 url=f"https://en.wikibooks.org/w/index.php?oldid={rev}", licence="CC BY-SA 4.0",
                 owner="Wikibooks contributors", attribution=f"Wikibooks contributors, \"{real}\", revision {rev}")
        time.sleep(0.2)
    pool.save()


def wikipedia() -> None:
    api = "https://en.wikipedia.org/w/api.php"
    titles: dict[str, set] = {}
    for cat in WIKI_CATEGORIES:
        cont = {}
        while True:
            q = urllib.parse.urlencode(dict(action="query", format="json", list="categorymembers",
                                            cmtitle=f"Category:{cat}", cmlimit=500, cmnamespace=0, **cont))
            d = json.loads(get(f"{api}?{q}", key("wp", "cat", cat, json.dumps(cont))))
            for m in d["query"]["categorymembers"]:
                titles.setdefault(m["title"], set()).add(cat)
            if "continue" not in d:
                break
            cont = {"cmcontinue": d["continue"]["cmcontinue"]}
        time.sleep(0.3)
    # the 55 hand-picked core articles of the course corpus, so the pool contains them too
    core = json.loads((ROOT / "data/rag/corpus/docs/online/sources.json").read_text(encoding="utf-8"))
    for r in core:
        if r["id"].startswith("wiki-"):
            titles.setdefault(r["title"].replace("Wikipedia — ", ""), set()).add("core list")
    # The TextExtracts endpoint is heavily rate-limited (HTTP 429 after a few dozen calls),
    # so wikitext is fetched 50 pages per request and converted with pandoc's MediaWiki reader.
    pool = Pool("wikipedia")
    seen = set()
    names = sorted(titles)
    for i in range(0, len(names), 50):
        batch = names[i:i + 50]
        q = urllib.parse.urlencode(dict(action="query", format="json", prop="revisions", rvprop="ids|content",
                                        rvslots="main", redirects=1, titles="|".join(batch)))
        d = json.loads(get(f"{api}?{q}", key("wp", "wt", *batch)))
        back = {r["to"]: r["from"] for r in d["query"].get("redirects", [])}
        for page in d["query"]["pages"].values():
            if "revisions" not in page:
                continue
            real, rev = page["title"], page["revisions"][0]["revid"]
            if real in seen:
                continue
            seen.add(real)
            md = wikitext_to_md(page["revisions"][0]["slots"]["main"]["*"], real)
            cats = titles.get(real) or titles.get(back.get(real, ""), set())
            pool.add(f"wp-{slug(real)}", f"Wikipedia — {real}", md, url=f"https://en.wikipedia.org/w/index.php?oldid={rev}",
                     licence="CC BY-SA 4.0", owner="Wikipedia contributors",
                     attribution=f"Wikipedia contributors, \"{real}\", revision {rev}", categories=sorted(cats))
        print(f"  wikipedia {min(i + 50, len(names))}/{len(names)}", flush=True)
        time.sleep(1)
    pool.save()


DROP_WIKI = {"see also", "references", "external links", "notes", "further reading", "bibliography",
             "sources", "citations", "footnotes"}


def wikitext_to_md(wt: str, title: str) -> str:
    """Wikitext -> Markdown: templates, references, files and categories removed; links kept as text."""
    import pypandoc
    wt = re.sub(r"<ref[^>/]*/>", "", wt)
    wt = re.sub(r"<ref[^>]*>.*?</ref>", "", wt, flags=re.S)
    wt = re.sub(r"<!--.*?-->", "", wt, flags=re.S)
    for _ in range(4):                                   # nested templates, innermost first
        wt = re.sub(r"\{\{[^{}]*\}\}", "", wt)
    wt = re.sub(r"\[\[(?:File|Image|Category):[^\]]*\]\]", "", wt, flags=re.I)
    try:
        md = pypandoc.convert_text(wt, "gfm", format="mediawiki", extra_args=["--wrap=none"])
    except RuntimeError:
        md = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", wt)
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)                 # images
    md = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", md)             # links -> text
    md = re.sub(r"<[^>]+>", "", md)
    out, keep = [f"# {title}", ""], True
    for line in md.splitlines():
        m = re.match(r"^(#+)\s+(.*)$", line)
        if m:
            level = len(m.group(1)) + 1                     # article title is level 1
            if len(m.group(1)) <= 2:                        # a top section (== X == in wikitext)
                keep = m.group(2).strip().lower() not in DROP_WIKI
            if keep:
                out.append("#" * level + " " + m.group(2).strip())
            continue
        if keep:
            out.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip() + "\n"


def se_licence(created: int) -> str:
    d = dt.datetime.fromtimestamp(created, dt.timezone.utc)
    if d < dt.datetime(2011, 4, 8, tzinfo=dt.timezone.utc):
        return "CC BY-SA 2.5"
    if d < dt.datetime(2018, 5, 2, tzinfo=dt.timezone.utc):
        return "CC BY-SA 3.0"
    return "CC BY-SA 4.0"


def stackexchange() -> None:
    api = "https://api.stackexchange.com/2.3"
    pool = Pool("stackexchange")
    for site, tags in SE_TAGS.items():
        qs = {}
        for tag in tags:
            for page in (1, 2):
                q = urllib.parse.urlencode(dict(order="desc", sort="votes", tagged=tag, site=site, pagesize=100,
                                                page=page, filter="withbody"))
                d = json.loads(get(f"{api}/questions?{q}", key("se", site, tag, str(page))))
                for x in d.get("items", []):
                    if x["score"] >= SE_MIN_Q and x.get("answer_count", 0):
                        qs[x["question_id"]] = x
                if d.get("backoff"):
                    time.sleep(d["backoff"])
                if not d.get("has_more"):
                    break
                time.sleep(0.5)
        ids = sorted(qs)
        answers: dict[int, list] = {}
        for i in range(0, len(ids), 100):
            chunk = ";".join(str(x) for x in ids[i:i + 100])
            for page in (1, 2, 3):
                q = urllib.parse.urlencode(dict(order="desc", sort="votes", site=site, pagesize=100, page=page,
                                                filter="withbody"))
                d = json.loads(get(f"{api}/questions/{chunk}/answers?{q}", key("se-a", site, chunk, str(page))))
                for a in d.get("items", []):
                    answers.setdefault(a["question_id"], []).append(a)
                if d.get("backoff"):
                    time.sleep(d["backoff"])
                if not d.get("has_more"):
                    break
                time.sleep(0.5)
        kept = 0
        for qid, x in qs.items():
            ans = sorted(answers.get(qid, []), key=lambda a: (-a.get("is_accepted", False), -a["score"]))
            ans = [a for a in ans if a["score"] >= SE_MIN_A][:2]
            if not ans:
                continue
            title = html.unescape(x["title"])
            parts = [f"# {title}", "", "## Question", "", html_to_md(x["body"])]
            lic = {se_licence(x["creation_date"])}
            who = [x.get("owner", {}).get("display_name", "unknown")]
            for k, a in enumerate(ans, 1):
                parts += ["", f"## Answer {k}" + (" (accepted)" if a.get("is_accepted") else ""), "", html_to_md(a["body"])]
                lic.add(se_licence(a["creation_date"]))
                who.append(html.unescape(a.get("owner", {}).get("display_name", "unknown")))
            md = "\n".join(parts).strip() + "\n"
            pool.add(f"se-{site}-{qid}", f"{site}.stackexchange — {title}", md,
                     url=x["link"], licence=" + ".join(sorted(lic)), owner="Stack Exchange contributors",
                     attribution=f"{', '.join(dict.fromkeys(html.unescape(w) for w in who))} on {site}.stackexchange.com, "
                                 f"question {qid}", score=x["score"], answer_scores=[a["score"] for a in ans],
                     tags=x.get("tags", []), site=site)
            kept += 1
        print(f"  {site}: {len(qs)} questions over score {SE_MIN_Q}, {kept} with a good answer", flush=True)
    pool.save()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default="csbu,wikibooks,wikipedia,stackexchange")
    a = ap.parse_args()
    for s in a.sources.split(","):
        {"csbu": csbu, "wikibooks": wikibooks, "wikipedia": wikipedia, "stackexchange": stackexchange}[s]()


if __name__ == "__main__":
    main()
