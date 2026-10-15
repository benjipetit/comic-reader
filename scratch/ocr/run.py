"""Assess OCR methods over a set of images.

    python run.py                                   # tesseract over fixtures/photos
    python run.py -m tesseract -m mistral           # several methods
    python run.py ../../fixtures/photos/zouk-*.png  # explicit files / dirs / globs
    python run.py --out results/                    # also write <out>/<method>/<image>.txt

If fixtures/transcripts/<image-stem>.txt exists, a similarity score (0-1) against it is shown.
"""
from __future__ import annotations

import argparse
import logging
import difflib
import glob
from pathlib import Path

import methods
from ocr import ocr_image

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SET = ROOT / "fixtures" / "photos"
TRANSCRIPTS = ROOT / "fixtures" / "transcripts"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def collect(targets: list[str]) -> list[Path]:
    paths: list[Path] = []
    for t in targets or [str(DEFAULT_SET)]:
        for match in sorted(glob.glob(t)) or [t]:
            p = Path(match)
            if p.is_dir():
                paths += sorted(f for f in p.iterdir() if f.suffix.lower() in IMAGE_EXTS)
            elif p.is_file():
                paths.append(p)
            else:
                raise SystemExit(f"Not found: {t}")
    return paths


def score(text: str, image: Path) -> str:
    ref = TRANSCRIPTS / f"{image.stem}.txt"
    if not ref.exists():
        return "-"
    return f"{difflib.SequenceMatcher(None, text.lower(), ref.read_text().lower()).ratio():.2f}"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("targets", nargs="*", help="image files, directories or globs (default: fixtures/photos)")
    p.add_argument("-m", "--method", action="append", choices=methods.METHODS, help="repeatable (default: all)")
    p.add_argument("--out", type=Path, help="write extracted text to <out>/<method>/<image>.txt")
    p.add_argument("--preview", type=int, default=200, help="chars of text to show per image (0 = full)")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    images = collect(args.targets)
    for method in args.method or methods.METHODS:
        print(f"\n=== {method} ({len(images)} images) ===")
        total = 0.0
        for img in images:
            r = ocr_image(method, img)
            total += r.elapsed_s
            shown = r.text if args.preview == 0 else r.text[: args.preview]
            print(f"\n[{img.name}] {r.elapsed_s}s  chars={len(r.text)}  score={score(r.text, img)}")
            print(f"  ERROR {r.error}" if r.error else "  " + shown.replace("\n", "\n  "))
            if args.out:
                out = args.out / method
                out.mkdir(parents=True, exist_ok=True)
                (out / f"{img.stem}.txt").write_text(r.text)
        print(f"\ntotal {total:.1f}s, avg {total / max(len(images), 1):.1f}s")


if __name__ == "__main__":
    main()
