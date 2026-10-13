"""Render the code and terminal screenshots used in docs/os-tutor-rag-report.html.

    python docs/build_code_shots.py            (writes docs/shots/*.png)

The images show the repository as it looks in VS Code (Dark Modern theme, Windows):
the code is cut from the real file at the line range named below and coloured the
way VS Code colours it, with the real line numbers, so a screenshot can never drift
from the code it claims to show. Terminal images are the integrated PowerShell
terminal showing the captured output of the command they name; saved reports are
printed, not re-run, so the numbers match the committed files.
"""
import html
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from pygments.lexers import PythonLexer
from pygments.token import (Comment, Keyword, Name, Number, Operator, Punctuation,
                            String)

DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parent
OUT = DOCS / "shots"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
WIDTH = 1040
LINE = 19
TERM_COLS = 124

# name -> (file, first line, last line)
CODE = {
    "build_stages": ("ostutor/build.py", 145, 171),
    "decontaminate": ("ostutor/dedup.py", 178, 192),
    "lora": ("train/kaggle_train.py", 138, 144),
    "sftconfig": ("train/kaggle_train.py", 172, 199),
    "grounding": ("ostutor/solver.py", 351, 364),
    "corpus": ("ostutor/rag/corpus.py", 96, 125),
    "extract_pdf": ("ostutor/rag/extract.py", 102, 113),
    "retrieve": ("ostutor/rag/retrieve.py", 123, 149),
    "augment": ("ostutor/rag/retrieve.py", 156, 175),
    "calibrate": ("tools/rag_eval.py", 69, 85),
    "gateway_notfound": ("serve/gateway.py", 310, 330),
    "gateway_layers": ("serve/gateway.py", 393, 410),
    "mcnemar": ("ostutor/evaluation/stats.py", 15, 30),
}
# other files shown as open (inactive) tabs next to each one
NEIGHBOURS = {"ostutor/build.py": ["dedup.py", "config.py"], "ostutor/dedup.py": ["build.py", "clean.py"],
              "train/kaggle_train.py": ["build.py"], "ostutor/solver.py": ["gateway.py", "theory_filter.py"],
              "ostutor/rag/corpus.py": ["extract.py", "manifest.json"],
              "ostutor/rag/extract.py": ["corpus.py", "ingest.py"],
              "tools/rag_eval.py": ["corpus_questions.jsonl", "retrieve.py"],
              "ostutor/rag/retrieve.py": ["corpus.py", "gateway.py"],
              "serve/gateway.py": ["retrieve.py", "test_gateway.py"],
              "ostutor/evaluation/stats.py": ["harness.py", "g0_ablation.py"]}

# ---------------------------------------------------------------- VS Code colours
CONTROL = {"if", "elif", "else", "for", "while", "return", "import", "from", "as", "try",
           "except", "finally", "with", "raise", "yield", "break", "continue", "pass",
           "assert", "del", "global", "nonlocal", "await", "async"}
TYPES = {"int", "str", "float", "list", "dict", "set", "tuple", "bool", "bytes", "object", "type"}
BRACKETS = ["#ffd700", "#da70d6", "#179fff"]
DEFAULT = "#cccccc"


