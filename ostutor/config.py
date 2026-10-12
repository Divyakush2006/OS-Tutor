"""OSTutorLLM data pipeline v2 - versioned configuration.

Everything that affects the output lives here. The build hashes this file into
the manifest so a dataset can be attributed to an exact configuration.

v2 changes, each grounded in a measurement or a paper:

  RATIO ENFORCEMENT. v1 treated MIX as ceilings. When a category came up short
  the others kept their full quota and their SHARE ballooned - measured drift was
  replay 31% against a 12% target and OS content 29% against 70%. v2 treats MIX
  as proportions and scales TARGET_TOTAL down to whatever the binding category
  can actually supply, so the realised mixture always matches the designed one.

  SPACED REPLAY (Ebbinghaus). FOREVER (arXiv 2601.03938) shows LLM forgetting
  mirrors the Ebbinghaus curve and that replay should be DENSE immediately after
  new material and progressively sparser. v1 used a uniform stride. v2 decays the
  replay interval across the epoch.

  SURPRISE-DRIVEN REPLAY SELECTION (SuRe, arXiv 2511.22367). Replay examples are
  chosen by per-token NLL under the base model rather than by a hand-written
  quality heuristic: high-NLL sequences carry large gradients, so the buffer
  approximates the gradient geometry of the original distribution instead of its
  surface frequency.

  OVERFITTING GUARDS. Diversity floors, answer-duplication limits and a genuine
  out-of-distribution holdout that the generators never produced.

v3.0 - the final build, driven by testing v2.2 through a chat UI (4/14 on free-
worded textbook questions, explanations worse than the untuned base):

  SKILL VOLUME. Procedures are skills, and v2.2 gave each of 21 algorithms ~30
  examples (heavy "gold" selection is right for knowledge, wrong for skills). The
  families are now weighted and filled from a 17k verified pool: hundreds per
  algorithm, plus 11 new formula kinds and missing-input clarification.
  EXPLICIT DECISIONS, STUDENT WORDING, SELF-DISTILLED THEORY - see
  simulators/scheduling.py, simulators/student.py and tools/generate_theory_sdft.py.
  LONG CONTEXT. Training length 16,384 tokens (two T4s); xl problems teach traces
  far longer than any exam needs.
"""
from pathlib import Path

PIPELINE_VERSION = "3.0.0"
DATASET_NAME = "ostutor-sft"
SEED = 42

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
BUILD = ROOT / "data" / "build"
ANALYSIS = ROOT / "reports" / "analysis"
REPORTS = ROOT / "reports"
MODEL = ROOT / "models" / "Qwen3-4B-Instruct-2507"

# ---------------------------------------------------------------- mixture
# Proportions, NOT ceilings. The build scales the total to the binding category.
MIX = {
    "procedural": 0.64,   # simulator-verified OS numericals, formulas, clarification
    "conceptual": 0.06,   # self-distilled + hand-written, fact-checked theory
    "tutoring":   0.08,   # Socratic behaviour (MathDial human + self-distilled OS tutoring)
    "shell":      0.06,   # NL -> bash, execution-relevant
    "replay":     0.16,   # anti-forgetting anchor set (SuRe-ranked, spaced)
}
TARGET_TOTAL = 12_000          # aspirational ceiling; actual total is ratio-bound
MIN_TOTAL = 2_000              # below this the build fails rather than ship a toy
MAX_DRIFT_PP = 2.0             # realised share may deviate at most this many points

# ---------------------------------------------------------------- quality
QUALITY_FLOOR_PCT = 0.40       # discard the weakest 40% of each category
# The floor exists to strip NOISE from scraped data. Hand-authored conceptual
# content and simulator-verified procedural rows have no noise to strip; a 40%
# floor there only discards verified material on heuristic score variance.
QUALITY_FLOOR_BY_CAT = {"procedural": 0.0, "conceptual": 0.05}
# v3.0: every procedural row is simulator-verified; a heuristic quality floor there
# only discarded the SHORT kinds (clarification, formulas) the model must learn.
SUBCAT_CAP = 0.35              # no single source may exceed this share of a category
MIN_CHARS_USER, MIN_CHARS_ASSISTANT = 8, 12
# MAX_TOKENS_TARGET must equal the trainer's max_length (train/kaggle_train.py).
# A longer row is TRUNCATED during training, which cuts off exactly the final
# answer the row exists to teach. v2.1's fully worked solutions made this bite.
TRAIN_MAX_LENGTH = 16_384  # v3.0: two T4s; xl traces reach ~10k tokens (reports/TOKEN_BUDGET.md)
MAX_CHARS_TOTAL, MAX_TOKENS_TARGET = 24_000, TRAIN_MAX_LENGTH

