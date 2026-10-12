"""Load a course-materials corpus and cut it into citable chunks.

A corpus is a directory with a manifest.json:

    {"corpus": "...", "documents": [
        {"id": "c-locks", "title": "Locks", "path": "docs/course/Theory/locks.pptx",
         "source": "where it came from", "owner": "who holds the rights",
         "licence": "...", "permission": "...", "added": "2026-10-12",
         "sha256": "<checksum of the file at path>"}]}

Ingestion REFUSES, never skips:
  * a document with no source, owner, date added or checksum, or with neither a licence
    nor a permission recorded;
  * a document whose bytes no longer match the recorded checksum;
  * any supported file inside the corpus that has no manifest entry.
The brief allows no text into the index whose right to be there is unrecorded.

Every document is converted to Markdown by extract.py (cached in <corpus>/extracted/,
keyed by checksum) and cut at its headings, so a chunk's section is the heading path
above it: "Slide 4: Is disabling interrupts enough?", "Page 3 › 28.1 Locks", or
"Deadlock › The Deadlock Problem".
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from .extract import SUPPORTED, extract

REQUIRED = ("id", "title", "path", "source", "owner", "added", "sha256")
MAX_WORDS = 180          # a chunk is one idea; long sections are split here
OVERLAP_WORDS = 30       # so a sentence cut at a boundary is still whole somewhere
MIN_WORDS = 6            # title slides and stray headings carry nothing to retrieve
NOT_DOCUMENTS = {"extracted", "index", "src"}   # corpus subfolders that hold derived files


@dataclass(frozen=True)
class Chunk:
    chunk_id: str        # "<doc id>#<n>"
    doc_id: str
    title: str           # document title
    section: str         # heading path above the text
    text: str
    licence: str
    source: str

    def citation(self) -> str:
        return f"{self.title} — {self.section}" if self.section else self.title


class CorpusError(ValueError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sections(md: str):
    """Yield (heading path, body) pairs. Level-1 headings are the document title and are
    left out of the path; deeper headings nest."""
    stack: dict[int, str] = {}
    buf: list[str] = []

    def path():
        return " › ".join(stack[k] for k in sorted(stack) if k >= 2)
    for line in md.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*\S)\s*$", line)
        if m:
            if "".join(buf).strip():
                yield path(), "\n".join(buf).strip()
            level = len(m.group(1))
            stack = {k: v for k, v in stack.items() if k < level}
            stack[level] = re.sub(r"[*_`]", "", m.group(2)).strip()
            buf = []
        else:
            buf.append(line)
    if "".join(buf).strip():
        yield path(), "\n".join(buf).strip()


def _windows(words: list[str]):
    if len(words) <= MAX_WORDS:
        yield words
        return
    step = MAX_WORDS - OVERLAP_WORDS
    for start in range(0, len(words), step):
        yield words[start:start + MAX_WORDS]
        if start + MAX_WORDS >= len(words):
            break


def validate(root: Path, manifest: dict) -> list[dict]:
    """Check every manifest entry and every file; raise CorpusError on the first problem."""
    docs, seen, listed = manifest.get("documents", []), set(), set()
    for doc in docs:
        missing = [k for k in REQUIRED if not str(doc.get(k, "")).strip()]
        if not str(doc.get("licence", "")).strip() and not str(doc.get("permission", "")).strip():
            missing.append("licence or permission")
        if missing:
            raise CorpusError(f"document {doc.get('id', '?')}: no {', '.join(missing)} "
                              "recorded - refusing to index it")
        if doc["id"] in seen:
            raise CorpusError(f"duplicate document id {doc['id']}")
        seen.add(doc["id"])
        path = root / doc["path"]
        if not path.is_file():
            raise CorpusError(f"document {doc['id']}: {doc['path']} does not exist")
        if path.suffix.lower() not in SUPPORTED:
            raise CorpusError(f"document {doc['id']}: unsupported format {path.suffix}")
        if sha256(path) != doc["sha256"]:
            raise CorpusError(f"document {doc['id']}: {doc['path']} does not match its recorded "
                              "checksum - refusing to index changed content")
        listed.add(path.resolve())
    unlisted = sorted(str(p.relative_to(root)) for p in root.rglob("*")
                      if p.is_file() and p.suffix.lower() in SUPPORTED
                      and not (set(p.relative_to(root).parts[:-1]) & NOT_DOCUMENTS)
                      and p.resolve() not in listed)
    if unlisted:
        raise CorpusError(f"{len(unlisted)} file(s) have no manifest entry - refusing to ingest: "
                          + ", ".join(unlisted[:5]) + (" ..." if len(unlisted) > 5 else ""))
    return docs


def markdown_of(root: Path, doc: dict) -> str:
    """The document as Markdown, from the extraction cache when its checksum is unchanged."""
    cache = root / "extracted" / f"{doc['id']}.md"
    stamp = f"<!-- sha256 {doc['sha256']} -->\n"
    if cache.is_file():
        text = cache.read_text(encoding="utf-8")
        if text.startswith(stamp):
            return text[len(stamp):]
    md = extract(root / doc["path"], doc["title"])
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(stamp + md, encoding="utf-8")
    return md


def load_corpus(root: Path) -> tuple[list[Chunk], dict]:
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    chunks: list[Chunk] = []
    for doc in validate(root, manifest):
        licence = doc.get("licence") or doc.get("permission")
        n = 0
        for heading, body in _sections(markdown_of(root, doc)):
            for win in _windows(body.split()):
                if len(win) < MIN_WORDS:
                    continue
                chunks.append(Chunk(f"{doc['id']}#{n}", doc["id"], doc["title"], heading,
                                    " ".join(win), licence, doc["source"]))
                n += 1
    digest = hashlib.sha256("\n".join(c.chunk_id + c.title + c.section + c.text for c in chunks)
                            .encode()).hexdigest()
    return chunks, dict(manifest, chunk_count=len(chunks), chunks_sha256=digest)
