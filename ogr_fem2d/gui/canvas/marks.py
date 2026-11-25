# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Where the canvas draws the conditions and the loads of a stage (spec 006,
T27; RF-15), without Qt.

* **conditions**: a mark at each vertex of a condition's stretch and at the
  middle of each of its segments (on the arc, for an arc), or at its vertex;
  a restraint not active in the stage, or an imposed displacement whose
  factor there is None, is not drawn. **The default restraint of the
  external** (``Model.default_restraint``) is drawn on every segment of the
  external no condition covers, marked as the default: the reference
  program fixed the external without showing it;
* **loads**: arrows whose tip is on the boundary, as long as the total in
  the stage (factor x value) over the largest of the stage, against the
  direction of a negative one. A NORMAL load pushes into the ground (004,
  D6): its arrow points into the model and out of an excavation; the other
  orientations are the core's directions
  (``ogr_core.loads.DistributedLoad.direction_vector``), and a point load's
  vertical is downward, as the core's.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ...model import model as md
from . import paths

Point = tuple[float, float]

#: arrows per segment of a distributed load, its ends included
ARROWS_PER_SEGMENT = 5


def segment_line(b: md.Boundary, k: int) -> list[Point]:
    """The points of segment ``k`` of ``b``, an arc by its chords."""
    p, q = b.segment(k)
    attr = b.attr(k)
    return paths.arc_points(p, q, attr.arc) if attr is not None and attr.arc is not None \
        else [p, q]


def _along(line: list[Point], t: float) -> tuple[Point, Point]:
    """The point at the fraction ``t`` of the length of ``line``, and the
    unit tangent there."""
    lengths = [math.dist(line[i], line[i + 1]) for i in range(len(line) - 1)]
    total = sum(lengths) or 1.0
    goal, run = t * total, 0.0
    for i, d in enumerate(lengths):
        if run + d >= goal or i == len(lengths) - 1:
            s = 0.0 if d == 0 else min(max((goal - run) / d, 0.0), 1.0)
            a, b = line[i], line[i + 1]
            tx, ty = (b[0] - a[0]) / (d or 1.0), (b[1] - a[1]) / (d or 1.0)
            return (a[0] + s * (b[0] - a[0]), a[1] + s * (b[1] - a[1])), (tx, ty)
        run += d
    return line[-1], (1.0, 0.0)


def _inside(p: Point, ring: list[Point]) -> bool:
    inside = False
    n = len(ring)
    for i in range(n):
        (x1, y1), (x2, y2) = ring[i], ring[(i + 1) % n]
        if (y1 > p[1]) != (y2 > p[1]):
            x = x1 + (p[1] - y1) * (x2 - x1) / (y2 - y1)
            if x > p[0]:
                inside = not inside
    return inside


def _in_ground(m: md.Model, p: Point) -> bool:
    """Inside the external and outside every excavation boundary."""
    rings = {b.kind: [] for b in m.boundaries}
    for b in m.boundaries:
        if b.closed:
            rings[b.kind].append(paths.boundary_line(b)[:-1])
    if not any(_inside(p, r) for r in rings.get(md.EXTERNAL, [])):
        return False
    return not any(_inside(p, r) for r in rings.get(md.EXCAVATION, []))


def into_ground(m: md.Model, p: Point, tangent: Point, size: float) -> Point:
    """The unit normal at ``p`` that points into the ground."""
    left = (-tangent[1], tangent[0])
    eps = 1e-4 * size
    probe = (p[0] + eps * left[0], p[1] + eps * left[1])
    return left if _in_ground(m, probe) else (-left[0], -left[1])


def _span_segments(m: md.Model, span: md.Span) -> tuple[md.Boundary | None, list[int]]:
    b = m.boundary(span.boundary)
    if b is None:
        return None, []
    return b, md.span_indices(b, span) or []


# ------------------------------------------------------------ conditions
@dataclass(frozen=True)
class ConditionMark:
    kind: str                       # x, y, xy, free or displacement
    at: Point
    default: bool = False           # the external's default restraint
    direction: Point | None = None  # an imposed displacement's, as given


