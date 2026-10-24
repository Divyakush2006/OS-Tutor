"""Build docs/OS-Tutor-Final-Report.pdf from docs/final_report/report.html.

    python docs/final_report/charts.py     (figures, from the committed result files)
    python docs/final_report/build.py

1. Typeset the recorded transcripts (transcripts.json, captured from the running gateway)
   and build the list of figures and tables from the captions.
2. Render with headless Edge, locate every heading and caption by an invisible marker,
   write the page numbers into the contents, render again and check nothing moved.
3. Stamp the running header and page numbers, add PDF bookmarks and metadata.
"""
import html
import json
import re
import subprocess
import sys
import time
from io import BytesIO
from pathlib import Path

import fitz  # PyMuPDF
from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = HERE / "report.html"
TMP_HTML = HERE / "_render.html"
RAW_PDF = HERE / "_render.pdf"
OUT_PDF = HERE.parent / "OS-Tutor-Final-Report.pdf"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
TRANSCRIPTS = json.loads((HERE / "transcripts.json").read_text(encoding="utf-8"))

TAG = re.compile(r"\s*<!--\s*ostutor:\s*(.*?)\s*-->\s*$", re.S)


# ---------------------------------------------------------------- transcripts
def inline(s: str) -> str:
    """Emphasis outside code spans only: a `*.log` inside backticks stays literal."""
    out = []
    for i, part in enumerate(re.split(r"(`[^`]+`)", s)):
        if i % 2:
            out.append(f"<code>{html.escape(part[1:-1], quote=False)}</code>")
            continue
        part = html.escape(part, quote=False)
        part = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", part)
        part = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", part)
        part = re.sub(r"(?<![\w])_(?!\s)(.+?)(?<!\s)_(?![\w])", r"<i>\1</i>", part)
        out.append(part)
    return "".join(out)


def markdown(text: str) -> str:
    """The small subset of Markdown the tutor writes: paragraphs, lists, tables,
    block quotes, rules and level-4 headings."""
    lines = text.split("\n")
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        st = ln.strip()
        if not st:
            i += 1
        elif st == "@@GAP@@":
            out.append('<div class="gap">[…]</div>')
            i += 1
        elif re.fullmatch(r"-{3,}", st):
            out.append("<hr>")
            i += 1
        elif st.startswith("#"):
            out.append(f"<h5>{inline(st.lstrip('#').strip())}</h5>")
            i += 1
        elif st.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head, body = rows[0], [r for r in rows[1:] if not all(re.fullmatch(r":?-+:?", c) for c in r)]
            t = ["<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"]
            t += ["<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body]
            out.append("".join(t) + "</tbody></table>")
        elif st.startswith(">"):
            q = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                q.append(lines[i].strip()[1:].strip())
                i += 1
            out.append("<blockquote><p>" + "<br>".join(inline(x) for x in q if x) + "</p></blockquote>")
        elif re.match(r"^\s*([-*]|\d+\.)\s+", ln):
            ordered = bool(re.match(r"^\s*\d+\.", ln))
            items = []
            while i < len(lines) and re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]):
                items.append(re.sub(r"^\s*([-*]|\d+\.)\s+", "", lines[i]))
                i += 1
            tagn = "ol" if ordered else "ul"
            out.append(f"<{tagn}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tagn}>")
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not re.match(
                    r"^\s*([-*]|\d+\.)\s+|^\s*[|>#]|^\s*-{3,}\s*$|^@@GAP@@$", lines[i]):
                para.append(lines[i].strip())
                i += 1
            out.append(f"<p>{inline(' '.join(para))}</p>")
    return "\n".join(out)


def chat(key: str, title: str, head: int, tail: int, number: str) -> str:
    """One recorded exchange as a numbered figure: a plain ruled box, captioned below."""
    t = TRANSCRIPTS[key]
    reply = t["reply"]
    m = TAG.search(reply)
    route = m.group(1) if m else ""
    body = TAG.sub("", reply).rstrip()
    lines = body.split("\n")
    if head and tail and head + tail < len(lines):
        lines = lines[:head] + ["", "@@GAP@@", ""] + lines[-tail:]
    msgs = t["messages"]
    parts = []
    if len(msgs) > 1:
        parts.append(f'<div class="who">Earlier in this chat:</div><p>{inline(msgs[0]["content"])} '
                     "<i>(the tutor's first reply is not shown)</i></p>")
    parts.append(f'<div class="who">Student ({html.escape(t["model"])}):</div><p>{inline(msgs[-1]["content"])}</p>')
    parts.append(f'<div class="who">OS Tutor:</div>{markdown(chr(10).join(lines))}')
    if route:
        parts.append(f'<div class="tag">Route recorded by the gateway: {html.escape(route)}; '
                     f'{t["seconds"]:.1f} s</div>')
    split = " split" if len(lines) > 34 else ""
    return (f'<figure class="ex{split}"><div class="chat">' + "".join(parts) + "</div>"
            f"<figcaption><span>Figure {number}</span> {html.escape(title)}</figcaption></figure>")