# ---------------------------------------------------------------- dedup
MINHASH_PERM, MINHASH_THRESHOLD, SHINGLE_N, MAX_SHINGLES = 128, 0.80, 5, 256
SEMANTIC_DUP_COSINE = 0.93
# Per-category override, used only for rows WITHOUT a parameter fingerprint.
SEMANTIC_DUP_COSINE_BY_CAT = {"procedural": 0.985}
# SIMULATOR-GENERATED rows are deduplicated by PARAMETER FINGERPRINT, not by
# embedding. MiniLM is nearly blind to numbers and reads only 256 tokens: two
# page-replacement problems with different reference strings score a median cosine
# of 0.994, so even a 0.985 threshold discarded two thirds of them as "duplicates"
# while CPU-scheduling rows (median 0.95) survived - a silent topic skew (page
# replacement 44 of 1,154 selected rows). Same fingerprint == same problem;
# different fingerprint == different problem, however similar the prose.
FINGERPRINT_DEDUP_CATS = ("procedural",)
# Categories selected by STRATIFIED farthest-point: equal quota per procedure family,
# then per variant within the family, with farthest-point inside each cell. Global
# farthest-point over a number-blind embedding favours whichever topic has the most
# varied PROSE, which is not the same as the most varied PROCEDURE.
STRATIFIED_CATS = ("procedural",)
PROCEDURE_FAMILIES = ("address_translation", "contiguous_allocation", "cpu_scheduling",
                      "deadlock_bankers", "disk_scheduling", "page_replacement",
                      "formula", "clarify")
# v3.0: families are filled by WEIGHT, not equally. Equal shares gave address
# translation (one simple procedure) the same budget as CPU scheduling (seven
# algorithms with arrivals and preemption). Weights follow procedural complexity
# and exam frequency; each family's budget is then split equally across its
# variants (algorithms), so every algorithm gets hundreds of examples.
# Tutoring is split by DOMAIN, for the same reason procedural is split by family:
# farthest-point selection rewards spread, and the self-distilled OS rows are
# mutually similar (nine misconception templates over three problem kinds), so they
# lose every comparison to MathDial's human variety. Unweighted, selection took 912
# MathDial rows and 26 OS rows - an Operating Systems tutor that had practically
# never seen OS tutoring. MathDial keeps a substantial share because its teacher
# moves are real human behaviour; the majority goes to OS because that is the
# domain, and the problems are the ones the model will actually be asked about.
TUTORING_WEIGHTS = {"os": 0.60, "math": 0.40}

FAMILY_WEIGHTS = {"cpu_scheduling": 0.23, "page_replacement": 0.13,
                  "deadlock_bankers": 0.14, "disk_scheduling": 0.13,
                  "contiguous_allocation": 0.07, "address_translation": 0.05,
                  "formula": 0.20, "clarify": 0.05}
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
NGRAM_N = 13                   # decontamination n-gram size (state it in the paper)
# An eval n-gram found in MORE than this many training rows is template
# boilerplate, not a leak. A naive any-overlap rule removed 58% of procedural data.
BOILERPLATE_DF = 5

# ------------------------------------------------- anti-forgetting (rectifier)
MAX_RUN_SAME_CAT = 4           # never more than N consecutive rows of one category
MAX_RUN_SAME_SOURCE = 3        # ... nor of one underlying dataset
# Ebbinghaus-style spacing: replay interval grows from EARLY to LATE across the
# epoch. FOREVER's model-time formulation is training-side; this is the data-side
# projection of the same principle.
REPLAY_GAP_EARLY = 4           # dense right after new material is introduced
REPLAY_GAP_LATE = 14           # sparser once the adapter has stabilised
SPACED_REPLAY = True
# SuRe: rank replay by base-model NLL inside a farthest-point diverse pool of
# SURPRISE_POOL_MULT x quota. Surprise never overrides the quality gate.
SURPRISE_REPLAY = True
SURPRISE_POOL_MULT = 3

# ---------------------------------------------------------------- overfitting
MIN_DISTINCT_ANSWER_RATIO = 0.90   # distinct assistant texts / rows, per category
MAX_TEMPLATE_SHARE = 0.25          # no single solution skeleton may exceed this
OOD_FRACTION = 0.0                 # v3.0: OOD = the held-out holdout file only (see render.split)
VAL_FRACTION = 0.05
VAL_MAX_ROWS = 240                 # eval passes at 16k context are costly; cap the split
MIN_PAIRWISE_DIVERSITY = 0.30      # 1 - mean cosine within a category

# ------------------------------------------------- production release gates
GATES = dict(
    max_defect_rate=0.000,
    max_nonlatin_rate=0.000,
    max_secret_hits=0,
    max_think_blocks=0,
    require_all_commercial=True,
    min_rows_per_category=50,
    max_token_p99=TRAIN_MAX_LENGTH,
    max_mixture_drift_pp=MAX_DRIFT_PP,
    max_run_same_source=MAX_RUN_SAME_SOURCE,
    min_distinct_answer_ratio=MIN_DISTINCT_ANSWER_RATIO,
    min_pairwise_diversity=MIN_PAIRWISE_DIVERSITY,
    min_total_rows=MIN_TOTAL,
    require_ood_holdout=True,
    max_template_share=MAX_TEMPLATE_SHARE,
    # An OS tutor must have seen OS tutoring. Set well below the designed share
    # (0.60 of the tutoring category) so the gate catches a category being emptied
    # by an upstream filter, not a few rows lost to ordinary selection.
    min_os_tutoring_rows=300,
)

