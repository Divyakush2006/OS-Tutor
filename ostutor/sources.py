"""Source registry and ingestion adapters.

Every adapter emits canonical Records with licence and line-level provenance, so
any row in the shipped dataset is traceable to the file and index it came from.
Adding a new bucket means adding ONE adapter here; nothing downstream changes.
"""
import json
import re
from collections import Counter

from .config import EXCLUDED, RAW, SOURCES
from .schema import Record

_MOVE = re.compile(r"^\((?P<move>[a-z ]+)\)\s*", re.I)
_BRACE = re.compile(r"\{\{(.*?)\}\}")


def _load(name):
    p = RAW / f"{name}.jsonl"
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f]


def _mk(category, subcategory, mode, domain, messages, source,
        lineage=None, difficulty=0.0, template_id=""):
    meta = SOURCES.get(source, dict(license="UNKNOWN", commercial=False, attribution=False))
    return Record(category=category, subcategory=subcategory, mode=mode, domain=domain,
                  messages=messages, source=source, license=meta["license"],
                  commercial_ok=meta["commercial"], attribution=meta["attribution"],
                  difficulty=difficulty, template_id=template_id,
                  lineage=dict(lineage or {}, source=source)).dict()


# ------------------------------------------------------------------ tutoring
def ingest_tutoring():
    """MathDial is MATHS, not OS. It is a BEHAVIOUR seed: teacher moves
    (focus/probing/generic/telling), hint-before-answer and misconception
    diagnosis transfer across domains. Rows are tagged domain='math' so the
    renderer cannot label them 'Operating Systems tutor'."""
    rows, moves = [], Counter()
    # TRAIN split only. mathdial_test is an evaluation split: ingesting it and then
    # decontaminating it away wasted it and inflated the "contamination" count.
    for split in ("train",):
        for i, r in enumerate(_load(f"mathdial_{split}")):
            turns = [t.strip() for t in (r.get("conversation") or "").split("|EOM|") if t.strip()]
            msgs, ok = [], True
            for t in turns:
                if t.startswith("Teacher:"):
                    body = t[len("Teacher:"):].strip()
                    m = _MOVE.match(body)
                    if m:
                        moves[m.group("move").strip().lower()] += 1
                        body = _MOVE.sub("", body)
                    msgs.append(dict(role="assistant", content=body.strip()))
                elif t.startswith("Student:"):
                    msgs.append(dict(role="user", content=t[len("Student:"):].strip()))
                else:
                    ok = False
            if not ok or len(msgs) < 4:
                continue
            if msgs[0]["role"] != "user":
                msgs.insert(0, dict(role="user", content=(r.get("question") or "").strip()))
            rows.append(_mk("tutoring", "mathdial_dialogue", "tutor", "math", msgs,
                            "eth-nlped/mathdial",
                            lineage=dict(file=f"mathdial_{split}.jsonl", row=i,
                                         qid=r.get("qid")),
                            difficulty=min(1.0, len(msgs) / 16)))
    # v3.0: OS tutoring comes from SELF-DISTILLED replies (tools/generate_theory_sdft.py):
    # the base model tutoring a student through a simulator-verified problem after a
    # wrong attempt built from a real misconception, filtered so that no reply
    # reveals the answer or affirms the mistake. The v2 template-generated OS
    # dialogues (tutoring_os_dialogues.jsonl) are retired: the same template family
    # made v2.2's explanations formulaic. The file is kept, not ingested.
    from .theory_filter import accept_tutor
    for i, r in enumerate(_load("tutor_sdft")):
        text, why = accept_tutor(r)
        if text is None:
            continue
        rows.append(_mk("tutoring", f"os_{r['kind']}", "tutor", "os",
                        [dict(role="user", content=r["user"]),
                         dict(role="assistant", content=text)],
                        "simulators/own",
                        # The problem inside a tutoring row is simulator-generated, so
                        # its identity is its PARAMETERS. Without a fingerprint these
                        # rows fell back to distinctive-n-gram decontamination, which
                        # misfires on template text next to small random integers
                        # exactly as it does for procedural rows: it removed 823 of
                        # 1,418 of them (58%) - the same 58% the decontaminate()
                        # docstring records for the procedural case.
                        lineage=dict(file="tutor_sdft.jsonl", row=i, self_distilled=True,
                                     fingerprint=fingerprint(r.get("verify", {}))),
                        difficulty=0.6))
    return rows, dict(moves)


# --------------------------------------------------------------------- shell
def _shell(nl, cmd, source, sub, lineage=None):
    clean = _BRACE.sub(r"\1", cmd).strip()
    diff = min(1.0, (clean.count("|") + clean.count("-") / 3 + len(clean) / 200) / 4)
    return _mk("shell", sub, "shell", "linux",
               [dict(role="user", content=nl.strip()),
                dict(role="assistant", content=clean)],
               source, lineage, difficulty=diff)


def ingest_shell():
    rows = []
    for split in ("train", "dev"):
        for i, r in enumerate(_load(f"tldr_{split}")):
            if r.get("nl") and r.get("cmd"):
                rows.append(_shell(r["nl"], r["cmd"], "neulab/tldr", "tldr",
                                   dict(file=f"tldr_{split}.jsonl", row=i,
                                        cmd_name=r.get("cmd_name"))))
    for i, r in enumerate(_load("nl2bash_official_mit")):
        if r.get("nl") and r.get("bash"):
            rows.append(_shell(r["nl"], r["bash"], "TellinaTool/nl2bash:data/bash",
                               "nl2bash", dict(file="nl2bash_official_mit.jsonl", row=i)))
    # NL2SH-ALFA's 300 human-verified rows are its TEST configuration and serve as
    # this project's shell evaluation set. They are never ingested for training.
    for i, r in enumerate(_load("intercode_nl2bash_curated")):
        if r.get("query") and r.get("gold"):
            rows.append(_shell(r["query"], r["gold"], "epinnock/intercode-nl2bash",
                               "intercode_curated",
                               dict(file="intercode_nl2bash_curated.jsonl", row=i,
                                    verified=True)))
    return rows


