"""Load a course-notes corpus and cut it into citable chunks.

A corpus is a directory with a manifest.json:

    {"corpus": "...", "documents": [
        {"id": "n01", "title": "Process management", "path": "notes/n01.md",
         "source": "who supplied it", "licence": "...", "permission": "...",
         "added": "2026-10-12"}]}

A document with no licence or permission field is REFUSED, not skipped silently: the
brief allows no text into the index whose right to be there is unrecorded.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

REQUIRED = ("id", "title", "path", "source", "licence", "permission")
MAX_WORDS = 180          # a chunk is one idea; long sections are split here
OVERLAP_WORDS = 30       # so a sentence cut at a boundary is still whole somewhere


@dataclass(frozen=True)
class Chunk:
    chunk_id: str        # "<doc id>#<n>"
    doc_id: str
    title: str           # document title
    section: str         # nearest heading above the text
    text: str
    licence: str
    source: str

    def citation(self) -> str:
        return f"{self.title} — {self.section}" if self.section else self.title


class CorpusError(ValueError):
    pass


def _sections(text: str):
    """Yield (heading, body) pairs; text before the first heading has heading ''."""
    heading, buf = "", []
    for line in text.splitlines():
        m = re.match(r"^#{1,4}\s+(.*\S)\s*$", line)
        if m:
            if "".join(buf).strip():
                yield heading, "\n".join(buf).strip()
            heading, buf = m.group(1), []
        else:
            buf.append(line)
    if "".join(buf).strip():
        yield heading, "\n".join(buf).strip()


def _windows(words: list[str]):
    if len(words) <= MAX_WORDS:
        yield words
        return
    step = MAX_WORDS - OVERLAP_WORDS
    for start in range(0, len(words), step):
        yield words[start:start + MAX_WORDS]
        if start + MAX_WORDS >= len(words):
            break


def load_corpus(root: Path) -> tuple[list[Chunk], dict]:
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    chunks: list[Chunk] = []
    seen: set[str] = set()
    for doc in manifest.get("documents", []):
        missing = [k for k in REQUIRED if not str(doc.get(k, "")).strip()]
        if missing:
            raise CorpusError(f"document {doc.get('id', '?')}: no {', '.join(missing)} "
                              "recorded - refusing to index it")
        if doc["id"] in seen:
            raise CorpusError(f"duplicate document id {doc['id']}")
        seen.add(doc["id"])
        text = (root / doc["path"]).read_text(encoding="utf-8")
        n = 0
        for heading, body in _sections(text):
            for win in _windows(body.split()):
                chunks.append(Chunk(f"{doc['id']}#{n}", doc["id"], doc["title"], heading,
                                    " ".join(win), doc["licence"], doc["source"]))
                n += 1
    digest = hashlib.sha256("\n".join(c.chunk_id + c.text for c in chunks).encode()).hexdigest()
    return chunks, dict(manifest, chunk_count=len(chunks), chunks_sha256=digest)
