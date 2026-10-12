"""Build the dataset end to end and emit a reproducibility manifest.

One command, one artefact set, one manifest. The manifest records the config
hash, every source file and its hash, per-stage counters, per-category analysis,
gate results and the SHA-256 of every output - so a reviewer can attribute a
dataset to a configuration, and a rerun can be proven identical.

    python -m ostutor.build
"""
import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from . import config as C
from . import dedup, gates, mix, quality, render, select, sources
from .analysis.categories import analyze_all
from .clean import clean_records


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return sha256(path)


def eval_texts():
    """Everything the model will ever be scored on. Nothing here may reach train."""
    out = []

    def load(n):
        p = C.RAW / f"{n}.jsonl"
        return [json.loads(l) for l in open(p, encoding="utf-8")] if p.exists() else []

    for n in ("mmlu_college_computer_science", "mmlu_computer_security",
              "mmlu_machine_learning", "mmlu_pro_computer_science"):
        for r in load(n):
            opts = r.get("options", r.get("choices", [])) or []
            out.append(f"{r.get('question','')} " + " ".join(map(str, opts)))
    for n in ("ceval_operating_system_val", "ceval_operating_system_dev"):
        out += [str(r.get("question", "")) for r in load(n)]
    out += [str(r.get("question", "")) for r in load("mathdial_test")]
    out += [str(r.get("nl", "")) for r in load("nl2sh_alfa_test_train")]
    for hn in ("procedural_ood_holdout", "procedural_v3_holdout"):
        out += [str(r.get("problem", "")) for r in load(hn)]
    for p in (C.ROOT / "data" / "eval").glob("*.jsonl"):
        out += [str(json.loads(l).get("problem", "")) for l in open(p, encoding="utf-8")]
    # v3.0: the theory benchmark and the general-knowledge forgetting items too
    for d in ("eval_theory", "eval_general"):
        for p in (C.ROOT / "data" / d).glob("*.jsonl"):
            for l in open(p, encoding="utf-8"):
                r = json.loads(l)
                out.append(f"{r.get('question', '')} " + " ".join(map(str, r.get("choices", []))))
    return [t for t in out if t.strip()]


def eval_fingerprints():
    """Parameter fingerprints of every generated item the model will be scored
    on: the OS-Solve suites and the OOD holdout."""
    fps = set()
    files = (list((C.ROOT / "data" / "eval").glob("*.jsonl"))
             + [C.RAW / "procedural_ood_holdout.jsonl", C.RAW / "procedural_v3_holdout.jsonl"])
    for p in files:
        if p.exists():
            for l in open(p, encoding="utf-8"):
                r = json.loads(l)
                if "verify" in r:
                    fps.add(sources.fingerprint(r["verify"]))
    return fps


def embed(texts):
    from sentence_transformers import SentenceTransformer
    import torch
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"    embedding {len(texts)} texts on {dev}", flush=True)
    m = SentenceTransformer(C.EMBED_MODEL, device=dev)
    return m.encode(texts, batch_size=256, convert_to_numpy=True,
                    normalize_embeddings=True, show_progress_bar=False)


def step(i, name):
    print(f"\n[{i}] {name}", flush=True)


