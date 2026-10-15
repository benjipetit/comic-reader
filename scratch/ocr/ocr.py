"""Run one OCR method on one image. Returns an OcrResult (also importable).

    python ocr.py tesseract ../../fixtures/photos/zouk-1.png
"""
from __future__ import annotations

import argparse
import logging
import time
from dataclasses import dataclass, replace
from pathlib import Path

from PIL import Image

import methods
from model import Segment


@dataclass
class OcrResult:
    segments: list[Segment]
    method: str
    image: str
    elapsed_s: float
    error: str | None = None

    @property
    def text(self) -> str:
        return "\n".join(s.text for s in self.segments)


def _require_png(image_path: Path) -> None:
    """The API only accepts PNG. Check the content, not the extension (zouk-1.png is a HEIC)."""
    with Image.open(image_path) as img:
        if img.format != "PNG":
            raise ValueError(f"unsupported image format: {img.format}")


def ocr_image(method: str, image_path: Path, settings: dict[str, str] | None = None) -> OcrResult:
    fn = methods.get(method)
    settings = {**methods.defaults(method), **(settings or {})}
    start = time.perf_counter()
    try:
        _require_png(image_path)
        segments = [replace(s, text=s.text.strip()) for s in fn(image_path, settings)]
        segments, error = [s for s in segments if s.text], None
    except Exception as exc:  # noqa: BLE001 - report per-image failures, don't abort a batch
        segments, error = [], f"{type(exc).__name__}: {exc}"
    return OcrResult(segments, method, image_path.name, round(time.perf_counter() - start, 2), error)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("method", choices=methods.METHODS)
    p.add_argument("image", type=Path)
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    result = ocr_image(args.method, args.image)
    print(result.text or "(no text)")
    print(f"\n-- {result.method} | {result.elapsed_s}s" + (f" | ERROR {result.error}" if result.error else ""))
