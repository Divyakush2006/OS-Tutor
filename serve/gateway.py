"""OS Tutor gateway: an OpenAI-compatible layer between any chat UI and llama-server.

    python serve/gateway.py            (started for you by serve/start_tutor.ps1)

Why it exists - the UI must not decide how the model is prompted:

  * TRAINED SYSTEM PROMPTS. The adapter learned each behaviour under one exact
    system prompt (ostutor/config.py). Each "model" this gateway lists is one of
    those modes; the prompt is injected unless the client sent its own.
  * GREEDY DECODING by default (temperature 0) - the setting every evaluation
    number was measured with. A client may still override it.
  * A HIGH CEILING, NOT A TARGET. max_tokens defaults to 16,384 (fits the laptop's
    8 GB; reports/TOKEN_BUDGET.md). Generation ends at the model's own end token;
    the ceiling only bounds a runaway.
  * LOOP GUARD. Runaways are stopped by content, not by length: if the same line
    repeats LOOP_REPEATS times in a row, or a short block of lines cycles, the
    stream is closed and the student is told why. (The v2.2 evaluation saw a
    `request 1000: must WAIT` line repeated 257 times on an unsolvable question.)
  * ONE MODEL, SEVERAL MODES. Every mode offered to the student is the fine-tuned
    adapter. The untuned base is not listed - it existed only for side-by-side
    comparison during development - but the per-request LoRA scale still lets the
    gateway call it internally at scale 0 for parameter extraction, which it does
    more reliably than the adapter (84% against 79%, measured).
  * VERIFIED NUMBERS. Where a simulator covers the procedure, the model reads the
    parameters and the simulator computes the answer: 64.9% -> 100% on the 57
    hand-written items, and faster, since a short extraction replaces a long
    generation. If extraction cannot be grounded in the question, the model answers
    for itself rather than guessing from invented values.
  * FACT-CHECKED PROSE. Explanations are screened against the misconception rules in
    ostutor/theory_filter.py and redrafted with the correct fact when one fires.
  * GROUNDED IN THE COURSE NOTES (G2, opt-in). With OSTUTOR_RAG set to a corpus
    directory, explain and analyze answers get the most relevant passages of the
    owners' notes appended to the trained prompt, cite them as [S1], [S2], and end
    with the list of sources. Retrieval runs on the CPU in a few milliseconds; when
    the notes do not cover the question it abstains and the answer says so, rather
    than passing general knowledge off as course material. Tutor mode never retrieves:
    a passage could state the answer the student is working towards.
  * AUTO ROUTING. "ostutor" reads the question and picks the mode, so a student does
    not have to know that a shown attempt wants tutoring and a stated procedure wants
    a worked solution.
"""
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ostutor.config import SYSTEM_PROMPTS  # noqa: E402  (single source of truth)
from ostutor.solver import (EXTRACT_PROMPT, SOLVER_KINDS, normalise,  # noqa: E402
                            parse_json, solve)
from ostutor.theory_filter import CORRECTIONS, fact_flags  # noqa: E402
from ostutor.rag.retrieve import Retriever, augment, sources_footer  # noqa: E402

UPSTREAM = os.environ.get("TUTOR_UPSTREAM", "http://127.0.0.1:8081")
log = logging.getLogger("tutor-gateway")
PORT = int(os.environ.get("TUTOR_GATEWAY_PORT", "8090"))
MAX_TOKENS = int(os.environ.get("TUTOR_MAX_TOKENS", "16384"))
LOOP_REPEATS = 6          # identical consecutive lines that count as a loop
CYCLE_MAX_LEN = 4         # also catch a block of up to 4 lines repeating
CYCLE_REPEATS = 5
# Retrieval over the owners' course notes: off unless this names a corpus directory, so
# a gateway started without it behaves exactly as before.
RAG_DIR = os.environ.get("OSTUTOR_RAG", "")