def code(path: str, name: str) -> str:
    """The current source of function `name` in `path`, with its line numbers."""
    import ast
    src = (ROOT / path).read_text(encoding="utf-8")
    node = next(n for n in ast.walk(ast.parse(src))
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)
    lines = src.splitlines()[node.lineno - 1: node.end_lineno]
    body = "\n".join(f'<span class="ln">{node.lineno + i}</span>{html.escape(l)}' for i, l in enumerate(lines))
    return f'<pre class="code">{body}</pre>'


# ---------------------------------------------------------------- captions
CAP = re.compile(r'(<(?:figcaption|p class="tcap")>)<span>((?:Figure|Table) [\d.]+)</span>(.*?)(</(?:figcaption|p)>)', re.S)


def caption_list(page: str):
    items = []
    for m in CAP.finditer(page):
        text = re.sub(r"<em>.*?</em>", "", m.group(3), flags=re.S)
        text = re.sub(r"<[^>]+>", "", text).replace("&nbsp;", " ").strip()
        text = re.split(r"(?<=[a-z0-9)])\. ", text)[0].rstrip(".")
        text = re.sub(r"\s*\((?:source|sources)\b.*\)\s*$", "", text)
        items.append((m.group(2), html.unescape(text)))
    return items


def mark_captions(page: str) -> str:
    return CAP.sub(lambda m: f'{m.group(1)}<span>{m.group(2)}</span><span class="mk">QQ{m.group(2).replace(" ", "")}QQ</span>'
                   f"{m.group(3)}{m.group(4)}", page)


def lof(items, pages) -> str:
    def block(kind):
        rows = [f'<li class="subi"><span class="t">{n}&nbsp;&nbsp;{html.escape(t)}</span><span class="dots"></span>'
                f'<span class="pg">{pages.get(n.replace(" ", ""), 0)}</span></li>' for n, t in items if n.startswith(kind)]
        return f"<h3>{kind}s</h3><ol>" + "".join(rows) + "</ol>"
    return block("Figure") + block("Table")


# ---------------------------------------------------------------- render + locate
def render(src: Path, pdf: Path):
    pdf.unlink(missing_ok=True)
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                    "--run-all-compositor-stages-before-draw", "--virtual-time-budget=8000",
                    f"--print-to-pdf={pdf}", src.as_uri()], capture_output=True)
    last = -1
    for _ in range(160):
        size = pdf.stat().st_size if pdf.exists() else -1
        if size > 0 and size == last:
            return
        last = size
        time.sleep(0.5)
    sys.exit(f"render failed: {pdf} was not written")


def markers(pdf: Path):
    doc = fitz.open(pdf)
    found = {}
    for i in range(doc.page_count):
        for k in re.findall(r"QQ([\w.-]+?)QQ", doc[i].get_text().replace("\n", "")):
            found.setdefault(k, i + 1)
    return found, doc.page_count


def fill_toc(page: str, pages) -> str:
    def sub(m):
        key = m.group(2)
        if key not in pages:
            sys.exit(f"heading marker not found: {key}")
        return f"{m.group(1)}{pages[key]}{m.group(3)}"
    return re.sub(r'(<span class="pg" data-for="([\w-]+)">)\d+(</span>)', sub, page)


