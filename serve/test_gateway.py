"""Gateway tests against a simulated llama-server (no GPU needed).

    serve/.venv-webui/Scripts/python serve/test_gateway.py
"""
import asyncio
import json
import sys
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gateway  # noqa: E402

SEEN = []
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  -> {detail}" if not ok and detail else ""))
    if not ok:
        FAILED.append(name)


mock = FastAPI()


@mock.post("/v1/chat/completions")
async def upstream(req: Request):
    body = await req.json()
    SEEN.append(body)
    user = body["messages"][-1]["content"]
    if user == "loop":
        lines = ["**Policy: FIRST-fit**", ""] + ["- request 1000: must WAIT"] * 300
    elif user == "legit":   # a real trace: repetitive shape, distinct lines
        lines = [f"- t={t}: A runs, {20 - t} left; queue [B, A]" for t in range(20)] + \
                ["| # | Ref | Result |", "|---|---|---|"] + [f"| {i} | 3 | HIT |" for i in range(8)]
    else:
        lines = ["Step 1", "Step 2", "**Answer: 42**"]
    if not body.get("stream"):
        return dict(id="x", choices=[dict(index=0, message=dict(role="assistant",
                                                                 content="\n".join(lines)),
                                          finish_reason="stop")])

    async def gen():
        for ln in lines:
            chunk = dict(id="x", object="chat.completion.chunk",
                         choices=[dict(index=0, delta=dict(content=ln + "\n"), finish_reason=None)])
            yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")


async def text_of_stream(c, model, prompt):
    out, n_chunks = "", 0
    async with c.stream("POST", "/v1/chat/completions",
                        json=dict(model=model, stream=True,
                                  messages=[dict(role="user", content=prompt)])) as r:
        async for line in r.aiter_lines():
            if line.startswith("data:") and line[5:].strip() != "[DONE]":
                n_chunks += 1
                out += json.loads(line[5:])["choices"][0]["delta"].get("content") or ""
    return out, n_chunks


