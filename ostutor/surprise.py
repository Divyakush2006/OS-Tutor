"""Surprise-driven replay selection (SuRe, arXiv 2511.22367).

Replay rows are ranked by the base model's mean per-token negative log-likelihood
on the ASSISTANT tokens. High-NLL sequences have large gradients, so a buffer
built from them approximates the gradient geometry of the general distribution
rather than its surface frequency - the rows the model already predicts easily
contribute almost nothing to holding its behaviour in place.

Two safeguards against SuRe's known failure mode (high NLL can also mean noise):
  1. It only ever ranks rows that already passed the quality gate and semantic
     dedup - surprise never overrides quality.
  2. It ranks inside a farthest-point DIVERSE candidate pool (SURPRISE_POOL_MULT x
     quota), so it cannot concentrate replay on one weird corner of the space.

Reproducibility: NLL is computed once, rounded, and cached by record id. A rebuild
reads the cache, so GPU non-determinism can never change the dataset.
"""
import json

from .config import BUILD, MODEL

CACHE = BUILD / "surprise_cache.json"


def load_cache():
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_cache(cache):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache), encoding="utf-8")
    tmp.replace(CACHE)                                   # atomic


def compute(rows, max_tokens=1024, log=print):
    """Return {id: mean assistant-token NLL}. Uses the cache; computes only misses."""
    cache = load_cache()
    todo = [r for r in rows if r["id"] not in cache]
    if not todo:
        return {r["id"]: cache[r["id"]] for r in rows}

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(str(MODEL))
    kw = dict(dtype=torch.float16)
    if torch.cuda.is_available():
        try:
            from transformers import BitsAndBytesConfig
            kw["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4")
            kw["device_map"] = "auto"
        except Exception:
            kw["device_map"] = "auto"
    model = AutoModelForCausalLM.from_pretrained(str(MODEL), **kw)
    model.eval()
    log(f"    SuRe: scoring {len(todo)} replay candidates under the base model")

    for i, r in enumerate(todo):
        msgs = [m for m in r["messages"] if m["role"] != "system"]
        prompt = tok.apply_chat_template(msgs[:-1], tokenize=False, add_generation_prompt=True)
        full = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)
        p_ids = tok(prompt, add_special_tokens=False)["input_ids"]
        f_ids = tok(full, add_special_tokens=False)["input_ids"][:max_tokens]
        if len(f_ids) <= len(p_ids) + 1:
            cache[r["id"]] = 0.0
            continue
        ids = torch.tensor([f_ids], device=model.device)
        labels = ids.clone()
        labels[0, :min(len(p_ids), labels.shape[1])] = -100     # assistant tokens only
        with torch.no_grad():
            loss = model(input_ids=ids, labels=labels).loss
        cache[r["id"]] = round(float(loss), 3)
        if (i + 1) % 200 == 0:
            save_cache(cache)
            log(f"      {i+1}/{len(todo)}")
    save_cache(cache)
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return {r["id"]: cache[r["id"]] for r in rows}