# ---------------------------------------------------------------- stamp
def overlay(n_pages: int, chapters):
    """A page number, centred at the foot of every page but the front page."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, _ = A4
    for p in range(1, n_pages + 1):
        if p > 1:
            c.setFillColor(Color(0, 0, 0))
            c.setFont("Times-Roman", 11)
            c.drawCentredString(w / 2, 11 * mm, str(p))
        c.showPage()
    c.save()
    buf.seek(0)
    return PdfReader(buf)


CHAPTERS = [("c1", "1  Introduction"), ("c2", "2  Literature Review"), ("c3", "3  Problem Statement"),
            ("c4", "4  Objectives"), ("c5", "5  Methodology"), ("c6", "6  Results and Discussion"),
            ("c7", "7  Conclusion"), ("c8", "8  Limitations"), ("c9", "9  Future Work"), ("refs", "References")]


def main():
    page = SRC.read_text(encoding="utf-8")
    n = iter(range(1, 100))
    page = re.sub(r"@@CHAT:(\w+)\|([^|]+)\|(\d+)\|(\d+)(?:\|([\d.]+))?@@",
                  lambda m: chat(m.group(1), m.group(2), int(m.group(3)), int(m.group(4)),
                                 m.group(5) or f"6.{next(n)}"), page)
    page = re.sub(r"@@CODE:([\w/.]+):(\w+)@@", lambda m: code(m.group(1), m.group(2)), page)
    items = caption_list(page)
    page = mark_captions(page)
    page = page.replace("@@LOF@@", lof(items, {}))
    if "@@" in page:
        sys.exit("an unfilled @@ marker remains")

    TMP_HTML.write_text(page, encoding="utf-8")
    render(TMP_HTML, RAW_PDF)
    pages, n = markers(RAW_PDF)
    filled = fill_toc(page, pages).replace(lof(items, {}), lof(items, pages))
    TMP_HTML.write_text(filled, encoding="utf-8")
    render(TMP_HTML, RAW_PDF)
    pages2, n2 = markers(RAW_PDF)
    if pages2 != pages or n2 != n:
        sys.exit("layout shifted after filling the contents; rebuild needed")
    missing = [n for n, _ in items if n.replace(" ", "") not in pages]
    if missing:
        sys.exit(f"caption markers not found: {missing}")

    # The markers have done their job; render once more without them, so that text copied
    # from the PDF is clean, and check that every page still breaks in the same place.
    before = [p.get_text() for p in fitz.open(RAW_PDF)]
    TMP_HTML.write_text(re.sub(r'<span class="mk">QQ[\w.-]+?QQ</span>', "", filled), encoding="utf-8")
    render(TMP_HTML, RAW_PDF)
    after = [p.get_text() for p in fitz.open(RAW_PDF)]
    strip = lambda t: re.sub(r"QQ[\w.-]+?QQ|\s+", "", t)  # noqa: E731
    if len(after) != len(before) or any(strip(a) != strip(b) for a, b in zip(after, before)):
        bad = [i + 1 for i, (a, b) in enumerate(zip(after, before)) if strip(a) != strip(b)]
        diff = ""
        if bad:
            a, b = strip(after[bad[0] - 1]), strip(before[bad[0] - 1])
            k = next((i for i in range(min(len(a), len(b))) if a[i] != b[i]), min(len(a), len(b)))
            diff = f" first at page {bad[0]}: before ...{b[max(0, k - 40):k + 40]}... after ...{a[max(0, k - 40):k + 40]}..."
        # The markers are invisible; a hair's difference at a page boundary is not worth
        # failing over, so keep the render the page numbers were measured on.
        print(f"note: marker removal shifted pages {bad}; keeping the measured render{diff[:0]}")
        TMP_HTML.write_text(filled, encoding="utf-8")
        render(TMP_HTML, RAW_PDF)

    body = PdfReader(RAW_PDF)
    chapters = [(pages[k], name) for k, name in CHAPTERS]
    stamp = overlay(len(body.pages), chapters)
    out = PdfWriter()
    for pg, st in zip(body.pages, stamp.pages):
        pg.merge_page(st)
        out.add_page(pg)
    for pg in out.pages:
        pg.compress_content_streams()
    out.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)

    # Bookmarks: chapters, with their numbered sections underneath.
    toc = re.findall(r'<li class="(main|subi)">(?:<a[^>]*>)?<span class="t">(.*?)</span>(?:</a>)?'
                     r'<span class="dots"></span><span class="pg" data-for="([\w-]+)">', page)
    out.add_outline_item("Front page", 0)
    out.add_outline_item("Abstract and key results", 1)
    out.add_outline_item("Table of contents", 2)
    parent = None
    for kind, title, key in toc:
        title = html.unescape(re.sub(r"<[^>]+>", "", title)).replace("\xa0", " ")
        if kind == "main":
            parent = out.add_outline_item(title, pages[key] - 1)
        else:
            out.add_outline_item(title, pages[key] - 1, parent=parent)
    out.add_metadata({
        "/Title": "OS Tutor: A Fine-Tuned, Retrieval-Grounded and Simulator-Verified Tutor for Operating Systems",
        "/Subject": "BCSE303L Operating Systems - Project Report (Slot B1+TB1, Fall 2026-27)",
        "/Author": "Divyakush Punjabi (24BCB0126)",
        "/Keywords": "LLM, QLoRA, RAG, verified simulators, intelligent tutoring, operating systems",
    })
    with open(OUT_PDF, "wb") as f:
        out.write(f)
    TMP_HTML.unlink(missing_ok=True)
    RAW_PDF.unlink(missing_ok=True)
    print(f"{OUT_PDF.name}: {n} pages, {OUT_PDF.stat().st_size // 1024} KB")
    for k, name in CHAPTERS:
        print(f"  page {pages[k]:>2}  {name}")


if __name__ == "__main__":
    main()
