"""Charts for the final report. Every value is read from, or copied verbatim from, a result
file; the file is named above each chart.

    python docs/final_report/charts.py
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "fig"
OUT.mkdir(exist_ok=True)

# Categorical order checked with the dataviz validator (light surface, CVD-safe adjacents).
BLUE, ORANGE, AQUA, GOLD = "#1f5fae", "#d9692b", "#1a9e77", "#b8901c"
LIGHT = "#8fb3e0"           # the same hue, lighter: "related, not the headline"
CONTEXT = "#cdd6e4"         # bars that give context rather than tell the story
INK, INK2, GRID = "#1b1b1b", "#4a4a4a", "#e2e2de"
FS = 1.45                   # text scale, so chart labels match the 13 pt body text in print

plt.rcParams.update({
    "font.family": "Times New Roman", "font.size": 10.5 * FS, "axes.edgecolor": GRID,
    "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False,
    "figure.dpi": 100, "savefig.dpi": 300, "legend.frameon": False,
})


def finish(fig, name):
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight", facecolor="white", pad_inches=0.06)
    plt.close(fig)


def xgrid(ax):
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def ygrid(ax):
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def hbar_clean(ax):
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)


# 1. Ablation, 57-item problem suite (reports/g0/20261012-1429/regraded.md)
cfg = ["Base (untuned)", "v2.2 adapter", "v3 adapter", "v2.2 + solver", "Base + solver",
       "v3 + solver (deployed)"]
val = [30, 19, 34, 43, 49, 57]
fig, ax = plt.subplots(figsize=(6.6, 2.7))
y = list(range(len(cfg)))[::-1]
ax.barh(y, val, height=0.56, color=[CONTEXT] * 3 + [LIGHT] * 2 + [BLUE], linewidth=0)
for yi, v in zip(y, val):
    ax.text(v + 0.8, yi, f"{v}/57  ({v / 57:.1%})", va="center", color=INK, fontsize=10 * FS)
ax.set_yticks(y, cfg)
ax.set_xlim(0, 70)
ax.set_xlabel("Problems solved exactly (simulator-graded, greedy decoding)")
xgrid(ax)
hbar_clean(ax)
finish(fig, "ablation")

# 2. Training loss (outputs/ostutor-lora-v3/ostutor-lora/train_metrics.json)
m = json.loads((ROOT / "outputs/ostutor-lora-v3/ostutor-lora/train_metrics.json").read_text())
tr = [(r["step"], r["loss"]) for r in m["log"] if "loss" in r]
va = [(r["step"], r["eval_val_loss"]) for r in m["log"] if "eval_val_loss" in r]
fig, ax = plt.subplots(figsize=(6.6, 2.5))
ax.plot(*zip(*tr), color=CONTEXT, lw=1.6, label="Training loss (logged every 10 steps)")
ax.plot(*zip(*va), color=BLUE, lw=2, marker="o", ms=4.5, mec="white", mew=1.2,
        label="Validation loss (240 rows)")
ax.annotate(f"{va[-1][1]:.4f}", va[-1], xytext=(4, 7), textcoords="offset points", color=INK,
            fontsize=9.5 * FS)
ax.annotate(f"{va[0][1]:.4f}", va[0], xytext=(6, 6), textcoords="offset points", color=INK,
            fontsize=9.5 * FS)
ax.set_xlabel("Optimiser step (735 = one epoch)")
ax.set_ylabel("Loss")
ax.set_ylim(0, 1.15)
ygrid(ax)
ax.legend(loc="upper right", fontsize=9.5 * FS)
finish(fig, "loss")

# 3. Catastrophic forgetting (reports/forgetting_v3_paired.json; p from
#    reports/g0/historical_significance.md)
bench = ["General MMLU (400)", "Adjacent CS (300)", "OS theory MCQ (70)"]
base = [80.25, 64.67, 90.00]
v3 = [79.50, 67.33, 85.71]
pv = ["p = 0.678", "p = 0.201", "p = 0.375"]
fig, ax = plt.subplots(figsize=(6.6, 2.3))
for i, (b, v) in enumerate(zip(base, v3)):
    yy = 2 - i
    ax.plot([b, v], [yy, yy], color=GRID, lw=3, solid_capstyle="round", zorder=1)
    ax.scatter([b], [yy], s=70, color=CONTEXT, edgecolor="white", linewidth=1.5, zorder=3)
    ax.scatter([v], [yy], s=70, color=BLUE, edgecolor="white", linewidth=1.5, zorder=3)
    ax.text(max(b, v) + 1.2, yy, f"{b:.2f}% → {v:.2f}%   ({pv[i]})", va="center", fontsize=9.5 * FS,
            color=INK)
ax.scatter([], [], s=60, color=CONTEXT, label="Base model")
ax.scatter([], [], s=60, color=BLUE, label="Fine-tuned v3")
ax.set_yticks([2, 1, 0], bench)
ax.set_xlim(60, 114)
ax.set_xticks([60, 70, 80, 90, 100])
ax.set_xlabel("Accuracy (%), log-likelihood scoring, same items for both models")
ax.set_ylim(-0.6, 2.6)
xgrid(ax)
hbar_clean(ax)
ax.legend(loc="lower center", ncol=2, fontsize=9.5 * FS, bbox_to_anchor=(0.45, 1.0))
finish(fig, "forgetting")

# 4. Short answers: retrieval off / course corpus / open corpus, test half
#    (reports/rag/e2e-20261013-1339/summary.md, reports/rag/e2e-short-course/summary.md)
groups = ["Base model", "Fine-tuned v3"]
off, course, open_ = [48, 49], [59, 59], [62, 62]
fig, ax = plt.subplots(figsize=(6.6, 2.7))
w = 0.22
for k, (vals, c, lab) in enumerate([(off, CONTEXT, "No retrieval"), (course, ORANGE, "+ course corpus"),
                                    (open_, BLUE, "+ open corpus")]):
    xs = [i + (k - 1) * (w + 0.03) for i in range(2)]
    ax.bar(xs, vals, width=w, color=c, linewidth=0, label=lab)
    for x, v in zip(xs, vals):
        ax.text(x, v + 1, f"{v}/72\n{v / 72:.1%}", ha="center", va="bottom", fontsize=9 * FS, color=INK)
ax.set_xticks([0, 1], groups)
ax.set_ylim(0, 88)
ax.set_ylabel("Correct (of 72)")
ygrid(ax)
ax.legend(loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.14), fontsize=9.5 * FS)
finish(fig, "short_answers")

# 5. Answer recall by corpus (reports/rag/compare_test.md)
rows = [("Course corpus", 73.6, 76.4), ("Open pool, unfiltered", 81.9, 94.4),
        ("Open corpus, compiled (served)", 83.3, 94.4), ("Open, without Wikipedia", 65.3, 79.2),
        ("Open, without Stack Exchange", 84.7, 93.1), ("Open, without Hailperin", 81.9, 93.1)]
fig, ax = plt.subplots(figsize=(6.6, 3.0))
y = list(range(len(rows)))[::-1]
h = 0.34
for yi, (n, r5, r10) in zip(y, rows):
    served = "served" in n
    ax.barh(yi + h / 2 + 0.02, r5, height=h, color=BLUE if served else LIGHT, linewidth=0)
    ax.barh(yi - h / 2 - 0.02, r10, height=h, color=ORANGE if served else "#f0b896", linewidth=0)
    ax.text(r5 + 0.8, yi + h / 2 + 0.02, f"{r5:.1f}%", va="center", fontsize=8.8 * 1.1, color=INK)
    ax.text(r10 + 0.8, yi - h / 2 - 0.02, f"{r10:.1f}%", va="center", fontsize=8.8 * 1.1, color=INK)
ax.set_yticks(y, [r[0] for r in rows])
ax.set_xlim(0, 108)
ax.set_xlabel("Answer recall (%), test half, n = 72")
xgrid(ax)
hbar_clean(ax)
ax.legend(handles=[Patch(color=BLUE, label="Recall@5"), Patch(color=ORANGE, label="Recall@10")],
          loc="lower center", ncol=2, fontsize=9.5 * FS, bbox_to_anchor=(0.35, 1.0))
finish(fig, "corpus_recall")

# 6. Re-ranker experiment (experiment logs e2e_rerank_test.log and rerank_test_notes.log,
#    23 Oct 2026; test half, n = 72)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.6, 2.5), gridspec_kw=dict(width_ratios=[1.6, 1]))
xs = [0, 1]
served, rr = [52.8, 81.9], [72.2, 87.5]
a1.bar([x - 0.17 for x in xs], served, width=0.32, color=CONTEXT, linewidth=0, label="Served (hybrid RRF)")
a1.bar([x + 0.17 for x in xs], rr, width=0.32, color=BLUE, linewidth=0, label="+ cross-encoder re-ranker")
for x, s, r in zip(xs, served, rr):
    a1.text(x - 0.17, s + 1.5, f"{s:.1f}%", ha="center", fontsize=9 * FS, color=INK)
    a1.text(x + 0.17, r + 1.5, f"{r:.1f}%", ha="center", fontsize=9 * FS, color=INK)
a1.set_xticks(xs, ["Recall@1", "Recall@4"])
a1.set_ylim(0, 100)
a1.set_title("Answer recall (%)", fontsize=10.5 * FS, color=INK)
ygrid(a1)
a2.bar([0, 1], [62, 61], width=0.5, color=[CONTEXT, BLUE], linewidth=0)
for x, v in zip([0, 1], [62, 61]):
    a2.text(x, v + 1.5, f"{v}/72", ha="center", fontsize=9 * FS, color=INK)
a2.set_xticks([0, 1], ["Served", "Re-ranked"])
a2.set_ylim(0, 80)
a2.set_title("Answers correct (p = 1.0)", fontsize=10.5 * FS, color=INK)
ygrid(a2)
fig.tight_layout(w_pad=2.5, rect=(0, 0.1, 1, 1))
fig.legend(*a1.get_legend_handles_labels(), loc="lower center", ncol=2, fontsize=8.5 * FS,
           bbox_to_anchor=(0.5, -0.02))
finish(fig, "reranker")

# 7. Why the 21 wrong short answers were wrong (v3 + open corpus, all 144; diagnosis of
#    reports/rag/e2e-20261013-1339)
cats = ["Passages misled a model that\nknew the answer without them",
        "Search missed the passage\n(the answer is in the corpus)",
        "Answer was in the passages,\nmodel chose a near miss", "Answer absent from\nthe corpus"]
n = [7, 7, 5, 2]
fig, ax = plt.subplots(figsize=(6.6, 2.3))
y = list(range(len(cats)))[::-1]
ax.barh(y, n, height=0.55, color=[BLUE, BLUE, LIGHT, CONTEXT], linewidth=0)
for yi, v in zip(y, n):
    ax.text(v + 0.15, yi, str(v), va="center", fontsize=10 * FS, color=INK)
ax.set_yticks(y, cats, fontsize=9.5 * FS)
ax.set_xlim(0, 9)
ax.set_xlabel("Wrong short answers, v3 + open corpus (21 of 144)")
xgrid(ax)
hbar_clean(ax)
finish(fig, "errors")

# 8. Dataset composition (DATASET_CARD.md)
cat = ["Procedural", "Replay", "Tutoring", "Shell", "Conceptual"]
rows_ = [7526, 1884, 938, 707, 705]
fig, ax = plt.subplots(figsize=(6.6, 1.9))
y = list(range(len(cat)))[::-1]
ax.barh(y, rows_, height=0.58, color=[BLUE, LIGHT, ORANGE, AQUA, GOLD], linewidth=0)
for yi, r in zip(y, rows_):
    ax.text(r + 90, yi, f"{r:,}  ({r / sum(rows_):.0%})", va="center", fontsize=9.5 * FS, color=INK)
ax.set_yticks(y, cat)
ax.set_xlim(0, 9000)
ax.set_xticks([0, 2000, 4000, 6000, 8000], ["0", "2K", "4K", "6K", "8K"])
ax.set_xlabel("Training rows (11,760 in total)")
xgrid(ax)
hbar_clean(ax)
finish(fig, "dataset_mix")

# 9. Pipeline funnel (DATASET_CARD.md, reports/manifest.json)
st = ["Ingest", "Clean", "Dedup", "Decontam.", "Select", "Train"]
rv = [80732, 70170, 68381, 67738, 12000, 11760]
fig, ax = plt.subplots(figsize=(6.6, 2.2))
ax.bar(range(len(st)), rv, width=0.55, color=[CONTEXT] * 4 + [LIGHT, BLUE], linewidth=0)
for i, v in enumerate(rv):
    ax.text(i, v + 1500, f"{v:,}", ha="center", fontsize=9.2 * FS, color=INK)
ax.set_xticks(range(len(st)), st)
ax.set_ylim(0, 92000)
ax.set_yticks([0, 20000, 40000, 60000, 80000], ["0", "20K", "40K", "60K", "80K"])
ax.set_ylabel("Rows")
ygrid(ax)
finish(fig, "funnel")

# 10. OOD holdout by kind (reports/g0/20261012-1429/ood.json; the 80 disk items re-run with
#     the range fix, reports/final_review/disk.json)
_disk = json.loads((ROOT / "reports/final_review/disk.json").read_text(encoding="utf-8"))
kinds = ["Banker's request", "Banker's safety", "Free-space allocation", "Page replacement",
         "Address translation", "Disk scheduling", "CPU scheduling"]
corr = [100.0, 100.0, 100.0, 100.0, 100.0, round(100 * _disk["after_correct"] / _disk["n"], 1), 98.9]
nn = [91, 96, 74, 86, 82, 80, 91]
fig, ax = plt.subplots(figsize=(6.6, 2.5))
y = list(range(len(kinds)))[::-1]
ax.barh(y, corr, height=0.55, color=[BLUE] * 6 + [LIGHT], linewidth=0)
for yi, v, k in zip(y, corr, nn):
    ax.text(v + 0.3, yi, f"{v:.1f}%  (n = {k})", va="center", fontsize=9.3 * FS, color=INK)
ax.set_yticks(y, kinds)
ax.set_xlim(80, 107)
ax.set_xlabel("Correct, end to end (v3 + solver); overall 99.8% of 600")
xgrid(ax)
hbar_clean(ax)
finish(fig, "ood")

# 11. Theory MCQ, 200 items, generated letter (reports/rag/e2e-20261012-2239/summary.md)
mc = [("Base, no retrieval", 185), ("Base + course corpus", 186), ("v3, no retrieval", 186),
      ("v3 + course corpus", 184)]
fig, ax = plt.subplots(figsize=(6.6, 1.9))
y = list(range(len(mc)))[::-1]
ax.barh(y, [v for _, v in mc], height=0.55, color=[CONTEXT, LIGHT, CONTEXT, BLUE], linewidth=0)
for yi, (_, v) in zip(y, mc):
    ax.text(v + 1.5, yi, f"{v}/200  ({v / 2:.1f}%)", va="center", fontsize=9.5 * FS, color=INK)
ax.set_yticks(y, [k for k, _ in mc])
ax.set_xlim(0, 225)
ax.set_xlabel("Correct of 200 theory MCQs; every pairwise difference p ≥ 0.75")
xgrid(ax)
hbar_clean(ax)
finish(fig, "mcq")

print("charts:", sorted(p.name for p in OUT.glob("*.png")))
