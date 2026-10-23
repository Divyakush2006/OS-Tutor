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
    elif user == "tagged":  # a model copying what it saw in the history
        lines = ["FIFO trace", "**Answer: 9**", "", "---", "> **Sources from your course notes**",
                 "> [S1] Fake (`wp-belady-anomaly`)", "", "<!-- ostutor: mode=ostutor-solve path=verified -->"]
    elif user == "lru":     # a known misconception
        lines = ["Yes, LRU suffers from Belady's anomaly."]
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

    def no_server(*a, **k):
        raise ConnectionError("tests never call the real model server")
    gateway._upstream = no_server
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

    # The fact checker must state the correct fact, not merely drop the answer. Its redraft
    # goes through gateway._upstream, a blocking call to the real model server, so it is
    # stubbed here: these tests must not depend on whether llama-server happens to be up.
    wrong = "Yes, LRU suffers from Belady's anomaly."
    real_upstream = gateway._upstream
    try:
        gateway._upstream = lambda *a, **k: "No. LRU is a stack algorithm and is immune."
        fixed, flagged = gateway.fact_checked(wrong, "sys", "Does LRU suffer from it?")
        check("a misconception in a draft is caught", flagged == ["lru_belady"], str(flagged))
        check("a clean redraft replaces the misconception",
              "suffers from Belady" not in fixed and "stack algorithm" in fixed, fixed[:120])

        gateway._upstream = lambda *a, **k: wrong
        fixed, _ = gateway.fact_checked(wrong, "sys", "Does LRU suffer from it?")
        check("a redraft that is still wrong gets the correction stated",
              "Correction applied" in fixed and "never suffers" in fixed, fixed[:120])

        def down(*a, **k):
            raise ConnectionError("model server unreachable")
        gateway._upstream = down
        fixed, flagged = gateway.fact_checked(wrong, "sys", "Does LRU suffer from it?")
        check("with the redraft unavailable, the correction is still surfaced",
              "Correction applied" in fixed and "never suffers" in fixed, fixed[:120])
        check("and the misconception is still flagged", flagged == ["lru_belady"], str(flagged))
    finally:
        gateway._upstream = real_upstream

    await c.post("/v1/chat/completions", json=dict(model="ostutor-solve", messages=[
        dict(role="system", content="custom"), dict(role="user", content="hi")]))
    check("a client system prompt is respected, not duplicated",
          [m["role"] for m in SEEN[-1]["messages"]] == ["system", "user"]
          and SEEN[-1]["messages"][0]["content"] == "custom")

    out, _ = await text_of_stream(c, "ostutor-solve", "normal")
    check("normal answer streams through intact",
          out.startswith("Step 1\nStep 2\n**Answer: 42**\n"), repr(out))
    check("a solve answer no simulator computed says so", "Not computed by a simulator" in out, out[-120:])

    out, _ = await text_of_stream(c, "ostutor-solve", "loop")
    check("loop guard stops a repetition loop early",
          "loop guard" in out and out.count("must WAIT") <= gateway.LOOP_REPEATS + 1,
          f"{out.count('must WAIT')} repeats")

    out, _ = await text_of_stream(c, "ostutor-solve", "legit")
    check("loop guard does not cut a long legitimate trace", "loop guard" not in out
          and out.count("left; queue") == 20 and out.count("| HIT |") == 8, out[-200:])

    r = await c.post("/v1/chat/completions", json=dict(model="ostutor-solve",
                                                       messages=[dict(role="user", content="loop")]))
    msg = r.json()["choices"][0]["message"]["content"]
    check("loop guard also applies to non-streaming answers",
          "loop guard" in msg and msg.count("must WAIT") <= gateway.LOOP_REPEATS)

    # Retrieval (G2). Off by default: every test above ran with RAG = None and saw the
    # trained prompt unchanged. Turned on here over the test fixture, never the real notes.
    check("retrieval is off unless OSTUTOR_RAG is set", gateway.RAG is None)
    from ostutor.rag.retrieve import Retriever
    gateway.RAG = Retriever(gateway.ROOT / "data" / "rag" / "fixture")
    try:
        explain = gateway.SYSTEM_PROMPTS[("explain", "os")]
        r = await c.post("/v1/chat/completions", json=dict(model="ostutor-explain", messages=[
            dict(role="user", content="Can LRU suffer from Belady's anomaly?")]))
        sent = SEEN[-1]["messages"][0]["content"]
        check("an explain question gets the trained prompt plus the notes",
              sent.startswith(explain + "\n\n") and "[S1] Page replacement" in sent, sent[:120])
        check("the answer ends with its sources",
              "Sources from your course notes" in r.json()["choices"][0]["message"]["content"])
        await c.post("/v1/chat/completions", json=dict(model="ostutor-tutor", messages=[
            dict(role="user", content="Can LRU suffer from Belady's anomaly? I think yes.")]))
        check("tutor mode never retrieves",
              SEEN[-1]["messages"][0]["content"] == gateway.SYSTEM_PROMPTS[("tutor", "os")])
        r = await c.post("/v1/chat/completions", json=dict(model="ostutor-explain", messages=[
            dict(role="user", content="What is the capital of Australia?")]))
        check("a question the notes do not cover gets no notes",
              SEEN[-1]["messages"][0]["content"] == explain)
        check("and the answer says it is not from the course materials",
              "Not found in the course materials" in r.json()["choices"][0]["message"]["content"])
        # RAG never overrides a computed answer: a solvable problem in a retrieving mode is
        # answered by the simulator layer, which runs first, and retrieval is not consulted.
        real_verified, real_retrieve = gateway.verified_answer, gateway.RAG.retrieve
        asked_rag = []
        gateway.verified_answer = lambda q: ("SIMULATOR ANSWER", "verified")
        gateway.RAG.retrieve = lambda q, **k: asked_rag.append(q) or real_retrieve(q, **k)
        try:
            r = await c.post("/v1/chat/completions", json=dict(model="ostutor-analyze", messages=[
                dict(role="user", content="FCFS, P1 arrives 0 burst 5, P2 arrives 1 burst 3. Average waiting time?")]))
            reply = r.json()["choices"][0]["message"]["content"]
            check("a solvable problem still gets the simulator's answer with retrieval on",
                  reply.startswith("SIMULATOR ANSWER") and "Sources from your course notes" not in reply, reply[:80])
            check("and retrieval is not consulted for it", asked_rag == [])
        finally:
            gateway.verified_answer, gateway.RAG.retrieve = real_verified, real_retrieve
        out, _ = await text_of_stream(c, "ostutor-explain", "How does the working set model "
                                                            "prevent thrashing?")
        check("a streamed answer also ends with its sources",
              out.startswith("Step 1") and "Sources from your course notes" in out, out[-160:])
    finally:
        gateway.RAG = None

    # --- audit fixes (24 Oct): artefacts, missing inputs, isolation, sources ---
    tag = "<!-- ostutor: mode=ostutor-solve path=verified -->"
    history = [dict(role="user", content="SRTF problem ..."),
               dict(role="assistant", content="Gantt ...\n\n---\n> **Sources from your course notes**\n"
                                              "> [S1] X (`wp-x`)\n\n" + tag),
               dict(role="user", content="hi")]
    await c.post("/v1/chat/completions", json=dict(model="ostutor-explain", messages=history))
    fwd = [m["content"] for m in SEEN[-1]["messages"] if m["role"] == "assistant"]
    check("earlier replies reach the model without gateway tags or footers",
          fwd == ["Gantt ..."], repr(fwd))

    r = await c.post("/v1/chat/completions", json=dict(model="ostutor-explain",
                                                       messages=[dict(role="user", content="tagged")]))
    msg = r.json()["choices"][0]["message"]["content"]
    check("a tag the model writes is removed; only the gateway's own remains",
          "path=verified" not in msg and msg.count("<!-- ostutor:") == 1 and "path=" in msg, msg[-160:])
    check("a Sources block the model writes is removed", "wp-belady-anomaly" not in msg, msg[-160:])
    out, _ = await text_of_stream(c, "ostutor-explain", "tagged")
    check("a tag the model writes is removed from a stream too",
          "<!--" not in out and "**Answer: 9**" in out, repr(out[-120:]))

    f = gateway.TagFilter()
    pieces = ["ok <", "!-", "- ostu", "tor: mode=x path=verified -", "-> done <b>"]
    got = "".join(f.feed(x) for x in pieces) + f.flush()
    check("the stream filter drops a tag split across pieces and keeps other markup",
          got == "ok  done <b>", repr(got))

    real_solve = gateway.solve
    try:
        gateway.solve = lambda q, ask: (None, dict(delegated=False, reason="incomplete",
                                                   missing="the time quantum (time slice)"))
        text, how = gateway.verified_answer("RR, P1 0 5, P2 1 3. I forgot the quantum.")
        check("a missing input is asked for, not guessed",
              how == "asked-for-input" and "time quantum" in text and "won't assume" in text, text)
        before = len(SEEN)
        r = await c.post("/v1/chat/completions", json=dict(model="ostutor-solve", messages=[
            dict(role="user", content="RR, P1 0 5, P2 1 3. I forgot the quantum.")]))
        msg = r.json()["choices"][0]["message"]["content"]
        check("and the model is not called to invent one",
              len(SEEN) == before and "path=asked-for-input" in msg, msg[-120:])

        asked = []
        gateway.solve = lambda q, ask: asked.append(q) or ("SOLVED", dict(delegated=True, kind="scheduling"))
        r = await c.post("/v1/chat/completions", json=dict(model="ostutor-solve", messages=[
            dict(role="user", content="RR, P1 0 5, P2 1 3. I forgot the quantum."),
            dict(role="assistant", content=msg),
            dict(role="user", content="the quantum is 2")]))
        check("the reply to a request for input is read with the question it completes",
              asked and "P1 0 5" in asked[-1] and "quantum is 2" in asked[-1], repr(asked[-1:]))
    finally:
        gateway.solve = real_solve

    await c.post("/v1/chat/completions", json=dict(model="ostutor-solve", messages=[
        dict(role="user", content="SRTF: P1 0 8, P2 1 4"), dict(role="assistant", content="old trace"),
        dict(role="user", content="FIFO, frames 3, refs 1 2 3 4 1 2")]))
    check("a worked problem is answered on its own, without earlier problems in the chat",
          [m["role"] for m in SEEN[-1]["messages"]] == ["system", "user"]
          and SEEN[-1]["messages"][-1]["content"].startswith("FIFO"), str(SEEN[-1]["messages"])[:160])
    await c.post("/v1/chat/completions", json=dict(model="ostutor-tutor", messages=history))
    check("tutoring keeps the conversation", len(SEEN[-1]["messages"]) == 4)

    # --- follow-ups (24 Oct): post-stream fact check, contextual retrieval ---
    out, _ = await text_of_stream(c, "ostutor-explain", "lru")
    check("a streamed answer with a misconception gets the correct fact after it",
          "Fact check" in out and "never suffers" in out, out[-200:])
    out, _ = await text_of_stream(c, "ostutor-tutor", "lru")
    check("tutor answers are not fact-checked, streamed or not", "Fact check" not in out, out[-120:])
    out, _ = await text_of_stream(c, "ostutor-explain", "normal")
    check("a clean streamed answer gets no fact-check note", "Fact check" not in out, out[-120:])
    await c.post("/v1/chat/completions", json=dict(model="ostutor-explain", messages=[
        dict(role="user", content="hi"),
        dict(role="assistant", content="ok\n\n---\n> **Fact check:** part of the answer above\n> fact"),
        dict(role="user", content="hi")]))
    check("the fact-check note is scrubbed from history like the other footers",
          [m["content"] for m in SEEN[-1]["messages"] if m["role"] == "assistant"] == ["ok"])

    gateway.RAG = Retriever(gateway.ROOT / "data" / "rag" / "fixture")
    try:
        q0 = "Can LRU suffer from Belady's anomaly?"
        await c.post("/v1/chat/completions", json=dict(model="ostutor-explain", messages=[
            dict(role="user", content=q0), dict(role="assistant", content="No."),
            dict(role="user", content="Why does it not?")]))
        sent = SEEN[-1]["messages"][0]["content"]
        check("a short follow-up is retrieved with the question before it", "[S1]" in sent, sent[:120])
        check("and the model still sees the student's own words",
              SEEN[-1]["messages"][-1]["content"] == "Why does it not?")
    finally:
        gateway.RAG = None

    print("\nALL GATEWAY TESTS PASSED" if not FAILED else f"\n{len(FAILED)} FAILED: {FAILED}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