async def main():
    gateway.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=mock), base_url="http://up")
    c = httpx.AsyncClient(transport=httpx.ASGITransport(app=gateway.app), base_url="http://gw")

    ids = [m["id"] for m in (await c.get("/v1/models")).json()["data"]]
    check("lists the six tutor modes", ids == ["ostutor", "ostutor-solve", "ostutor-analyze",
                                               "ostutor-explain", "ostutor-tutor",
                                               "ostutor-shell"], ids)
    check("auto mode is the default", gateway.DEFAULT_MODEL == "ostutor")
    # The untuned base was only ever offered for side-by-side comparison during
    # development. It is still called internally at LoRA scale 0 for parameter
    # extraction, but a student should not be able to pick it by accident.
    check("the untuned base is not offered as a mode",
          not any("base" in i for i in ids), ids)
    check("every offered mode is the fine-tuned adapter",
          all(gateway.MODELS[i]["lora"] == 1.0 for i in ids))

    await c.post("/v1/chat/completions", json=dict(model="ostutor-explain",
                                                   messages=[dict(role="user", content="hi")]))
    b = SEEN[-1]
    check("injects the trained system prompt for the mode",
          b["messages"][0] == dict(role="system", content=gateway.SYSTEM_PROMPTS[("explain", "os")]))
    check("greedy decoding by default", b["temperature"] == 0.0)
    check("16k ceiling applied", b["max_tokens"] == 16384)
    check("fine-tuned modes use the LoRA", b["lora"] == [dict(id=0, scale=1.0)])

    await c.post("/v1/chat/completions", json=dict(model="ostutor-tutor", max_tokens=999999,
                                                   messages=[dict(role="user", content="hi")]))
    check("client max_tokens is capped at the ceiling", SEEN[-1]["max_tokens"] == 16384)

    # Routing. A shown attempt must reach the tutor, because handing that student a
    # computed answer is exactly what the Socratic mode exists to avoid.
    # route() returns (mode, reason); the reason is logged so a misroute is diagnosable.
    mode, reason = gateway.route("P1(0,7) P2(1,4) SRTF. My attempt: I got 5.0. Am I right?")
    check("a shown attempt routes to tutoring", mode == "ostutor-tutor", f"{mode} ({reason})")
    check("and the reason says why", "attempt" in reason, reason)
    # Two branches, tested separately. With the classifier available its verdict wins;
    # with it unavailable (no model server, or unparseable reply) routing must still be
    # sensible, so the lexical fallback is exercised with _classify stubbed out.
    _real_classify = gateway._classify
    gateway._classify = lambda q: "analysis"
    mode, reason = gateway.route("Why is Round Robin better than FCFS?")
    check("the classifier's verdict is honoured", mode == "ostutor-analyze", mode)
    gateway._classify = lambda q: None
    mode, reason = gateway.route("Why is Round Robin better than FCFS for interactive work?")
    check("an open comparison falls back to analysis without a classifier",
          mode == "ostutor-analyze" and "fallback" in reason, f"{mode} ({reason})")
    mode, _ = gateway.route("Which command shows the processes using the most memory?")
    check("a command request falls back to shell without a classifier",
          mode == "ostutor-shell", mode)
    mode, _ = gateway.route("What is a page fault?")
    check("a plain concept question ends at explanation", mode == "ostutor-explain", mode)
    gateway._classify = _real_classify
    # The lexical attempt signal must outrank the classifier: a solvable-looking problem
    # from a student who showed working is still a teaching moment.
    mode, _ = gateway.route("Disk queue 98 183 37, head 53, SSTF. I got 150. Am I correct?")
    check("a solvable problem with a shown attempt still routes to tutoring",
          mode == "ostutor-tutor", mode)
    check("tutoring never gets a simulator-computed answer",
          not gateway.MODELS["ostutor-tutor"].get("verify"))
    check("tutoring is not fact-check-rewritten either",
          not gateway.MODELS["ostutor-tutor"].get("factcheck"))

    # The fact checker must state the correct fact, not merely drop the answer.
    fixed, flagged = gateway.fact_checked(
        "Yes, LRU suffers from Belady's anomaly.", "sys", "Does LRU suffer from it?")
    check("a misconception in a draft is caught", flagged == ["lru_belady"], str(flagged))
    check("the correction is surfaced to the student",
          "never suffers" in fixed or "does not" in fixed.lower(), fixed[:120])

    await c.post("/v1/chat/completions", json=dict(model="ostutor-solve", messages=[
        dict(role="system", content="custom"), dict(role="user", content="hi")]))
    check("a client system prompt is respected, not duplicated",
          [m["role"] for m in SEEN[-1]["messages"]] == ["system", "user"]
          and SEEN[-1]["messages"][0]["content"] == "custom")

    out, _ = await text_of_stream(c, "ostutor-solve", "normal")
    check("normal answer streams through intact", out == "Step 1\nStep 2\n**Answer: 42**\n", repr(out))

    out, _ = await text_of_stream(c, "ostutor-solve", "loop")
    check("loop guard stops a repetition loop early",
          "loop guard" in out and out.count("must WAIT") <= gateway.LOOP_REPEATS + 1,
          f"{out.count('must WAIT')} repeats")

    out, _ = await text_of_stream(c, "ostutor-solve", "legit")
    check("loop guard does not cut a long legitimate trace", "loop guard" not in out
          and out.count("\n") == 30, out[-200:])

    r = await c.post("/v1/chat/completions", json=dict(model="ostutor-solve",
                                                       messages=[dict(role="user", content="loop")]))
    msg = r.json()["choices"][0]["message"]["content"]
    check("loop guard also applies to non-streaming answers",
          "loop guard" in msg and msg.count("must WAIT") <= gateway.LOOP_REPEATS)

    print("\nALL GATEWAY TESTS PASSED" if not FAILED else f"\n{len(FAILED)} FAILED: {FAILED}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
