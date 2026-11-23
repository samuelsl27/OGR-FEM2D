# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Step 1 of the mesher: the nodes of every segment of the geometry (spec 003,
RF-2, D5 and D10). The result is shown before meshing, and it is what the
refinement receives: every node here is kept (RF-3), and the refinement may
add more on a segment when it must (Shewchuk 2002a, §3.1).

How many divisions a segment gets:

* a forced number (``SegmentSpec.divisions``) is kept (D10);
* an arc gets at least ceil(theta / 60 degrees) divisions in every case, so
  that no piece of it turns more than 60 degrees (D14; Pav and Walkington,
  def. 4); a forced number below that is refused by the input's validation;
* graded mesh (D5): ``boundary_nodes`` is the total number of divisions of
  the segments that take it (the excavation, or the outer boundary when
  there is no excavation; on a closed boundary it is its number of nodes).
  They are shared out in proportion to the length of each segment, at least
  one each, and add up exactly: every segment gets the whole part of its
  share (at least one), and the divisions left go to the largest fractions,
  ties to the segment met first (the largest remainder rule). Every other
  segment enters with its two end points only, and the refinement grades
  from them (spec 003, plan, "Decisiones de diseño");
* uniform mesh (D5): the fewest divisions whose pieces are no longer than
  the size h, ceil(L / h); with an approximate number of elements N instead
  of h, h comes from the area of the equilateral triangle,
  h^2 = 4 A / (sqrt(3) N), A being the area of the meshed domain.

The windows (D9) are not looked at here: they bound the refinement (T11).

Every coordinate and every count here comes from +, -, *, / and sqrt (the
trigonometry of ``_trig``), so the same input gives the same nodes on every
platform (D11).

An arc is divided into equal angles of its minor arc, so every node is on
the circle; a straight segment, into equal lengths. The ends of a segment
are its two input points, shared with the segments that meet there; the new
nodes are added after the input points, segment by segment in the order of
``geometry.segments``, so the same input gives the same points (D11).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from . import _trig
from . import geometry as g


@dataclass(frozen=True)
class DiscreteSegment:
    """A segment and its nodes, as point indices from its ``a`` to its
    ``b`` (both ends included)."""
    segment: g.Segment
    nodes: tuple[int, ...]

    @property
    def divisions(self) -> int:
        return len(self.nodes) - 1


@dataclass(frozen=True)
class Discretization:
    """The points (the input's, in their order, then the new nodes) and the
    nodes of every segment. ``size`` is the h of a uniform mesh, which
    changes the result and goes with it (rule 12); None for a graded one."""
    points: tuple[g.Point, ...]
    segments: tuple[DiscreteSegment, ...]
    size: float | None


def segment_length(m: g.MeshInput, s: g.Segment) -> float:
    """The length of a segment: its chord, or R theta for an arc."""
    a, b = m.points[s.a], m.points[s.b]
    if s.arc is None:
        return _trig.length(a, b)
    geo = g._ArcGeo(a, b, s.arc.centre)
    return geo.r * geo.theta


def share_out(total: int, lengths: list[float], minimums: list[int] | None = None
              ) -> list[int]:
    """``total`` divisions in proportion to ``lengths``, at least
    ``minimums`` each (one by default), adding up exactly (the largest
    remainder rule; ties to the first)."""
    minimums = minimums or [1] * len(lengths)
    if total < sum(minimums):
        raise ValueError(f"{total} divisions for segments that need {sum(minimums)}")
    whole = sum(lengths)
    ideal = [total * length / whole for length in lengths]
    counts = [max(least, math.floor(x)) for least, x in zip(minimums, ideal)]
    left = total - sum(counts)
    if left > 0:
        order = sorted(range(len(ideal)), key=lambda k: (-(ideal[k] - counts[k]), k))
        for k in order[:left]:
            counts[k] += 1
    while left < 0:
        # the minimum of one pushed the sum over: take back from the largest
        # excess over the ideal share, among those above one
        k = max((k for k in range(len(counts)) if counts[k] > minimums[k]),
                key=lambda k: (counts[k] - ideal[k], -k))
        counts[k] -= 1
        left += 1
    return counts


def uniform_size(m: g.MeshInput) -> float:
    """The h of a uniform mesh: the one given, or the one of N equilateral
    triangles covering the meshed domain."""
    st = m.settings
    if st.size is not None:
        return float(st.size)
    area = sum(g.region_area(m, r) for r in range(len(m.regions)))
    return math.sqrt(4.0 * area / (math.sqrt(3.0) * st.elements))


def divisions(m: g.MeshInput) -> tuple[tuple[g.Segment, int], ...]:
    """Every segment of a valid input with its number of divisions."""
    segs = g.segments(m)
    st = m.settings
    count: dict[int, int] = {}
    if st.kind == g.GRADED:
        targets = g.graded_targets(segs)
        if targets:
            shares = share_out(st.boundary_nodes,
                               [segment_length(m, s) for s in targets],
                               [g.minimum_divisions(m, s) for s in targets])
            ids = {id(s): k for k, s in enumerate(targets)}
            for k, s in enumerate(segs):
                if id(s) in ids:
                    count[k] = shares[ids[id(s)]]
        for k, s in enumerate(segs):
            count.setdefault(k, s.divisions if s.divisions is not None
                             else g.minimum_divisions(m, s))
    else:
        h = uniform_size(m)
        for k, s in enumerate(segs):
            count[k] = (s.divisions if s.divisions is not None
                        else max(g.minimum_divisions(m, s),
                                 math.ceil(segment_length(m, s) / h)))
    return tuple((s, count[k]) for k, s in enumerate(segs))


def _arc_points(a: g.Point, b: g.Point, c: g.Point, n: int) -> list[g.Point]:
    """The n - 1 inner nodes of the minor arc from a to b about c, at equal
    angles."""
    r = 0.5 * (_trig.length(a, c) + _trig.length(b, c))
    ua = (a[0] - c[0], a[1] - c[1])
    ub = (b[0] - c[0], b[1] - c[1])
    start = _trig.atan2(ua[1], ua[0])
    sweep = _trig.atan2(ua[0] * ub[1] - ua[1] * ub[0], ua[0] * ub[0] + ua[1] * ub[1])
    out = []
    for k in range(1, n):
        s, co = _trig.sin_cos(start + k * sweep / n)
        out.append((c[0] + r * co, c[1] + r * s))
    return out


def _line_points(a: g.Point, b: g.Point, n: int) -> list[g.Point]:
    return [(a[0] + k / n * (b[0] - a[0]), a[1] + k / n * (b[1] - a[1]))
            for k in range(1, n)]


def discretize(m: g.MeshInput) -> Discretization:
    """Step 1 (spec 003, RF-2): validates the input and returns the nodes of
    every segment."""
    g.validate(m)
    points = list(m.points)
    out = []
    for s, n in divisions(m):
        a, b = m.points[s.a], m.points[s.b]
        inner = (_line_points(a, b, n) if s.arc is None
                 else _arc_points(a, b, s.arc.centre, n))
        ids = list(range(len(points), len(points) + len(inner)))
        points.extend(inner)
        out.append(DiscreteSegment(s, (s.a, *ids, s.b)))
    size = uniform_size(m) if m.settings.kind == g.UNIFORM else None
    return Discretization(tuple(points), tuple(out), size)
