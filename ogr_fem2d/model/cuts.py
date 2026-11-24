# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The cuts between boundaries (spec 006, RF-2; spec 004, D15).

Boundaries meet only at the vertices they share. When a boundary is drawn or
moved across others, ``cut(m, boundary_id)`` puts a vertex wherever it meets
them away from a vertex they share, in both, as the reference program does,
and says which:

* where two segments cross, a new vertex in both;
* where an end of one lies on the other (a T), that end goes into the other;
* where they meet at a vertex both already have, nothing.

Straight with straight, straight with an arc and arc with arc: the arc is
the minor arc of its segment, about its centre (spec 003, D3 and D4), and a
vertex put on it splits it in two arcs about the same centre
(``edit.insert_vertex``). Two segments that run along each other for a
stretch without being the same side are an error that names both: that is
not a cut, and which of them should give way is the engineer's to say.

A meeting point within the geometric tolerance of the mesher (``ARC_TOL`` of
the size of the model) of a vertex of either segment is that vertex: a cut
never puts a second vertex next to one there is.

The arithmetic is elementary analytic geometry (a line with a line, with a
circle; a circle with a circle), with no source to cite; the tests check it
by identities: every point put is on both segments.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ..engine.model import Problem
from ..mesh import geometry as g
from ..mesh import _trig
from . import edit
from . import model as md

Point = tuple[float, float]

RULES = ("overlap",)


@dataclass(frozen=True)
class Cut:
    """The model with its cuts, and every vertex put: (boundary id, point),
    in the order they went in."""
    model: md.Model
    added: tuple[tuple[str, Point], ...]


@dataclass(frozen=True)
class _Seg:
    """A segment of a boundary, ready for the intersections."""
    boundary: str
    index: int
    a: Point
    b: Point
    arc: g._ArcGeo | None

    @property
    def ends(self) -> tuple[Point, Point]:
        return (self.a, self.b)


def _segs(b: md.Boundary) -> list[_Seg]:
    out = []
    for k in range(b.n_segments):
        p, q = (edit._pt(v) for v in b.segment(k))
        attr = b.attr(k)
        arc = g._ArcGeo(p, q, edit._pt(attr.arc)) if attr is not None and attr.arc is not None \
            else None
        out.append(_Seg(b.id, k, p, q, arc))
    return out


def _on_closed(s: _Seg, p: Point, tol: float) -> bool:
    """A point already on the line or circle of ``s`` lies on ``s``, its
    ends included."""
    if min(_trig.length(p, s.a), _trig.length(p, s.b)) <= tol:
        return True
    if s.arc is not None:
        return s.arc.on_open_arc(p, tol)
    ab = _trig.length(s.a, s.b)
    t = ((p[0] - s.a[0]) * (s.b[0] - s.a[0]) + (p[1] - s.a[1]) * (s.b[1] - s.a[1])) / (ab * ab)
    return 0.0 <= t <= 1.0


def _line_line(u: _Seg, v: _Seg) -> list[Point]:
    d1 = (u.b[0] - u.a[0], u.b[1] - u.a[1])
    d2 = (v.b[0] - v.a[0], v.b[1] - v.a[1])
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if den == 0.0 or abs(den) <= 1e-14 * _trig.norm(*d1) * _trig.norm(*d2):
        return []                         # parallel: a common stretch is an overlap
    w = (v.a[0] - u.a[0], v.a[1] - u.a[1])
    t = (w[0] * d2[1] - w[1] * d2[0]) / den
    return [(u.a[0] + t * d1[0], u.a[1] + t * d1[1])]


def _line_circle(s: _Seg, c: Point, r: float) -> list[Point]:
    dx, dy = s.b[0] - s.a[0], s.b[1] - s.a[1]
    fx, fy = s.a[0] - c[0], s.a[1] - c[1]
    aa = dx * dx + dy * dy
    bb = dx * fx + dy * fy
    cc = fx * fx + fy * fy - r * r
    disc = bb * bb - aa * cc
    if disc < 0.0:
        if disc < -1e-12 * aa * r * r:
            return []
        disc = 0.0                        # tangent, to rounding
    root = math.sqrt(disc)
    return [(s.a[0] + t * dx, s.a[1] + t * dy) for t in ((-bb - root) / aa, (-bb + root) / aa)]


