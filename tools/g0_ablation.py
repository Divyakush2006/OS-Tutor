"""G0: measure what each component of OS Tutor contributes.

    python tools/g0_ablation.py                 # everything, resumable
    python tools/g0_ablation.py --phases suite  # just the 57-item suite
    python tools/g0_ablation.py --phases ood factcheck

Phases
  suite      57 hand-written items, six configurations on the SERVED path:
             base, base+solver, v2.2, v2.2+solver, v3, v3+solver.
  ood        the 600-item OOD holdout, end to end through the served configuration
             (v3 answers, untuned base extracts), with extraction scored field by
             field against the simulator parameters each item was generated from.
  factcheck  10 targeted misconception probes (base and v3) and the 70-item broad
             theory set (v3): how often the fact checker fires and what it changes.

One adapter per server, always. reports/benchmark_v3.json is void because it loaded
two adapters into one llama-server and switched with per-request scales; that does
not isolate them (v3 measured 17/57 there vs 36/57 alone). Each server here is
started with exactly the adapter its configurations need, and the run aborts if
/lora-adapters reports anything else.

Output: reports/g0/<run>/ — one JSON per configuration or phase (written as soon as it
finishes, so an interrupted run resumes where it stopped), plus summary.json and
summary.md. Nothing outside that directory is written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "serve"))

from ostutor import config as C  # noqa: E402
from ostutor.evaluation.extraction import fields_match  # noqa: E402
from ostutor.evaluation.harness import grade  # noqa: E402
from ostutor.evaluation.stats import paired  # noqa: E402
from ostutor.solver import EXTRACT_PROMPT, solve  # noqa: E402
from ostutor.theory_filter import fact_flags  # noqa: E402

PORT = 8081
SERVER = f"http://127.0.0.1:{PORT}"
EXE = ROOT / "serve" / "llama.cpp" / "bin" / "llama-server.exe"
GGUF = ROOT / "models" / "gguf"
BASE = GGUF / "qwen3-4b-instruct-2507-Q8_0.gguf"
LORAS = {"v2.2": GGUF / "ostutor-v2.2-lora-f16.gguf", "v3": GGUF / "ostutor-v3-lora-f16.gguf"}
# The serving configuration from serve/start_tutor.ps1, so every number is the one a
# student would actually get.
SERVER_ARGS = ["-ngl", "99", "-c", "20480", "-np", "1", "-fa", "on",
               "-ctk", "q8_0", "-ctv", "q8_0", "--jinja"]
ANSWER_TOKENS = 4096      # same ceiling as tools/benchmark.py, so 36/57 is comparable
EXTRACT_TOKENS = 900      # same as the gateway's extraction call
EXPLAIN_TOKENS = 1500

SUITE = ROOT / "data" / "eval" / "os_freeform.jsonl"
OOD = ROOT / "data" / "build" / "ood.jsonl"
OOD_SOURCE = ROOT / "data" / "raw"
PROBES = ROOT / "data" / "eval_factcheck" / "probes.jsonl"
THEORY = ROOT / "data" / "eval_theory" / "os_theory_mcq.jsonl"

# (server name, adapter or None, [(label, answer scale, delegate)])
# answer scale None = send no lora field (the base server has no adapter loaded).
SERVERS = [
    ("base", None, [("base+solver", None, True), ("base", None, False)]),
    ("v2.2", "v2.2", [("v2.2+solver", 1.0, True), ("v2.2", 1.0, False)]),
    ("v3", "v3", [("v3+solver", 1.0, True), ("v3", 1.0, False)]),
]


# ---------------------------------------------------------------- llama-server

def _get(path: str, timeout: float = 3):
    return json.load(urllib.request.urlopen(SERVER + path, timeout=timeout))


def server_running() -> bool:
    try:
        _get("/health")
        return True
    except Exception:
        return False


def check_adapters(reported: list[dict], expected: str | None) -> None:
    """Abort unless the server holds exactly the adapter this phase needs."""
    names = sorted(Path(a.get("path", "")).name for a in reported)
    want = [] if expected is None else [LORAS[expected].name]
    if names != want:
        raise SystemExit(f"server adapters {names} != expected {want}; refusing to measure "
                         "(see the void-benchmark note in this file's docstring)")


def start_server(adapter: str | None, log: Path) -> subprocess.Popen:
    if server_running():
        raise SystemExit(f"something is already serving on :{PORT}; stop it first "
                         "(serve/stop_tutor.ps1)")
    args = [str(EXE), "-m", str(BASE), *SERVER_ARGS, "--host", "127.0.0.1", "--port", str(PORT)]
    if adapter:
        args[3:3] = ["--lora", str(LORAS[adapter])]
    log.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(args, cwd=ROOT, stdout=open(log, "w", encoding="utf-8"),
                            stderr=subprocess.STDOUT)
    for _ in range(300):
        if proc.poll() is not None:
            raise SystemExit(f"llama-server exited early; see {log}")
        if server_running():
            check_adapters(_get("/lora-adapters"), adapter)
            return proc
        time.sleep(1)
    proc.kill()
    raise SystemExit(f"llama-server did not become healthy; see {log}")


def stop_server(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
    for _ in range(30):
        if not server_running():
            return
        time.sleep(1)


def chat(system: str, user: str, max_tokens: int, scale: float | None) -> dict:
    # cache_prompt=False: the prompt cache reuses the KV of a shared prefix from whatever
    # request came before, which changes batching and so the logits; with it on, greedy
    # decoding is NOT reproducible across runs (tools/g0_diagnostics.py: 5/6 differ).
    body = dict(messages=[dict(role="system", content=system), dict(role="user", content=user)],
                temperature=0, max_tokens=max_tokens, cache_prompt=False)
    if scale is not None:
        body["lora"] = [dict(id=0, scale=scale)]
    req = urllib.request.Request(SERVER + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=1800))
    c = d["choices"][0]
    return dict(text=c["message"]["content"] or "", finish=c.get("finish_reason"),
                tokens=d.get("usage", {}).get("completion_tokens"))


# ---------------------------------------------------------------- provenance

def _sha256(path: Path, cache: dict) -> str:
    st = path.stat()
    key = f"{path.name}:{st.st_size}:{int(st.st_mtime)}"
    if key not in cache:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(1 << 22), b""):
                h.update(block)
        cache[key] = h.hexdigest()
    return cache[key]


def provenance(out: Path) -> dict:
    git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True,  # noqa: E731
                                    text=True).stdout.strip()
    cache_file = ROOT / "reports" / "g0" / "model_hashes.json"
    cache = json.loads(cache_file.read_text()) if cache_file.exists() else {}
    models = {p.name: _sha256(p, cache) for p in [BASE, *LORAS.values()]}
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(cache, indent=1))
    manifest = json.loads((ROOT / "reports" / "manifest.json").read_text(encoding="utf-8"))
    version = subprocess.run([str(EXE), "--version"], capture_output=True, text=True)
    prompt = lambda s: hashlib.sha256(s.encode()).hexdigest()[:16]  # noqa: E731
    return dict(
        started_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        commit=git("rev-parse", "HEAD"), dirty=bool(git("status", "--porcelain")),
        models_sha256=models, dataset_train_sha256=manifest["artifacts"]["train.jsonl"],
        llama_cpp=(version.stdout + version.stderr).strip().splitlines()[:2],
        server_args=SERVER_ARGS, decoding=dict(temperature=0, answer_tokens=ANSWER_TOKENS,
                                               extract_tokens=EXTRACT_TOKENS,
                                               cache_prompt=False),
        prompts_sha256_16=dict(extract=prompt(EXTRACT_PROMPT),
                               solve=prompt(C.system_for("solve", "os")),
                               explain=prompt(C.system_for("explain", "os"))),
        out=str(out.relative_to(ROOT)),
    )


# ---------------------------------------------------------------- phases

def _load(path: Path) -> list[dict]:
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def _answer(question: str, delegate: bool, extract_scale, answer_scale) -> dict:
    """One question through either the plain model or the solver pipeline."""
    trace: list = []
    text, meta = None, {}
    if delegate:
        text, meta = solve(question, lambda s, u: chat(s, u, EXTRACT_TOKENS, extract_scale)["text"],
                           trace=trace)
    finish, tokens = "stop", 0
    if text is None:
        r = chat(C.system_for("solve", "os"), question, ANSWER_TOKENS, answer_scale)
        text, finish, tokens = r["text"], r["finish"], r["tokens"]
    return dict(text=text, finish=finish, tokens=tokens, delegated=bool(meta.get("delegated")),
                reason=meta.get("reason"), trace=trace)


def run_suite(label: str, extract_scale, answer_scale, delegate: bool, out: Path,
              limit: int | None = None) -> dict:
    path = out / f"suite_{label}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    items, t0 = [], time.time()
    for i, rec in enumerate(_load(SUITE)[:limit]):
        t = time.time()
        r = _answer(rec["problem"], delegate, extract_scale, answer_scale)
        g = grade(rec, r["text"])
        items.append(dict(id=rec["id"], kind=rec["verify"]["kind"], correct=bool(g["final_correct"]),
                          delegated=r["delegated"], reason=r["reason"], finish=r["finish"],
                          seconds=round(time.time() - t, 1), trace=r["trace"], output=r["text"]))
        if (i + 1) % 10 == 0:
            print(f"    {label}: {i + 1} correct so far {sum(x['correct'] for x in items)}",
                  flush=True)
    res = dict(label=label, n=len(items), correct=sum(x["correct"] for x in items),
               delegated=sum(x["delegated"] for x in items),
               truncated=sum(x["finish"] == "length" for x in items),
               seconds=round(time.time() - t0, 1), items=items)
    res["accuracy"] = round(res["correct"] / res["n"], 4)
    path.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"  {label:<12} {res['correct']}/{res['n']} = {res['accuracy']:.1%}  delegated {res['delegated']}"
          f"  truncated {res['truncated']}  ({res['seconds']:.0f}s)", flush=True)
    return res


def _ood_records() -> list[dict]:
    """The 600 OOD rows, joined back to the simulator parameters they came from."""
    sources: dict[str, list] = {}
    out = []
    for r in _load(OOD):
        lin = r["lineage"]
        if lin["file"] not in sources:
            sources[lin["file"]] = _load(OOD_SOURCE / lin["file"])
        src = sources[lin["file"]][lin["row"]]
        question = next(m["content"] for m in r["messages"] if m["role"] == "user")
        if question.strip() != src["problem"].strip():
            raise SystemExit(f"OOD row {r['id']} does not match its source row; lineage broken")
        out.append(dict(id=r["id"], subcategory=r["subcategory"], problem=question,
                        verify=src["verify"]))
    return out


def run_ood(out: Path, limit: int | None = None) -> dict:
    """End to end through the served configuration: v3 answers, base extracts."""
    final, partial = out / "ood.json", out / "ood.partial.jsonl"
    if final.exists():
        return json.loads(final.read_text(encoding="utf-8"))
    done = {json.loads(l)["id"]: json.loads(l) for l in open(partial, encoding="utf-8")} \
        if partial.exists() else {}
    recs, t0 = _ood_records()[:limit], time.time()
    with open(partial, "a", encoding="utf-8") as fp:
        for i, rec in enumerate(recs):
            if rec["id"] in done:
                continue
            t = time.time()
            r = _answer(rec["problem"], True, 0.0, 1.0)
            g = grade(rec, r["text"])
            accepted = next((e["params"] for e in r["trace"] if e["outcome"] == "ok"), None)
            exact, wrong = fields_match(accepted, rec["verify"])
            item = dict(id=rec["id"], kind=rec["verify"]["kind"], subcategory=rec["subcategory"],
                        correct=bool(g["final_correct"]), delegated=r["delegated"],
                        reason=r["reason"], finish=r["finish"], extraction_exact=exact,
                        wrong_fields=wrong, outcomes=[e["outcome"] for e in r["trace"]],
                        seconds=round(time.time() - t, 1),
                        output=None if r["delegated"] else r["text"])
            done[rec["id"]] = item
            fp.write(json.dumps(item) + "\n")
            fp.flush()
            if len(done) % 25 == 0:
                c = sum(x["correct"] for x in done.values())
                print(f"    ood: {len(done)}/600 correct {c} "
                      f"({(time.time() - t0) / 60:.0f} min)", flush=True)
    items = [done[r["id"]] for r in recs]
    res = dict(n=len(items), items=items, per_kind=ood_metrics(items),
               overall=ood_metrics(items, overall=True))
    final.write_text(json.dumps(res, indent=1), encoding="utf-8")
    partial.unlink()
    return res


def ood_metrics(items: list[dict], overall: bool = False) -> dict:
    groups = {"all": items} if overall else defaultdict(list)
    if not overall:
        for x in items:
            groups[x["kind"]].append(x)

    def m(xs):
        n = len(xs)
        dele = [x for x in xs if x["delegated"]]
        fall = [x for x in xs if not x["delegated"]]
        ever_ungrounded = sum("ungrounded" in x["outcomes"] for x in xs)
        final_ungrounded = sum(x["reason"] == "extraction could not be grounded in the question"
                               and "ungrounded" in x["outcomes"] for x in xs)
        rate = lambda a, b: round(a / b, 4) if b else None  # noqa: E731
        return dict(
            n=n,
            extraction_accuracy=rate(sum(x["extraction_exact"] for x in xs), n),
            grounding_rejection_rate_any_attempt=rate(ever_ungrounded, n),
            grounding_rejection_rate_final=rate(final_ungrounded, n),
            invalid_json_rate_any_attempt=rate(sum("invalid_json" in x["outcomes"] for x in xs), n),
            delegation_rate=rate(len(dele), n),
            final_correctness=rate(sum(x["correct"] for x in xs), n),
            correct_when_delegated=rate(sum(x["correct"] for x in dele), len(dele)),
            correct_when_fallback=rate(sum(x["correct"] for x in fall), len(fall)),
            # The dangerous case: the solver accepted parameters that were read wrongly,
            # and so answered a different problem with full confidence.
            delegated_with_wrong_extraction=sum(1 for x in dele if not x["extraction_exact"]),
            wrong_fields=dict(Counter(f for x in xs for f in x["wrong_fields"]
                                      if x["delegated"] or "ok" in x["outcomes"])),
        )
    return {k: m(v) for k, v in sorted(groups.items())}


def run_factcheck(server: str, scale, out: Path, broad: bool, limit: int | None = None) -> dict:
    path = out / f"factcheck_{server}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    import gateway  # the real fact checker, so this measures what students get
    system = C.system_for("explain", "os")
    sets = [("probe", r["id"], r["question"], r["rule"]) for r in _load(PROBES)]
    if broad:
        sets += [("broad", f"theory-{i}", r["question"].rstrip(":") + " Explain.", None)
                 for i, r in enumerate(_load(THEORY))]
    items = []
    for kind, iid, q, rule in sets[:limit]:
        draft = chat(system, q, EXPLAIN_TOKENS, scale)["text"]
        flags = sorted({n for n, _ in fact_flags(draft)})
        final, final_flags = draft, flags
        if flags and scale is not None:          # redraft only where an adapter is served
            final, _ = gateway.fact_checked(draft, system, q)
            body = final.split("\n\n", 1)[-1] if final.startswith("> **Correction") else final
            final_flags = sorted({n for n, _ in fact_flags(body)})
        items.append(dict(set=kind, id=iid, rule=rule, question=q, draft_flags=flags,
                          final_flags=final_flags,
                          correction_attached=final.startswith("> **Correction"),
                          draft=draft, final=final if flags else None))
    res = dict(server=server, items=items)
    path.write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


# ---------------------------------------------------------------- summary

COMPARISONS = [
    ("base", "v3", "adapter, no solver"),
    ("base+solver", "v3+solver", "adapter, with solver"),
    ("base", "base+solver", "solver, on the base model"),
    ("v3", "v3+solver", "solver, on v3"),
    ("base", "v2.2", "v2.2 adapter, no solver"),
    ("v2.2", "v3", "v2.2 -> v3, no solver"),
    ("v2.2+solver", "v3+solver", "v2.2 -> v3, with solver"),
]


def summarise(out: Path, prov: dict) -> None:
    suites = {p.stem[len("suite_"):]: json.loads(p.read_text(encoding="utf-8"))
              for p in out.glob("suite_*.json")}
    ids = lambda s: {x["id"]: x["correct"] for x in s["items"]}  # noqa: E731
    comps = [dict(paired(ids(suites[a]), ids(suites[b]), a, b), question=q)
             for a, b, q in COMPARISONS if a in suites and b in suites]
    # Is "scale 0 on an adapter server" really the base model? Extraction runs that way
    # in production, so compare its traces with the base server's, item by item.
    def tr(s):
        return {x["id"]: [(e["outcome"], json.dumps(e.get("params"), sort_keys=True))
                          for e in x["trace"]] for x in s["items"]}
    scale0 = {}
    if "base+solver" in suites:
        ref = tr(suites["base+solver"])
        for lab in ("v2.2+solver", "v3+solver"):
            if lab in suites:
                other = tr(suites[lab])
                scale0[lab] = dict(identical_traces=sum(ref[i] == other.get(i) for i in ref),
                                   n=len(ref))
    summary = dict(provenance=prov,
                   suite={k: {f: v[f] for f in ("n", "correct", "accuracy", "delegated",
                                                "truncated", "seconds")}
                          for k, v in sorted(suites.items())},
                   suite_by_kind={k: dict(Counter(x["kind"] for x in v["items"] if x["correct"]))
                                  for k, v in suites.items()},
                   paired=comps, scale0_extraction_equals_base=scale0)
    if (out / "ood.json").exists():
        o = json.loads((out / "ood.json").read_text(encoding="utf-8"))
        summary["ood"] = dict(overall=o["overall"], per_kind=o["per_kind"])
    for s in ("base", "v3"):
        p = out / f"factcheck_{s}.json"
        if p.exists():
            f = json.loads(p.read_text(encoding="utf-8"))["items"]
            summary[f"factcheck_{s}"] = {
                st: dict(n=len(xs), drafts_flagged=sum(bool(x["draft_flags"]) for x in xs),
                         finals_still_flagged=sum(bool(x["final_flags"]) for x in xs),
                         corrections_attached=sum(x["correction_attached"] for x in xs))
                for st, xs in {k: [x for x in f if x["set"] == k] for k in ("probe", "broad")}.items()
                if xs}
    (out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    (out / "summary.md").write_text(_markdown(summary), encoding="utf-8")
    print((out / "summary.md").read_text(encoding="utf-8"))


def _markdown(s: dict) -> str:
    p = s["provenance"]
    L = [f"# G0 ablation — {p['started_utc']}", "",
         f"Commit `{p['commit'][:10]}`{' (dirty)' if p['dirty'] else ''} · dataset "
         f"`{p['dataset_train_sha256'][:12]}` · {p['llama_cpp'][0] if p['llama_cpp'] else ''}", "",
         "## 57-item suite (served path, one adapter per server)", "",
         "| Configuration | Correct | Accuracy | Delegated | Truncated |", "|---|---|---|---|---|"]
    for k, v in s["suite"].items():
        L.append(f"| {k} | {v['correct']}/{v['n']} | {v['accuracy']:.1%} | {v['delegated']} | {v['truncated']} |")
    L += ["", "## Paired comparisons (exact McNemar)", "",
          "| Question | A → B | Accuracy A → B | Right→wrong | Wrong→right | p |",
          "|---|---|---|---|---|---|"]
    for c in s["paired"]:
        L.append(f"| {c['question']} | {c['a']} → {c['b']} | {c['accuracy_a']:.1%} → "
                 f"{c['accuracy_b']:.1%} | {c['right_to_wrong']} | {c['wrong_to_right']} | "
                 f"{c['mcnemar_p']:.4f} |")
    if s.get("scale0_extraction_equals_base"):
        L += ["", "Extraction at LoRA scale 0 vs the base server (identical traces): " +
              ", ".join(f"{k} {v['identical_traces']}/{v['n']}"
                        for k, v in s["scale0_extraction_equals_base"].items())]
    if "ood" in s:
        L += ["", "## OOD holdout, end to end (v3 + solver)", "",
              "| Kind | n | Extraction | Grounding rejected (any / final) | Delegated | "
              "Correct | Delegated but misread |", "|---|---|---|---|---|---|---|"]
        rows = dict(s["ood"]["per_kind"], **{"**all**": s["ood"]["overall"]["all"]})
        for k, m in rows.items():
            L.append(f"| {k} | {m['n']} | {m['extraction_accuracy']:.1%} | "
                     f"{m['grounding_rejection_rate_any_attempt']:.1%} / "
                     f"{m['grounding_rejection_rate_final']:.1%} | {m['delegation_rate']:.1%} | "
                     f"{m['final_correctness']:.1%} | {m['delegated_with_wrong_extraction']} |")
    for srv in ("base", "v3"):
        if f"factcheck_{srv}" in s:
            L += ["", f"## Fact checker — {srv}", ""]
            for st, m in s[f"factcheck_{srv}"].items():
                L.append(f"- {st}: {m['drafts_flagged']}/{m['n']} drafts flagged, "
                         f"{m['corrections_attached']} corrections attached, "
                         f"{m['finals_still_flagged']} finals still flagged")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--phases", nargs="*", default=["suite", "ood", "factcheck"],
                    choices=["suite", "ood", "factcheck"])
    ap.add_argument("--run", default=None, help="resume this run directory name")
    ap.add_argument("--limit", type=int, default=None,
                    help="smoke test: only the first N items of each set (run named smoke-*)")
    a = ap.parse_args()

    run = a.run or (("smoke-" if a.limit else "") + datetime.now().strftime("%Y%m%d-%H%M"))
    out = ROOT / "reports" / "g0" / run
    out.mkdir(parents=True, exist_ok=True)
    prov_path = out / "provenance.json"
    prov = json.loads(prov_path.read_text()) if prov_path.exists() else provenance(out)
    prov_path.write_text(json.dumps(prov, indent=1))
    if prov["dirty"]:
        print("WARNING: working tree is dirty; the commit hash does not fully describe this run",
              flush=True)
    print(f"G0 run {run} at commit {prov['commit'][:10]}", flush=True)

    logs = ROOT / "serve" / "logs"
    for name, adapter, configs in SERVERS:
        need_suite = "suite" in a.phases
        need_ood = "ood" in a.phases and name == "v3"
        need_fc = "factcheck" in a.phases and name in ("base", "v3")
        if not (need_suite or need_ood or need_fc):
            continue
        print(f"\n=== server: {name} ({datetime.now():%H:%M}) ===", flush=True)
        proc = start_server(adapter, logs / f"g0-{name}.log")
        try:
            extract_scale = None if adapter is None else 0.0
            if need_suite:
                for label, answer_scale, delegate in configs:
                    run_suite(label, extract_scale, answer_scale, delegate, out, a.limit)
            if need_fc:
                run_factcheck(name, None if adapter is None else 1.0, out,
                              broad=(name == "v3"), limit=a.limit)
                print(f"  factcheck {name} done", flush=True)
            if need_ood:
                run_ood(out, a.limit)
                print("  ood done", flush=True)
        finally:
            stop_server(proc)
    summarise(out, prov)
    print(f"\nG0 DONE {datetime.now():%H:%M} -> {out.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    main()
