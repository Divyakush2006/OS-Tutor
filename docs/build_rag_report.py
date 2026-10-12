"""Build docs/OS-Tutor-Project-Report.pdf from docs/os-tutor-rag-report.html.

    python docs/build_code_shots.py      (first: screenshots and the loss chart)
    python docs/build_rag_report.py

1. Fill the code listings (cut from the repository at the ranges the screenshots use)
   and the end-to-end RAG results (read from the newest reports/rag/e2e-*/results.json).
2. Render with headless Edge, find the page of every heading, write the page numbers
   into the contents, render again, then stamp footers and metadata.
"""
import html
import json
import re
import sys
from pathlib import Path

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer
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
    "s0": "Every number in this report carries",
    "s1": "1.1 Training dataset", "s1-1": "1.1 Training dataset", "s1-2": "1.2 Evaluation datasets",
    "s1-3": "1.3 Retrieval knowledge base",
    "s2": "2.1 The eleven-stage build", "s2-1": "2.1 The eleven-stage build",
    "s2-2": "2.2 Cleaning, deduplication and", "s2-3": "2.3 Selection, rendering, ordering",
    "s2-4": "2.4 Preprocessing for retrieval",
    "s3": "3.1 System architecture", "s3-1": "3.1 System architecture", "s3-2": "3.2 Data pipeline",
    "s3-3": "3.3 Fine-tuning", "s3-4": "3.4 Verified solver", "s3-5": "3.5 RAG pipeline",
    "s3-6": "3.6 Gateway integration", "s3-7": "3.7 Evaluation and tests",
    "s4": "4.1 Metrics and why", "s4-1": "4.1 Metrics and why", "s4-2": "4.2 Training loss",
    "s4-3": "4.3 Procedural accuracy and", "s4-4": "4.4 Out-of-distribution holdout",
    "s4-5": "4.5 Catastrophic forgetting", "s4-6": "4.6 Fact checker",
    "s4-7": "4.7 RAG: retrieval quality", "s4-8": "4.8 RAG: end to end",
    "s4-9": "4.9 Discussion", "s4-10": "4.10 Expected outcome",
    "s5": "5.1 Errors in measurement", "s6": "6.1 Evaluate before training",
    "a": "The code shown in the screenshots", "b": "Reproducing",
}


def listings() -> str:
    fmt = HtmlFormatter(style="default", nowrap=True)
    out = [f"<style>{fmt.get_style_defs('.listing pre')}</style>", '<div class="listing">']
    for n, (name, (path, a, b)) in enumerate(CODE.items(), 1):
        src = (ROOT / path).read_text(encoding="utf-8").splitlines()[a - 1:b]
        body = highlight("\n".join(src) + "\n", PythonLexer(), fmt).rstrip("\n").split("\n")
        lines = "\n".join(f'<span class="ln">{a + i}</span>{l}' for i, l in enumerate(body))
        out.append(f"<h4>A.{n}&nbsp;&nbsp;{html.escape(name.replace('_', ' '))} "
                   f"<span>{html.escape(path)} : {a}–{b}</span></h4><pre>{lines}</pre>")
    return "\n".join(out + ["</div>"])