def main():
    t0 = time.time()
    M = dict(dataset=C.DATASET_NAME, pipeline_version=C.PIPELINE_VERSION,
             built_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
             python=platform.python_version(), seed=C.SEED,
             config_sha256=sha256(Path(C.__file__)), stages={})
    C.REPORTS.mkdir(parents=True, exist_ok=True)

    # 1 -------------------------------------------------------------- ingest
    step(1, "ingest")
    buckets, ing = sources.ingest_all()
    M["stages"]["ingest"] = ing
    M["source_files"] = {p.name: dict(sha256=sha256(p), bytes=p.stat().st_size)
                         for p in sorted(C.RAW.glob("*.jsonl"))}
    print(f"    {sum(len(v) for v in buckets.values())} records | {ing['by_category']}")

    # 2 ---------------------------------------------- per-category analysis
    step(2, "per-category forensic analysis (before any cleaning)")
    # Offline `bash -n` results (tools/validate_shell.sh): one failing id per line,
    # written atomically. A missing file means fewer shell drops, not a broken build.
    bl_path = C.BUILD / "shell_syntax_fail.txt"
    blocklist = {}
    if bl_path.exists():
        blocklist = {l.strip(): True for l in bl_path.read_text(encoding="utf-8").splitlines()
                     if l.strip()}
    else:
        print("    WARNING: no shell syntax results - run tools/validate_shell.sh")
    M["shell_syntax_failures"] = len(blocklist)
    analysis = analyze_all(buckets, blocklist, C.ANALYSIS)
    M["stages"]["analysis"] = {
        k: dict(rows=v.get("rows", 0),
                actionable_defects=v.get("actionable_defects", {}),
                rejected_rules=list(v.get("rejected_rules", {})),
                distinct_answer_ratio=v.get("redundancy", {}).get("distinct_ratio"))
        for k, v in analysis.items()}
    for k, v in analysis.items():
        if not v.get("rows"):
            print(f"    {k:<12} NOT BUILT")
            continue
        ad = v.get("actionable_defects", {})
        rj = v.get("rejected_rules", {})
        print(f"    {k:<12} {v['rows']:>6} rows | defects {sum(ad.values()):>5} "
              f"| rules rejected on evidence: {len(rj)} "
              f"| distinct answers {v['redundancy']['distinct_ratio']:.3f}")

    # 3 ---------------------------------------------- clean / scrub / repair
    step(3, "clean / scrub / repair")
    rows = [r for v in buckets.values() for r in v]
    rep = {}
    rows = clean_records(rows, shell_blocklist=blocklist, report=rep)
    M["stages"]["clean"] = rep
    print(f"    kept {rep['kept']}/{rep['input']} | repaired "
          f"{sum(rep['repaired'].values())} | PII redactions "
          f"{sum(rep['pii_redactions'].values())}")

    # 4 ------------------------------------------------ exact + lexical dedup
    step(4, "deduplicate (exact + lexical)")
    rep = {}
    rows = dedup.exact(rows, rep)
    rows = dedup.lexical(rows, rep)
    M["stages"]["dedup"] = rep
    print(f"    exact -{rep['exact_removed']} | lexical -{rep['lexical_removed']} "
          f"| {len(rows)} remain")

    # 5 -------------------------------------------------------- decontaminate
    step(5, "decontaminate vs held-out eval + OOD")
    rep = {}
    rows = dedup.decontaminate(rows, eval_texts(), rep,
                               eval_fingerprints=eval_fingerprints())
    M["stages"]["decontaminate"] = rep
    print(f"    removed {rep['removed_total']} {rep['removed']} | {len(rows)} remain")

    # 6 ---------------------------------------------------------------- score
    step(6, "score")
    rows = quality.score_all(rows)
    M["stages"]["score"] = {
        c: round(float(np.mean([r["quality"] for r in rows if r["category"] == c])), 4)
        for c in sorted({r["category"] for r in rows})}
    print(f"    {M['stages']['score']}")

    # 7 ------------------------------ gold selection with RATIO ENFORCEMENT
    step(7, "gold selection: quality gate -> semantic dedup -> farthest-point")
    emb = embed([" ".join(m["content"] for m in r["messages"])[:2000] for r in rows])
    sel_report = {}
    gold, total, binding = select.select_all(
        rows, emb, lambda rr, ee: dedup.semantic(rr, ee), sel_report)
    M["stages"]["gold_selection"] = sel_report
    sz = sel_report["_sizing"]
    print(f"    achievable total {sz['achievable_total']} "
          f"(ceiling {sz['target_ceiling']}), bound by '{sz['binding_category']}'")
    for c in C.MIX:
        d = sel_report.get(c, {})
        print(f"    {c:<12} pool {d.get('raw_pool',0):>6} -> gate {d.get('after_gate',0):>6}"
              f" -> distinct {d.get('distinct_supply',0):>6} -> picked "
              f"{d.get('selected',0):>5}  meanQ {d.get('mean_quality',0):.3f}"
              f"  [{d.get('status','-')}]")

    # diversity per category, measured on the SELECTED rows
    idx_by_id = {r["id"]: i for i, r in enumerate(rows)}
    div = {}
    for c in C.MIX:
        sub = [idx_by_id[r["id"]] for r in gold if r["category"] == c and r["id"] in idx_by_id]
        if len(sub) >= 2:
            div[c] = dedup.diversity(emb[sub])
    M["stages"]["diversity"] = {k: round(v, 4) for k, v in div.items()}
    print(f"    diversity (1 - mean cosine): "
          f"{ {k: round(v,3) for k,v in div.items()} }")

    # 8 --------------------------------------------------------------- render
    step(8, "render to ChatML")
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(str(C.MODEL))
    rep = {}
    gold = render.render(gold, tok, rep)
    M["stages"]["render"] = rep
    print(f"    {rep['rendered']} rows | tokens mean {rep['mean']} p99 {rep['p99']} "
          f"max {rep['max']} | total {rep['total_tokens']:,}")

    # 9 ------------------- split FIRST, then rectifier on the shipped train rows
    step(9, "split, then rectifier interleaving on the train split")
    ood_extra = []
    p = C.RAW / "procedural_v3_holdout.jsonl"
    if p.exists():
        raw_ood = [json.loads(l) for l in open(p, encoding="utf-8")]
        ood_rows = sources._mk  # reuse the canonical constructor
        tmp = []
        for i, r in enumerate(raw_ood):
            tmp.append(ood_rows("procedural", r.get("topic", "unknown"), "solve", "os",
                                [dict(role="user", content=r["problem"]),
                                 dict(role="assistant", content=r["solution"])],
                                "simulators/own",
                                dict(file=p.name, row=i, seed=r.get("seed"),
                                     verified=r.get("verified", False),
                                     holdout_framing=True)))
        ood_extra = render.render(quality.score_all(tmp), tok, {})

    def order_fn(rs):
        return mix.interleave({c: [r for r in rs if r["category"] == c]
                               for c in sorted({r["category"] for r in rs})}, C.SEED)

    rep = {}
    train, val, ood = render.split(gold, C.SEED, order_fn, ood_extra, rep)
    M["stages"]["split"] = rep
    print(f"    train {rep['train']} | val {rep['val']} | ood {rep['ood']} "
          f"(of which {rep['ood_from_holdout_file']} genuinely OOD)")

    # 10 ----------------------- verify rectifier invariants ON THE SHIPPED ROWS
    step(10, "verify rectifier invariants on shipped train rows")
    ok, inv = mix.verify_invariants(train)
    M["stages"]["rectifier"] = inv
    print(f"    category run {inv['longest_same_category_run']}/{inv['max_run_allowed']}"
          f" | source run {inv['longest_same_source_run']}/{inv['max_source_run_allowed']}"
          f" | spaced replay {inv['replay_gap_early']}->{inv['replay_gap_late']}"
          f" | worst spacing violation {inv['worst_spacing_violation']}")

    # 11 --------------------------------------------------------- release gates
    step(11, "release gates")
    passed, results, extra = gates.run_gates(
        train, inv, div, rep["ood"], rep["ood_from_holdout_file"])
    gates.print_gates(results)
    M["gates"] = results
    M["gates_passed"] = passed
    M["gate_metrics"] = extra

    outs = {}
    for name, part in (("train", train), ("val", val), ("ood", ood)):
        outs[f"{name}.jsonl"] = write_jsonl(C.BUILD / f"{name}.jsonl", part)
    M["artifacts"] = outs
    M["duration_sec"] = round(time.time() - t0, 1)
    with open(C.REPORTS / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(M, f, indent=2)

    print(f"\n{'BUILD PASSED' if passed else 'BUILD FAILED'} in {M['duration_sec']}s")
    print(f"  artefacts -> {C.BUILD}")
    print(f"  manifest  -> {C.REPORTS / 'manifest.json'}")
    print(f"  analysis  -> {C.ANALYSIS}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
