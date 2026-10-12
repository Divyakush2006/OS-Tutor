"""QLoRA fine-tune of Qwen3-4B-Instruct-2507 on ostutor-sft v3 (Kaggle, 2x T4).

Kaggle setup
  1. Upload data/build/{train,val,ood}.jsonl + reports/manifest.json as a dataset.
  2. Notebook: Accelerator = GPU T4 x2, Internet on. First cell: !pip install -q unsloth
  3. Run (both GPUs, DDP):
        import glob; s = glob.glob("/kaggle/input/**/kaggle_train.py", recursive=True)[0]
        !torchrun --nproc_per_node=2 {s}
     One GPU instead:            !python {s}
     Smoke test before the run:  !torchrun --nproc_per_node=2 {s} --max-steps 3 --longest-first
  4. If a session dies, attach this notebook's output as a dataset and resume:
        !torchrun --nproc_per_node=2 {s} --resume-from /kaggle/input/<prev>/ostutor-lora

Decisions, and why
  * TWO GPUs BY DDP. Unsloth enables DDP automatically under torchrun; each rank
    holds a full 4-bit copy of the model and accelerate shards each batch, so the
    effective batch is per_device x accum x world_size. The trainer keeps the
    dataset's ORDER (sequential sampler): train.jsonl is emitted in rectifier order
    (categories interleaved, runs bounded, replay spaced 4 -> 14 rows apart), and
    the default shuffling would silently destroy that schedule.
  * 16,384-TOKEN SEQUENCES. reports/TOKEN_BUDGET.md measured the worst case for
    every question type; the longest training row is ~10.3k tokens. Nothing a
    student can ask is truncated. With per_device=1 the limit only bounds
    truncation - memory follows the ACTUAL row length - so the ceiling is free.
    The smoke test runs with --longest-first, which puts the longest rows through
    the real trainer, so an OOM would happen in the first minutes rather than
    after hours.
  * LOSS ON ASSISTANT TOKENS ONLY, so the model learns to answer, not to echo.
  * fp16, not bf16: the T4 (Turing) has no bf16.
  * ANTI-FORGETTING: 16% general replay in the mix, spaced; r=32 / alpha=64 on all
    linear layers with lr 1e-4; validation every ~8% of steps with early stopping
    and best-checkpoint restore. The OOD split is logged as a second loss but never
    used to select a checkpoint - it is test data.
  * OVERFITTING CONTROL: one epoch over a large, deduplicated, fingerprint-distinct
    pool by default (v2.2's second epoch bought little and memorised more), NEFTune
    noise, LoRA dropout, early stopping.
  * No packing: it would merge neighbouring rows and break the ordering guarantees.
"""
import argparse
import json
import math
import os
from pathlib import Path

# Single-GPU runs pin GPU 0 (with "T4 x2" selected, device_map="auto" split the
# model across both cards: naive model parallelism, slower). Under torchrun every
# rank must see its own GPU, so the pin is skipped.
if "LOCAL_RANK" not in os.environ and "RANK" not in os.environ:
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

from unsloth import FastLanguageModel  # must be imported before trl/transformers
from unsloth.chat_templates import train_on_responses_only

from datasets import Dataset
from torch.utils.data import SequentialSampler
from transformers import EarlyStoppingCallback
from trl import SFTConfig, SFTTrainer

BASE = "Qwen/Qwen3-4B-Instruct-2507"
SEED = 42
# Must equal TRAIN_MAX_LENGTH in ostutor/config.py: the build drops longer rows, so
# no example is ever truncated mid-answer.
MAX_LEN = 16384
EVAL_VAL_ROWS = 120        # a full 240-row pass at 16k costs ~10 min per round
EVAL_OOD_ROWS = 60
WORLD = int(os.environ.get("WORLD_SIZE", "1"))
RANK = int(os.environ.get("RANK", "0"))


def log(*a):
    if RANK == 0:
        print(*a, flush=True)


def find_data():
    kaggle = Path("/kaggle/input")
    found = sorted(kaggle.rglob("train.jsonl")) if kaggle.exists() else []
    for d in [p.parent for p in found] + [Path("data/build")]:
        if (d / "train.jsonl").exists() and (d / "val.jsonl").exists():
            return d
    raise FileNotFoundError("train.jsonl/val.jsonl not found under /kaggle/input or data/build")


class OrderedSFTTrainer(SFTTrainer):
    """Keeps the dataset's row order (see module docstring). Under DDP, accelerate
    shards the batches of this sampler across ranks, so order is preserved
    globally while each rank sees a different slice."""

    def _get_train_sampler(self, train_dataset=None, *args, **kwargs):
        return SequentialSampler(train_dataset if train_dataset is not None
                                 else self.train_dataset)


