"""Bundle the released dataset for upload as the Kaggle dataset `ostutor-sft`.

    python tools/package_kaggle.py

Copies train/val/ood.jsonl, manifest.json, DATASET_CARD.md and the training script
into dist/ostutor-sft/, after checking that the build passed its gates and that every
file's SHA-256 still matches the manifest (so a hand-edited or stale file cannot be
uploaded by mistake).
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "data" / "build"
OUT = ROOT / "dist" / "ostutor-sft"


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    m = json.loads((ROOT / "reports" / "manifest.json").read_text(encoding="utf-8"))
    if not m["gates_passed"]:
        sys.exit("refusing to package: the build did not pass its release gates")
    for name, want in m["artifacts"].items():
        if sha256(BUILD / name) != want:
            sys.exit(f"refusing to package: {name} does not match the manifest hash")
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for name in m["artifacts"]:
        shutil.copy2(BUILD / name, OUT / name)
    shutil.copy2(ROOT / "reports" / "manifest.json", OUT / "manifest.json")
    shutil.copy2(ROOT / "DATASET_CARD.md", OUT / "README.md")
    shutil.copy2(ROOT / "train" / "kaggle_train.py", OUT / "kaggle_train.py")
    for p in sorted(OUT.iterdir()):
        print(f"  {p.name:18s} {p.stat().st_size:>12,} bytes")
    print(f"ready to upload: {OUT}")


if __name__ == "__main__":
    main()
