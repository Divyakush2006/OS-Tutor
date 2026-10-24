"""Brand the chat frontend as OS Tutor.

    serve/.venv-webui/Scripts/python serve/branding.py [--restore]

Open WebUI ships its own logo, favicon and name, and appends " (Open WebUI)" to a
custom WEBUI_NAME. This script, which start_tutor.ps1 runs before it starts the
frontend, makes three changes inside the installed package:

  1. the icon set (favicon, sidebar and model avatar, splash, app icons) is drawn
     from assets/logo.jpg;
  2. the " (Open WebUI)" suffix is removed from the application name;
  3. the page title and web-app manifest name read "OS Tutor".

It is idempotent. The first run saves the original files under
serve/webui-data/branding-originals, and --restore puts them back. The Open WebUI
licence allows this for deployments with at most 50 end users in 30 days; this one
is a single-user localhost deployment.
"""
import base64
import importlib.util
import io
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageOps

SERVE = Path(__file__).resolve().parent
ROOT = SERVE.parent
LOGO = ROOT / "assets" / "logo.jpg"
BACKUP = SERVE / "webui-data" / "branding-originals"
NAME = "OS Tutor"

SUFFIX_OLD = "if WEBUI_NAME != 'Open WebUI':\n    WEBUI_NAME += ' (Open WebUI)'\n"
SUFFIX_NEW = "# OS Tutor: the name is shown as set, without Open WebUI's suffix (serve/branding.py).\n"


def package_dir() -> Path:
    spec = importlib.util.find_spec("open_webui")
    if spec is None or not spec.submodule_search_locations:
        sys.exit("open_webui is not installed in this Python; run with serve/.venv-webui")
    return Path(list(spec.submodule_search_locations)[0])


# ------------------------------------------------------------------ artwork
def runs(mask_rows):
    """Consecutive row indices that contain ink."""
    out, start = [], None
    for i, has in enumerate(mask_rows):
        if has and start is None:
            start = i
        if not has and start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(mask_rows)))
    return out


def load_art():
    """The emblem alone and the full lockup, each as an 'ink' mask (255 = black ink)."""
    gray = ImageOps.grayscale(Image.open(LOGO))
    ink = gray.point(lambda v: 255 - v)                   # 255 where the artwork is black
    bin_ = ink.point(lambda v: 255 if v > 60 else 0)
    w, h = bin_.size
    px = bin_.load()
    rows = [any(px[x, y] for x in range(w)) for y in range(h)]
    bands = runs(rows)
    if len(bands) < 2:
        sys.exit("could not separate the emblem from the wordmark in logo.jpg")
    top, bottom = bands[0]                                # cap and circle
    emblem = ink.crop((0, top, w, bottom))
    emblem = emblem.crop(emblem.point(lambda v: 255 if v > 60 else 0).getbbox())
    lockup = ink.crop(bin_.getbbox())
    return emblem, lockup


