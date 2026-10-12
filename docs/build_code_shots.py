"""Render the code and terminal screenshots used in docs/os-tutor-rag-report.html.

    python docs/build_code_shots.py            (writes docs/shots/*.png)

Every code image is cut from the repository file at the line range named below, so a
screenshot can never drift from the code it claims to show; line numbers are the real
ones. Every terminal image is the captured output of the command it names, run now
(CPU only; the end-to-end run is read from its saved summary, not re-run).
"""
import html
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer

DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parent
OUT = DOCS / "shots"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
WIDTH = 980
LINE = 19

# name -> (file, first line, last line)
CODE = {
    "build_stages": ("ostutor/build.py", 145, 171),
    "decontaminate": ("ostutor/dedup.py", 178, 192),
    "lora": ("train/kaggle_train.py", 138, 144),
    "sftconfig": ("train/kaggle_train.py", 172, 199),
    "grounding": ("ostutor/solver.py", 351, 364),
    "corpus": ("ostutor/rag/corpus.py", 70, 91),
    "retrieve": ("ostutor/rag/retrieve.py", 88, 114),
    "augment": ("ostutor/rag/retrieve.py", 121, 134),
    "gateway_layers": ("serve/gateway.py", 383, 400),
    "mcnemar": ("ostutor/evaluation/stats.py", 15, 30),
}

