# OS Tutor: local chat stack

```
Browser ──► Open WebUI :3000 ──► tutor gateway :8090 ──► llama-server :8081 (CUDA)
             chat frontend        mode routing,             Qwen3-4B Q8_0 GGUF
             history, markdown    verified solver,          + ostutor v3.0 LoRA
                                  fact checker,             (applied at runtime)
                                  16k ceiling, loop guard
```

The gateway is not a proxy. It is the layer that makes a 4B model trustworthy:

| layer | what it does | measured effect |
|---|---|---|
| **Mode routing** | reads the question and picks the mode, so the student need not choose | a shown attempt reaches tutoring, not a worked answer |
| **Verified solver** | the model reads the PARAMETERS, a simulator computes the trace, `render_solution()` writes it in the trained format | hand-written suite **64.9% → 100%**, and 76 min → 141 s |
| **Fact checker** | screens prose against the misconception rules and redrafts with the correct fact | "Does LRU suffer from Belady's anomaly?" answered **wrongly** by the model alone, **correctly** through the gateway |
| **Loop guard** | stops repetition by content, not length | a v2.2 run repeated one line 257 times |

Why the solver layer exists: of the seven scheduling questions v3.0 got wrong, **all
seven had a perfect table built from a wrong schedule** — the arithmetic was right and
the schedule was not. That is the deterministic horizon, it is architectural, and more
training data does not move it (the family with the most rows, 1,733, scored worst at
42%). So the model stopped executing procedures and started reading them.

## Start / stop

```powershell
powershell -ExecutionPolicy Bypass -File serve\start_tutor.ps1   # opens http://localhost:3000
powershell -ExecutionPolicy Bypass -File serve\stop_tutor.ps1    # frees the GPU
```

The launcher refuses to start while another job holds the GPU (for example
`tools/run_eval.py`). The stack needs about 6.5 GB of the 8 GB.

## Modes in the picker

Every mode is the fine-tuned adapter. The untuned base is no longer offered — it existed
only for side-by-side comparison during development — but the gateway still calls it
internally at LoRA scale 0 for parameter extraction, which it does more reliably than the
adapter (84% against 79%, measured on the same 57 items).

| mode | what it is | layers applied |
|---|---|---|
| `ostutor` (default) | reads the question and picks the mode itself | routing + whichever layers that mode uses |
| `ostutor-solve` | worked problems, numbered auditable steps | verified solver |
| `ostutor-analyze` | assumptions → mechanisms → trade-offs → a quantified recommendation | verified solver + fact checker |
| `ostutor-explain` | concept explanations with a concrete example | fact checker |
| `ostutor-tutor` | Socratic: diagnoses your attempt, never hands over the answer | **none, deliberately** |

Tutoring gets no verification layer on purpose: handing a Socratic reply a computed
answer defeats the mode, and rewriting it against a fact list would let it leak the
result the student is meant to reach.

Each mode injects the **exact system prompt it was trained with**
(`ostutor/config.py`). Do not set a global system prompt in Open WebUI settings:
a client-sent system prompt replaces the trained one.

To compare base and fine-tuned answers, click **+** next to the model name and add
a second model; both answer the same question side by side (one after the other on
this GPU).

## Production settings, and why

- **Greedy decoding** (temperature 0) by default: the setting all evaluation results
  were measured with.
- **16,384-token ceiling.** Answers end at the model's own end token; the ceiling only
  bounds a runaway. Measured needs per question type are in
  `reports/TOKEN_BUDGET.md`: exam-sized questions need at most about 3,500 tokens.
- **Loop guard.** If one line repeats 6 times in a row, or a block of 2-4 lines
  cycles 5 times, the gateway stops the answer and says why.
- **Base + LoRA at runtime** instead of a merged model: the adapter keeps its exact
  weights, and the same server also serves the base model (LoRA scale 0).

## One-time setup (already done on this machine)

```bash
# llama.cpp b11050, CUDA 13.4 build            -> serve/llama.cpp/bin
gh release download b11050 -R ggml-org/llama.cpp -p "llama-b11050-bin-win-cuda-13.4-x64.zip" -p "cudart-llama-bin-win-cuda-13.4-x64.zip"
git clone --depth 1 --branch b11050 https://github.com/ggml-org/llama.cpp serve/llama.cpp/src
# convert (CPU)
PYTHONPATH=serve/llama.cpp/src/gguf-py python serve/llama.cpp/src/convert_hf_to_gguf.py models/Qwen3-4B-Instruct-2507 --outtype q8_0 --outfile models/gguf/qwen3-4b-instruct-2507-Q8_0.gguf
PYTHONPATH=serve/llama.cpp/src/gguf-py python serve/llama.cpp/src/convert_lora_to_gguf.py outputs/ostutor-lora --base models/Qwen3-4B-Instruct-2507 --outtype f16 --outfile models/gguf/ostutor-v2.2-lora-f16.gguf
# Open WebUI (needs Python 3.11)
py -3.11 -m venv serve/.venv-webui && serve/.venv-webui/Scripts/python -m pip install open-webui
```

After retraining, re-run only the LoRA conversion line on the new adapter.

## Logs

`serve/logs/`: `llama-server.log`, `gateway.log`, `webui.log`.
