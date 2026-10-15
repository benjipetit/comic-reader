"""Local OCR. Needs the binary (`brew install tesseract tesseract-lang`) + `pip install pytesseract Pillow`."""
from __future__ import annotations

from pathlib import Path

import pytesseract
from PIL import Image

from model import Segment


def run(image_path: Path, settings: dict[str, str]) -> list[Segment]:
    with Image.open(image_path) as img:
        text = pytesseract.image_to_string(img, lang=settings["lang"], config=f"--psm {settings['psm']}")
    return [Segment(text)]  # whole-page text, no boxes
