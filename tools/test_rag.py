"""Tests for the RAG pipeline (G2). Hermetic: no GPU, no model server, no network.

    python tools/test_rag.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ostutor.rag.corpus import MAX_WORDS, CorpusError, load_corpus  # noqa: E402
from ostutor.rag.retrieve import (BM25, Retriever, augment, cited,  # noqa: E402
                                  sources_footer, tokens)

FIXTURE = ROOT / "data" / "rag" / "fixture"
FAILED: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  -> {detail}" if not ok and detail else ""))
    if not ok:
        FAILED.append(name)


def corpus(docs: dict[str, str], meta: dict | None = None) -> Path:
    d = Path(tempfile.mkdtemp())
    entries = []
    for i, (name, text) in enumerate(docs.items()):
        (d / name).write_text(text, encoding="utf-8")
        entries.append({**dict(id=f"d{i}", title=name, path=name, source="test",
                               licence="CC0-1.0", permission="test"), **(meta or {})})
    (d / "manifest.json").write_text(json.dumps(dict(documents=entries)), encoding="utf-8")
    return d


print("corpus")
chunks, man = load_corpus(FIXTURE)
check("the fixture loads", len(chunks) > 0 and man["chunk_count"] == len(chunks))
check("every chunk carries its note and section", all(c.doc_id and c.section for c in chunks))
check("every chunk carries a licence", all(c.licence for c in chunks))
check("no chunk exceeds the size limit", max(len(c.text.split()) for c in chunks) <= MAX_WORDS)
check("chunk ids are unique", len({c.chunk_id for c in chunks}) == len(chunks))
check("the corpus hash is stable", load_corpus(FIXTURE)[1]["chunks_sha256"] == man["chunks_sha256"])

d = corpus({"a.md": "# T\n## One\nalpha beta\n## Two\ngamma delta\n"})
c, _ = load_corpus(d)
check("headings split a note into sections", [x.section for x in c] == ["One", "Two"])
shutil.rmtree(d)

d = corpus({"long.md": "## S\n" + " ".join(f"w{i}" for i in range(400))})
c, _ = load_corpus(d)
check("a long section is split with overlap",
      len(c) == 3 and c[0].text.split()[-30:] == c[1].text.split()[:30], str(len(c)))
shutil.rmtree(d)

for field in ("licence", "permission", "source"):
    d = corpus({"a.md": "## S\ntext"}, meta={field: ""})
    try:
        load_corpus(d)
        check(f"a document with no {field} is refused", False)
    except CorpusError:
        check(f"a document with no {field} is refused", True)
    shutil.rmtree(d)

empty, _ = load_corpus(ROOT / "data" / "rag" / "corpus")
check("the course-notes corpus is empty until the owners supply notes", empty == [])

print("bm25")
bm = BM25([tokens("page replacement belady anomaly fifo"), tokens("disk scheduling elevator scan")])
check("the matching document scores highest", bm.scores(tokens("belady fifo")).argmax() == 0)
check("an unrelated query scores zero", bm.scores(tokens("javascript closure")).max() == 0)
check("stop words are ignored", tokens("What is the TLB?") == ["tlb"])

print("retrieval (BM25 only)")
r = Retriever(FIXTURE, dense=False)
hits = r.retrieve("Can LRU suffer from Belady's anomaly?", mode="bm25")
check("finds the Belady section", hits and hits[0]["chunk"].section == "Belady's anomaly")
check("returns at most k chunks", len(r.retrieve("page", k=2, mode="bm25")) <= 2)
check("a query sharing no word with the notes returns nothing",
      r.retrieve("javascript closure", mode="bm25") == [])
check("an empty corpus returns nothing", Retriever(ROOT / "data/rag/corpus", dense=False)
      .retrieve("paging") == [])

print("retrieval (hybrid, local embedding model)")
rh = Retriever(FIXTURE)
h = rh.retrieve("The system spends nearly all its time swapping pages and the CPU is idle")
check("a paraphrase finds thrashing", h and h[0]["chunk"].doc_id == "n08", str(h[:1]))
check("an off-topic question abstains", rh.retrieve("What is the capital of Australia?") == [])
check("the v1 gate is still available",
      isinstance(rh.retrieve("paging", gate="cosine"), list))

print("prompt and citations")
SYSTEM = "You are an Operating Systems tutor."
check("no hits leaves the trained prompt untouched", augment(SYSTEM, []) == SYSTEM)
aug = augment(SYSTEM, hits[:2])
check("the trained prompt is kept word for word at the start", aug.startswith(SYSTEM + "\n\n"))
check("each passage is labelled [S1], [S2]", "[S1] Page replacement" in aug and "[S2]" in aug)
check("the model is told never to invent a citation", "Never invent a citation" in aug)
check("the footer names each source", "`n07`" in sources_footer(hits[:2]))
check("no hits, no footer", sources_footer([]) == "")
check("valid and invented citations are told apart",
      cited("as [S1] and [S2] show, and [S7]", 2) == ({1, 2}, {7}))

print("\nALL RAG TESTS PASSED" if not FAILED else f"\n{len(FAILED)} FAILED: {FAILED}")
sys.exit(1 if FAILED else 0)