# -------------------------------------------------------------------- replay
def ingest_replay():
    """Anti-forgetting anchor set. SmolTalk2 is used ONLY via `_no_think` splits:
    its `_think` splits are Nemotron/OpenThoughts reasoning traces, and feeding
    chain-of-thought replay to a model chosen for having no thinking mode would
    reintroduce the behaviour through the side door."""
    rows = []
    for i, r in enumerate(_load("tulu3_sft_sample20k_commercial_safe")):
        m = r.get("messages") or []
        if len(m) >= 2:
            rows.append(_mk("replay", r.get("source", "tulu3"), "explain", "general",
                            [dict(role=x["role"], content=x["content"]) for x in m],
                            "allenai/tulu-3-sft-mixture",
                            dict(file="tulu3_sft_sample20k_commercial_safe.jsonl", row=i)))
    for i, r in enumerate(_load("smoltalk2_no_think_replay")):
        m = r.get("messages") or []
        if len(m) >= 2:
            rows.append(_mk("replay", r.get("_split", "smoltalk2"), "explain", "general",
                            [dict(role=x["role"], content=x["content"]) for x in m],
                            "HuggingFaceTB/smoltalk2",
                            dict(file="smoltalk2_no_think_replay.jsonl", row=i)))
    return rows


# --------------------------------------------------- procedural / conceptual
def fingerprint(verify):
    """Identity of a generated problem = its PARAMETERS, not its wording. Two rows
    with the same fingerprint are the same problem however they are phrased."""
    import hashlib
    # v3.0: presentation-only fields (which quantity was asked, hex vs decimal, the
    # direction stated via a previous request, Need given instead of Max, ...) do not
    # change the problem, so they must not change its identity either.
    core = {k: v for k, v in verify.items()
            if k not in ("ask", "hex", "prev", "assumed", "given", "total", "la_as_size")}
    return hashlib.blake2b(json.dumps(core, sort_keys=True).encode(),
                           digest_size=12).hexdigest()


def ingest_procedural():
    rows = []
    # v3.0: only the v3 pool is ingested. The v2 files (procedural_simulated*.jsonl)
    # use the v2 solution format (implicit decisions, 0-based holes) and 47 of their
    # rows had duplicate process names; mixing formats would teach two answer styles.
    # They stay on disk as the v2 record. The OOD holdout is never ingested.
    for p in sorted(RAW.glob("procedural_v3_*.jsonl")):
        if "holdout" in p.name:
            continue
        with open(p, encoding="utf-8") as f:
            for i, line in enumerate(f):
                r = json.loads(line)
                rows.append(_mk("procedural", r.get("topic", "unknown"), "solve", "os",
                                [dict(role="user", content=r["problem"]),
                                 dict(role="assistant", content=r["solution"])],
                                "simulators/own",
                                dict(file=p.name, row=i, seed=r.get("seed"),
                                     verified=r.get("verified", False),
                                     regime=r.get("regime", "normal"),
                                     fingerprint=fingerprint(r.get("verify", {}))),
                                difficulty=r.get("difficulty", 0.5),
                                template_id=r.get("template_id", r.get("topic", ""))))
    return rows


def ingest_conceptual():
    """v3.0 theory: the base model's own answers to the hand-written question bank
    (self-distillation, sanitised and fact-checked by theory_filter) plus the
    hand-written gold explanations of the most-confused topics. The v2 template-
    generated misconception rows (conceptual_misconceptions.jsonl) are retired:
    measured through the chat UI they made explanations formulaic and worse than
    the untuned base. The file is kept, not ingested."""
    from .simulators.theory_gold import GOLD
    from .theory_filter import accept_theory
    rows = []
    for i, r in enumerate(_load("theory_sdft")):
        text, why = accept_theory(r)
        if text is None:
            continue
        rows.append(_mk("conceptual", f"sdft_{r['area']}", "explain", "os",
                        [dict(role="user", content=r["user"]),
                         dict(role="assistant", content=text)],
                        "simulators/own",
                        dict(file="theory_sdft.jsonl", row=i, style=r.get("style"),
                             self_distilled=True),
                        difficulty=0.5, template_id=f"sdft_{r['area']}"))
    for i, (q, a) in enumerate(GOLD):
        rows.append(_mk("conceptual", "gold_explanation", "explain", "os",
                        [dict(role="user", content=q), dict(role="assistant", content=a)],
                        "simulators/own", dict(file="theory_gold.py", row=i, hand_written=True),
                        difficulty=0.7, template_id=f"gold_{i}"))
    return rows


def ingest_all():
    tut, moves = ingest_tutoring()
    buckets = dict(procedural=ingest_procedural(), conceptual=ingest_conceptual(),
                   tutoring=tut, shell=ingest_shell(), replay=ingest_replay())
    buckets = {k: [r for r in v if r["source"] not in EXCLUDED] for k, v in buckets.items()}
    meta = dict(teacher_moves=moves,
                by_category={k: len(v) for k, v in buckets.items()},
                excluded_sources=EXCLUDED)
    return buckets, meta