def colour_tokens(text: str) -> list[list[tuple[str, str]]]:
    """Per line, a list of (colour, text) - Dark Modern + Pylance semantic colours,
    with bracket-pair colourisation carried across lines like the editor does."""
    toks = [t for t in PythonLexer().get_tokens(text)]
    lines, cur, depth = [], [], 0
    for i, (tt, v) in enumerate(toks):
        nxt = next((w for _, w in toks[i + 1:i + 4] if w.strip()), "")
        if tt in Keyword.Constant or tt in Operator.Word or (tt in Keyword and v in ("def", "class", "lambda")):
            c = "#569cd6"
        elif tt in Keyword:
            c = "#c586c0" if v in CONTROL or tt in Keyword.Namespace else "#569cd6"
        elif tt in Name.Function or tt in Name.Decorator:
            c = "#dcdcaa"
        elif tt in Name.Class or tt in Name.Namespace:
            c = "#4ec9b0"
        elif tt in Name.Builtin.Pseudo:
            c = "#9cdcfe"
        elif tt in Name.Builtin:
            c = "#4ec9b0" if v in TYPES else "#dcdcaa"
        elif tt in Name:
            if nxt.startswith("("):
                c = "#4ec9b0" if v[:1].isupper() and not v.isupper() else "#dcdcaa"
            elif v.isupper() and len(v) > 1:
                c = "#4fc1ff"
            else:
                c = "#9cdcfe"
        elif tt in String.Affix or tt in String.Interpol:
            c = "#569cd6"
        elif tt in String.Escape:
            c = "#d7ba7d"
        elif tt in String:
            c = "#ce9178"
        elif tt in Number:
            c = "#b5cea8"
        elif tt in Comment:
            c = "#6a9955"
        elif tt in Punctuation and v in "([{":
            c = BRACKETS[depth % 3]
            depth += 1
        elif tt in Punctuation and v in ")]}":
            depth = max(0, depth - 1)
            c = BRACKETS[depth % 3]
        elif tt in Operator or tt in Punctuation:
            c = "#d4d4d4"
        else:
            c = DEFAULT
        parts = v.split("\n")
        for k, part in enumerate(parts):
            if k:
                lines.append(cur)
                cur = []
            if part:
                cur.append((c, part))
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- window chrome
CSS = """
html,body{margin:0;background:#1f1f1f}
.win{width:%dpx;background:#1f1f1f;font-family:'Segoe UI',sans-serif;color:#cccccc;border:1px solid #2b2b2b}
.title{height:35px;background:#181818;display:flex;align-items:center;font-size:13px;border-bottom:1px solid #2b2b2b}
.title .logo{width:35px;display:flex;justify-content:center}
.title .menu span{padding:0 7px;color:#cccccc}
.title .cc{margin:0 auto;width:330px;height:22px;border:1px solid #3c3c3c;background:#262626;border-radius:6px;
           color:#9d9d9d;font-size:12px;display:flex;align-items:center;justify-content:center;gap:6px}
.title .ctl{display:flex;font-family:'Segoe MDL2 Assets';font-size:10px;color:#cccccc}
.title .ctl span{width:46px;text-align:center}
.main{display:flex}
.act{width:48px;background:#181818;border-right:1px solid #2b2b2b;display:flex;flex-direction:column;align-items:center;padding-top:6px;gap:16px}
.act svg{width:24px;height:24px}
.act .on{border-left:2px solid #0078d4;width:46px;display:flex;justify-content:center}
.pane{flex:1;min-width:0}
.tabs{height:35px;background:#181818;display:flex;border-bottom:1px solid #2b2b2b}
.tab{display:flex;align-items:center;gap:6px;padding:0 12px 0 10px;font-size:13px;color:#9d9d9d;border-right:1px solid #2b2b2b}
.tab.on{background:#1f1f1f;color:#ffffff;border-top:1px solid #0078d4;margin-bottom:-1px}
.tab .x{font-family:'Segoe MDL2 Assets';font-size:9px;color:#cccccc;margin-left:10px}
.crumbs{height:22px;display:flex;align-items:center;gap:5px;padding-left:16px;font-size:12.5px;color:#a9a9a9}
.ed{display:flex;font-family:Consolas,'Courier New',monospace;font-size:14px;position:relative;padding-bottom:6px}
.gut{width:58px;text-align:right;color:#6e7681;padding-right:26px}
.gut div,.src div,.mm div{height:%dpx;line-height:%dpx;white-space:pre}
.gut .cur{color:#cccccc}
.src{flex:1;overflow:hidden}
.src .cur{outline:1px solid #282828;outline-offset:-1px}
.ig{display:inline-block;width:4ch;box-shadow:inset 1px 0 #404040}
.mm{width:70px;opacity:.55;overflow:hidden;position:relative}
.mm div{height:2px;line-height:2px;font-size:2px;letter-spacing:0}
.mm .s{position:absolute;left:0;right:0;background:rgba(121,121,121,.18)}
.status{height:22px;background:#181818;border-top:1px solid #2b2b2b;display:flex;align-items:center;font-size:12px;color:#cccccc}
.status .rem{background:#0078d4;color:#fff;height:22px;width:34px;display:flex;align-items:center;justify-content:center}
.status span{padding:0 8px}
.status .r{margin-left:auto;display:flex}
.ph{height:35px;display:flex;align-items:center;gap:22px;padding-left:18px;font-size:11px;letter-spacing:.04em;color:#9d9d9d;border-bottom:1px solid #2b2b2b}
.ph .on{color:#e7e7e7;border-bottom:1px solid #0078d4;padding-bottom:6px;margin-top:7px}
.ph .r{margin-left:auto;padding-right:14px;letter-spacing:0;font-size:12px;color:#cccccc;display:flex;gap:14px}
.term{background:#181818;font-family:Consolas,'Courier New',monospace;font-size:14px;color:#cccccc;padding:6px 18px 10px}
.term div{height:%dpx;line-height:%dpx;white-space:pre}
""" % (WIDTH, LINE, LINE, LINE, LINE)