# Every listed mode is the FINE-TUNED model. The untuned base is no longer offered as a
# chat model - it was only ever there for side-by-side comparison during development -
# but it is still used internally, at LoRA scale 0, for parameter extraction, because it
# reads a problem statement more reliably than the adapter (84% against 79% measured).
#
# `verify` turns on simulator delegation: the model reads the parameters and the
# simulator computes the answer (64.9% -> 100% on the hand-written suite). `factcheck`
# turns on the misconception critic for prose answers. Tutoring gets NEITHER: a Socratic
# reply must not state the final answer, so handing it a computed one defeats the mode.
MODELS = {
    "ostutor": dict(prompt=None, lora=1.0, route=True, verify=True, factcheck=True,
                    desc="OS Tutor - reads the question and picks the right mode itself"),
    "ostutor-solve": dict(prompt=SYSTEM_PROMPTS[("solve", "os")], lora=1.0, verify=True,
                          desc="Worked problems - numbered steps, simulator-verified numbers"),
    "ostutor-analyze": dict(prompt=SYSTEM_PROMPTS[("analyze", "os")], lora=1.0,
                            verify=True, factcheck=True, rag=True,
                            desc="Analysis - assumptions, trade-offs, a quantified recommendation"),
    "ostutor-explain": dict(prompt=SYSTEM_PROMPTS[("explain", "os")], lora=1.0,
                            factcheck=True, rag=True,
                            desc="Concept explanations - fact-checked against known misconceptions"),
    "ostutor-tutor": dict(prompt=SYSTEM_PROMPTS[("tutor", "os")], lora=1.0,
                          desc="Socratic tutoring - diagnoses your attempt, never hands over the answer"),
    # 707 shell rows were trained and, until routing existed, unreachable: nothing in
    # the picker used the ("shell", "linux") prompt.
    "ostutor-shell": dict(prompt=SYSTEM_PROMPTS[("shell", "linux")], lora=1.0,
                          desc="Linux commands - the right command, with each flag explained"),
}
DEFAULT_MODEL = "ostutor"

app = FastAPI(title="OS Tutor gateway")
RAG = Retriever(Path(RAG_DIR)) if RAG_DIR else None   # loaded once: ~7 s, then ~5 ms a query
client = httpx.AsyncClient(base_url=UPSTREAM, timeout=httpx.Timeout(None, connect=10))


def loop_detected(lines):
    """True when the tail of the answer is a repetition loop."""
    tail = [l.strip() for l in lines if l.strip()]
    if len(tail) >= LOOP_REPEATS and len(set(tail[-LOOP_REPEATS:])) == 1:
        return True
    for k in range(2, CYCLE_MAX_LEN + 1):
        need = k * CYCLE_REPEATS
        if len(tail) >= need:
            block = tail[-k:]
            if all(tail[-need + i] == block[i % k] for i in range(need)):
                return True
    return False


def prepare(body, prompt_override=None):
    name = body.get("model", DEFAULT_MODEL)
    spec = MODELS.get(name, MODELS[DEFAULT_MODEL])
    prompt = prompt_override or spec["prompt"] or SYSTEM_PROMPTS[("solve", "os")]
    msgs = list(body.get("messages", []))
    if not any(m.get("role") == "system" and str(m.get("content", "")).strip() for m in msgs):
        msgs = [dict(role="system", content=prompt)] + \
               [m for m in msgs if m.get("role") != "system"]
    out = dict(body, messages=msgs, model=name)
    out.setdefault("temperature", 0.0)
    out["max_tokens"] = min(int(body.get("max_tokens") or MAX_TOKENS), MAX_TOKENS)
    out.pop("max_completion_tokens", None)
    out["lora"] = [dict(id=0, scale=spec["lora"])]
    return out


GUARD_NOTE = ("\n\n---\n> **Stopped by the loop guard:** the model started repeating the "
              "same step. Check that the question states every input (for example the "
              "request list or the Available vector), or rephrase and ask again.")


@app.get("/v1/models")
async def models():
    return dict(object="list", data=[dict(id=k, object="model", owned_by="ostutor",
                                          created=0, description=v["desc"])
                                     for k, v in MODELS.items()])


@app.get("/health")
async def health():
    try:
        r = await client.get("/health")
        return JSONResponse(dict(gateway="ok", model_server=r.json()), status_code=r.status_code)
    except httpx.HTTPError as e:
        return JSONResponse(dict(gateway="ok", model_server=str(e)), status_code=503)


def log_request(raw, body):
    """One line per request: what the client sent and what was forwarded. Content is
    not logged, only its shape - enough to audit prompts and parameters."""
    print(json.dumps(dict(
        t=time.strftime("%H:%M:%S"), model=body["model"], stream=bool(body.get("stream")),
        client_roles=[m.get("role") for m in raw.get("messages", [])],
        client_system=any(m.get("role") == "system" for m in raw.get("messages", [])),
        client_params={k: raw[k] for k in raw if k not in ("messages", "model")},
        sent=dict(temperature=body.get("temperature"), max_tokens=body["max_tokens"],
                  lora=body["lora"][0]["scale"]))), flush=True)