def longest_first(texts, tok):
    """Order the rows longest-first, for the SMOKE TEST only.

    This replaces a hand-written "memory probe" that ran one forward+backward on the
    longest row before training started. That probe reported an OOM at 13.85 GiB on a
    10,863-token row and aborted the run - a FALSE ALARM: calling the model directly
    bypasses the gradient checkpointing that Unsloth engages through the trainer, so
    it measured a code path training never takes, and vetoed a configuration that
    fits.

    Feeding the longest rows to the REAL trainer for a few steps tests the same worst
    case through the code that will actually run. If those steps fit, every later
    step fits, because no row is longer. The real run keeps the rectifier order; only
    the throwaway smoke run is sorted."""
    order = sorted(range(len(texts)), key=lambda i: -len(texts[i]))
    n_tok = len(tok(texts[order[0]], add_special_tokens=False)["input_ids"])
    log(f"smoke test ordered longest-first: worst row {n_tok} tokens "
        f"({len(texts[order[0]]):,} chars)")
    return [texts[i] for i in order]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=float, default=1)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--rank", type=int, default=32)
    ap.add_argument("--max-steps", type=int, default=-1)
    ap.add_argument("--resume-from", default=None,
                    help="checkpoint directory from a previous (killed) session")
    ap.add_argument("--longest-first", action="store_true",
                    help="smoke test only: train on the longest rows first, so the "
                         "worst case for memory is exercised through the real trainer")
    ap.add_argument("--out", default="/kaggle/working/ostutor-lora"
                    if Path("/kaggle/working").exists() else "outputs/ostutor-lora-v3")
    a = ap.parse_args()

    data = find_data()
    manifest = data / "manifest.json"
    if manifest.exists():
        m = json.loads(manifest.read_text())
        assert m["gates_passed"], "dataset build did not pass its release gates"
        log(f"dataset {m['dataset']} {m['pipeline_version']} | train sha256 "
            f"{m['artifacts']['train.jsonl'][:16]} | world size {WORLD}")

    model, tok = FastLanguageModel.from_pretrained(
        BASE, max_seq_length=MAX_LEN, load_in_4bit=True, dtype=None)
    model = FastLanguageModel.get_peft_model(
        model, r=a.rank, lora_alpha=2 * a.rank, lora_dropout=0.05, bias="none",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        use_gradient_checkpointing="unsloth", random_state=SEED)

    # Load ONLY the rendered `text` field: load_dataset("json") infers one schema for
    # all splits, and the OOD split's lineage carries an extra key, which made the
    # cast fail. File order is preserved.
    def read_text(split):
        with open(data / f"{split}.jsonl", encoding="utf-8") as f:
            return [json.loads(l)["text"] for l in f if l.strip()]

    train_texts = read_text("train")
    if a.longest_first:
        train_texts = longest_first(train_texts, tok)
    ds = {"train": Dataset.from_dict({"text": train_texts})}
    for split, cap in (("val", EVAL_VAL_ROWS), ("ood", EVAL_OOD_ROWS)):
        rows = read_text(split)
        ds[split] = Dataset.from_dict({"text": rows}).shuffle(seed=SEED) \
            .select(range(min(cap, len(rows))))
    log({s: len(d) for s, d in ds.items()})

    # Memory is proven by the smoke test running the longest rows through the real
    # trainer (--longest-first), not by a separate probe outside it.

    per_device, accum = 1, 8
    steps_per_epoch = math.ceil(len(ds["train"]) / (per_device * accum * WORLD))
    total = a.max_steps if a.max_steps > 0 else math.ceil(steps_per_epoch * a.epochs)
    every = max(10, round(total * 0.08))        # ~12 validation rounds
    log(f"{steps_per_epoch} steps/epoch, {total} total, eval every {every}")

    cfg = SFTConfig(
        output_dir=a.out,
        dataset_text_field="text",
        max_length=MAX_LEN,
        packing=False,
        per_device_train_batch_size=per_device,
        gradient_accumulation_steps=accum,      # effective batch = 1 x 8 x world
        per_device_eval_batch_size=1,
        num_train_epochs=a.epochs,
        max_steps=a.max_steps,
        learning_rate=a.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        weight_decay=0.01,
        max_grad_norm=1.0,
        optim="adamw_8bit",
        neftune_noise_alpha=5,
        fp16=True,
        bf16=False,
        eval_strategy="steps",
        eval_steps=every,
        save_strategy="steps",
        save_steps=every,
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_val_loss",
        greater_is_better=False,
        logging_steps=10,
        report_to="none",
        seed=SEED,
        data_seed=SEED,
        ddp_find_unused_parameters=False,
        dataloader_num_workers=2,
    )
    trainer = OrderedSFTTrainer(
        model=model, processing_class=tok, args=cfg,
        train_dataset=ds["train"],
        eval_dataset={"val": ds["val"], "ood": ds["ood"]},
        callbacks=[EarlyStoppingCallback(early_stopping_patience=3)],
    )
    trainer = train_on_responses_only(
        trainer, instruction_part="<|im_start|>user\n",
        response_part="<|im_start|>assistant\n")

    trainer.train(resume_from_checkpoint=a.resume_from)
    final = trainer.evaluate()
    log({k: round(v, 4) for k, v in final.items() if isinstance(v, float)})

    if RANK == 0:
        model.save_pretrained(a.out)
        tok.save_pretrained(a.out)
        with open(os.path.join(a.out, "train_metrics.json"), "w") as f:
            json.dump(dict(final=final, log=trainer.state.log_history,
                           best_checkpoint=trainer.state.best_model_checkpoint,
                           world_size=WORLD, max_len=MAX_LEN, rank=a.rank,
                           epochs=a.epochs, lr=a.lr), f, indent=1)
        log(f"adapter saved to {a.out}")


if __name__ == "__main__":
    main()