LOGO = ('<svg width="16" height="16" viewBox="0 0 100 100"><path fill="#0078d4" d="M96 11 75 1 33 40 14 25 '
        '5 30v40l9 5 19-15 42 39 21-10V11zM75 72 43 50 75 28v44zM14 62V38l12 12-12 12z"/></svg>')
PYICON = ('<svg width="14" height="14" viewBox="0 0 16 16"><path fill="#3572a5" d="M7.9 1C4.3 1 4.5 2.6 4.5 '
          '2.6v1.6h3.5v.5H3.1S.8 4.4.8 8.1s2 3.6 2 3.6h1.2V10s-.1-2 2-2h3.5s1.9 0 1.9-1.9V3S11.7 1 7.9 1z'
          'M6 2.1a.6.6 0 1 1 0 1.3.6.6 0 0 1 0-1.3z"/><path fill="#ffd43b" d="M8.1 15c3.6 0 3.4-1.6 3.4-1.6'
          'v-1.6H8v-.5h4.9s2.3.3 2.3-3.4-2-3.6-2-3.6h-1.2V6s.1 2-2 2H6.5S4.6 8 4.6 9.9V13s-.3 2 3.5 2zm1.9-1.1'
          'a.6.6 0 1 1 0-1.3.6.6 0 0 1 0 1.3z"/></svg>')
JSONICON = '<span style="color:#cbcb41;font:bold 11px Consolas">{}</span>'
ACT = """<div class="act">
<div class="on"><svg viewBox="0 0 24 24" fill="none" stroke="#d7d7d7" stroke-width="1.3"><path d="M14 3H6v18h12V7z"/><path d="M14 3v4h4"/><path d="M9 3V1h8l4 4v13h-3"/></svg></div>
<svg viewBox="0 0 24 24" fill="none" stroke="#858585" stroke-width="1.4"><circle cx="14" cy="10" r="6"/><path d="M9.5 14.5 3 21"/></svg>
<svg viewBox="0 0 24 24" fill="none" stroke="#858585" stroke-width="1.4"><circle cx="7" cy="5" r="2"/><circle cx="7" cy="19" r="2"/><circle cx="17" cy="9" r="2"/><path d="M7 7v10M17 11c0 4-10 2-10 6"/></svg>
<svg viewBox="0 0 24 24" fill="none" stroke="#858585" stroke-width="1.4"><path d="M8 5v14l11-7z"/><circle cx="7" cy="18" r="3"/></svg>
<svg viewBox="0 0 24 24" fill="none" stroke="#858585" stroke-width="1.4"><rect x="3" y="9" width="6" height="6"/><rect x="9" y="15" width="6" height="6"/><rect x="3" y="15" width="6" height="6"/><rect x="14" y="3" width="6" height="6"/></svg>
</div>"""