def _upstream(system, user, scale=0.0, max_tokens=900):
    """One blocking call to llama-server. Used by the verification layers, which must
    finish before a reply is sent, so there is nothing to stream."""
    r = httpx.post(f"{UPSTREAM}/v1/chat/completions", timeout=600.0,
                   json=dict(messages=[dict(role="system", content=system),
                                       dict(role="user", content=user)],
                             temperature=0, max_tokens=max_tokens,
                             lora=[dict(id=0, scale=scale)]))
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _last_user(body):
    return next((m.get("content") for m in reversed(body["messages"])
                 if m.get("role") == "user"), None)


def _reply(text, asked, chose, how, extra=""):
    """An OpenAI-shaped reply. `chose` and `how` are surfaced so the UI (and the log) can
    show which mode answered and whether a verification layer acted. `extra` is appended
    to the visible answer, and carries the out-of-scope note."""
    note = f"\n\n<!-- ostutor: mode={chose} path={how} -->"
    print(json.dumps(dict(t=time.strftime("%H:%M:%S"), asked=asked, mode=chose,
                          path=how, why=_WHY.get("last", ""))), flush=True)
    return JSONResponse(dict(
        id=f"ostutor-{how}", object="chat.completion", created=int(time.time()),
        model=asked, choices=[dict(index=0, finish_reason="stop",
                                   message=dict(role="assistant",
                                                content=text + extra + note))],
        usage=dict(prompt_tokens=0, completion_tokens=0, total_tokens=0)))


_classify_cache = {}
_WHY = {}


def _classify(question):
    """What kind of question is this? Reuses the extraction call, which already returns
    the kind, so routing costs nothing extra. Cached because the handler needs the
    answer twice (to route, and to decide whether to add the scope note)."""
    if question in _classify_cache:
        return _classify_cache[question]
    try:
        d = normalise(parse_json(_upstream(EXTRACT_PROMPT, question)), question) or {}
        kind = d.get("kind")
    except Exception as e:
        log.warning("classification failed, falling back to lexical routing: %s", e)
        kind = None
    if len(_classify_cache) > 256:
        _classify_cache.clear()
    _classify_cache[question] = kind
    return kind


# A student showing their own work. This one signal stays lexical rather than
# model-judged, because it decides whether the student is handed an answer or taught,
# and getting it wrong is the difference between tutoring and spoiling the exercise.
_ATTEMPT = re.compile(r"\b(?:my attempt|my answer|my working|i got|i calculated|i used|"
                      r"i think it(?:'s| is)|i believe|is (?:that|this|my answer) (?:right|correct)|"
                      r"am i (?:right|correct)|did i (?:get|do) (?:it|this)|"
                      r"where (?:did|have) i (?:go|gone) wrong|check my|"
                      r"what did i do wrong)\b", re.I)
# Fallbacks used only when the classifier is unavailable or returns nothing.
_ANALYSIS_HINT = re.compile(r"\b(?:why|compare|comparison|versus|vs\.?|trade-?offs?|better|"
                            r"best|worse|choose|choice|which (?:would|one|scheduler|"
                            r"algorithm)|design|diagnose|when should|should i|"
                            r"advantages?|disadvantages?|pros and cons)\b", re.I)
_SHELL_HINT = re.compile(r"\b(?:bash|shell|command line|terminal|one-?liner|"
                         r"(?:which|what) command|grep|awk|sed|chmod|ps aux|kill -9)\b", re.I)

OFFTOPIC_REASON = "not an operating-systems question"

MODE_FOR_KIND = {
    "formula": "ostutor-solve",
    "incomplete": "ostutor-solve",     # its prompt asks for the missing input
    "analysis": "ostutor-analyze",
    "concept": "ostutor-explain",
    "shell": "ostutor-shell",
    "offtopic": "ostutor-explain",     # answered, but with the scope note below
}


