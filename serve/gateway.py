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
from ostutor.theory_filter import CORRECTIONS, _reveals, fact_flags  # noqa: E402
from ostutor.shell_check import check_shell  # noqa: E402
from ostutor.rag.retrieve import Retriever, augment, contextual_query, sources_footer  # noqa: E402

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
    # `guard`: the reply is checked before it is shown (tutor_reply below). The simulator
    # runs privately to tell whether the student is right; its answer never reaches the
    # model, and a reply that works the problem out or states a result is redrafted.
    "ostutor-tutor": dict(prompt=SYSTEM_PROMPTS[("tutor", "os")], lora=1.0, guard=True,
                          desc="Socratic tutoring - diagnoses your attempt, never hands over the answer"),
    # 707 shell rows were trained and, until routing existed, unreachable: nothing in
    # the picker used the ("shell", "linux") prompt. `shellcheck`: commands are checked
    # against known pitfalls (ostutor/shell_check.py) before they are shown.
    "ostutor-shell": dict(prompt=SYSTEM_PROMPTS[("shell", "linux")], lora=1.0, shellcheck=True,
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


# Text only the gateway may write: the mode tag and the notes under an answer. Open WebUI
# sends every earlier reply back as history, tags and footers included, and a model shown
# them copies them - a "path=verified" tag on an answer no simulator produced, a second
# Sources block with misremembered ids, a simulator-style trace it made up. So they are
# removed from the history before it is forwarded, and from anything the model writes,
# before the gateway appends its own.
_TAG = re.compile(r"[ \t]*<!--\s*ostutor:.*?-->[ \t]*\n?", re.S | re.I)
_FOOTER = re.compile(
    r"\n*^---[ \t]*\n(?=> (?:\*\*Sources|\*\*Not found in|_Computed by the verified|"
    r"_Not computed by a simulator|_I am an Operating Systems tutor|"
    r"\*\*Stopped by the loop guard|\*\*Fact check))(?:^>.*(?:\n|\Z))+", re.M)


def scrub(text):
    """`text` without the gateway's own tags and footers."""
    return _FOOTER.sub("", _TAG.sub("", text or "")).rstrip()


def clean_history(body):
    """The request with every earlier assistant reply scrubbed of gateway artefacts."""
    msgs = [dict(m, content=scrub(m["content"]))
            if m.get("role") == "assistant" and isinstance(m.get("content"), str) else m
            for m in body.get("messages", [])]
    return dict(body, messages=msgs)


def _followup(raw):
    """When the gateway's previous reply asked for a missing input, the student's next
    message is that input: read it together with the question it completes, so that
    "the quantum is 3" can be solved. Detected from the gateway's own tag, before the
    history is scrubbed."""
    msgs = [m for m in raw.get("messages", []) if m.get("role") in ("user", "assistant")]
    if (len(msgs) >= 3 and [m.get("role") for m in msgs[-3:]] == ["user", "assistant", "user"]
            and "path=asked-for-input" in str(msgs[-2].get("content", ""))):
        return f"{msgs[-3].get('content', '')}\n{msgs[-1].get('content', '')}"
    return None


class TagFilter:
    """Drops `<!-- ostutor: ... -->` from streamed text, which arrives in pieces: text
    from a "<" on is held back until it is known whether it starts such a tag."""

    HOLD = 300

    def __init__(self):
        self.buf = ""

    def feed(self, piece):
        self.buf += piece
        out = ""
        while self.buf:
            i = self.buf.find("<")
            if i < 0:
                out, self.buf = out + self.buf, ""
                break
            out, self.buf = out + self.buf[:i], self.buf[i:]
            if len(self.buf) < 4 and "<!--".startswith(self.buf):
                break                                   # may still become a comment
            if not self.buf.startswith("<!--"):
                out, self.buf = out + self.buf[0], self.buf[1:]
                continue
            j = self.buf.find("-->")
            if j < 0:
                if len(self.buf) > self.HOLD:            # not a short tag: let it through
                    out, self.buf = out + self.buf, ""
                break
            comment, self.buf = self.buf[:j + 3], self.buf[j + 3:]
            if not _TAG.match(comment):
                out += comment
        return out

    def flush(self):
        rest, self.buf = self.buf, ""
        return "" if re.match(r"<!--\s*ostutor", rest, re.I) else rest


def _reply(text, asked, chose, how, extra=""):
    """An OpenAI-shaped reply. `chose` and `how` are surfaced so the UI (and the log) can
    show which mode answered and whether a verification layer acted. `extra` is appended
    to the visible answer."""
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
    answer twice (to route, and to decide whether a hand-picked mode got an off-topic question)."""
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
    "offtopic": "ostutor-explain",     # declined in chat() with OFFTOPIC_REPLY
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


ASK_MISSING = ("I can't solve this one yet: the question doesn't give **{missing}**, and "
               "the answer depends on it. I won't assume a value, because a guessed input "
               "gives a confident wrong answer.\n\nReply with {missing} and I'll compute "
               "the full solution.")

UNVERIFIED_NOTE = ("\n\n---\n> _Not computed by a simulator: the numbers above come from the "
                   "language model and may be wrong. Check them, or restate the problem with "
                   "every value written out._")


OFFTOPIC_REPLY = ("That question is outside what I am built for: I am an Operating Systems "
                  "tutor. Ask me about scheduling, memory management, deadlock, file systems, "
                  "concurrency or the Linux command line and I can help properly.")


def _respond(text, asked, chose, how, extra="", stream=False):
    """A finished answer, as JSON or - when the client asked to stream - as one SSE
    stream, so every client sees the shape it requested."""
    if not stream:
        return _reply(text, asked, chose, how, extra)
    print(json.dumps(dict(t=time.strftime("%H:%M:%S"), asked=asked, mode=chose, path=how)),
          flush=True)
    full = text + extra + f"\n\n<!-- ostutor: mode={chose} path={how} -->"

    def gen():
        for i in range(0, len(full), 400):
            yield "data: " + json.dumps(dict(
                id=f"ostutor-{how}", object="chat.completion.chunk", created=int(time.time()),
                model=asked, choices=[dict(index=0, delta=dict(content=full[i:i + 400]),
                                           finish_reason=None)])) + "\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")


# --- Verified tutoring ---------------------------------------------------------------
# Tutor mode is kept away from the solver's answer so it cannot leak it, and so for a
# while nothing checked what it said: asked about a FIFO attempt of 13 faults, it walked
# the whole trace itself, ignored the three-frame limit, and stated "total page faults =
# 7" (the simulator gives 10). Now the simulator runs privately, the model is told only
# whether the student is right, and the reply is checked before it is shown.
NUMERIC_KINDS = ("scheduling", "paging", "disk", "translate")
_NUM = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])")
# The student's own result: "I got 13", "my answer is 4.5", "= 236".
# A few words may sit between the verb and the number: "I got an average waiting time of
# 7", "I got a total head movement of 643 cylinders", "I got physical address 4306".
_CLAIM = re.compile(r"\b(?:got|get|getting|obtained|answer(?:\s+(?:is|was))?|calculated|computed|"
                    r"came\s+to|comes\s+to|think\s+it(?:'s|\s+is)|believe\s+it(?:'s|\s+is))\s+"
                    r"(?:[A-Za-z][\w-]*\s+){0,6}?(-?\d+(?:\.\d+)?)|=\s*(-?\d+(?:\.\d+)?)", re.I)
# The reply asserting a result of its own: "total page faults = 7", "the answer is 9".
_RESULT = re.compile(r"(?:\btotal\b|\banswer\b|\bresult\b|\baltogether\b|\bin all\b|"
                     r"\bshould (?:be|get)\b|\bcorrect (?:count|value|number)\b)"
                     r"[^\n.?]{0,30}?(?:=|\bis\b|\bare\b|\bof\b|:|\bbe\b|\bget\b)\s*\**\s*"
                     r"(-?\d+(?:\.\d+)?)", re.I)
# One step of a worked trace: a list item with a number and a step word, or a table row.
_STEP = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+.*\d.*\b(?:fault|hit|evict|replac\w*|runs?|"
                   r"serve[ds]?|seek|moves?|allocat\w*|need|work|queue|t\s*=)", re.I)
TRACE_STEPS = 4
TUTOR_GUIDE = {
    "correct": ("The student's final answer has been checked and is correct. Tell them so, "
                "and ask them to explain why one step of their method works."),
    "incorrect": ("The student's final answer has been checked and is incorrect. Do not tell "
                  "them the correct value. Name the idea behind their first mistake and ask "
                  "one question that leads them to it."),
    "unknown": ("Diagnose the misconception behind the attempt and ask one question that "
                "leads the student to it."),
}
TUTOR_RULE = ("\n\nBefore you reply: {guide} Do not solve the problem for them: write no "
              "step-by-step trace, schedule or table, and state no final answer or total. "
              "Keep it short and end with one question.")
TUTOR_RETRY = ("\n\nYour previous draft worked the problem out for the student. Rewrite it in "
               "at most four sentences, using no numbers except those the student wrote, and "
               "end with one question.")
# A verified correct attempt is confirmed by the gateway itself: the model, told the
# student is right, still opened with "let's verify it" in every such case measured.
TUTOR_CONFIRM = ("Your answer is correct: the simulator gets the same result. To make sure the "
                 "method is solid, explain one step in your own words: {step}")
CONFIRM_STEP = {
    "paging": "at the first reference where a page had to leave, which page left, and why did "
              "the policy choose it?",
    "scheduling": "at the first moment two processes were ready, why did the one you chose get "
                  "the CPU?",
    "disk": "why did the head serve your second request before the others?",
    "translate": "how did you split the logical address into a page number and an offset?",
    None: "which step of your working would you check first if the numbers had changed, and why?",
}
TUTOR_FALLBACK = {
    "paging": ("Let's check one step rather than the whole count. Before you mark a reference "
               "as a fault, ask: is that page already in one of the frames at that moment? Go "
               "back to the first reference that repeats a page. Was it a fault in your count, "
               "and should it be?"),
    "scheduling": ("Let's check the schedule before the arithmetic. Write down the ready queue "
                   "each time a process arrives or a time slice ends. At which point does your "
                   "order first differ from the rule this algorithm uses?"),
    "disk": ("Before adding up distances, write down the order in which the head visits the "
             "requests. Does that order follow the algorithm's rule at every step, including "
             "what happens at the end of the disk?"),
    "translate": ("Split the logical address into a page number and an offset first. Which "
                  "page does your address fall in, and which frame does the table map it to?"),
    None: ("Let's go through your working one step at a time and check each against the rule "
           "for this method. Which step is the first one you are least sure about?"),
}


def _nums(text):
    return {float(x) for x in _NUM.findall(text or "")}


def _claimed(question):
    return {float(x or y) for x, y in _CLAIM.findall(question or "")}


def tutor_truth(question):
    """(kind, right answers, verdict) from a private simulator run. The answer is used
    only to judge the student and to check the reply; it is never sent to the model."""
    try:
        text, meta = solve(question, lambda s, u: _upstream(s, u, scale=0.0))
    except Exception as e:                       # never let this break the chat path
        log.warning("tutor check unavailable: %s", e)
        return None, set(), "unknown"
    if not text:
        return None, set(), "unknown"
    kind = meta.get("kind")
    line = next((l for l in text.splitlines() if l.startswith("**Answer:")), "")
    right = _nums(line) if kind in NUMERIC_KINDS else set()
    claimed = _claimed(question)
    if not right or not claimed:
        return kind, right, "unknown"
    return kind, right, "correct" if claimed & right else "incorrect"


def tutor_leak(reply, right, claimed):
    """Why the reply must not be shown, or "" when it may be. It leaks if it states the
    simulator's answer (when the student does not have it), asserts any result the
    student did not write, or works the problem out step by step."""
    for r in right - claimed:
        if _reveals(reply, int(r) if r == int(r) else r):
            return "states the answer"
    for x in _RESULT.findall(reply or ""):
        if float(x) not in claimed:
            return f"asserts a result ({x})"
    steps = sum(bool(_STEP.search(l)) for l in (reply or "").splitlines())
    rows = sum(l.lstrip().startswith("|") for l in (reply or "").splitlines())
    if steps >= TRACE_STEPS or rows >= 5:
        return "works the problem out"
    return ""


async def tutor_reply(raw, question):
    """(text, path) for tutor mode: checked, redrafted once, or a safe hint."""
    kind, right, verdict = tutor_truth(question)
    claimed = _claimed(question)
    if verdict == "correct":
        return TUTOR_CONFIRM.format(step=CONFIRM_STEP.get(kind, CONFIRM_STEP[None])), "tutor-confirmed"
    system = SYSTEM_PROMPTS[("tutor", "os")] + TUTOR_RULE.format(guide=TUTOR_GUIDE[verdict])
    for attempt in range(2):
        body = prepare(raw, prompt_override=system)
        body.update(stream=False, lora=[dict(id=0, scale=1.0)])
        try:
            r = await client.post("/v1/chat/completions", json=body)
            text = scrub(r.json()["choices"][0]["message"]["content"] or "")
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as e:
            log.warning("tutor draft failed: %s", e)
            break
        why = tutor_leak(text, right, claimed)
        if not why:
            return text, "tutor-checked" if attempt == 0 else "tutor-redrafted"
        log.info("tutor draft rejected: %s", why)
        system += TUTOR_RETRY
    return TUTOR_FALLBACK.get(kind, TUTOR_FALLBACK[None]), "tutor-safe-hint"


def shell_checked(text):
    """The answer with mechanical command fixes applied and a note explaining each."""
    fixed, notes = check_shell(text)
    if not notes:
        return text, False
    return fixed + "\n\n---\n> **Command check:**\n" + "\n".join(f"> - {n}" for n in notes), True


def stream_fact_note(text):
    """The note appended after a STREAMED answer that states a known misconception. A
    streamed answer has already been shown, so it cannot be redrafted as fact_checked()
    does; the correct fact is stated under it instead."""
    names = sorted({n for n, _ in fact_flags(text or "", serving=True)})
    facts = [CORRECTIONS[n] for n in names if n in CORRECTIONS]
    if not facts:
        return ""
    return ("\n\n---\n> **Fact check:** part of the answer above states a known "
            "misconception. The correct fact:\n" + "\n".join(f"> {f}" for f in facts))


def verified_answer(question):
    """(text, path) for a simulator-computed worked solution, or for a request for a
    missing input; None when the model should answer for itself.

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
        # Pre-flight validation: extraction found the problem but not every input it needs
        # (Round Robin without a quantum, paging without a frame count, ...). The model is
        # not asked to answer - it would invent the value - the input is asked for.
        missing = " ".join(str(meta.get("missing") or "").split())[:120]
        if meta.get("reason") == "incomplete" and missing:
            return ASK_MISSING.format(missing=missing), "asked-for-input"
        return None
    return text + ("\n\n---\n> _Computed by the verified "
                   f"{meta['kind'].replace('_', ' ')} simulator rather than by the "
                   "language model, so these numbers are exact._"), "verified"


NOT_IN_NOTES = ("\n\n---\n> **Not found in the course materials.** This answer comes from the "
                "tutor's general knowledge, not from your notes; check it against your textbook "
                "or ask your instructor.")


def grounded(spec, question, query=None):
    """(system prompt, footer): the mode's trained prompt with the relevant course notes
    appended and a sources footer; or, when the notes do not cover the question, the
    trained prompt unchanged and a footer saying so. Retrieval off, or a mode that does
    not retrieve, leaves both untouched. `query` is what to retrieve with when it differs
    from the question (a follow-up read with the question before it)."""
    if RAG is None or not spec.get("rag") or not question:
        return spec["prompt"], ""
    not_found = RAG.not_found or NOT_IN_NOTES
    try:
        hits = RAG.retrieve(query or question)
    except Exception as e:                       # never let retrieval break the chat path
        log.warning("retrieval failed, answering without notes: %s", e)
        return spec["prompt"], not_found
    if not hits:
        return spec["prompt"], not_found
    return augment(spec["prompt"], hits, RAG.noun), sources_footer(hits, RAG.sources_heading)


def fact_checked(answer, system, question):
    """Re-ask once if the drafted answer asserts a known misconception.

    The dataset drops answers that assert one, which removes the error from training but
    does not teach the correction - the trained model still says "Yes, LRU suffers from
    Belady's anomaly", because one row cannot outweigh a confident pretrained prior. So
    the check moves to serving, where the fact can be stated and the answer redrafted."""
    flags = fact_flags(answer or "", serving=True)
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
    if fact_flags(second, serving=True):
        return corrected(second), names
    return second + ("\n\n---\n> _Checked against known OS misconceptions; one "
                     "statement was corrected before answering._"), names


@app.post("/v1/chat/completions")
async def chat(req: Request):
    raw = await req.json()
    pending = _followup(raw)
    raw = clean_history(raw)
    asked = raw.get("model", DEFAULT_MODEL)
    spec = MODELS.get(asked, MODELS[DEFAULT_MODEL])
    question = pending or _last_user(prepare(raw))
    chose = asked

    # AUTO mode: read the question, pick the mode, then behave exactly as that mode.
    why = ""
    if spec.get("route") and question:
        chose, why = route(question)
        _WHY["last"] = why
        spec = MODELS[chose]
        # Not an OS question: say so, rather than answer it with OS analogies attached.
        # Read from the routing decision itself rather than the classifier cache: one
        # source of truth, and it survives the cache being cleared.
        if why == OFFTOPIC_REASON:
            return _respond(OFFTOPIC_REPLY, asked, chose, "out-of-scope",
                            stream=bool(raw.get("stream")))
    # A worked problem is answered on its own: earlier problems in the same chat (SRTF,
    # then RR, then FIFO) are not shown to the model, so their rules cannot bleed in.
    client_system = any(m.get("role") == "system" and str(m.get("content", "")).strip()
                        for m in raw.get("messages", []))
    if chose == "ostutor-solve" and question and not client_system:
        raw = dict(raw, messages=[dict(role="user", content=question)])
    body = prepare(raw, prompt_override=spec["prompt"])
    body["lora"] = [dict(id=0, scale=spec["lora"])]
    log_request(raw, body)

    # Tutor mode: the reply is checked against a private simulator run before it is shown.
    if spec.get("guard") and question and not client_system:
        text, how = await tutor_reply(raw, question)
        return _respond(text, asked, chose, how, stream=bool(body.get("stream")))

    # Shell mode: commands are checked against known pitfalls, and fixed, before shown.
    if spec.get("shellcheck") and question and not client_system:
        r = await client.post("/v1/chat/completions", json=dict(body, stream=False))
        try:
            text = scrub(r.json()["choices"][0]["message"]["content"] or "")
        except (KeyError, IndexError, TypeError, ValueError):
            text = None
        if text is not None:
            text, fixed = shell_checked(text)
            return _respond(text, asked, chose, "command-fixed" if fixed else "command-checked",
                            stream=bool(body.get("stream")))

    # LAYER 1 - the numbers come from a simulator wherever one applies.
    if spec.get("verify") and question and not client_system:
        verified = verified_answer(question)
        if verified is not None:
            return _reply(verified[0], asked, chose, verified[1])

    # LAYER 2 - prose is grounded in the course notes (when retrieval is on).
    system, footer = (spec["prompt"], "") if client_system else \
        grounded(spec, question, contextual_query(raw.get("messages", []), question))
    # A mode picked by hand is not routed, so an off-topic question reaches it unread.
    # When retrieval finds nothing relevant (or is off), ask the classifier, and decline
    # a question that is not about operating systems at all.
    if (spec.get("rag") and question and not client_system and asked == chose
            and system == spec["prompt"] and _classify(question) == "offtopic"):
        return _respond(OFFTOPIC_REPLY, asked, chose, "out-of-scope", stream=bool(body.get("stream")))
    # Solve mode without a simulator: the model's own numbers, marked as such.
    if chose == "ostutor-solve" and not client_system:
        footer += UNVERIFIED_NOTE
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
            checked, flagged = fact_checked(scrub(text), system, question)
            if checked:
                return _reply(checked + footer, asked, chose,
                              "fact-corrected" if flagged else "checked")

    if not body.get("stream"):
        r = await client.post("/v1/chat/completions", json=body)
        data = r.json()
        try:
            text = scrub(data["choices"][0]["message"]["content"] or "")
            data["choices"][0]["message"]["content"] = text
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
        tags = TagFilter()

        def piece(content, finish=None):
            return "data: " + json.dumps(dict(id=last_id, object="chat.completion.chunk",
                                              created=created, model=body["model"],
                                              choices=[dict(index=0, delta=dict(content=content),
                                                            finish_reason=finish)])) + "\n\n"
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
                    rest = tags.flush()
                    if rest:
                        yield piece(rest)
                    # Post-stream check: Open WebUI streams, which used to skip the fact
                    # checker for every Explain and Analyze answer in the UI.
                    note = stream_fact_note(text) if spec.get("factcheck") and not client_system else ""
                    if note or footer:
                        yield piece(note + footer)
                    yield "data: [DONE]\n\n"
                    return
                try:
                    chunk = json.loads(payload)
                    last_id = chunk.get("id", last_id)
                    delta = chunk["choices"][0]["delta"].get("content") or ""
                except (ValueError, KeyError, IndexError, TypeError):
                    yield f"data: {payload}\n\n"
                    continue
                if delta:
                    clean = tags.feed(delta)
                    chunk["choices"][0]["delta"]["content"] = clean
                    if clean or chunk["choices"][0].get("finish_reason"):
                        yield f"data: {json.dumps(chunk)}\n\n"
                else:
                    yield f"data: {payload}\n\n"
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