def condition_marks(m: md.Model, stage: int = 0) -> list[ConditionMark]:
    out: list[ConditionMark] = []
    covered: set[tuple[str, int]] = set()
    for c in m.conditions:
        if c.kind == md.DISPLACEMENT:
            acts = bool(c.factors) and stage < len(c.factors) and c.factors[stage] is not None
            d = (c.ux or 0.0, c.uy or 0.0)
            direction = d if d != (0.0, 0.0) else None
        else:
            acts = not c.active or (stage < len(c.active) and c.active[stage])
            direction = None
        if c.span is not None:
            b, segs = _span_segments(m, c.span)
            covered.update((c.span.boundary, k) for k in segs)
        if not acts:
            continue
        if c.vertex is not None:
            out.append(ConditionMark(c.kind, tuple(c.vertex), False, direction))
            continue
        for k in segs:
            line = segment_line(b, k)
            out.append(ConditionMark(c.kind, line[0], False, direction))
            out.append(ConditionMark(c.kind, _along(line, 0.5)[0], False, direction))
            out.append(ConditionMark(c.kind, line[-1], False, direction))
    for b in m.boundaries:
        if b.kind != md.EXTERNAL:
            continue
        for k in range(b.n_segments):
            if (b.id, k) not in covered:
                line = segment_line(b, k)
                out.append(ConditionMark(m.default_restraint, _along(line, 0.5)[0], True))
    # one mark per place and kind (the ends of two segments meet)
    seen, unique = set(), []
    for mk in out:
        key = (mk.kind, round(mk.at[0], 9), round(mk.at[1], 9), mk.default)
        if key not in seen:
            seen.add(key)
            unique.append(mk)
    return unique


# ------------------------------------------------------------ loads
@dataclass(frozen=True)
class LoadArrow:
    load: int                       # its index in Model.loads
    tail: Point
    tip: Point


def _direction(orientation: str, angle: float, tangent: Point, normal: Point) -> Point:
    if orientation == md.NORMAL:
        return normal
    if orientation == md.VERTICAL:
        return (0.0, -1.0)
    if orientation == md.HORIZONTAL:
        return (1.0, 0.0)
    a = math.radians(angle)
    if orientation == md.ANGLE_FROM_HORIZONTAL:
        return (math.cos(a), math.sin(a))
    tx, ty = tangent                                   # angle to the boundary
    return (tx * math.cos(a) - ty * math.sin(a), tx * math.sin(a) + ty * math.cos(a))


def load_arrows(m: md.Model, stage: int = 0) -> list[LoadArrow]:
    box = paths.bounds(m)
    if box is None:
        return []
    size = max(box[2] - box[0], box[3] - box[1], 1e-9)
    longest = 0.08 * size

    def factor(ld) -> float:
        return ld.factors[stage] if stage < len(ld.factors) else 1.0

    values = []
    for ld in m.loads:
        f = factor(ld)
        if isinstance(ld, md.PointLoad):
            values.append(abs(f * ld.magnitude))
        else:
            values.append(max(abs(f * ld.start_value), abs(f * ld.end_value)))
    top = max(values, default=0.0)
    if top == 0.0:
        return []
    out: list[LoadArrow] = []

    def arrow(k: int, at: Point, d: Point, value: float) -> None:
        length = longest * abs(value) / top
        if length <= 1e-12 * size:
            return
        sign = 1.0 if value > 0 else -1.0             # a negative one points back
        tail = (at[0] - sign * d[0] * length, at[1] - sign * d[1] * length)
        out.append(LoadArrow(k, tail, at))

    for k, ld in enumerate(m.loads):
        f = factor(ld)
        if isinstance(ld, md.PointLoad):
            d = _direction(ld.orientation, ld.angle, (1.0, 0.0), (0.0, -1.0))
            arrow(k, tuple(ld.vertex), d, f * ld.magnitude)
            continue
        b, segs = _span_segments(m, ld.span)
        lines = [segment_line(b, s) for s in segs]
        total = sum(math.dist(ln[i], ln[i + 1]) for ln in lines for i in range(len(ln) - 1)) or 1.0
        run = 0.0
        for ln in lines:
            seg_len = sum(math.dist(ln[i], ln[i + 1]) for i in range(len(ln) - 1))
            # which side is the ground, found at the middle (at a corner a probe is on
            # the other boundary), then kept along the segment
            mid, mid_tangent = _along(ln, 0.5)
            side = 1.0 if into_ground(m, mid, mid_tangent, size) == (
                -mid_tangent[1], mid_tangent[0]) else -1.0
            for j in range(ARROWS_PER_SEGMENT):
                t = j / (ARROWS_PER_SEGMENT - 1)
                at, tangent = _along(ln, t)
                s = (run + t * seg_len) / total
                value = f * (ld.start_value + s * (ld.end_value - ld.start_value))
                normal = (-side * tangent[1], side * tangent[0])
                arrow(k, at, _direction(ld.orientation, ld.angle, tangent, normal), value)
            run += seg_len
    return out