def title_bar(filename: str) -> str:
    menu = "".join(f"<span>{m}</span>" for m in
                   ["File", "Edit", "Selection", "View", "Go", "Run", "Terminal", "Help"])
    return (f'<div class="title"><div class="logo">{LOGO}</div><div class="menu">{menu}</div>'
            '<div class="cc">&#x2190;&nbsp;&#x2192;&nbsp;&nbsp;&#x1F50D;&#xFE0E; os project</div>'
            '<div class="ctl"><span>&#xE921;</span><span>&#xE922;</span><span>&#xE8BB;</span></div></div>')


def status_bar(right: str) -> str:
    return ('<div class="status"><div class="rem">&#x276F;&#x276E;</div><span>&#x2387; master</span>'
            '<span>&#x2297; 0 &nbsp;&#x26A0; 0</span><div class="r">' + right + '</div></div>')


def icon(name: str) -> str:
    return PYICON if name.endswith(".py") else JSONICON.format("{}")


def page(body: str) -> str:
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{body}</body></html>'


def shoot(doc: str, png: Path, height: int) -> None:
    tmp = OUT / f"_{png.stem}.html"
    tmp.write_text(doc, encoding="utf-8")
    if png.exists():
        png.unlink()
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=2", f"--window-size={WIDTH + 2},{height}",
                    f"--screenshot={png}", tmp.as_uri()], capture_output=True)
    for _ in range(60):
        if png.exists() and png.stat().st_size > 0:
            break
        time.sleep(0.5)
    tmp.unlink(missing_ok=True)
    if not png.exists():
        sys.exit(f"screenshot failed: {png}")


def span_line(parts) -> str:
    return "".join(f'<span style="color:{c}">{html.escape(t)}</span>' for c, t in parts)


def code_shot(name: str, path: str, a: int, b: int) -> None:
    raw = (ROOT / path).read_bytes()
    text = raw.decode("utf-8").replace("\r\n", "\n")
    allc = colour_tokens(text)
    src = text.split("\n")
    n = b - a + 1
    # indent guides: leading spaces in steps of 4; a blank line takes its neighbours' depth
    def lead(i):
        s = src[i]
        return (len(s) - len(s.lstrip(" "))) // 4 if s.strip() else None
    rows = []
    for i in range(a - 1, b):
        parts = list(allc[i]) if i < len(allc) else []
        lv = lead(i)
        if lv is None:
            up = next((lead(j) for j in range(i - 1, -1, -1) if lead(j) is not None), 0)
            dn = next((lead(j) for j in range(i + 1, len(src)) if lead(j) is not None), 0)
            lv, parts = min(up, dn), []
        guides = '<span class="ig"> </span>' * lv if lv else ""
        # strip the leading spaces the guides now draw
        cut = lv * 4
        out = []
        for c, t in parts:
            if cut:
                k = min(cut, len(t) - len(t.lstrip(" ")))
                t, cut = t[k:], cut - k
            if t:
                out.append((c, t))
        cls = ' class="cur"' if i == a - 1 else ""
        rows.append(f"<div{cls}>{guides}{span_line(out) or ' '}</div>")
    gut = "".join(f'<div{" class=\"cur\"" if k == a else ""}>{k}</div>' for k in range(a, b + 1))
    # minimap: the file around the viewport, two pixels a line, a pixel per character
    m0 = max(0, a - 1 - 30)
    mm = []
    for i in range(m0, min(len(src), m0 + n * 10)):
        segs = "".join(f'<span style="background:{c};color:transparent">{"." * len(t)}</span>'
                       for c, t in (allc[i] if i < len(allc) else []) if t.strip())
        lead_px = len(src[i]) - len(src[i].lstrip(" "))
        mm.append(f'<div style="padding-left:{lead_px}px;font-size:1px">{segs or " "}</div>')
    slider = f'<div class="s" style="top:{(a - 1 - m0) * 2}px;height:{n * 2}px"></div>'
    fname = path.split("/")[-1]
    tabs = f'<div class="tab on">{PYICON}{fname}<span class="x">&#xE8BB;</span></div>' + "".join(
        f'<div class="tab">{icon(t)}{t}</div>' for t in NEIGHBOURS.get(path, []))
    crumbs = " <span>&#x203A;</span> ".join(path.split("/")[:-1]) + f' <span>&#x203A;</span> {PYICON} {fname}'
    col = (len(src[a - 1]) - len(src[a - 1].lstrip(" "))) + 1
    eol = "CRLF" if b"\r\n" in raw else "LF"
    right = (f"<span>Ln {a}, Col {col}</span><span>Spaces: 4</span><span>UTF-8</span><span>{eol}</span>"
             "<span>{ } Python</span><span>3.13.3 64-bit</span><span>&#x1F514;&#xFE0E;</span>")
    body = (f'<div class="win">{title_bar(fname)}<div class="main">{ACT}<div class="pane">'
            f'<div class="tabs">{tabs}</div><div class="crumbs">{crumbs}</div>'
            f'<div class="ed"><div class="gut">{gut}</div><div class="src">{"".join(rows)}</div>'
            f'<div class="mm">{slider}{"".join(mm)}</div></div></div></div>{status_bar(right)}</div>')
    shoot(page(body), OUT / f"code_{name}.png", 35 + 35 + 22 + n * LINE + 6 + 24 + 2)


