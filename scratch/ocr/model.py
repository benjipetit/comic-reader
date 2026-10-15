"""Shared types for OCR methods, the CLI harness and the GUI."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Segment:
    """One piece of text. `text` is what the API stores (Segment.text); `box` is for visualisation."""

    text: str
    box: list[tuple[float, float]] | None = None  # polygon in image pixel coordinates
    confidence: float | None = None


@dataclass
class Setting:
    name: str
    label: str
    default: str
    choices: list[str] | None = None  # None = free text