def sharpen(ink: Image.Image, size: int) -> Image.Image:
    """Upscale flat black-on-white artwork without soft edges, then antialias down."""
    scale = max(1, (size * 2) // max(ink.size) + 1)
    big = ink.resize((ink.width * scale, ink.height * scale), Image.LANCZOS)
    big = big.point(lambda v: 0 if v < 70 else 255 if v > 150 else int((v - 70) * 255 / 80))
    return big


def fit(ink: Image.Image, canvas: int, pad: float) -> Image.Image:
    """Centre the artwork in a square canvas; returns an ink mask of that size."""
    inner = int(canvas * (1 - 2 * pad))
    art = sharpen(ink, inner)
    art.thumbnail((inner, inner), Image.LANCZOS)
    out = Image.new("L", (canvas, canvas), 0)
    out.paste(art, ((canvas - art.width) // 2, (canvas - art.height) // 2))
    return out


def on_white(ink: Image.Image) -> Image.Image:
    """Black artwork on an opaque white square."""
    return Image.merge("RGBA", (*([ink.point(lambda v: 255 - v)] * 3), Image.new("L", ink.size, 255)))


def on_clear(ink: Image.Image, colour: int) -> Image.Image:
    """Artwork in one colour on a transparent square (for the splash screen)."""
    flat = Image.new("L", ink.size, colour)
    return Image.merge("RGBA", (flat, flat, flat, ink))


def png_bytes(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def build_icons(emblem, lockup):
    """file name -> bytes, for static/ and the frontend copy."""
    icons = {}
    for name, size in (("favicon.png", 512), ("favicon-96x96.png", 96), ("apple-touch-icon.png", 180)):
        icons[name] = png_bytes(on_white(fit(emblem, size, 0.10)))
    for name, size in (("web-app-manifest-192x192.png", 192), ("web-app-manifest-512x512.png", 512)):
        icons[name] = png_bytes(on_white(fit(emblem, size, 0.22)))          # maskable safe zone
    icons["logo.png"] = png_bytes(on_white(fit(lockup, 500, 0.06)))
    icons["splash.png"] = png_bytes(on_clear(fit(emblem, 500, 0.04), 0))
    icons["splash-dark.png"] = png_bytes(on_clear(fit(emblem, 500, 0.04), 255))

    ico = io.BytesIO()
    big = on_white(fit(emblem, 256, 0.06))
    big.save(ico, "ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64)])
    icons["favicon.ico"] = ico.getvalue()

    data = base64.b64encode(png_bytes(on_white(fit(emblem, 128, 0.06)))).decode()
    icons["favicon.svg"] = (
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        'viewBox="0 0 128 128" width="128" height="128">'
        f'<image width="128" height="128" xlink:href="data:image/png;base64,{data}"/></svg>'
    ).encode()
    return icons


# ------------------------------------------------------------------ patching
def stash(path: Path, pkg: Path):
    """Keep the first, untouched copy of every file this script changes."""
    saved = BACKUP / path.relative_to(pkg)
    if path.exists() and not saved.exists():
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, saved)


def write_if_changed(path: Path, data: bytes, pkg: Path) -> bool:
    if path.exists() and path.read_bytes() == data:
        return False
    stash(path, pkg)
    path.write_bytes(data)
    return True


def replace_text(path: Path, old: str, new: str, pkg: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if new in text and old not in text:
        return False
    if old not in text:
        sys.exit(f"expected text not found in {path} (a different Open WebUI version?)")
    stash(path, pkg)
    path.write_bytes(text.replace(old, new).encode("utf-8"))
    return True


def apply(pkg: Path):
    if not LOGO.exists():
        sys.exit(f"missing {LOGO}")
    emblem, lockup = load_art()
    icons = build_icons(emblem, lockup)
    changed = []
    targets = [pkg / "static", pkg / "frontend" / "static"]
    for folder in targets:
        for name, data in icons.items():
            if write_if_changed(folder / name, data, pkg):
                changed.append(f"{folder.relative_to(pkg)}/{name}")
        manifest = folder / "site.webmanifest"
        if manifest.exists():
            text = manifest.read_text(encoding="utf-8")
            new = text.replace('"name": "Open WebUI"', f'"name": "{NAME}"').replace(
                '"short_name": "WebUI"', f'"short_name": "{NAME}"')
            if new != text:
                stash(manifest, pkg)
                manifest.write_bytes(new.encode("utf-8"))
                changed.append(f"{folder.relative_to(pkg)}/site.webmanifest")
    if write_if_changed(pkg / "frontend" / "favicon.png", icons["favicon.png"], pkg):
        changed.append("frontend/favicon.png")
    if replace_text(pkg / "env.py", SUFFIX_OLD, SUFFIX_NEW, pkg):
        changed.append("env.py (name suffix removed)")
    if replace_text(pkg / "frontend" / "index.html", "<title>Open WebUI</title>", f"<title>{NAME}</title>", pkg):
        changed.append("frontend/index.html (title)")
    print("branding: " + (f"{len(changed)} file(s) updated" if changed else "already applied"))
    for c in changed:
        print("  " + c)


def restore(pkg: Path):
    n = 0
    for saved in BACKUP.rglob("*"):
        if saved.is_file():
            shutil.copy2(saved, pkg / saved.relative_to(BACKUP))
            n += 1
    print(f"branding: restored {n} original file(s)")


if __name__ == "__main__":
    package = package_dir()
    restore(package) if "--restore" in sys.argv else apply(package)
