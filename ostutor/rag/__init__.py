"""Retrieval over owner-supplied course notes (G2).

    python tools/rag_eval.py data/rag/fixture     # measure retrieval
    OSTUTOR_RAG=data/rag/corpus  (gateway env)    # turn it on for students

Why retrieval, and why only for prose. The verified solver already guarantees the
numbers in a worked problem; a document cannot certify a schedule for a student's own
inputs. What retrieval CAN do is ground a concept explanation in the course's own notes
and let the student check it, because every claim carries a citation to a named note
and section. So RAG is wired into the explain and analyze modes only. Tutor mode does
not retrieve (a retrieved passage could state the answer the student is working
towards), and solve mode does not need to.

Everything runs on the CPU, so it cannot slow generation on the GPU:
BM25 (pure Python) and all-MiniLM-L6-v2 embeddings (Apache-2.0, loaded from the local
cache only), fused with reciprocal-rank fusion.
"""
from .corpus import Chunk, load_corpus  # noqa: F401
from .retrieve import Retriever, augment  # noqa: F401
