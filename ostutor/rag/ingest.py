"""Ingest course materials into the RAG corpus (G2).

    # 1. record who supplied the files and on what terms (writes manifest entries + checksums)
    python -m ostutor.rag.ingest add data/rag/corpus docs/course/Week5/*.pptx \\
        --owner "Course instructor" --source "Week 5 slides, LMS" \\
        --permission "Supplied by the course instructor for use in this tutor"

    # 2. validate, extract and index everything - the single command after adding files
    python -m ostutor.rag.ingest data/rag/corpus

`build` (the default) refuses the whole corpus if any document lacks a manifest entry,
licence/permission, owner, source, date or checksum, or if a file changed after it was
recorded (corpus.validate). It then extracts every document to Markdown (cached),
chunks it, embeds the chunks on the CPU (cached under the corpus hash) and prints a
per-document summary. The gateway loads the result with OSTUTOR_RAG=<corpus dir>.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

from .corpus import CorpusError, load_corpus, sha256
from .extract import SUPPORTED


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def add(root: Path, files: list[str], owner: str, source: str, licence: str, permission: str,
        id_prefix: str = "doc", extra: dict | None = None) -> list[dict]:
    """Add (or refresh) manifest entries for files that live inside the corpus directory."""
    if not (licence or permission):
        raise SystemExit("refusing to add documents with neither --licence nor --permission")
    mpath = root / "manifest.json"
    manifest = json.loads(mpath.read_text(encoding="utf-8")) if mpath.is_file() else \
        dict(corpus=root.name, documents=[])
    by_path = {d["path"]: d for d in manifest["documents"]}
    ids = {d["id"] for d in manifest["documents"]}
    added = []
    for f in files:
        p = Path(f).resolve()
        rel = p.relative_to(root.resolve()).as_posix()
        if p.suffix.lower() not in SUPPORTED:
            raise SystemExit(f"{rel}: unsupported format {p.suffix}")
        entry = by_path.get(rel)
        if entry is None:
            base, n = f"{id_prefix}-{_slug(p.stem)}", 1
            new_id = base
            while new_id in ids:
                n += 1
                new_id = f"{base}-{n}"
            ids.add(new_id)
            entry = dict(id=new_id, title=p.stem.strip())
            manifest["documents"].append(entry)
            by_path[rel] = entry
        entry.update(path=rel, source=source, owner=owner, licence=licence, permission=permission,
                     added=dt.date.today().isoformat(), sha256=sha256(p), **(extra or {}))
        added.append(entry)
    mpath.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return added


def build(root: Path, dense: bool = True) -> dict:
    from .retrieve import Retriever
    t = time.perf_counter()
    try:
        r = Retriever(root, dense=dense)
    except CorpusError as e:
        raise SystemExit(f"REFUSED: {e}")
    per_doc = Counter(c.doc_id for c in r.chunks)
    docs = r.manifest["documents"]
    for d in docs:
        print(f"  {per_doc.get(d['id'], 0):5d}  {d['id']:<44} {(d.get('licence') or d.get('permission'))[:40]}")
    print(f"{len(docs)} documents, {len(r.chunks)} chunks, corpus {r.manifest['chunks_sha256'][:12]}, "
          f"built in {time.perf_counter() - t:.1f} s")
    empty = [d["id"] for d in docs if not per_doc.get(d["id"])]
    if empty:
        print(f"WARNING: {len(empty)} document(s) produced no text (scanned images?): {', '.join(empty)}")
    return dict(documents=len(docs), chunks=len(r.chunks), empty=empty)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="python -m ostutor.rag.ingest")
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("add", help="record files in the manifest")
    a.add_argument("corpus")
    a.add_argument("files", nargs="+")
    a.add_argument("--owner", required=True)
    a.add_argument("--source", required=True)
    a.add_argument("--licence", default="")
    a.add_argument("--permission", default="")
    a.add_argument("--id-prefix", default="doc")
    b = sub.add_parser("build", help="validate, extract and index (default)")
    b.add_argument("corpus")
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in ("add", "build", "-h", "--help"):
        argv = ["build"] + argv
    args = ap.parse_args(argv)
    if args.cmd == "add":
        out = add(Path(args.corpus), args.files, args.owner, args.source, args.licence,
                  args.permission, args.id_prefix)
        print(f"recorded {len(out)} document(s) in {Path(args.corpus) / 'manifest.json'}")
    elif args.cmd == "build":
        build(Path(args.corpus))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