def route(question):
    """Which mode should answer, and why.

    Returns (mode, reason). Precedence is deliberate:

      1. The student SHOWED THEIR WORKING -> tutoring, always. This outranks the
         classifier: a question can look like a solvable exercise and still be a
         student asking to be taught, and handing them the answer is the one failure
         this mode exists to prevent.
      2. The classifier's kind, which is the same extraction call the solver already
         makes, so routing costs nothing extra. A procedure it can name goes to the
         verified solver.
      3. Lexical hints, only if the classifier said nothing useful.

    Model-judged intent with a lexical override for the one case that must not be got
    wrong, rather than regexes pretending to be a classifier."""
    q = question or ""
    if _ATTEMPT.search(q):
        return "ostutor-tutor", "the student showed their own attempt"
    kind = _classify(q)
    if kind in SOLVER_KINDS:
        return "ostutor-solve", f"a {kind.replace('_', ' ')} procedure"
    if kind == "offtopic":
        return MODE_FOR_KIND[kind], OFFTOPIC_REASON
    if kind in MODE_FOR_KIND:
        return MODE_FOR_KIND[kind], f"classified as {kind}"
    if _SHELL_HINT.search(q):
        return "ostutor-shell", "asks for a shell command (lexical fallback)"
    if _ANALYSIS_HINT.search(q):
        return "ostutor-analyze", "open/comparative question (lexical fallback)"
    return "ostutor-explain", "no other signal; treated as a concept question"


SCOPE_NOTE = ("\n\n---\n> _I am an Operating Systems tutor, so that is outside what I am "
              "built for. Ask me about scheduling, memory, deadlock, file systems, "
              "concurrency or the Linux command line and I can be genuinely useful._")


def verified_answer(question):
    """A simulator-computed worked solution, or None.

    Measured on the 57 hand-written items: the model alone scores 64.9%, and every
    scheduling failure was a perfect table built from a wrong schedule. Reading the
    parameters and letting the simulator execute scores 100%, and is faster, because a
    short extraction call replaces a long generation."""
    try:
        text, meta = solve(question, lambda s, u: _upstream(s, u, scale=0.0))
    except Exception as e:                       # never let this break the chat path
        log.warning("solver path failed, falling back to the model: %s", e)
        return None
    if text is None:
        return None
    return text + ("\n\n---\n> _Computed by the verified "
                   f"{meta['kind'].replace('_', ' ')} simulator rather than by the "
                   "language model, so these numbers are exact._")


NOT_IN_NOTES = ("\n\n---\n> **Not found in the course materials.** This answer comes from the "
                "tutor's general knowledge, not from your notes; check it against your textbook "
                "or ask your instructor.")


def grounded(spec, question):
    """(system prompt, footer): the mode's trained prompt with the relevant course notes
    appended and a sources footer; or, when the notes do not cover the question, the
    trained prompt unchanged and a footer saying so. Retrieval off, or a mode that does
    not retrieve, leaves both untouched."""
    if RAG is None or not spec.get("rag") or not question:
        return spec["prompt"], ""
    try:
        hits = RAG.retrieve(question)
    except Exception as e:                       # never let retrieval break the chat path
        log.warning("retrieval failed, answering without notes: %s", e)
        return spec["prompt"], NOT_IN_NOTES
    if not hits:
        return spec["prompt"], NOT_IN_NOTES
    return augment(spec["prompt"], hits), sources_footer(hits)


def fact_checked(answer, system, question):
    """Re-ask once if the drafted answer asserts a known misconception.

    The dataset drops answers that assert one, which removes the error from training but
    does not teach the correction - the trained model still says "Yes, LRU suffers from
    Belady's anomaly", because one row cannot outweigh a confident pretrained prior. So
    the check moves to serving, where the fact can be stated and the answer redrafted."""
    flags = fact_flags(answer or "")
    if not flags:
        return answer, []
    names = sorted({n for n, _ in flags})
    facts = [CORRECTIONS[n] for n in names if n in CORRECTIONS]
    if not facts:
        return answer, names
    note = (system + "\n\nOne or more statements in your draft were incorrect. "
            "The following is correct and must be reflected in your answer:\n"
            + "\n".join(f"- {f}" for f in facts)
            + "\nRewrite the explanation so it is consistent with this.")

    def corrected(draft):
        # State the fact plainly rather than ship the misconception unmarked.
        return ("> **Correction applied by the fact checker.**\n"
                + "\n".join(f"> {f}" for f in facts) + "\n\n" + draft)

    try:
        second = _upstream(note, question, scale=1.0, max_tokens=2048)
    except Exception as e:
        # The redraft is unavailable (server down, timeout). Returning the draft as-is
        # would hand the student a known misconception with no warning, so the
        # correction is attached to it instead.
        log.warning("fact-check retry failed: %s", e)
        return corrected(answer), names
    if fact_flags(second):
        return corrected(second), names
    return second + ("\n\n---\n> _Checked against known OS misconceptions; one "
                     "statement was corrected before answering._"), names


