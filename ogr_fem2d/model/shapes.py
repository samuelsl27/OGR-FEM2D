# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Arcs and circles as the segments of a boundary (spec 006, RF-3, D10).

A segment of a boundary is straight or the MINOR arc about its centre (spec
004, D2; spec 003, D3 and D4): the arc between its two ends that is less
than half a circle. So an arc of half a circle or more is drawn as two
segments, split at its middle, and a circle as four arcs of 90°, its
vertices at 0°, 90°, 180° and 270° from the start (by default, from +x: the
hole of case 005 is drawn so).

* ``arc_three_points(start, through, end)``: the arc from ``start`` through
  ``through`` to ``end``, about the circle through the three;
* ``arc_by_angle(start, centre, angle)``: from ``start`` about ``centre``,
  turning ``angle`` degrees (positive anticlockwise);
* ``arc_by_centre(start, centre, end, anticlockwise)``: from ``start`` to
  ``end`` about ``centre``, the way asked;
* ``circle(centre, radius)`` and ``circle_through(centre, point)``.

An arc is a ``Piece``: the vertices it adds after its start and its centre.
``Drawn`` puts straight lines and pieces together into a boundary being
drawn, with the segment attributes ``edit.add_boundary`` takes.

The arithmetic is elementary analytic geometry (the circle through three
points, a point turned about a centre), with no source to cite; the tests
check it by identities: every vertex on its circle, the area of a circle of
four arcs equal to pi r^2 through the model's own region areas.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

from ..engine.model import Problem
from ..mesh import geometry as g
from . import model as md

Point = tuple[float, float]

#: An arc turning this close to half a circle, or more, is split in two:
#: the minor arc of a segment must have its centre off the chord by more
#: than the model's tolerance (rule ``arc``), and a margin of a micro-radian
#: keeps it well clear of it.
HALF_TURN_MARGIN = 1e-6


def _fail(where: str, message: str):
    raise md.ModelError([Problem("arc", where, message)])


def _pt(p) -> Point:
    return (float(p[0]), float(p[1]))


@dataclass(frozen=True)
class Piece:
    """An arc: the vertices it adds after its start (its end last) and its
    centre, which every segment of it has."""
    vertices: tuple[Point, ...]
    centre: Point


def _turned(start: Point, centre: Point, angle: float) -> Point:
    """``start`` turned ``angle`` radians about ``centre``. A cosine or sine
    within 1e-15 of 0 is 0 (cos(pi/2) is 6e-17 in floating point), so a
    quarter or half turn puts its vertex where it is drawn."""
    c, s = math.cos(angle), math.sin(angle)
    c, s = (0.0 if abs(c) < 1e-15 else c), (0.0 if abs(s) < 1e-15 else s)
    dx, dy = start[0] - centre[0], start[1] - centre[1]
    return (centre[0] + c * dx - s * dy, centre[1] + s * dx + c * dy)


def _piece(start: Point, centre: Point, sweep: float, end: Point) -> Piece:
    """The arc from ``start`` turning ``sweep`` radians (signed) about
    ``centre`` to ``end``: one segment, or two split at its middle when it
    turns half a circle or more."""
    if abs(sweep) < math.pi - HALF_TURN_MARGIN:
        return Piece((end,), centre)
    return Piece((_turned(start, centre, 0.5 * sweep), end), centre)


def arc_by_angle(start, centre, angle: float) -> Piece:
    """From ``start`` about ``centre``, turning ``angle`` degrees (positive
    anticlockwise), less than a whole turn."""
    a, c = _pt(start), _pt(centre)
    where = f"arc from {a} about {c}"
    if not (md._finite(*a, *c, angle)):
        _fail(where, "the points and the angle must be finite")
    if a == c:
        _fail(where, "the start is the centre: the radius is zero")
    if not 0.0 < abs(angle) < 360.0:
        _fail(where, f"the angle {angle!r} must be between 0 and 360 degrees, either way "
                     "(a whole circle is a circle)")
    sweep = math.radians(angle)
    return _piece(a, c, sweep, _turned(a, c, sweep))


def arc_by_centre(start, centre, end, anticlockwise: bool = True) -> Piece:
    """From ``start`` to ``end`` about ``centre``, anticlockwise or
    clockwise. ``end`` must be on the circle of ``start`` (to the model's
    tolerance); it is taken as given, exactly."""
    a, c, b = _pt(start), _pt(centre), _pt(end)
    where = f"arc from {a} to {b} about {c}"
    if not md._finite(*a, *b, *c):
        _fail(where, "the points must be finite")
    ra, rb = math.dist(a, c), math.dist(b, c)
    if ra == 0.0 or a == b:
        _fail(where, "the radius is zero, or the start is the end")
    if abs(ra - rb) > g.ARC_TOL * max(ra, rb):
        _fail(where, f"the end is at {rb!r} from the centre and the start at {ra!r}: not on "
                     "one circle")
    turn = math.atan2(b[1] - c[1], b[0] - c[0]) - math.atan2(a[1] - c[1], a[0] - c[0])
    if anticlockwise:
        sweep = turn % (2.0 * math.pi)
    else:
        sweep = -((-turn) % (2.0 * math.pi))
    return _piece(a, c, sweep, b)


