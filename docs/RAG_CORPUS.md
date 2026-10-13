# Course-materials corpus (RAG) — how to add notes

The tutor's explain and analyze modes answer from the course materials in
`data/rag/corpus/`, cite them (`[S1]` … plus a "Sources from your course notes" list),
and say **"Not found in the course materials"** when the materials do not cover a
question. Solve mode still uses the simulators; tutor mode never retrieves.

## Adding documents (two commands)

1. Copy the files into a folder under `data/rag/corpus/docs/`, for example
   `data/rag/corpus/docs/course/Week07/`. Supported formats: **PDF, PPTX, DOCX, Markdown,
   plain text**. Convert legacy `.ppt` / `.doc` first:

   ```powershell
   powershell -ExecutionPolicy Bypass -File tools\convert_office_legacy.ps1 <folder with .ppt/.doc> <output folder>
   ```

2. Record who supplied them and on what terms, then rebuild:

   ```powershell
   python -m ostutor.rag.ingest add data/rag/corpus data/rag/corpus/docs/course/Week07/*.pptx `
       --owner "Course instructor" --source "Week 7 slides (LMS)" `
       --permission "Supplied by the course instructor for use in this tutor"
   python -m ostutor.rag.ingest data/rag/corpus
   ```

   Use `--licence "CC BY 4.0"` instead of, or as well as, `--permission` for openly licensed
   material. The second command validates, extracts, chunks and embeds everything on the
   CPU (about 50 s for the current corpus, a few seconds when nothing changed) and prints a
   per-document chunk count. A document that yields 0 chunks is a scanned image with no
   text layer and needs OCR first.

3. Restart the tutor with retrieval on:

   ```powershell
   $env:OSTUTOR_RAG = "data/rag/corpus"
   powershell -ExecutionPolicy Bypass -File serve\start_tutor.ps1
   ```

## What ingestion refuses

The whole corpus is refused, never partly loaded, when:

- a file under the corpus has **no manifest entry** (copying a file in is not enough);
- an entry lacks `source`, `owner`, `added`, `sha256`, or both `licence` and `permission`;
- a file's bytes no longer match its recorded **checksum** (re-run `add` after editing a file).

## After adding a substantial amount of material

The "not covered" threshold depends on the corpus. Re-measure and re-fit it:

```powershell
python tools/rag_eval.py data/rag/corpus --calibrate
```

This uses `data/rag/eval/corpus_questions.jsonl` (labelled question → document + evidence
phrase; dev half fits the gate, test half reports it). Add questions for new material to
`tools/build_rag_questions.py` so recall stays measured on what students will ask.

## What is in the corpus now (2026-10-12)

| Part | Documents | Licence / permission |
|---|---|---|
| Professor's material (`dataset_rag.zip`): lecture slides, OSTEP chapters supplied as reading, handouts, lab material | 42 | supplied by the owners for this tutor; **not for redistribution** (not committed to git) |
| Max Hailperin, *Operating Systems and Middleware*, rev. 1.3.1 — 8 OS chapters | 8 | CC BY-SA 3.0, pinned to commit `3567f8f8` |
| English Wikipedia OS articles | 55 | CC BY-SA 4.0, pinned to revision ids |

12 files were excluded, each with its reason in `manifest.json` → `excluded` (duplicates,
images without text, the assignment brief, one legacy `.doc` Office could not convert —
open it in Word and save as `.docx` to include it). Online sources are re-fetched exactly
by `python tools/fetch_open_os_sources.py`; the course corpus is rebuilt from the zip by
`python tools/import_rag_sources.py`. Decisions: `docs/DECISIONS.md` D-006, D-007, D-008.

## The open corpus (`data/rag/open`, 2026-10-13)

The open corpus is a second corpus with no course material. It holds 2,970 openly
licensed documents (CC BY-SA): Hailperin, CSBU, Wikipedia, Wikibooks and Stack Exchange
cs/unix. They are selected from a 3,291-document pool by measured filters (D-009).
Rebuild it with:

    python tools/fetch_rag_pool.py        # downloads into data/rag/pool/ (cached)
    python tools/analyze_rag_pool.py      # analysis report + data/rag/open (+ the unfiltered control)
    python -m ostutor.rag.ingest data/rag/open
    python tools/rag_compare.py --calibrate data/rag/open   # refit the gate after any change

Serve it with `$env:OSTUTOR_RAG = "data/rag/open"`. It retrieves the answer more often than
the course corpus (answer recall@5 83% vs 74% over 144 questions). However, its citations
are Wikipedia articles and Stack Exchange posts, not the course slides. It also says "not
covered" less often for near-topic questions (14/20 off-topic withheld vs 18/20). Which
corpus students see is the owners' choice; the default stays off.
