"""Run OS-Solve against a model and report accuracy.

    python tools/run_eval.py --model models/Qwen3-4B-Instruct-2507 --limit 60

Establishes the BASELINE before any fine-tuning. Without it, every later claim
about accuracy is unfalsifiable, and there is no way to detect whether a LoRA
helped, hurt, or simply memorised the training templates.

Decoding is GREEDY and explicit. Qwen3-4B-Instruct-2507 ships
`do_sample: true, temperature: 0.7` in generation_config.json - so a run that
does not override it produces run-to-run variance on identical inputs and looks
like an unstable model.

Reports three numbers that must be read together:
  in-distribution accuracy   how well it does on familiar phrasing
  OOD accuracy               same procedures, framings never seen in training
  the GAP between them       large gap == template learning, not procedure learning
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ostutor import config as C
from ostutor.evaluation.harness import grade, load_suite, summarise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=str(C.MODEL))
    ap.add_argument("--adapter", default=None, help="optional LoRA adapter path")
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--max-new", type=int, default=1100)
    ap.add_argument("--4bit", dest="four_bit", action="store_true",
                    help="load NF4 4-bit (needed on 8 GB GPUs)")
    ap.add_argument("--out", default=str(C.REPORTS / "eval_baseline.json"))
    ap.add_argument("--suites", default="os_solve_indist,os_solve_ood",
                    help="comma-separated suites to run")
    ap.add_argument("--update", action="store_true",
                    help="replace only these suites in an existing --out report; the "
                         "replaced results are kept under 'superseded'")
    a = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(a.model)
    quant = None
    if a.four_bit:
        from transformers import BitsAndBytesConfig
        quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                   bnb_4bit_compute_dtype=torch.float16)
    model = AutoModelForCausalLM.from_pretrained(
        a.model, dtype=torch.float16, quantization_config=quant,
        device_map="auto" if torch.cuda.is_available() else None)
    if a.adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, a.adapter)
    model.eval()

    report = dict(model=a.model, adapter=a.adapter, limit=a.limit,
                  four_bit=a.four_bit, suites={})
    if a.update and Path(a.out).exists():
        report = json.loads(Path(a.out).read_text(encoding="utf-8"))
    for suite_name in a.suites.split(","):
        if suite_name in report["suites"]:
            report.setdefault("superseded", {})[suite_name] = report["suites"][suite_name]
        path = C.ROOT / "data" / "eval" / f"{suite_name}.jsonl"
        # Loud, not silent: skipping a mistyped suite name would leave a missing
        # number in the comparison table that looks like a result of zero.
        if not path.exists():
            sys.exit(f"no such suite: {path} (available: "
                     f"{', '.join(sorted(p.stem for p in path.parent.glob('*.jsonl')))})")
        suite = load_suite(path)[:a.limit]
        results, items, t0 = [], [], time.time()
        for i, rec in enumerate(suite):
            msgs = [dict(role="system", content=C.system_for("solve", "os")),
                    dict(role="user", content=rec["problem"])]
            text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            ids = tok(text, return_tensors="pt").to(model.device)
            with torch.no_grad():
                out = model.generate(**ids, max_new_tokens=a.max_new,
                                     do_sample=False,          # GREEDY - see docstring
                                     temperature=None, top_p=None, top_k=None,
                                     pad_token_id=tok.pad_token_id or tok.eos_token_id)
            new = out[0][ids["input_ids"].shape[1]:]
            gen = tok.decode(new, skip_special_tokens=True)
            g = grade(rec, gen)
            results.append(g)
            # Keep every answer: a score that cannot be audited is not a result.
            # `truncated` separates "ran out of budget" from "answered wrongly".
            items.append(dict(suite=suite_name, index=i, kind=rec["verify"]["kind"],
                              final_correct=g["final_correct"], new_tokens=len(new),
                              truncated=len(new) >= a.max_new, output=gen))
            if (i + 1) % 10 == 0:
                acc = sum(r["final_correct"] for r in results) / len(results)
                print(f"  {suite_name} {i+1}/{len(suite)}  running acc {acc:.3f}", flush=True)
        s = summarise(results)
        s["seconds"] = round(time.time() - t0, 1)
        s["max_new_tokens"] = a.max_new
        s["truncation_rate"] = round(sum(x["truncated"] for x in items) / max(len(items), 1), 4)
        done = [x for x in items if not x["truncated"]]
        s["accuracy_when_finished"] = (round(sum(x["final_correct"] for x in done) / len(done), 4)
                                       if done else None)
        s["items"] = items
        report["suites"][suite_name] = s
        print(f"\n{suite_name}: truncated {s['truncation_rate']} | accuracy when finished "
              f"{s['accuracy_when_finished']}")
        print(f"{suite_name}: final {s['final_answer_accuracy']} "
              f"step {s['step_accuracy']} ({s['seconds']}s)")
        for k, v in s["by_topic"].items():
            print(f"    {k:<18}{v['n']:>4}  {v['accuracy']}")

    ind = report["suites"].get("os_solve_indist", {}).get("final_answer_accuracy")
    ood = report["suites"].get("os_solve_ood", {}).get("final_answer_accuracy")
    if ind is not None and ood is not None:
        report["generalisation_gap"] = round(ind - ood, 4)
        print(f"\ngeneralisation gap (in-dist - OOD): {report['generalisation_gap']:+.4f}")
        print("  a large positive gap means the model learned the TEMPLATE, "
              "not the procedure")

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwritten -> {a.out}")


if __name__ == "__main__":
    main()
