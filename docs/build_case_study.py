"""Build docs/OS-Tutor-Case-Study.pdf from docs/os-tutor-case-study.html.

    python docs/build_case_study.py

1. Render the HTML to PDF with headless Edge.
2. Find the page every section heading landed on, and write those numbers into the
   table of contents (the contents fit on one page, so filling them in cannot move
   anything after it).
3. Render again, then stamp a footer with page numbers on every page but the cover,
   and set the document metadata.
"""
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

DOCS = Path(__file__).resolve().parent
SRC = DOCS / "os-tutor-case-study.html"
TMP_HTML = DOCS / "_case_study_render.html"
RAW_PDF = DOCS / "_case_study_raw.pdf"
OUT_PDF = DOCS / "OS-Tutor-Case-Study.pdf"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# toc id -> text that appears only in that section's heading (or first line)
ANCHORS = {
    "s1": "1.1 Background", "s1-1": "1.1 Background", "s1-2": "1.2 The problem",
    "s1-3": "1.3 Project status at a glance",
    "s2": "2.1 Parameter-efficient", "s2-1": "2.1 Parameter-efficient",
    "s2-2": "2.2 Catastrophic forgetting", "s2-3": "2.3 Limits of procedural",
    "s2-4": "2.4 Language models as tutors", "s2-5": "2.5 Research gap",
    "s3": "Primary objective:",
    "s4": "4.1 Collection strategy", "s4-1": "4.1 Collection strategy",
    "s4-2": "4.2 Sources", "s4-3": "4.3 Generated data", "s4-4": "4.4 Licensing policy",
    "s4-5": "4.5 Evaluation data",
    "s5": "5.1 Pipeline overview", "s5-1": "5.1 Pipeline overview",
    "s5-2": "5.2 Analysis before cleaning", "s5-3": "5.3 Cleaning, deduplication",
    "s5-4": "5.4 Quality scoring", "s5-5": "5.5 Final composition",
    "s5-6": "5.6 Rectifier ordering", "s5-7": "5.7 Release gates",
    "s6": "6.1 Design principle", "s6-1": "6.1 Design principle",
    "s6-2": "6.2 Base model selection", "s6-3": "6.3 Fine-tuning configuration",
    "s6-4": "6.4 Verified-solver layer", "s6-5": "6.5 Serving architecture",
    "s7": "7.1 Current status", "s7-1": "7.1 Current status", "s7-2": "7.2 Findings",
    "s7-3": "7.3 Limitations", "s7-4": "7.4 Next steps",
    "refs": "Catastrophic Interference in Connectionist",
}
FIRST_BODY_PAGE = 2  # 0-based: cover is 0, contents is 1


def render(html: Path, pdf: Path):
    if pdf.exists():
        pdf.unlink()
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
                    "--virtual-time-budget=6000", f"--print-to-pdf={pdf}", html.as_uri()],
                   capture_output=True)
    # The Edge launcher can return before the renderer has finished writing, so wait
    # until the file exists and its size has stopped changing.
    last = -1
    for _ in range(120):
        size = pdf.stat().st_size if pdf.exists() else -1
        if size > 0 and size == last:
            return
        last = size
        time.sleep(0.5)
    sys.exit(f"render failed: {pdf} was not written")


def heading_pages(pdf: Path):
    doc = fitz.open(pdf)
    contents = [i for i in range(doc.page_count) if doc[i].search_for("Contents")]
    # "References" is the last entry in the list; if it is not on the same page as the
    # "Contents" heading, the list spilled over and filling in numbers could move pages.
    if not contents or not doc[contents[0]].search_for("References"):
        sys.exit("the contents list must fit on a single page")
    found = {}
    for key, needle in ANCHORS.items():
        # Every sub-heading also appears in the contents list, so take the LAST page
        # that carries it: that is always the body, however long the contents are.
        hits = [i for i in range(FIRST_BODY_PAGE - 1, doc.page_count) if doc[i].search_for(needle)]
        hits = [i for i in hits if i != contents[0]]
        if hits:
            found[key] = hits[-1] + 1  # printed page number = physical page
    missing = sorted(set(ANCHORS) - set(found))
    if missing:
        sys.exit(f"could not locate headings: {missing}")
    return found, doc.page_count


def footer_overlay(n_pages: int):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, _ = A4
    grey = Color(0.36, 0.39, 0.43)
    for p in range(1, n_pages + 1):
        if p > 1:  # the cover carries no footer
            c.setStrokeColor(Color(0.84, 0.85, 0.88))
            c.setLineWidth(0.5)
            c.line(18 * mm, 13 * mm, w - 18 * mm, 13 * mm)
            c.setFillColor(grey)
            c.setFont("Helvetica", 7.5)
            c.drawString(18 * mm, 9 * mm, "OS Tutor  |  Case Study: Current Project Status")
            c.drawRightString(w - 18 * mm, 9 * mm, f"Page {p} of {n_pages}")
        c.showPage()
    c.save()
    buf.seek(0)
    return PdfReader(buf)


def main():
    html = SRC.read_text(encoding="utf-8")
    TMP_HTML.write_text(html, encoding="utf-8")
    render(TMP_HTML, RAW_PDF)

    pages, n = heading_pages(RAW_PDF)
    filled = re.sub(r'(<span class="pg" data-for="([\w-]+)">)0(</span>)',
                    lambda m: f"{m.group(1)}{pages[m.group(2)]}{m.group(3)}", html)
    TMP_HTML.write_text(filled, encoding="utf-8")
    render(TMP_HTML, RAW_PDF)

    pages2, n2 = heading_pages(RAW_PDF)
    if pages2 != pages or n2 != n:
        sys.exit("layout shifted after filling the contents page; rebuild needed")

    body = PdfReader(RAW_PDF)
    overlay = footer_overlay(len(body.pages))
    out = PdfWriter()
    for page, stamp in zip(body.pages, overlay.pages):
        page.merge_page(stamp)
        out.add_page(page)
    # merge_page leaves content streams uncompressed and fonts duplicated per page,
    # which inflated the file from ~0.3 MB to 3.5 MB.
    for page in out.pages:
        page.compress_content_streams()
    out.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)
    out.add_metadata({
        "/Title": "OS Tutor: Fine-Tuning a Small Language Model into a Verified Operating Systems Tutor",
        "/Subject": "Case study: current status of the LLM project",
        "/Author": "Divyakush Punjabi (24BCB0126)",
        "/Keywords": "LLM, fine-tuning, QLoRA, operating systems, tutoring, catastrophic forgetting",
    })
    with open(OUT_PDF, "wb") as f:
        out.write(f)

    TMP_HTML.unlink(missing_ok=True)
    RAW_PDF.unlink(missing_ok=True)
    print(f"{OUT_PDF.name}: {n} pages")
    for k in ("s1", "s2", "s3", "s4", "s5", "s6", "s7", "refs"):
        print(f"  {k:<5} page {pages[k]}")


if __name__ == "__main__":
    main()
