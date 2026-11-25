# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
What the canvas draws of a model, as points (spec 006, T21; RF-15), without
Qt: the line of every boundary (its arcs as short chords) and every region
that can be found, with its material and whether it is excavated in the
stage shown.

A model being drawn may not let its regions be found (a crossing, no
external yet): then there are no regions to fill, and the boundaries are
drawn all the same. A region without its material is drawn without fill,
and the canvas says so.

The chords of an arc are for the picture only: every model value, the mesh
and the queries keep the arc itself.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ...model import model as md
from ...model import regions

Point = tuple[float, float]

#: how many chords an arc of a quarter of a circle is drawn with
CHORDS_PER_QUARTER = 16


def arc_points(a: Point, b: Point, c: Point) -> list[Point]:
    """The minor arc from a to b about c, as points (a and b included)."""
    r = math.dist(a, c)
    t0 = math.atan2(a[1] - c[1], a[0] - c[0])
    t1 = math.atan2(b[1] - c[1], b[0] - c[0])
    d = (t1 - t0 + math.pi) % (2.0 * math.pi) - math.pi          # the minor way round
    n = max(2, int(math.ceil(abs(d) / (0.5 * math.pi) * CHORDS_PER_QUARTER)))
    pts = [a]
    for k in range(1, n):
        t = t0 + d * k / n
        pts.append((c[0] + r * math.cos(t), c[1] + r * math.sin(t)))
    pts.append(b)
    return pts


def boundary_line(b: md.Boundary) -> list[Point]:
    """The points of a boundary in order, its arcs as chords; the first
    point again at the end when it is closed."""
    if not b.vertices:
        return []
    out: list[Point] = [b.vertices[0]]
    for k in range(b.n_segments):
        p, q = b.segment(k)
        attr = b.attr(k)
        piece = arc_points(p, q, attr.arc) if attr is not None and attr.arc is not None else [p, q]
        out.extend(piece[1:])
    return out


def _ring(points, segs, ring) -> list[Point]:
    """A ring of point indices as points, its arcs as chords."""
    arcs = {(s.a, s.b): s.arc for s in segs if s.arc is not None}
    out = [points[ring[0]]]
    for k in range(len(ring)):
        i, j = ring[k], ring[(k + 1) % len(ring)]
        c = arcs.get((i, j)) or arcs.get((j, i))
        piece = arc_points(points[i], points[j], c) if c is not None else [points[i], points[j]]
        out.extend(piece[1:])
    return out


@dataclass(frozen=True)
class RegionShape:
    outline: tuple[Point, ...]
    holes: tuple[tuple[Point, ...], ...]
    #: the index of its assignment in the model, or None (no material yet)
    assignment: int | None
    material: str | None
    excavated: bool


def region_shapes(m: md.Model, stage: int = 0) -> list[RegionShape]:
    """The regions of ``m`` that can be found, each with its material and
    whether it is excavated in ``stage`` (empty if the geometry does not
    let them be found)."""
    try:
        points, segs, arcs, rings = regions._rings(m)
    except Exception:                      # a model being drawn: no regions yet
        return []
    from ...mesh import geometry as g
    out = []
    for outline, holes in rings:
        region = g.Region(outline, holes)
        inside = [k for k, a in enumerate(m.assignments)
                  if g._inside_region((float(a.point[0]), float(a.point[1])), region, points, arcs)]
        k = inside[0] if len(inside) == 1 else None
        a = m.assignments[k] if k is not None else None
        exc = bool(a is not None and stage < len(a.excavated) and a.excavated[stage])
        out.append(RegionShape(tuple(_ring(points, segs, outline)),
                               tuple(tuple(_ring(points, segs, h)) for h in holes), k,
                               a.material if a is not None else None, exc))
    return out


def bounds(m: md.Model) -> tuple[float, float, float, float] | None:
    """(xmin, ymin, xmax, ymax) of every boundary drawn, arcs included."""
    pts = [p for b in m.boundaries for p in boundary_line(b)]
    if not pts:
        return None
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


# ------------------------------------------------------------ the field stress
@dataclass(frozen=True)
class FieldMarks:
    """What the canvas draws of the field stress (spec 006, T24; RF-15):
    ``lines`` are polylines in model coordinates. A constant field is a
    block beside the model's top right corner: a square turned by the angle
    of sigma_1, with an arrow on each face, as long as its stress over the
    largest one, pointing in for compression and out for tension. A
    gravitational field is the ground surface and the bottom of each
    stratum, across the model."""
    kind: str                   # "constant" or "gravity"
    lines: tuple
    centre: tuple | None = None


def field_marks(m: md.Model) -> FieldMarks | None:
    box = bounds(m)
    if box is None:
        return None
    x0, y0, x1, y1 = box
    size = max(x1 - x0, y1 - y0, 1e-9)
    f = m.field
    if isinstance(f, md.GravityField):
        a, b = x0 - 0.05 * size, x1 + 0.05 * size
        levels = (f.surface,) + tuple(s.bottom for s in f.strata)
        return FieldMarks("gravity", tuple(((a, y), (b, y)) for y in levels))
    half, longest = 0.04 * size, 0.06 * size
    c = (x1 + 0.15 * size, y1 - 0.1 * size)
    t = math.radians(f.angle)
    e1, e2 = (math.cos(t), math.sin(t)), (-math.sin(t), math.cos(t))
    at = lambda u, v: (c[0] + u * e1[0] + v * e2[0], c[1] + u * e1[1] + v * e2[1])  # noqa: E731
    lines = [(at(-half, -half), at(half, -half), at(half, half), at(-half, half),
              at(-half, -half))]
    top = max(abs(f.sigma_1), abs(f.sigma_3), 1e-300)
    for sigma, axis in ((f.sigma_1, 0), (f.sigma_3, 1)):
        length = longest * abs(sigma) / top
        if length <= 1e-12 * size:
            continue
        head = min(0.3 * length, 0.4 * half)
        for side in (1.0, -1.0):
            def p(along, across, axis=axis, side=side):
                return at(side * along, across) if axis == 0 else at(across, side * along)
            near, far = half, half + length
            tip, tail = (near, far) if sigma > 0 else (far, near)   # compression: inward
            back = tip + head if sigma > 0 else tip - head
            lines.append((p(tail, 0.0), p(tip, 0.0)))
            lines.append((p(back, -0.6 * head), p(tip, 0.0), p(back, 0.6 * head)))
    return FieldMarks("constant", tuple(lines), c)
