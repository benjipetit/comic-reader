"""easyocr + geometry-only post-processing: sort boxes into reading order, then one segment per line."""
from __future__ import annotations

import logging
from pathlib import Path

import layout
from methods.easyocr import run as run_easyocr
from model import Segment

log = logging.getLogger(__name__)


def run(image_path: Path, settings: dict[str, str]) -> list[Segment]:
    raw = run_easyocr(image_path, settings)

    lines = layout.sort_into_lines(raw)  # step 1: order the boxes
    log.info("%d boxes -> %d lines", len(raw), len(lines))
    for i, line in enumerate(lines):
        log.info("  line %-3d %s", i, " | ".join(s.text for s in line))

    return layout.lines_to_segments(lines)  # step 2: clean segments
