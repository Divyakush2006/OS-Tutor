"""Build data/rag/corpus from the owners' course material and the open online sources.

    python tools/import_rag_sources.py           (after tools/convert_office_legacy.ps1 and
                                                  tools/fetch_open_os_sources.py)
    python -m ostutor.rag.ingest data/rag/corpus  (then: validate, extract, index)

Course material: dataset_rag.zip, extracted to data/rag/corpus/src/professor/ (legacy
.ppt/.doc converted into src/professor_converted/). Each usable file is copied to
docs/course/ and recorded with the owners' permission. Excluded, with the reason kept in
the manifest's "excluded" list: Office lock files, byte-identical "(1)" copies, images
(no text layer), the assignment brief (not course content), a legacy .doc Office could not
convert, and near-duplicates - the same handout as both PDF and Word/PowerPoint, where the
structured format is kept because its headings and slide titles make better citations.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ostutor.rag.extract import SUPPORTED, extract  # noqa: E402
from ostutor.rag.ingest import add  # noqa: E402

CORPUS = ROOT / "data" / "rag" / "corpus"
SRC = CORPUS / "src" / "professor"
CONVERTED = CORPUS / "src" / "professor_converted"
COURSE = CORPUS / "docs" / "course"
ONLINE = CORPUS / "docs" / "online"
NEAR_DUP = 0.80                       # word-set Jaccard above which two files are one handout
PREFER = {".pptx": 0, ".docx": 0, ".md": 1, ".pdf": 2, ".txt": 3}
OWNER = "Course instructor (material supplied by the project owners)"
PERMISSION = ("Course material supplied by the project owners (dataset_rag.zip) for use in this "
              "tutor; not for redistribution")
NOT_COURSE = {"Problem Statement LLM.docx": "the assignment brief, not course content"}
# readable titles for citations; the OSTEP chapter titles are read from each PDF's first page
TITLES = {
    "Extra/10. Multiprocessor Scheduling (Advanced).ppt": "Lecture slides: Multiprocessor Scheduling",
    "Extra/2. OS Functionalities.pptx": "Lecture slides: OS Functionalities",
    "Extra/3. Unix filestructure related system calls.pptx": "Lecture slides: Unix File-Structure System Calls",
    "Extra/4. The Abstraction The process.ppt": "Lecture slides: The Abstraction - The Process",
    "Extra/5. Process API.ppt": "Lecture slides: Process API (extra)",
    "Extra/6. Direct Execution.ppt": "Lecture slides: Limited Direct Execution",
    "Extra/7. Scheduling.ppt": "Lecture slides: Scheduling",
    "Extra/8. Multi level feedback scheduling.ppt": "Lecture slides: Multi-Level Feedback Queue",
    "Extra/9. Scheduling Proportional Share.ppt": "Lecture slides: Proportional-Share Scheduling",
    "Lab/Linux commands.pdf": "Lab handout: Basic Unix Commands",
    "Lab/Shell programming.pptx": "Lab slides: Shell Programming",
    "Theory/1. Introduction to OS.ppt": "Lecture slides: Introduction to OS",
    "Theory/13. Segmentation.ppt": "Lecture slides: Segmentation",
    "Theory/15. Paging.ppt": "Lecture slides: Paging",
    "Theory/17. Advanced Page Tables.ppt": "Lecture slides: Advanced Page Tables",
    "Theory/Concurrency bugs.pptx": "Lecture slides: Concurrency Bugs",
    "Theory/Condition variable.pptx": "Lecture slides: Condition Variables",
    "Theory/Deadlock problem.pdf": "Course handout: Deadlock Problem",
    "Theory/IPC.pdf": "Course handout: IPC with Shared Memory",
    "Theory/Introduction to OS.pptx": "Lecture slides: Introduction to OS (short)",
    "Theory/Memory allocation algorithm.pptx": "Lecture slides: Memory Allocation Algorithms",
    "Theory/Paging problem.pdf": "Course handout: Paging Problems",
    "Theory/Process API.pptx": "Lecture slides: Process API",
    "Theory/Process abstractions.pptx": "Lecture slides: Process Abstractions",
    "Theory/Process execution mechanism.pptx": "Lecture slides: Process Execution Mechanism",
    "Theory/Reader writer problem.docx": "Course handout: Readers-Writers Problem",
    "Theory/Semaphore.ppt - Copy.pptx": "Lecture slides: Semaphores",
    "Theory/Threads and concurrency.pptx": "Lecture slides: Threads and Concurrency",
    "Theory/Virtual memory.pptx": "Lecture slides: Virtual Memory",
    "Theory/demand paging.pptx": "Lecture slides: Demand Paging",
    "Theory/dining philospher.docx": "Course handout: Dining Philosophers",
    "Theory/locks.pptx": "Lecture slides: Locks",
    "Theory/paging (1).pptx": "Lecture slides: Paging (second deck)",
}
OSTEP = {"process API.pdf", "process abstraction.pdf", "process execution mechanism.pdf",
         "threads-api.pdf", "threads-bugs.pdf", "threads-cv.pdf", "threads-intro.pdf",
         "threads-locks.pdf", "threads-sema.pdf"}


def course_title(rel: str, path: Path) -> str:
    if Path(rel).name in OSTEP:
        import fitz
        lines = [l.strip() for l in fitz.open(str(path))[0].get_text().splitlines() if l.strip()]
        return f"OSTEP ch. {lines[0]}: {lines[1]} (course reading)"
    return TITLES.get(rel, Path(rel).stem)


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z]{3,}", text.lower()))


def main() -> None:
    excluded, candidates = [], []
    seen_hash: dict[str, str] = {}
    # a "(1)" copy sorts after its original, so the original name is the one kept
    for p in sorted(SRC.rglob("*"), key=lambda q: (" (1)" in q.name, str(q))):
        if not p.is_file():
            continue
        rel = p.relative_to(SRC).as_posix()
        if p.name.startswith("~$"):
            excluded.append(dict(file=rel, reason="Office lock file"))
            continue
        if p.name in NOT_COURSE:
            excluded.append(dict(file=rel, reason=NOT_COURSE[p.name]))
            continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        if h in seen_hash:
            excluded.append(dict(file=rel, reason=f"byte-identical copy of {seen_hash[h]}"))
            continue
        seen_hash[h] = rel
        if p.suffix.lower() in (".png", ".jpg", ".jpeg"):
            excluded.append(dict(file=rel, reason="image with no text layer (diagram/poster)"))
            continue
        use = p
        if p.suffix.lower() in (".ppt", ".doc"):
            conv = CONVERTED / (rel + "x")
            if not conv.is_file():
                excluded.append(dict(file=rel, reason="legacy Office format; automatic conversion "
                                                      "failed - open in Office and save as "
                                                      f"{p.suffix}x to include it"))
                continue
            use = conv
        if use.suffix.lower() not in SUPPORTED:
            excluded.append(dict(file=rel, reason=f"unsupported format {use.suffix}"))
            continue
        candidates.append(dict(rel=rel, path=use, text=words(extract(use, p.stem))))

    # near-duplicates: keep the structured format (slides/Word) over a PDF export of it
    keep = []
    for c in sorted(candidates, key=lambda c: PREFER.get(c["path"].suffix.lower(), 9)):
        twin = next((k for k in keep if c["text"] and k["text"] and
                     len(c["text"] & k["text"]) / len(c["text"] | k["text"]) >= NEAR_DUP), None)
        if twin:
            j = len(c["text"] & twin["text"]) / len(c["text"] | twin["text"])
            excluded.append(dict(file=c["rel"], reason=f"near-duplicate of {twin['rel']} "
                                                       f"(word overlap {j:.2f}); kept the structured one"))
        else:
            keep.append(c)

    if COURSE.exists():
        shutil.rmtree(COURSE)
    files = []
    for c in sorted(keep, key=lambda c: c["rel"]):
        dest = COURSE / Path(c["rel"]).parent / c["path"].name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(c["path"], dest)
        files.append((dest, c["rel"], c["path"] != SRC / c["rel"]))

    man = CORPUS / "manifest.json"
    man.write_text(json.dumps(dict(
        corpus="ostutor-course-notes",
        note="Course material from the owners plus openly licensed OS texts (D-007). "
             "Each document needs id, title, path, source, owner, licence or permission, "
             "added and sha256; ingestion refuses anything else.",
        documents=[], excluded=excluded), indent=1) + "\n", encoding="utf-8")
    for dest, rel, converted in files:
        e = add(CORPUS, [str(dest)], owner=OWNER, source=f"dataset_rag.zip: {rel}", licence="",
                permission=PERMISSION, id_prefix="course",
                extra=dict(kind="course", **({"converted": "legacy Office file converted to OOXML by "
                                                          "tools/convert_office_legacy.ps1"} if converted else {})))[0]
        m = json.loads(man.read_text(encoding="utf-8"))
        for d in m["documents"]:
            if d["path"] == e["path"]:
                d["title"] = course_title(rel, dest)
        man.write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for rec in json.loads((ONLINE / "sources.json").read_text(encoding="utf-8")):
        e = add(CORPUS, [str(CORPUS / rec["path"])], owner=rec["owner"], source=rec["source"],
                licence=rec["licence"], permission=rec["permission"], id_prefix="online",
                extra=dict(kind="online", converted=rec["converted"]))[0]
        # keep the fetcher's stable id and readable title
        m = json.loads(man.read_text(encoding="utf-8"))
        for d in m["documents"]:
            if d["path"] == e["path"]:
                d["id"], d["title"] = rec["id"], rec["title"]
        man.write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    m = json.loads(man.read_text(encoding="utf-8"))
    kinds = {k: sum(d["kind"] == k for d in m["documents"]) for k in ("course", "online")}
    print(f"manifest: {kinds['course']} course + {kinds['online']} online documents, "
          f"{len(excluded)} excluded")
    for x in excluded:
        print(f"  excluded {x['file']}: {x['reason']}")


if __name__ == "__main__":
    main()