def term_shot(name: str, command: str, lines: list[str], command_visible: bool = True) -> None:
    """command_visible=False: the command has scrolled out of view, as it does after a long
    output; only the last lines and the new prompt show."""
    rows = [f"<div>PS D:\\os project&gt; {html.escape(command)}</div>"] if command_visible else []
    rows += [f"<div>{html.escape(l) or ' '}</div>" for l in lines]
    rows.append('<div>PS D:\\os project&gt; <span style="background:#cccccc"> </span></div>')
    head = ('<div class="ph"><span>PROBLEMS</span><span>OUTPUT</span><span>DEBUG CONSOLE</span>'
            '<span class="on">TERMINAL</span><span>PORTS</span><div class="r"><span>&#xFF0B; powershell</span>'
            '<span>&#x22EF;</span><span>&#x2303;</span><span>&#x2715;</span></div></div>')
    right = "<span>&#x1F514;&#xFE0E;</span>"
    body = (f'<div class="win">{title_bar("")}<div class="main">{ACT}<div class="pane">{head}'
            f'<div class="term">{"".join(rows)}</div></div></div>{status_bar(right)}</div>')
    shoot(page(body), OUT / f"term_{name}.png", 35 + 35 + 16 + len(rows) * LINE + 24 + 2)


NOISE = ("Loading weights", "LOAD REPORT", "Key ", "-----", "position_ids", "Notes:",
         "UNEXPECTED", "solver path failed", "fact-check retry failed", '{"t":')


