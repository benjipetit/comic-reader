"""Local OCR in two explicit stages: detect text boxes (logged), then recognize each box.

`pip install easyocr` (pulls torch). Models are downloaded on first use.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import easyocr

from model import Segment

log = logging.getLogger(__name__)

GPU = True  # uses CUDA or Apple MPS when available, falls back to CPU


@lru_cache(maxsize=2)
def _reader(langs: tuple[str, ...]) -> easyocr.Reader:
    return easyocr.Reader(list(langs), gpu=GPU)


def run(image_path: Path, settings: dict[str, str]) -> list[Segment]:
    reader = _reader(tuple(l.strip() for l in settings["langs"].split(",") if l.strip()))

    # Stage 1: detection. Returns axis-aligned boxes [x_min, x_max, y_min, y_max]
    # and free-form (rotated) quads [[x, y] * 4], per input image.
    horizontal, free = reader.detect(str(image_path))
    horizontal, free = horizontal[0], free[0]
    log.info("%s: %d horizontal boxes, %d free-form boxes", image_path.name, len(horizontal), len(free))
    for i, (x0, x1, y0, y1) in enumerate(horizontal):
        log.info("  h%-3d x=%d..%d y=%d..%d", i, x0, x1, y0, y1)
    for i, quad in enumerate(free):
        log.info("  f%-3d %s", i, [[int(x), int(y)] for x, y in quad])

    # Stage 2: recognition on the detected boxes only.
    results = reader.recognize(str(image_path), horizontal_list=horizontal, free_list=free)
    for box, text, conf in results:
        log.info("  %.2f %r", conf, text)

    # Rough reading order: top-to-bottom, then left-to-right (by top-left corner of each box).
    results.sort(key=lambda r: (min(p[1] for p in r[0]), min(p[0] for p in r[0])))
    return [Segment(text, [(float(x), float(y)) for x, y in box], float(conf)) for box, text, conf in results]