SYSTEM_PROMPTS = {
    # The last sentence is the fix for a measured failure. Without it the prompt is an
    # unconditional order to produce a final answer, and the 295 clarification rows -
    # which teach the model to ASK when an input is missing - were contradicted by the
    # instruction they were rendered under AND outnumbered 24:1 by procedural rows that
    # always solve. Measured on the three hand-written clarification items: 0/3 with the
    # instruction as it was, 2/3 with the exception stated. The gateway reads prompts
    # from here, so serving and training cannot drift apart.
    ("solve", "os"): "You are an Operating Systems tutor. Solve the problem with numbered, auditable steps. Show every intermediate state. State the final answer last. If the question does not state an input the answer depends on, do not assume a value: say which input is missing and ask for it instead.",
    ("explain", "os"): "You are an Operating Systems tutor. Explain the concept clearly and precisely, using a concrete example.",
    # v3.0: "...until they have attempted it" was self-defeating. Every OS tutoring
    # example IS a student who has already attempted the problem, so the clause
    # licensed the tutor to hand over the answer - and the base model duly did, in
    # 24% of self-distilled replies, which the filter then had to discard. The
    # instruction now says what the behaviour actually is, and matches what
    # ostutor/theory_filter.accept_tutor() enforces. The gateway reads these prompts
    # from here, so serving and training cannot drift apart.
    ("tutor", "os"): "You are an Operating Systems tutor. Guide the student with hints and questions rather than solutions. When the student shows an attempt, diagnose the misconception behind it and ask a question that leads them to the error. Never state the correct final answer - the student must reach it.",
    ("tutor", "math"): "You are a patient tutor. Guide the student with hints and questions. Diagnose the misconception behind their answer. Do not reveal the final answer until they have attempted it.",
    # v3.0: open-ended analysis - design trade-offs, "which scheduler for this workload",
    # "why is this server thrashing". The base model is non-thinking by design, so the
    # analysis is VISIBLE and structured rather than hidden in a reasoning block: the
    # student can audit it, which is the whole point of a tutor. Assumptions come first
    # because most real questions are underspecified, and a recommendation comes last
    # because an analysis that refuses to conclude is not useful.
    ("analyze", "os"): "You are a senior Operating Systems engineer teaching a student to reason about system behaviour. Work in this order: (1) state what the question gives you and any assumption you must make; (2) identify the mechanisms involved and what each one costs; (3) weigh the trade-offs, quantifying with a concrete calculation wherever the numbers allow; (4) give a clear recommendation or conclusion, and say what evidence would change it. Be precise about what is certain and what depends on the workload. If an input the analysis depends on is missing, say which and ask for it.",
    ("shell", "linux"): "You are a Linux systems instructor. Give the correct shell command and explain each flag.",
    ("explain", "general"): "You are a helpful, knowledgeable assistant.",
}
DEFAULT_SYSTEM = "You are a helpful, knowledgeable assistant."


def system_for(mode, domain):
    """(mode, DOMAIN)-keyed. MathDial rows are maths, not OS: labelling one
    'You are an Operating Systems tutor' would teach the model that OS tutoring
    means arithmetic. Behaviour transfers; the false domain claim must not."""
    return (SYSTEM_PROMPTS.get((mode, domain))
            or SYSTEM_PROMPTS.get((mode, "os")) or DEFAULT_SYSTEM)


# ---------------------------------------------------------------- licensing
SOURCES = {
    "eth-nlped/mathdial":            dict(license="cc-by-4.0", commercial=True, attribution=True, cite="Macina et al., EMNLP Findings 2023"),
    "neulab/tldr":                   dict(license="cc-by-4.0", commercial=True, attribution=True, cite="tldr-pages (content CC BY 4.0)"),
    "TellinaTool/nl2bash:data/bash": dict(license="mit", commercial=True, attribution=True, cite="Lin et al., LREC 2018"),
    "westenfelder/NL2SH-ALFA":       dict(license="mit", commercial=True, attribution=True, cite="NL2SH-ALFA"),
    "epinnock/intercode-nl2bash":    dict(license="mit", commercial=True, attribution=True, cite="InterCode, NeurIPS 2023"),
    "allenai/tulu-3-sft-mixture":    dict(license="odc-by-1.0", commercial=True, attribution=True, cite="AI2 Tulu 3"),
    "HuggingFaceTB/smoltalk2":       dict(license="mixed-permissive", commercial=True, attribution=True, cite="SmolTalk2, _no_think splits only"),
    "simulators/own":                dict(license="mit", commercial=True, attribution=False, cite="this work"),
}
EXCLUDED = {
    "AnishJoshi/nl2bash-custom": "no declared licence; superseded by MIT TellinaTool data/bash",
    "ostep-homework":            "no declared licence; offline test oracle only, never ingested",
    "ceval/ceval-exam":          "CC BY-NC-SA: evaluation only, never training",
}
