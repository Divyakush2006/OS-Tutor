"""End-to-end check of the running stack (after serve/start_tutor.ps1).

    serve/.venv-webui/Scripts/python serve/smoke_test.py

Sends one evaluation question through the gateway as the fine-tuned model and as
the base model, grades both with the simulator, and confirms the LoRA switch is
live (the two answers must differ). Also reports generation speed on this GPU.
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ostutor.evaluation.harness import grade  # noqa: E402

GW = "http://127.0.0.1:8090/v1/chat/completions"


def ask(model, question):
    req = urllib.request.Request(GW, data=json.dumps(dict(
        model=model, messages=[dict(role="user", content=question)])).encode(),
        headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        data = json.load(r)
    dt = time.time() - t0
    n = (data.get("usage") or {}).get("completion_tokens", 0)
    return data["choices"][0]["message"]["content"], n, dt


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    suite = [json.loads(l) for l in open(ROOT / "data/eval/os_solve_indist.jsonl", encoding="utf-8")]
    rec = next(r for r in suite if r["verify"]["kind"] == "translate")
    print("QUESTION:\n" + rec["problem"] + "\n")
    outs = {}
    for model in ("ostutor-solve", "qwen3-4b-base"):
        text, n, dt = ask(model, rec["problem"])
        g = grade(rec, text)
        outs[model] = text
        print(f"== {model}: correct={g['final_correct']}  {n} tokens in {dt:.1f}s "
              f"({n / max(dt, 1e-6):.1f} tok/s)")
        print(text[:900] + ("\n..." if len(text) > 900 else "") + "\n")
    live = outs["ostutor-solve"] != outs["qwen3-4b-base"]
    print("LoRA switch live (fine-tuned and base answers differ):", live)
    sys.exit(0 if live else 1)


if __name__ == "__main__":
    main()