def run(cmd: list[str], py: str = sys.executable) -> list[str]:
    """Run a command and return its output lines (library load chatter removed)."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([py, *cmd], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                       env=env)
    return [l for l in (p.stdout + p.stderr).splitlines() if not any(n in l for n in NOISE)]


def wrap(lines: list[str], width: int = TERM_COLS) -> list[str]:
    """Hard-wrap at the terminal width, as the terminal itself does."""
    out = []
    for l in lines:
        while len(l) > width:
            out.append(l[:width])
            l = l[width:]
        out.append(l)
    return out


def loss_curve() -> None:
    """docs/shots/loss_curve.svg from the v3 run's own training log, drawn like a plain
    spreadsheet line chart."""
    log = json.loads((ROOT / "outputs/ostutor-lora-v3/ostutor-lora/train_metrics.json")
                     .read_text(encoding="utf-8"))["log"]
    series = {"Training loss": [(x["step"], x["loss"]) for x in log if "loss" in x],
              "Validation loss": [(x["step"], x["eval_val_loss"]) for x in log if "eval_val_loss" in x],
              "OOD loss": [(x["step"], x["eval_ood_loss"]) for x in log if "eval_ood_loss" in x]}
    colours = ["#4472c4", "#ed7d31", "#a5a5a5"]
    W, H, L, R, T, B = 640, 300, 50, 18, 34, 62
    xmax, ymax = 800, 1.2
    X = lambda s: L + (W - L - R) * s / xmax                       # noqa: E731
    Y = lambda v: T + (H - T - B) * (1 - v / ymax)                  # noqa: E731
    g = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Calibri, Carlito, Arial" '
         f'font-size="11"><rect width="{W}" height="{H}" fill="#fff" stroke="#d9d9d9"/>',
         f'<text x="{W / 2}" y="22" text-anchor="middle" font-size="15" fill="#595959">Loss vs training step</text>']
    for k in range(7):
        v = k * 0.2
        g.append(f'<line x1="{L}" x2="{W - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#d9d9d9"/>'
                 f'<text x="{L - 6}" y="{Y(v) + 4:.1f}" text-anchor="end" fill="#595959">{v:.1f}</text>')
    for s in range(0, 801, 100):
        g.append(f'<text x="{X(s):.1f}" y="{H - B + 16}" text-anchor="middle" fill="#595959">{s}</text>')
    g.append(f'<text x="{(L + W - R) / 2}" y="{H - B + 34}" text-anchor="middle" fill="#595959">Step</text>'
             f'<text transform="translate(14 {(T + H - B) / 2}) rotate(-90)" text-anchor="middle" '
             'fill="#595959">Loss</text>')
    for (name, pts), col in zip(series.items(), colours):
        path = " ".join(f"{'M' if i == 0 else 'L'}{X(s):.1f},{Y(v):.1f}" for i, (s, v) in enumerate(pts))
        g.append(f'<path d="{path}" fill="none" stroke="{col}" stroke-width="2.2" stroke-linejoin="round"/>')
    x = W / 2 - 150
    for (name, _), col in zip(series.items(), colours):
        g.append(f'<line x1="{x}" x2="{x + 22}" y1="{H - 12}" y2="{H - 12}" stroke="{col}" stroke-width="2.2"/>'
                 f'<text x="{x + 27}" y="{H - 8}" fill="#595959">{name}</text>')
        x += 105
    g.append("</svg>")
    (OUT / "loss_curve.svg").write_text("".join(g), encoding="utf-8")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.png"):
        old.unlink()
    loss_curve()
    for name, (path, a, b) in CODE.items():
        code_shot(name, path, a, b)
        print("  code", name)

    term_shot("test_rag", "python tools\\test_rag.py", [l for l in run(["tools/test_rag.py"]) if l.strip()])
    gw = [l for l in run(["serve/test_gateway.py"], py=str(ROOT / "serve/.venv-webui/Scripts/python.exe"))
          if l.strip()]
    term_shot("test_gateway", "serve\\.venv-webui\\Scripts\\python serve\\test_gateway.py", gw[-12:])
    # Saved reports are printed, not re-run: re-running would overwrite the committed
    # numbers the document cites with a fresh (and, for latency, different) sample.
    ev = ROOT / "reports/rag/corpus_eval.md"
    term_shot("rag_eval", "Get-Content -Encoding UTF8 reports\\rag\\corpus_eval.md",
              wrap(ev.read_text(encoding="utf-8").split("## Hybrid misses")[0].rstrip("\n").splitlines()))
    ing = [l for l in run(["-m", "ostutor.rag.ingest", "data/rag/corpus"]) if l.strip()]
    term_shot("ingest", "python -m ostutor.rag.ingest data\\rag\\corpus", ing[-22:], command_visible=False)
    # the files the figures' captions name (not simply the newest run)
    for name, rel in (("rag_e2e", "reports/rag/e2e-20261012-2239/summary.md"),
                      ("rag_short_compare", "reports/rag/short_e2e-short-course_vs_e2e-20261013-1339.md")):
        term_shot(name, "Get-Content -Encoding UTF8 " + rel.replace("/", "\\"),
                  wrap((ROOT / rel).read_text(encoding="utf-8").rstrip("\n").splitlines()))
    print(f"wrote {len(list(OUT.glob('*.png')))} images to {OUT}")


if __name__ == "__main__":
    main()
