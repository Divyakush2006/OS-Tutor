# Commit map

Run manifests under `reports/` record the commit that produced them (`"commit": "…"`). Those ids refer to the
development history as it was **before first publication**. That history was rewritten before it was published,
to normalise author identity, drop commit trailers and remove material that is not redistributed. Commit
messages and dates are unchanged. This table maps each original commit to its published id.

The four commits that run manifests cite are in **bold**.

| Date | Original id | Published id | Subject |
|---|---|---|---|
| 2026-10-12 | `f6f554ec5f` | `8ca928340c` | Baseline: OS Tutor v3.0 as of 2026-10-12 |
| 2026-10-12 | `b7521be984` | `6dbea088a2` | Fact checker: attach the correction when the redraft is unavailable |
| 2026-10-12 | `3d9f65403a` | `68c21ecdfb` | Store 57 files byte-exact, as they are on disk |
| 2026-10-12 | **`f86cd5c380`** | **`d05feeb6d7`** | G0 harness: measure what each component contributes |
| 2026-10-12 | `5bd760344f` | `52c9597fa3` | G0: grader audit flags wrong-graded answers that still contain the expected value |
| 2026-10-12 | `1b0745dfc3` | `9459d2f49c` | Grader: read an explicit final-answer marker first (D-004) |
| 2026-10-12 | `0369b1834d` | `995e091e1b` | Evaluation disables the prompt cache; add G0 diagnostics (D-005) |
| 2026-10-12 | `523be57d17` | `739edd7df2` | G0 run 20261012-1429 (prompt cache ON), as graded at f86cd5c |
| 2026-10-12 | `8fdcea4936` | `9a8d9461c5` | G2: CPU hybrid retrieval over course notes, opt-in in the gateway (D-006) |
| 2026-10-12 | **`18e5025ea5`** | **`f8c80c20c5`** | PROJECT_CONTEXT: correct the training-loss record (no 0.2710 in any artifact) |
| 2026-10-12 | `55302345f3` | `38bcff142d` | Project report with RAG integration; RAG end-to-end run; G0 regrade |
| 2026-10-12 | `ed02bd85df` | `2712c33e25` | Report: plain Word-style layout; VS Code screenshots |
| 2026-10-12 | `ed21ce86be` | `2a8d1e6413` | G2: ingest the course corpus (owners' material + CC BY-SA texts); calibrated gate |
| 2026-10-12 | **`e92fa8b055`** | **`f6a3453882`** | G2 eval: 200-item theory MCQ (130 new, unreviewed); end-to-end RAG tool for the corpus |
| 2026-10-12 | `ad5694275c` | `bff9fe33f0` | G2 measured end to end on the course corpus; owners' corpus guide |
| 2026-10-12 | `c94d5beeca` | `eb41c2305c` | PROJECT_CONTEXT: G2 results and open issues |
| 2026-10-12 | `a201db2b2d` | `ce1d2a749f` | Report: RAG sections rewritten for the course corpus; new code and terminal figures |
| 2026-10-13 | `5ce2e568d5` | `e18f80c540` | G2: open OS corpus compiled from openly licensed sources by measured filters (D-009) |
| 2026-10-13 | `c09745a55a` | `03b61858b9` | G2 open corpus: drop Wikipedia reference sections; label passages as references, not course notes |
| 2026-10-13 | **`4983451d0d`** | **`3b69d66d39`** | rag_e2e: secondary short-answer grading reported next to the pre-registered one |
| 2026-10-13 | `4e8da172c0` | `bcd98715e6` | G2 open corpus measured end to end; course vs open short-answer comparison |
| 2026-10-13 | `7d109563db` | `efacc9cb8a` | Report: open corpus dataset, pool analysis, retrieval and end-to-end results |
| 2026-10-24 | `5725714997` | `63595b091a` | Gateway owns its tags and footers; missing inputs asked for; worked problems isolated (D-010) |
| 2026-10-24 | `638891d22d` | `be22a8a8a9` | Follow-ups are retrieved with the question before them; streamed answers are fact-checked |
