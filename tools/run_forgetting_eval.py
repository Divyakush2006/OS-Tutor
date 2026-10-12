"""Catastrophic-forgetting check: general knowledge before vs after fine-tuning.

    python tools/run_forgetting_eval.py --4bit --out reports/forgetting_base.json
    python tools/run_forgetting_eval.py --4bit --adapter outputs/ostutor-lora \
        --compare reports/forgetting_base.json --out reports/forgetting_finetuned.json

The dataset carries 15% replay data and a spaced replay schedule to protect the
base model's general ability. This measures whether that worked: MMLU questions
from subjects UNRELATED to operating systems (world history, biology, philosophy,
nutrition) plus adjacent computer-science subjects, scored identically for the base
model and the fine-tuned adapter.

Scoring is the model's next-token preference among A/B/C/D after a chat-formatted
prompt. It needs no generation, so it is fast, deterministic and immune to the
verbosity differences that dominate the OS-Solve results.

Contamination: every general item was checked against the shipped train.jsonl with
13-gram overlap (0 of 1,164 items overlap). The CS items are in the build's
decontamination set, so none reached training.

The comparison reports accuracy deltas AND paired flips (right -> wrong and
wrong -> right on the same item). Flips are the direct signature of forgetting;
an unchanged mean can hide many cancelling flips.
"""
import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ostutor import config as C

GENERAL = C.ROOT / "data" / "eval_general"
ADJACENT = ["mmlu_college_computer_science", "mmlu_computer_security", "mmlu_machine_learning"]
LETTERS = "ABCD"
PER_SUBJECT = 100
SEED = 42


def load_items():
    groups = {}
    for p in sorted(GENERAL.glob("mmlu_general_*.jsonl")):
        groups.setdefault("general", []).append((p.stem.replace("mmlu_general_", ""), p))
    for n in ADJACENT:
        p = C.RAW / f"{n}.jsonl"
        if p.exists():
            groups.setdefault("adjacent_cs", []).append((n.replace("mmlu_", ""), p))
    theory = C.ROOT / "data" / "eval_theory" / "os_theory_mcq.jsonl"
    if theory.exists():                     # v3.0: hand-written OS theory benchmark
        groups.setdefault("os_theory", []).append(("os_theory", theory))
    items = []
    for group, subjects in groups.items():
        for subject, p in subjects:
            rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
            rows = [r for r in rows if len(r.get("choices", [])) == 4]
            random.Random(SEED).shuffle(rows)
            for i, r in enumerate(rows[:PER_SUBJECT]):
                items.append(dict(id=f"{subject}:{i}", group=group, subject=subject,
                                  question=r["question"], choices=r["choices"],
                                  answer=int(r["answer"])))
    return items


def prompt(item):
    opts = "\n".join(f"{L}. {c}" for L, c in zip(LETTERS, item["choices"]))
    return (f"Answer the following multiple-choice question with the letter of the "
            f"correct option only.\n\n{item['question']}\n\n{opts}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=str(C.MODEL))
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--4bit", dest="four_bit", action="store_true")
    ap.add_argument("--compare", default=None, help="baseline JSON for paired comparison")
    ap.add_argument("--out", default=str(C.REPORTS / "forgetting_base.json"))
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

    letter_ids = [tok.encode(L, add_special_tokens=False)[0] for L in LETTERS]
    items = load_items()
    for it in items:
        text = tok.apply_chat_template([dict(role="user", content=prompt(it))],
                                       tokenize=False, add_generation_prompt=True)
        ids = tok(text, return_tensors="pt").to(model.device)
        with torch.no_grad():
            logits = model(**ids).logits[0, -1]
        scores = logits[letter_ids].float()
        it["pred"] = int(torch.argmax(scores))
        it["correct"] = it["pred"] == it["answer"]

    def acc(rows):
        return round(sum(r["correct"] for r in rows) / max(len(rows), 1), 4)

    summary = {}
    for g in sorted({i["group"] for i in items}):
        rows = [i for i in items if i["group"] == g]
        summary[g] = dict(n=len(rows), accuracy=acc(rows), by_subject={
            s: acc([r for r in rows if r["subject"] == s])
            for s in sorted({r["subject"] for r in rows})})
    report = dict(model=a.model, adapter=a.adapter, four_bit=a.four_bit,
                  per_subject=PER_SUBJECT, seed=SEED, summary=summary,
                  items=[{k: i[k] for k in ("id", "group", "pred", "answer", "correct")}
                         for i in items])

    for g, s in summary.items():
        print(f"{g:12s} n={s['n']:4d}  accuracy {s['accuracy']:.4f}  {s['by_subject']}")

    if a.compare:
        base = json.loads(Path(a.compare).read_text(encoding="utf-8"))
        prev = {i["id"]: i for i in base["items"]}
        comp = {}
        for g in summary:
            rows = [i for i in items if i["group"] == g and i["id"] in prev]
            lost = sum(1 for i in rows if prev[i["id"]]["correct"] and not i["correct"])
            gained = sum(1 for i in rows if not prev[i["id"]]["correct"] and i["correct"])
            delta = round(summary[g]["accuracy"] - base["summary"][g]["accuracy"], 4)
            comp[g] = dict(delta=delta, right_to_wrong=lost, wrong_to_right=gained, n=len(rows))
            print(f"{g:12s} delta {delta:+.4f}  right->wrong {lost}  wrong->right {gained}")
        report["comparison"] = comp

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"written -> {a.out}")


if __name__ == "__main__":
    main()