FRAME = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;background:#1e2127}}
.win{{width:{w}px;background:#282c34;font-family:Consolas,'Cascadia Mono',monospace}}
.bar{{height:34px;background:#21252b;display:flex;align-items:center;padding:0 12px;gap:7px;
      border-bottom:1px solid #181a1f}}
.dot{{width:11px;height:11px;border-radius:50%}}
.tab{{margin-left:14px;color:#d7dae0;font:12.5px 'Segoe UI',sans-serif;background:#282c34;
      padding:7px 14px;border-radius:5px 5px 0 0;margin-top:6px}}
.tab b{{color:#e5c07b;font-weight:600;margin-right:6px}}
.body{{display:flex;padding:12px 0 14px}}
.gut{{color:#4b5263;text-align:right;padding:0 14px 0 16px;user-select:none}}
.gut div,.src div{{height:{lh}px;line-height:{lh}px;font-size:13.4px;white-space:pre}}
.src{{color:#abb2bf;flex:1;overflow:hidden}}
.term{{color:#cfd3da;padding:12px 18px 16px}}
.term div{{height:{lh}px;line-height:{lh}px;font-size:13.4px;white-space:pre}}
.ps{{color:#61afef}} .ok{{color:#98c379}} .bad{{color:#e06c75}} .hd{{color:#e5c07b}}
{css}
</style></head><body><div class="win"><div class="bar">
<span class="dot" style="background:#ff5f57"></span><span class="dot" style="background:#febc2e"></span>
<span class="dot" style="background:#28c840"></span><span class="tab">{tab}</span></div>{content}</div>
</body></html>"""


def shoot(page: str, png: Path, lines: int, chrome: int = 34 + 26) -> None:
    tmp = OUT / f"_{png.stem}.html"
    tmp.write_text(page, encoding="utf-8")
    if png.exists():
        png.unlink()
    h = chrome + lines * LINE + 4
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=2", f"--window-size={WIDTH},{h}",
                    f"--screenshot={png}", tmp.as_uri()], capture_output=True)
    for _ in range(60):
        if png.exists() and png.stat().st_size > 0:
            break
        time.sleep(0.5)
    tmp.unlink(missing_ok=True)
    if not png.exists():
        sys.exit(f"screenshot failed: {png}")


def code_shot(name: str, path: str, a: int, b: int) -> None:
    src = (ROOT / path).read_text(encoding="utf-8").splitlines()[a - 1:b]
    fmt = HtmlFormatter(style="one-dark", nowrap=True)
    body = highlight("\n".join(src) + "\n", PythonLexer(), fmt).rstrip("\n").split("\n")
    gut = "".join(f"<div>{n}</div>" for n in range(a, b + 1))
    srcs = "".join(f"<div>{l or ' '}</div>" for l in body)
    css = fmt.get_style_defs(".src")
    page = FRAME.format(w=WIDTH, lh=LINE, css=css, tab=f"<b>py</b>{html.escape(path)}  ·  lines {a}–{b}",
                        content=f'<div class="body"><div class="gut">{gut}</div>'
                                f'<div class="src">{srcs}</div></div>')
    shoot(page, OUT / f"code_{name}.png", len(src))


def colour(line: str) -> str:
    e = html.escape(line) or " "
    if "PASS" in line or "ALL " in line and "PASSED" in line:
        return f'<div class="ok">{e}</div>'
    if "FAIL" in line:
        return f'<div class="bad">{e}</div>'
    if line.startswith(("#", "Configuration", "Items", "----")):
        return f'<div class="hd">{e}</div>'
    return f"<div>{e}</div>"


def term_shot(name: str, command: str, lines: list[str]) -> None:
    rows = [f'<div><span class="ps">PS D:\\os project&gt;</span> {html.escape(command)}</div>']
    rows += [colour(l) for l in lines]
    page = FRAME.format(w=WIDTH, lh=LINE, css="", tab="<b>&gt;_</b>PowerShell",
                        content=f'<div class="term">{"".join(rows)}</div>')
    shoot(page, OUT / f"term_{name}.png", len(rows))


NOISE = ("Loading weights", "LOAD REPORT", "Key ", "-----", "position_ids", "Notes:",
         "UNEXPECTED", "solver path failed", "fact-check retry failed", '{"t":')


def run(cmd: list[str], py: str = sys.executable) -> list[str]:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([py, *cmd], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                       env=env)
    return [l for l in (p.stdout + p.stderr).splitlines()
            if l.strip() and not any(n in l for n in NOISE)]


def wrap(lines: list[str], width: int = 124) -> list[str]:
    out = []
    for l in lines:
        while len(l) > width:
            out.append(l[:width])
            l = "    " + l[width:]
        out.append(l)
    return out


def tables(md: list[str]) -> list[str]:
    """Markdown as a terminal would show it: tables aligned in columns, marks removed."""
    out, block = [], []

    def flush():
        if block:
            cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in block
                     if not set(r.replace("|", "").strip()) <= set("-: ")]
            w = [max(len(r[i]) for r in cells) for i in range(len(cells[0]))]
            for n, r in enumerate(cells):
                out.append("  ".join(c.ljust(w[i]) for i, c in enumerate(r)).rstrip())
                if n == 0:
                    out.append("  ".join("-" * x for x in w))
            block.clear()
    for l in md:
        l = l.replace("`", "").replace("**", "")
        if l.startswith("|"):
            block.append(l)
            continue
        flush()
        if l.strip():
            out.append(l)
    flush()
    return out


def loss_curve() -> None:
    """docs/shots/loss_curve.svg from the v3 run's own training log."""
    log = json.loads((ROOT / "outputs/ostutor-lora-v3/ostutor-lora/train_metrics.json")
                     .read_text(encoding="utf-8"))["log"]
    series = {"training loss (per 10 steps)": [(x["step"], x["loss"]) for x in log if "loss" in x],
              "validation loss": [(x["step"], x["eval_val_loss"]) for x in log if "eval_val_loss" in x],
              "OOD loss": [(x["step"], x["eval_ood_loss"]) for x in log if "eval_ood_loss" in x]}
    colours = ["#9aa3b2", "#2b4c7e", "#1d6b3a"]
    W, H, L, R, T, B = 640, 250, 46, 14, 14, 34
    xmax, ymax = 740, 1.1
    X = lambda s: L + (W - L - R) * s / xmax                       # noqa: E731
    Y = lambda v: T + (H - T - B) * (1 - v / ymax)                  # noqa: E731
    g = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial" '
         'font-size="10">']
    for v in (0, 0.2, 0.4, 0.6, 0.8, 1.0):
        g.append(f'<line x1="{L}" x2="{W - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#e3e5e9"/>'
                 f'<text x="{L - 6}" y="{Y(v) + 3:.1f}" text-anchor="end" fill="#5d636e">{v:.1f}</text>')
    for s in range(0, 741, 100):
        g.append(f'<text x="{X(s):.1f}" y="{H - B + 14}" text-anchor="middle" fill="#5d636e">{s}</text>')
    g.append(f'<text x="{(L + W - R) / 2}" y="{H - 4}" text-anchor="middle" fill="#5d636e">optimiser step '
             '(735 = one epoch)</text>')
    for (name, pts), col in zip(series.items(), colours):
        path = " ".join(f"{'M' if i == 0 else 'L'}{X(s):.1f},{Y(v):.1f}" for i, (s, v) in enumerate(pts))
        g.append(f'<path d="{path}" fill="none" stroke="{col}" stroke-width="{1.2 if 'training' in name else 2}"/>')
        if "training" not in name:
            g += [f'<circle cx="{X(s):.1f}" cy="{Y(v):.1f}" r="2.4" fill="{col}"/>' for s, v in pts]
    for k, ((name, _), col) in enumerate(zip(series.items(), colours)):
        x = W - R - 190
        g.append(f'<rect x="{x}" y="{T + 6 + 15 * k}" width="12" height="3" fill="{col}"/>'
                 f'<text x="{x + 18}" y="{T + 10 + 15 * k}" fill="#16181d">{name}</text>')
    g.append("</svg>")
    (OUT / "loss_curve.svg").write_text("".join(g), encoding="utf-8")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    loss_curve()
    for name, (path, a, b) in CODE.items():
        code_shot(name, path, a, b)
        print("  code", name)

    term_shot("test_rag", "python tools/test_rag.py", run(["tools/test_rag.py"]))
    gw = run(["serve/test_gateway.py"], py=str(ROOT / "serve/.venv-webui/Scripts/python.exe"))
    term_shot("test_gateway", "serve/.venv-webui/Scripts/python serve/test_gateway.py",
              ["  ..."] + gw[-9:])
    # Saved reports are shown, not re-run: re-running would overwrite the committed
    # numbers the document cites with a fresh (and, for latency, different) sample.
    ev = ROOT / "reports/rag/fixture_eval.md"
    term_shot("rag_eval", "Get-Content reports/rag/fixture_eval.md",
              wrap(tables(ev.read_text(encoding="utf-8").split("## Misses")[0].splitlines())))
    e2e = sorted((ROOT / "reports/rag").glob("e2e-*/summary.md"))
    if e2e:
        rel = str(e2e[-1].relative_to(ROOT)).replace("\\", "/")
        term_shot("rag_e2e", f"Get-Content {rel}",
                  wrap(tables(e2e[-1].read_text(encoding="utf-8").splitlines())))
    print(f"wrote {len(list(OUT.glob('*.png')))} images to {OUT}")


if __name__ == "__main__":
    main()