@app.post("/v1/chat/completions")
async def chat(req: Request):
    raw = await req.json()
    asked = raw.get("model", DEFAULT_MODEL)
    spec = MODELS.get(asked, MODELS[DEFAULT_MODEL])
    question = _last_user(prepare(raw))
    chose = asked

    # AUTO mode: read the question, pick the mode, then behave exactly as that mode.
    why, scope = "", ""
    if spec.get("route") and question:
        chose, why = route(question)
        _WHY["last"] = why
        # Read it from the routing decision itself rather than peeking at the classifier
        # cache: one source of truth, and it survives the cache being cleared.
        if why == OFFTOPIC_REASON:
            scope = SCOPE_NOTE
        spec = MODELS[chose]
    body = prepare(raw, prompt_override=spec["prompt"])
    body["lora"] = [dict(id=0, scale=spec["lora"])]
    log_request(raw, body)

    # LAYER 1 - the numbers come from a simulator wherever one applies.
    client_system = any(m.get("role") == "system" and str(m.get("content", "")).strip()
                        for m in raw.get("messages", []))
    if spec.get("verify") and question and not client_system:
        verified = verified_answer(question)
        if verified is not None:
            return _reply(verified, asked, chose, "verified", scope)

    # LAYER 2 - prose is grounded in the course notes (when retrieval is on).
    system, footer = (spec["prompt"], "") if client_system else grounded(spec, question)
    if system != spec["prompt"]:
        body = prepare(raw, prompt_override=system)
        body["lora"] = [dict(id=0, scale=spec["lora"])]

    # LAYER 3 - prose answers are checked against known misconceptions.
    if (spec.get("factcheck") and question and not client_system
            and not body.get("stream")):
        draft = await client.post("/v1/chat/completions", json=body)
        if draft.status_code == 200:
            try:
                text = draft.json()["choices"][0]["message"]["content"] or ""
            except (KeyError, IndexError, TypeError):
                text = ""
            checked, flagged = fact_checked(text, system, question)
            if checked:
                return _reply(checked + footer, asked, chose,
                              "fact-corrected" if flagged else "checked", scope)

    if not body.get("stream"):
        r = await client.post("/v1/chat/completions", json=body)
        data = r.json()
        try:
            text = data["choices"][0]["message"]["content"] or ""
            lines = text.split("\n")
            for i in range(len(lines)):
                if loop_detected(lines[: i + 1]):
                    data["choices"][0]["message"]["content"] = "\n".join(lines[: i + 1]) + GUARD_NOTE
                    data["choices"][0]["finish_reason"] = "stop"
                    break
            data["choices"][0]["message"]["content"] += footer
        except (KeyError, IndexError, TypeError):
            pass
        # Tag the mode here too, so every answer records which mode produced it -
        # otherwise the two modes that need no verification layer are the only ones
        # the log cannot attribute.
        try:
            data["choices"][0]["message"]["content"] += \
                f"\n\n<!-- ostutor: mode={chose} path=model -->"
            print(json.dumps(dict(t=time.strftime("%H:%M:%S"), asked=asked,
                                  mode=chose, path="model")), flush=True)
        except (KeyError, IndexError, TypeError):
            pass
        return JSONResponse(data, status_code=r.status_code)

    async def stream():
        text, last_id, created = "", "guard", int(time.time())
        async with client.stream("POST", "/v1/chat/completions", json=body) as r:
            if r.status_code != 200:
                err = (await r.aread()).decode("utf-8", "replace")
                yield f"data: {json.dumps(dict(error=dict(message=err, code=r.status_code)))}\n\n"
                yield "data: [DONE]\n\n"
                return
            async for line in r.aiter_lines():
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    if footer:
                        note = dict(id=last_id, object="chat.completion.chunk", created=created,
                                    model=body["model"],
                                    choices=[dict(index=0, delta=dict(content=footer),
                                                  finish_reason=None)])
                        yield f"data: {json.dumps(note)}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                yield f"data: {payload}\n\n"
                try:
                    chunk = json.loads(payload)
                    last_id = chunk.get("id", last_id)
                    delta = chunk["choices"][0]["delta"].get("content") or ""
                except (ValueError, KeyError, IndexError, TypeError):
                    continue
                if "\n" in delta:
                    text += delta
                    if loop_detected(text.split("\n")[:-1]):
                        note = dict(id=last_id, object="chat.completion.chunk", created=created,
                                    model=body["model"],
                                    choices=[dict(index=0, delta=dict(content=GUARD_NOTE),
                                                  finish_reason="stop")])
                        yield f"data: {json.dumps(note)}\n\n"
                        yield "data: [DONE]\n\n"
                        return          # leaving the context closes the upstream stream
                else:
                    text += delta
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
