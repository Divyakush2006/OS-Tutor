"""Render to Qwen3 ChatML and build the splits.

System prompts are keyed by (mode, DOMAIN). MathDial rows are maths, not OS:
labelling one "You are an Operating Systems tutor" would teach the model that OS
tutoring means solving arithmetic word problems. Behaviour transfers across
domains; the false domain claim must not. This was a real defect in an earlier
build - the kind that surfaces weeks later as unexplained eval degradation.

SPLIT FIRST, THEN ORDER. Ordering before splitting is a real bug that shipped
once: val/ood are carved out of the interleaved sequence afterwards, tearing out
the replay anchors holding runs apart. The gate verified "longest run 4" on the
pre-split list while train.jsonl contained runs of 25. The invariant must be
established on the object actually written to disk.

OOD is held out by REGIME, not at random. A random split is drawn from the same
generator as train and therefore cannot detect shortcut learning.
"""
import random
from collections import Counter

from .config import MAX_TOKENS_TARGET, OOD_FRACTION, VAL_FRACTION, VAL_MAX_ROWS, system_for


def render(records, tokenizer, report=None):
    out, lens, drops = [], [], {}

    def drop(k):
        drops[k] = drops.get(k, 0) + 1

    for r in records:
        msgs = [dict(role="system", content=system_for(r["mode"], r["domain"]))] + r["messages"]
        text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)
        if "<think>" in text:
            drop("think_block_present")
            continue
        n = len(tokenizer(text, add_special_tokens=False)["input_ids"])
        if n > MAX_TOKENS_TARGET:
            drop("over_token_budget")
            continue
        r = dict(r)
        r.update(messages=msgs, text=text, n_tokens=n)
        out.append(r)
        lens.append(n)

    if report is not None:
        s = sorted(lens)
        def pct(p):
            return s[min(len(s) - 1, int(p * len(s)))] if s else 0
        report.update(rendered=len(out), dropped=drops, total_tokens=int(sum(lens)),
                      mean=round(sum(lens) / max(len(lens), 1), 1),
                      p50=pct(.50), p90=pct(.90), p99=pct(.99),
                      max=s[-1] if s else 0,
                      fits_2048=round(100 * sum(1 for x in lens if x <= 2048) / max(len(lens), 1), 1),
                      fits_4096=round(100 * sum(1 for x in lens if x <= 4096) / max(len(lens), 1), 1))
    return out


def split(records, seed, order_fn, ood_extra=None, report=None):
    """ood_extra: genuinely out-of-distribution rows the generators never made.
    A same-generator OOD split tests size generalisation only; template learning
    is invisible to it."""
    rng = random.Random(seed)

    ood = list(ood_extra or [])
    ood_ids = {r["id"] for r in ood}
    for cat in sorted({r["category"] for r in records}):
        c = sorted([r for r in records if r["category"] == cat and r["id"] not in ood_ids],
                   key=lambda r: r["quality"])
        # v3.0: OOD_FRACTION = 0. Taking the lowest-QUALITY rows of every category
        # as "OOD" removed the shortest rows - clarification and formula answers -
        # from training. OOD is the genuinely held-out holdout file only.
        take = c[:int(len(c) * OOD_FRACTION)] if OOD_FRACTION > 0 else []
        ood += take
        ood_ids |= {r["id"] for r in take}

    rest = [r for r in records if r["id"] not in ood_ids]
    rng.shuffle(rest)
    n_val = min(int(len(rest) * VAL_FRACTION), VAL_MAX_ROWS)
    val, train = rest[:n_val], rest[n_val:]
    train = order_fn(train)

    if report is not None:
        report.update(train=len(train), val=len(val), ood=len(ood),
                      ood_from_holdout_file=len(ood_extra or []),
                      train_tokens=int(sum(r["n_tokens"] for r in train)),
                      train_by_category=dict(Counter(r["category"] for r in train)))
    return train, val, ood