def e2e() -> tuple[str, str]:
    runs = sorted((ROOT / "reports/rag").glob("e2e-*/results.json"))
    if not runs:
        sys.exit("no reports/rag/e2e-*/results.json - run tools/rag_e2e.py first")
    r = json.loads(runs[-1].read_text(encoding="utf-8"))
    s, e = r["summary"], r["summary"]["explain"]
    rel = str(runs[-1].parent.relative_to(ROOT)).replace("\\", "/")
    a, c = s["mcq_all"], s["mcq_with_notes"]
    pv = lambda p: "&lt; 0.0001" if p < 1e-4 else f"{p:.3f}"  # noqa: E731
    rows = (f"<tr><td>All 70 items</td><td class='num'>{a['correct_a']}/70</td>"
            f"<td class='num'>{a['correct_b']}/70</td><td class='num'>{a['right_to_wrong']}</td>"
            f"<td class='num'>{a['wrong_to_right']}</td><td class='num'>{pv(a['mcnemar_p'])}</td></tr>")
    if c:
        rows += (f"<tr><td>{s['mcq_items_with_notes']} items where notes were retrieved</td>"
                 f"<td class='num'>{c['correct_a']}/{c['n']}</td><td class='num'>{c['correct_b']}/{c['n']}</td>"
                 f"<td class='num'>{c['right_to_wrong']}</td><td class='num'>{c['wrong_to_right']}</td>"
                 f"<td class='num'>{pv(c['mcnemar_p'])}</td></tr>")
    ins = e["in_scope_with_notes"]
    block = f"""
<p>The served v3 model (one adapter, greedy decoding, prompt cache off) answered the same questions twice: once with the trained explain prompt alone, and once with the retrieved notes appended. Commit <code>{r['provenance']['commit'][:10]}</code>.</p>
<p><strong>A. Theory MCQ, RAG off vs on.</strong> These are the 70 OS-theory items. The model is asked for the option letter, and retrieval uses only the question text, as a student would type it. This generated-letter protocol is not the logit-scored one behind the 85.71% in §4.5, so only the off-versus-on comparison is meaningful.</p>
<table>
  <thead><tr><th>Items</th><th class="num">RAG off</th><th class="num">RAG on</th><th class="num">Right→wrong</th><th class="num">Wrong→right</th><th class="num">exact McNemar p</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
<p class="caption">Source: <code>{rel}/results.json</code>. The fixture notes were written by the team, which had seen the fact-checker rules; they were not written from the MCQ items, but they cover the same canonical facts. Read this as an upper bound for what well-matched course notes can do.</p>
<p><strong>B. Explain answers over the fixture questions.</strong></p>
<table>
  <thead><tr><th>Measure</th><th class="num">RAG off</th><th class="num">RAG on</th></tr></thead>
  <tbody>
    <tr><td>In-scope answers citing at least one note (of {ins} given notes)</td><td class="num">—</td><td class="num">{e['cited_at_least_once']}/{ins}</td></tr>
    <tr><td>Invented citations ([S<i>n</i>] with no such note), all {len(r['explain'])} answers</td><td class="num">—</td><td class="num">{e['invented_citations']}</td></tr>
    <tr><td>Out-of-scope questions given notes</td><td class="num">—</td><td class="num">{e['out_of_scope_given_notes']}/{e['out_of_scope']}</td></tr>
    <tr><td>Answers flagged by the fact checker</td><td class="num">{e['fact_flags_off']}</td><td class="num">{e['fact_flags_on']}</td></tr>
    <tr><td>Median prompt tokens (in-scope)</td><td class="num">{e['prompt_tokens_median']['off']}</td><td class="num">{e['prompt_tokens_median']['on']}</td></tr>
    <tr><td>Median answer length, tokens</td><td class="num">{e['completion_tokens_median']['off']}</td><td class="num">{e['completion_tokens_median']['on']}</td></tr>
    <tr><td>Median time to the full answer, s</td><td class="num">{e['seconds_median']['off']}</td><td class="num">{e['seconds_median']['on']}</td></tr>
    <tr><td>Median generation speed, tok/s (server timings)</td><td class="num">{e['tok_s_median']['off']}</td><td class="num">{e['tok_s_median']['on']}</td></tr>
    <tr><td>Slowest answer with RAG, tok/s (brief: ≥ 20)</td><td class="num">—</td><td class="num">{e['tok_s_min_on']}</td></tr>
  </tbody>
</table>
<figure><img src="shots/term_rag_e2e.png" alt="end-to-end summary">
<figcaption><strong>Figure 16.</strong> The run's own summary file, <code>{rel}/summary.md</code>.</figcaption></figure>"""
    return block, rel


def main():
    page = SRC.read_text(encoding="utf-8")
    block, rel = e2e()
    page = page.replace("@@E2E@@", block).replace("@@E2E_DIR@@", f"{rel}/") \
               .replace("@@LISTINGS@@", listings())
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
            c.setStrokeColor(Color(0.84, 0.85, 0.88))
            c.setLineWidth(0.5)
            c.line(18 * mm, 13 * mm, w - 18 * mm, 13 * mm)
            c.setFillColor(Color(0.36, 0.39, 0.43))
            c.setFont("Helvetica", 7.5)
            c.drawString(18 * mm, 9 * mm, "OS Tutor  |  Project Report with RAG Integration")
            c.drawRightString(w - 18 * mm, 9 * mm, f"Page {p} of {n_pages}")
        c.showPage()
    c.save()
    buf.seek(0)
    return PdfReader(buf)


if __name__ == "__main__":
    main()