def arc_three_points(start, through, end) -> Piece:
    """The arc from ``start`` through ``through`` to ``end``, about the
    circle through the three. Refused if they are on one line."""
    a, p, b = _pt(start), _pt(through), _pt(end)
    where = f"arc through {a}, {p} and {b}"
    if not md._finite(*a, *p, *b):
        _fail(where, "the points must be finite")
    if len({a, p, b}) < 3:
        _fail(where, "two of the points are the same")
    # the circumcentre: equidistant from the three
    d = 2.0 * (a[0] * (p[1] - b[1]) + p[0] * (b[1] - a[1]) + b[0] * (a[1] - p[1]))
    size = max(math.dist(a, p), math.dist(p, b), math.dist(a, b))
    if abs(d) <= 1e-12 * size * size:
        _fail(where, "the three points are on one line: there is no circle through them")
    na, np_, nb = a[0] ** 2 + a[1] ** 2, p[0] ** 2 + p[1] ** 2, b[0] ** 2 + b[1] ** 2
    c = ((na * (p[1] - b[1]) + np_ * (b[1] - a[1]) + nb * (a[1] - p[1])) / d,
         (na * (b[0] - p[0]) + np_ * (a[0] - b[0]) + nb * (p[0] - a[0])) / d)
    # the way round is the one that passes through ``through``: anticlockwise
    # when a, p, b turn left
    return arc_by_centre(a, c, b, anticlockwise=d > 0.0)


def circle(centre, radius: float, start_angle: float = 0.0) -> tuple[tuple[Point, ...],
                                                                       tuple[md.SegmentAttr, ...]]:
    """A circle as four arcs of 90°, anticlockwise from ``start_angle``
    degrees: its vertices and its segment attributes, for a closed
    boundary. At the default start the vertices are exact: the centre plus
    (r, 0), (0, r), (-r, 0), (0, -r)."""
    c = _pt(centre)
    if not (md._finite(*c, radius, start_angle) and radius > 0.0):
        _fail(f"circle about {c}", f"the radius {radius!r} must be > 0 and finite")
    r = float(radius)
    if start_angle == 0.0:
        offsets = ((r, 0.0), (0.0, r), (-r, 0.0), (0.0, -r))
        vertices = tuple((c[0] + dx, c[1] + dy) for dx, dy in offsets)
    else:
        first = _turned((c[0] + r, c[1]), c, math.radians(start_angle))
        vertices = tuple(_turned(first, c, 0.5 * math.pi * k) for k in range(4))
    return vertices, tuple(md.SegmentAttr(k, c) for k in range(4))


def circle_through(centre, point) -> tuple[tuple[Point, ...], tuple[md.SegmentAttr, ...]]:
    """The circle about ``centre`` through ``point``, its first vertex at
    ``point``."""
    c, p = _pt(centre), _pt(point)
    angle = math.degrees(math.atan2(p[1] - c[1], p[0] - c[0]))
    vertices, segments = circle(c, math.dist(c, p), angle)
    return (p,) + vertices[1:], segments


@dataclass(frozen=True)
class Drawn:
    """A boundary being drawn: its vertices, the attributes of its arc
    segments, and whether an arc has closed it on its first vertex."""
    vertices: tuple[Point, ...]
    segments: tuple[md.SegmentAttr, ...] = ()
    closed: bool = False

    @staticmethod
    def start(point) -> "Drawn":
        return Drawn((_pt(point),))

    def line_to(self, point) -> "Drawn":
        return replace(self, vertices=self.vertices + (_pt(point),))

    def arc_to(self, piece: Piece) -> "Drawn":
        """The arc's vertices after the last one, each segment about its
        centre. An arc that ends on the first vertex closes the boundary."""
        vertices, segments, closed = list(self.vertices), list(self.segments), self.closed
        for k, v in enumerate(piece.vertices):
            last = k == len(piece.vertices) - 1
            segments.append(md.SegmentAttr(len(vertices) - 1, piece.centre))
            if last and v == vertices[0] and len(vertices) > 1:
                closed = True
            else:
                vertices.append(v)
        return Drawn(tuple(vertices), tuple(segments), closed)