def _circle_circle(c1: Point, r1: float, c2: Point, r2: float) -> list[Point]:
    d = _trig.length(c1, c2)
    if d == 0.0 or d > r1 + r2 or d < abs(r1 - r2):
        return []
    a = (r1 * r1 - r2 * r2 + d * d) / (2.0 * d)
    h = math.sqrt(max(0.0, r1 * r1 - a * a))
    ex, ey = (c2[0] - c1[0]) / d, (c2[1] - c1[1]) / d
    bx, by = c1[0] + a * ex, c1[1] + a * ey
    return [(bx - s * h * ey, by + s * h * ex) for s in (-1.0, 1.0)]


def _meetings(u: _Seg, v: _Seg, tol: float) -> list[Point]:
    """Where segments u and v meet (on both, ends included)."""
    if u.arc is None and v.arc is None:
        pts = _line_line(u, v)
    elif u.arc is not None and v.arc is not None:
        pts = _circle_circle(u.arc.c, u.arc.r, v.arc.c, v.arc.r)
    elif u.arc is not None:
        pts = _line_circle(v, u.arc.c, u.arc.r)
    else:
        pts = _line_circle(u, v.arc.c, v.arc.r)
    return [p for p in pts if _on_closed(u, p, tol) and _on_closed(v, p, tol)]


def _snap(p: Point, u: _Seg, v: _Seg, tol: float) -> Point:
    """A meeting point next to a vertex of either segment is that vertex."""
    for e in u.ends + v.ends:
        if _trig.length(p, e) <= tol:
            return e
    return p


def _same_side(u: _Seg, v: _Seg) -> bool:
    return set(u.ends) == set(v.ends)


def _overlap(u: _Seg, v: _Seg, tol: float) -> bool:
    """u and v run along each other for a stretch."""
    if (u.arc is None) != (v.arc is None):
        return False
    if u.arc is None:
        ab = _trig.length(u.a, u.b)
        if any(abs(g._cross(u.a, u.b, p)) > tol * ab for p in v.ends):
            return False                   # not on one line
        dx, dy = (u.b[0] - u.a[0]) / ab, (u.b[1] - u.a[1]) / ab
        s = sorted(((p[0] - u.a[0]) * dx + (p[1] - u.a[1]) * dy) for p in v.ends)
        return min(ab, s[1]) - max(0.0, s[0]) > tol
    if _trig.length(u.arc.c, v.arc.c) > tol or abs(u.arc.r - v.arc.r) > tol:
        return False                       # not on one circle
    return (u.arc.on_open_arc(v.a, tol) or u.arc.on_open_arc(v.b, tol)
            or v.arc.on_open_arc(u.a, tol) or v.arc.on_open_arc(u.b, tol)
            or _trig.length(u.arc.mid, v.arc.mid) <= tol)


def _pairs(m: md.Model, boundary_id: str):
    target = edit._boundary(m, boundary_id)
    for u in _segs(target):
        for x in m.boundaries:
            if x.id == boundary_id:
                continue
            for v in _segs(x):
                if not _same_side(u, v):
                    yield u, v


def _first(m: md.Model, boundary_id: str, tol: float):
    """The first vertex to put: (boundary, segment, point), or None."""
    for u, v in _pairs(m, boundary_id):
        for p in _meetings(u, v, tol):
            p = _snap(p, u, v, tol)
            if p not in u.ends:
                return u.boundary, u.index, p
            if p not in v.ends:
                return v.boundary, v.index, p
    return None


def cut(m: md.Model, boundary_id: str) -> Cut:
    """``m`` with a vertex wherever boundary ``boundary_id`` meets another
    away from a vertex they share, in both (see the module's notes).
    Refused, naming both, where two segments run along each other; and as
    ``edit.insert_vertex`` refuses (a side with forced divisions)."""
    tol = g.ARC_TOL * edit._scale(m)
    for u, v in _pairs(m, boundary_id):
        if _overlap(u, v, tol):
            raise md.ModelError([Problem(
                "overlap", f"segment {u.index} of boundary {u.boundary!r} and segment {v.index} "
                           f"of boundary {v.boundary!r}",
                "run along each other without being the same side: give them the same vertices, "
                "or move one (a stretch in common is not a cut)")])
    added: list[tuple[str, Point]] = []
    for _ in range(10_000):
        hit = _first(m, boundary_id, tol)
        if hit is None:
            return Cut(m, tuple(added))
        bid, k, p = hit
        before = {b.id for b in m.boundaries if p in b.vertices}
        m = edit.insert_vertex(m, bid, k, p)
        added.extend((b.id, p) for b in m.boundaries if p in b.vertices and b.id not in before)
    raise RuntimeError("the cuts did not end")             # pragma: no cover
