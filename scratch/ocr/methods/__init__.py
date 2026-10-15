"""OCR methods. Each module exposes `run(image_path: Path, settings: dict[str, str]) -> list[Segment]`.

To add a method: create methods/<name>.py with `run`, then register it (and its settings) below.
Imports are lazy so a method's dependencies are only needed when it is used.
"""
from __future__ import annotations

import importlib

from model import Setting

METHODS: dict[str, list[Setting]] = {
    "tesseract": [
        Setting("lang", "Languages (+ separated)", "eng+fra"),
        Setting("psm", "Page segmentation mode", "6", ["3", "4", "6", "11", "12"]),
    ],
    "easyocr": [
        Setting("langs", "Languages (comma separated)", "en,fr"),
    ],
    "easyocr_sorted": [
        Setting("langs", "Languages (comma separated)", "en,fr"),
    ],
}


def defaults(name: str) -> dict[str, str]:
    return {s.name: s.default for s in METHODS[name]}


def get(name: str):
    if name not in METHODS:
        raise SystemExit(f"Unknown method {name!r}. Available: {', '.join(METHODS)}")
    return importlib.import_module(f"methods.{name}").run
