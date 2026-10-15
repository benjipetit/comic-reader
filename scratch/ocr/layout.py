"""Geometry-only post-processing for methods that return boxes.

Two steps, both pure functions:
  1. sort_into_lines: chain side-by-side boxes into lines, order lines top-to-bottom and boxes
     left-to-right.
  2. lines_to_segments: collapse each line into one clean Segment (joined text, one box).

Lines are built from *local* adjacency instead of a global deskew, so they follow curved or
tilted baselines (e.g. a page photographed with a curl).
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass

from model import Segment

Point = tuple[float, float]

MAX_GAP = 1.0  # max horizontal gap between neighbours, in box heights
MAX_OVERLAP = 0.25  # max horizontal overlap, as a fraction of the narrower box (boxes touch)
MAX_DY = 0.5  # max vertical distance between box centres, in box heights


@dataclass
class _Item:
    seg: Segment
    x0: float
    x1: float
    y0: float
    y1: float

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def w(self) -> float:
        return self.x1 - self.x0

    @property
    def h(self) -> float:
        return self.y1 - self.y0


def _same_line(a: _Item, b: _Item) -> bool:
    h = min(a.h, b.h)
    gap = max(a.x0, b.x0) - min(a.x1, b.x1)  # negative when the boxes overlap horizontally
    side_by_side = gap <= MAX_GAP * h and -gap <= MAX_OVERLAP * min(a.w, b.w)
    return side_by_side and abs(a.cy - b.cy) <= MAX_DY * h


def sort_into_lines(segments: list[Segment]) -> list[list[Segment]]:
    """Lines in reading order, each line's boxes left to right. Segments without a box are
    appended as one trailing line each."""
    items = []
    for s in segments:
        if s.box:
            xs, ys = [p[0] for p in s.box], [p[1] for p in s.box]
            items.append(_Item(s, min(xs), max(xs), min(ys), max(ys)))

    # Connected components of the "same line" relation (union-find).
    parent = list(range(len(items)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, a in enumerate(items):
        for j in range(i + 1, len(items)):
            if _same_line(a, items[j]):
                parent[find(i)] = find(j)

    groups: dict[int, list[_Item]] = {}
    for i, it in enumerate(items):
        groups.setdefault(find(i), []).append(it)

    lines = sorted(groups.values(), key=lambda g: statistics.mean(i.cy for i in g))
    ordered = [[i.seg for i in sorted(g, key=lambda i: i.cx)] for g in lines]
    return ordered + [[s] for s in segments if not s.box]


def _convex_hull(points: list[Point]) -> list[Point]:
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts

    def half(seq: list[Point]) -> list[Point]:
        hull: list[Point] = []
        for p in seq:
            while len(hull) >= 2 and (
                (hull[-1][0] - hull[-2][0]) * (p[1] - hull[-2][1])
                - (hull[-1][1] - hull[-2][1]) * (p[0] - hull[-2][0])
            ) <= 0:
                hull.pop()
            hull.append(p)
        return hull

    return half(pts)[:-1] + half(pts[::-1])[:-1]


def lines_to_segments(lines: list[list[Segment]]) -> list[Segment]:
    """One Segment per line: texts joined with spaces, box = convex hull of its boxes (follows a
    tilted line), confidence = lowest of the line so weak lines stand out."""
    out = []
    for line in lines:
        confs = [s.confidence for s in line if s.confidence is not None]
        pts = [p for s in line if s.box for p in s.box]
        out.append(Segment(
            " ".join(s.text for s in line),
            _convex_hull(pts) if pts else None,
            min(confs) if confs else None,
        ))
    return out
