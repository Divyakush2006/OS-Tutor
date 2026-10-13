"""Build docs/OS-Tutor-Project-Report.pdf from docs/os-tutor-rag-report.html.

    python docs/build_code_shots.py      (first: screenshots and the loss chart)
    python docs/build_rag_report.py

1. Fill the code listings (cut from the repository at the ranges the screenshots use).
2. Render with headless Edge, find the page of every heading, write the page numbers
   into the contents, render again, then stamp footers and metadata.
"""
import html
import re
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter

DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parent
sys.path.insert(0, str(DOCS))
import build_case_study as base  # noqa: E402  (render, footer, heading search)
from build_code_shots import CODE  # noqa: E402

SRC = DOCS / "os-tutor-rag-report.html"
TMP_HTML = DOCS / "_rag_report_render.html"
RAW_PDF = DOCS / "_rag_report_raw.pdf"
OUT_PDF = DOCS / "OS-Tutor-Project-Report.pdf"

ANCHORS = {
    "s0": "Every number in this report was produced",
    "s1": "1.1 Training dataset", "s1-1": "1.1 Training dataset", "s1-2": "1.2 Evaluation datasets",
    "s1-3": "1.3 Retrieval knowledge base",
    "s1-4": "1.4 Open retrieval corpus",
    "s2": "2.1 The eleven-stage build", "s2-1": "2.1 The eleven-stage build",
    "s2-2": "2.2 Cleaning, deduplication and", "s2-3": "2.3 Selection, rendering, ordering",
    "s2-4": "2.4 Preprocessing for retrieval",
    "s2-5": "2.5 Analysis and compilation",
    "s3": "3.1 System architecture", "s3-1": "3.1 System architecture", "s3-2": "3.2 Data pipeline",
    "s3-3": "3.3 Fine-tuning", "s3-4": "3.4 Verified solver", "s3-5": "3.5 RAG pipeline",
    "s3-6": "3.6 Gateway integration", "s3-7": "3.7 Evaluation and tests",
    "s4": "4.1 Metrics and why", "s4-1": "4.1 Metrics and why", "s4-2": "4.2 Training loss",
    "s4-3": "4.3 Procedural accuracy and", "s4-4": "4.4 Out-of-distribution holdout",
    "s4-5": "4.5 Catastrophic forgetting", "s4-6": "4.6 Fact checker",
    "s4-7": "4.7 RAG: retrieval quality", "s4-8": "4.8 RAG: end to end",
    "s4-9": "4.9 Discussion", "s4-10": "4.10 Targets and results",
    "s5": "5.1 Errors in measurement", "s6": "6.1 Evaluate before training",
    "a": "This appendix gives the code shown", "b": "Reproducing",
}


def listings() -> str:
    out = ['<div class="listing">']
    for n, (name, (path, a, b)) in enumerate(CODE.items(), 1):
        src = (ROOT / path).read_text(encoding="utf-8").splitlines()[a - 1:b]
        lines = "\n".join(f'<span class="ln">{a + i}</span>{html.escape(l)}' for i, l in enumerate(src))
        out.append(f"<h4>A.{n}&nbsp;&nbsp;{html.escape(name.replace('_', ' '))} "
                   f"<span>{html.escape(path)} : {a}–{b}</span></h4><pre>{lines}</pre>")
    return "\n".join(out + ["</div>"])


def main():
    page = SRC.read_text(encoding="utf-8")
    page = page.replace("@@LISTINGS@@", listings())
    if "@@" in page:
        sys.exit("an unfilled @@ marker remains")
    base.ANCHORS = ANCHORS
    base.FIRST_BODY_PAGE = 2
    TMP_HTML.write_text(page, encoding="utf-8")
    base.render(TMP_HTML, RAW_PDF)
    pages, n = heading_pages(RAW_PDF)
    filled = re.sub(r'(<span class="pg" data-for="([\w-]+)">)0(</span>)',
                    lambda m: f"{m.group(1)}{pages[m.group(2)]}{m.group(3)}", page)
    TMP_HTML.write_text(filled, encoding="utf-8")
    base.render(TMP_HTML, RAW_PDF)
    pages2, n2 = heading_pages(RAW_PDF)
    if pages2 != pages or n2 != n:
        sys.exit("layout shifted after filling the contents page; rebuild needed")

    body = PdfReader(RAW_PDF)
    overlay = footer(len(body.pages))
    out = PdfWriter()
    for p, stamp in zip(body.pages, overlay.pages):
        p.merge_page(stamp)
        out.add_page(p)
    for p in out.pages:
        p.compress_content_streams()
    out.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)
    out.add_metadata({
        "/Title": "OS Tutor: A Fine-Tuned, Retrieval-Grounded and Simulator-Verified Operating Systems Tutor",
        "/Subject": "Project report: dataset, preprocessing, implementation, results, failures, improvements",
        "/Author": "Divyakush Punjabi (24BCB0126)",
        "/Keywords": "LLM, QLoRA, RAG, retrieval, operating systems, tutoring, evaluation",
    })
    with open(OUT_PDF, "wb") as f:
        out.write(f)
    TMP_HTML.unlink(missing_ok=True)
    RAW_PDF.unlink(missing_ok=True)
    print(f"{OUT_PDF.name}: {n} pages, {OUT_PDF.stat().st_size // 1024} KB")
    for k in ("s0", "s1", "s2", "s3", "s4", "s5", "s6", "a", "b"):
        print(f"  {k:<4} page {pages[k]}")


def heading_pages(pdf):
    import fitz
    doc = fitz.open(pdf)
    toc = next(i for i in range(doc.page_count) if doc[i].search_for("Contents"))
    found = {}
    for key, needle in ANCHORS.items():
        hits = [i for i in range(doc.page_count) if i != toc and doc[i].search_for(needle)]
        if hits:
            found[key] = hits[0] + 1 if key in ("s0",) else hits[-1] + 1
    missing = sorted(set(ANCHORS) - set(found))
    if missing:
        sys.exit(f"could not locate headings: {missing}")
    return found, doc.page_count


def footer(n_pages):
    from io import BytesIO
    from reportlab.lib.colors import Color
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, _ = A4
    for p in range(1, n_pages + 1):
        if p > 1:
            c.setFillColor(Color(0, 0, 0))
            c.setFont("Times-Roman", 11)
            c.drawCentredString(w / 2, 13 * mm, str(p))
        c.showPage()
    c.save()
    buf.seek(0)
    return PdfReader(buf)


if __name__ == "__main__":
    main()
