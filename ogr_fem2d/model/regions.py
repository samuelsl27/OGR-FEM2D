# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
From the boundaries of a model to its regions (spec 004, RF-1, D15).

Boundaries meet only at vertices they share (D15: the cuts are the
interface's to put, spec 006, as the reference program adds the vertex of an
intersection). Then:

1. **points**: every vertex, once, in the order of the boundaries of the
   model and of their vertices;
2. **segments**: every side of every boundary, once; the same side in two
   boundaries is one segment, and with different arcs or divisions it is an
   error that names both. A side of an excavation boundary is marked for
   the graded mesh (spec 003, D5);
3. **crossings**: two segments that meet away from a point they share are
   an error that names both (the predicates of ``mesh.geometry``: exact for
   straight segments, analytic for arcs);
4. **faces**: the faces of the planar graph of the segments, walking every
   half-edge with the face on its left and taking at each vertex the next
   side clockwise from the one it came by (the doubly connected edge list
   of de Berg, Cheong, van Kreveld and Overmars 2008, *Computational
   Geometry*, 3rd ed., ch. 2; not in the bibliography: an algorithm, not a
   formula, checked by the identities of area and of Euler in the tests).
   At an arc the direction leaving a vertex is its tangent there, and two
   sides leaving with the same tangent are ordered by their curvature. A
   walk that passes a vertex twice (regions that touch at a point) is split
   there into simple rings. A side with the same walk on both of its sides
   is a loose end: an error;
5. **regions**: every ring going anticlockwise is the outline of a region;
   the clockwise ones are holes: of the same face, when they came from
   splitting it, or the outer ring of a separate group of boundaries, a
   hole of the smallest region of another group that holds it. The one
   group nothing holds is the external boundary's, and its outer ring must
   be exactly the external boundary;
6. **assignments**: every region holds exactly one assignment point
   (D15: no region takes a material by default).

The order is canonical (D11 of spec 003, and the key of case 005): the
points as above; every ring starting at its smallest point index; the
regions by their outline, the holes by theirs, as tuples. The same model
gives the same geometry, bit for bit.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ..engine.model import Problem
from ..mesh import geometry as g
from ..mesh import _trig
from . import model as md

Point = tuple[float, float]

RULES = ("arc", "segment_conflict", "crossing", "dangling", "outside_external",
         "region_unassigned", "region_twice", "assignment_outside")


@dataclass(frozen=True)
class Seg:
    """A segment of the geometry: its two points (in the direction of the
    first boundary that has it), its arc and divisions, whether it bounds an
    excavation, and where it comes from: (boundary id, segment index)."""
    a: int
    b: int
    arc: Point | None
    divisions: int | None
    excavation: bool
    origin: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class Region:
    """A region: its outline (anticlockwise) and holes (clockwise), as point
    indices, and the index of its assignment in the model."""
    outline: tuple[int, ...]
    holes: tuple[tuple[int, ...], ...]
    assignment: int


@dataclass(frozen=True)
class Geometry:
    points: tuple[Point, ...]
    segments: tuple[Seg, ...]
    regions: tuple[Region, ...]

    def segment_index(self, i: int, j: int) -> int:
        for k, s in enumerate(self.segments):
            if (s.a, s.b) in ((i, j), (j, i)):
                return k
        raise KeyError((i, j))


class _Fail(Exception):
    """Problems found that stop the later steps."""

    def __init__(self, problems):
        self.problems = problems


def _seg_name(s: Seg) -> str:
    return " = ".join(f"segment {k} of boundary {b!r}" for b, k in s.origin)


# ---------------------------------------------------------- points, segments
def _points_and_segments(m: md.Model):
    index: dict[Point, int] = {}
    points: list[Point] = []
    for b in m.boundaries:
        for v in b.vertices:
            key = (float(v[0]), float(v[1]))
            if key not in index:
                index[key] = len(points)
                points.append(key)
    found: dict[tuple[int, int], dict] = {}
    order: list[tuple[int, int]] = []
    problems = []
    for b in m.boundaries:
        for k in range(b.n_segments):
            p, q = b.segment(k)
            i, j = index[(float(p[0]), float(p[1]))], index[(float(q[0]), float(q[1]))]
            key = (min(i, j), max(i, j))
            attr = b.attr(k)
            arc = attr.arc if attr is not None else None
            div = attr.divisions if attr is not None else None
            if arc is not None:
                arc = (float(arc[0]), float(arc[1]))
            if key not in found:
                found[key] = {"a": i, "b": j, "arc": arc, "div": div,
                              "exc": b.kind == md.EXCAVATION, "origin": [(b.id, k)]}
                order.append(key)
                continue
            s = found[key]
            first = f"segment {s['origin'][0][1]} of boundary {s['origin'][0][0]!r}"
            if s["arc"] != arc:
                problems.append(Problem(
                    "segment_conflict", f"segment {k} of boundary {b.id!r} and {first}",
                    f"the same side, one with arc {s['arc']} and the other with {arc}"))
            if div is not None and s["div"] is not None and div != s["div"]:
                problems.append(Problem(
                    "segment_conflict", f"segment {k} of boundary {b.id!r} and {first}",
                    f"the same side, with {s['div']} and {div} divisions"))
            if s["div"] is None:
                s["div"] = div
            s["exc"] = s["exc"] or b.kind == md.EXCAVATION
            s["origin"].append((b.id, k))
    segs = tuple(Seg(found[k]["a"], found[k]["b"], found[k]["arc"], found[k]["div"],
                     found[k]["exc"], tuple(found[k]["origin"])) for k in order)
    return tuple(points), segs, problems


def _scale(points) -> float:
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return _trig.norm(max(xs) - min(xs), max(ys) - min(ys)) or 1.0


def _arcs(points, segs) -> dict:
    """The arc of every segment that has one, keyed as ``mesh.geometry``."""
    return {g._key(s.a, s.b): g._ArcGeo(points[s.a], points[s.b], s.arc)
            for s in segs if s.arc is not None}


def _arc_problems(points, segs) -> list[Problem]:
    """An arc whose points are not on one circle about its centre, or whose
    centre is on its chord (half a circle or more: spec 003, D4)."""
    out = []
    scale = _scale(points)
    for s in segs:
        if s.arc is None:
            continue
        a, b, c = points[s.a], points[s.b], s.arc
        ra, rb = _trig.length(a, c), _trig.length(b, c)
        if abs(ra - rb) > g.ARC_TOL * max(ra, rb, scale):
            out.append(Problem("arc", _seg_name(s),
                               f"its points are at {ra!r} and {rb!r} from the centre {c}: "
                               "not on one circle"))
        elif abs(g._cross(a, b, c)) <= g.ARC_TOL * scale * _trig.length(a, b):
            out.append(Problem("arc", _seg_name(s),
                               "the centre is on the chord: half a circle or more must be "
                               "split by a vertex (spec 003, D4)"))
    return out


def _crossing_problems(points, segs) -> list[Problem]:
    arcs = _arcs(points, segs)
    tol = g.ARC_TOL * _scale(points)
    out = []
    keys = [g._key(s.a, s.b) for s in segs]
    for x, e in enumerate(keys):
        for y in range(x + 1, len(keys)):
            f = keys[y]
            ge, gf = arcs.get(e), arcs.get(f)
            if ge is None and gf is None:
                hit = g._straight_meet(e, f, points)
            elif ge is not None and gf is not None:
                hit = g._arc_meets_arc(ge, gf, tol)
            elif ge is not None:
                hit = g._arc_meets_straight(ge, points[f[0]], points[f[1]], tol)
            else:
                hit = g._arc_meets_straight(gf, points[e[0]], points[e[1]], tol)
            if hit:
                out.append(Problem(
                    "crossing", f"{_seg_name(segs[x])} and {_seg_name(segs[y])}",
                    "meet away from a vertex they share: boundaries meet only at shared "
                    "vertices (D15; put a vertex where they cross)"))
    return out


# ------------------------------------------------------------------ faces
def _departure(points, s: Seg, forward: bool) -> tuple[float, float]:
    """(angle, signed curvature) of segment s leaving its start (a if
    forward, else b): for an arc, the tangent there, and +1/R when it bends
    to the left of that direction, -1/R to the right."""
    u, v = (points[s.a], points[s.b]) if forward else (points[s.b], points[s.a])
    # + 0.0 turns a -0.0 into 0.0: atan2(-0.0, -1) is -pi, and a side going
    # left would sort first instead of last
    if s.arc is None:
        return math.atan2(v[1] - u[1] + 0.0, v[0] - u[0] + 0.0), 0.0
    c = s.arc
    rx, ry = u[0] - c[0], u[1] - c[1]
    ccw = g._cross(c, u, v) > 0.0          # the minor arc from u to v goes anticlockwise
    tx, ty = (-ry, rx) if ccw else (ry, -rx)
    r = math.hypot(rx, ry)
    return math.atan2(ty + 0.0, tx + 0.0), (1.0 / r if ccw else -1.0 / r)


def _walks(points, segs):
    """Every closed walk of half-edges, the face on its left: lists of
    half-edges (2k is segment k from a to b, 2k + 1 from b to a)."""
    out_of: dict[int, list] = {}
    for k, s in enumerate(segs):
        out_of.setdefault(s.a, []).append((_departure(points, s, True), 2 * k))
        out_of.setdefault(s.b, []).append((_departure(points, s, False), 2 * k + 1))
    ordered = {v: [h for _key, h in sorted(lst)] for v, lst in out_of.items()}
    position = {h: (v, i) for v, lst in ordered.items() for i, h in enumerate(lst)}

    def dest(h):
        s = segs[h // 2]
        return s.b if h % 2 == 0 else s.a

    def nxt(h):
        twin = h ^ 1
        v, i = position[twin]
        lst = ordered[v]
        return lst[(i - 1) % len(lst)]

    seen = set()
    walks = []
    for h0 in range(2 * len(segs)):
        if h0 in seen:
            continue
        walk, h = [], h0
        while h not in seen:
            seen.add(h)
            walk.append(h)
            h = nxt(h)
        walks.append(walk)
    return walks, dest


def _origin(segs, h) -> int:
    s = segs[h // 2]
    return s.a if h % 2 == 0 else s.b


def _split(ring: list[int]) -> list[list[int]]:
    """A ring of points that passes a point more than once, split there
    into simple rings."""
    out, stack, pos = [], [], {}
    for p in ring:
        if p in pos:
            start = pos[p]
            loop = stack[start:]
            out.append(loop)
            for q in loop[1:]:
                pos.pop(q, None)
            del stack[start + 1:]
        else:
            pos[p] = len(stack)
            stack.append(p)
    out.append(stack)
    return [r for r in out if len(r) >= 2]


def _rotate(ring) -> tuple[int, ...]:
    k = ring.index(min(ring))
    return tuple(ring[k:]) + tuple(ring[:k])


def _components(segs) -> dict[int, int]:
    """The group of boundaries every point belongs to (connected by
    segments)."""
    parent: dict[int, int] = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for s in segs:
        ra, rb = find(s.a), find(s.b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    return {p: find(p) for p in list(parent)}


def _faces(m: md.Model, points, segs):
    arcs = _arcs(points, segs)
    walks, _dest = _walks(points, segs)
    problems = []
    walk_of = {}
    for w, walk in enumerate(walks):
        for h in walk:
            walk_of[h] = w
    for k, s in enumerate(segs):
        if walk_of[2 * k] == walk_of[2 * k + 1]:
            problems.append(Problem(
                "dangling", _seg_name(s),
                "has the same region on both sides: a loose end of an open boundary, or a "
                "boundary that bounds nothing (D15)"))
    if problems:
        raise _Fail(problems)
    comp = _components(segs)
    outlines, holes = [], []          # (ring, area, component); holes: (ring, owner or None)
    for walk in walks:
        ring = [_origin(segs, h) for h in walk]
        pieces = _split(ring)
        areas = [g._ring_area(tuple(r), points, arcs) for r in pieces]
        positive = [(r, a) for r, a in zip(pieces, areas) if a > 0.0]
        negative = [(r, a) for r, a in zip(pieces, areas) if a <= 0.0]
        c = comp[ring[0]]
        if len(positive) == 1:
            owner = len(outlines)
            outlines.append((tuple(positive[0][0]), positive[0][1], c))
            for r, _a in negative:
                holes.append((tuple(r), owner, c))
        else:
            for r, _a in positive:
                outlines.append((tuple(r), _a, c))
            for r, _a in negative:
                holes.append((tuple(r), None, c))
    # the outer ring of every group: a hole of the smallest outline of
    # another group that holds it, or the outside of everything
    region_holes: dict[int, list] = {i: [] for i in range(len(outlines))}
    unbounded = []
    for ring, owner, c in holes:
        if owner is not None:
            region_holes[owner].append(ring)
            continue
        p = g._edge_midpoint(ring[0], ring[1], points, arcs)
        best = None
        for i, (outline, area, oc) in enumerate(outlines):
            if oc == c:
                continue
            if g._winding(p, outline, points, arcs) != 0 and (best is None or area < outlines[best][1]):
                best = i
        if best is None:
            unbounded.append(ring)
        else:
            region_holes[best].append(ring)
    external = [b for b in m.boundaries if b.kind == md.EXTERNAL][0]
    ext_segments = {k for k, s in enumerate(segs) if any(b == external.id for b, _k in s.origin)}
    problems = []
    if len(unbounded) != 1:
        problems.append(Problem("outside_external", "model",
                                f"{len(unbounded)} groups of boundaries lie apart from each "
                                "other: every boundary must be inside the external one"))
    else:
        ring = unbounded[0]
        on_outside = {_seg_of(segs, ring[i], ring[(i + 1) % len(ring)])
                      for i in range(len(ring))}
        for k in sorted(on_outside - ext_segments):
            problems.append(Problem("outside_external", _seg_name(segs[k]),
                                    "lies on the outside of the model: every boundary must be "
                                    "inside the external one"))
        for k in sorted(ext_segments - on_outside):
            problems.append(Problem("outside_external", _seg_name(segs[k]),
                                    "the external boundary has a side inside the model"))
    if problems:
        raise _Fail(problems)
    return [(o[0], region_holes[i]) for i, o in enumerate(outlines)], arcs


def _seg_of(segs, i, j) -> int:
    for k, s in enumerate(segs):
        if (s.a, s.b) in ((i, j), (j, i)):
            return k
    raise KeyError((i, j))


# --------------------------------------------------------------- the build
def _rings(m: md.Model):
    """Steps 1 to 5: the points, the segments, the arcs and the rings of
    every region (outline, holes), in the canonical order."""
    points, segs, problems = _points_and_segments(m)
    problems += _arc_problems(points, segs)
    if problems:
        raise _Fail(problems)
    problems = _crossing_problems(points, segs)
    if problems:
        raise _Fail(problems)
    faces, arcs = _faces(m, points, segs)
    rings = sorted((_rotate(list(o)), tuple(sorted(_rotate(list(h)) for h in hs)))
                   for o, hs in faces)
    return points, segs, arcs, rings


def region_of(m: md.Model, point) -> int | None:
    """The index of the assignment of the region that holds ``point``, or
    None if that region has none yet (spec 006, T5): found from the
    geometry alone, so that a model whose other regions are still without
    their material is assigned one region at a time. ModelError if the
    geometry does not let the regions be found (no external boundary, a
    crossing…), if the point lies in no region or on a boundary, or if the
    region holds two assignments already."""
    found: list[Problem] = []
    md._boundary_problems(m, lambda rule, where, message: found.append(Problem(rule, where, message)))
    if found:
        raise md.ModelError(found)
    try:
        points, segs, arcs, rings = _rings(m)
    except _Fail as fail:
        raise md.ModelError(fail.problems) from None
    p = (float(point[0]), float(point[1]))
    # on a boundary the point would belong to one side by the half-open rule
    # of the winding number: a click there is ambiguous, and it is refused
    tol = g.ARC_TOL * _scale(points)
    for s in segs:
        a, b = points[s.a], points[s.b]
        if s.arc is None:
            on = g._on_closed_segment(p, a, b)
        else:
            geo = g._ArcGeo(a, b, s.arc)
            on = abs(_trig.length(p, geo.c) - geo.r) <= tol and (
                geo.on_open_arc(p, tol) or min(_trig.length(p, a), _trig.length(p, b)) <= tol)
        if on:
            raise md.ModelError([Problem("assignment_outside", f"point {p}",
                                         f"lies on {_seg_name(s)}: a point inside a region "
                                         "is needed")])
    for outline, holes in rings:
        region = g.Region(outline, holes)
        if not g._inside_region(p, region, points, arcs):
            continue
        inside = [k for k, a in enumerate(m.assignments)
                  if g._inside_region((float(a.point[0]), float(a.point[1])), region, points, arcs)]
        if len(inside) > 1:
            raise md.ModelError([Problem(
                "region_twice", f"the region with outline through {points[outline[0]]}",
                f"holds the assignments at {[m.assignments[k].point for k in inside]}: "
                "delete one first")])
        return inside[0] if inside else None
    raise md.ModelError([Problem("assignment_outside", f"point {p}",
                                 "lies in no region (or on a boundary)")])


def _build(m: md.Model) -> Geometry:
    points, segs, arcs, rings = _rings(m)
    problems = []
    regions = []
    held: set[int] = set()
    for outline, holes in rings:
        region = g.Region(outline, holes)
        inside = [k for k, a in enumerate(m.assignments)
                  if g._inside_region((float(a.point[0]), float(a.point[1])), region, points, arcs)]
        held.update(inside)
        where = f"the region with outline through {points[outline[0]]}"
        if not inside:
            problems.append(Problem("region_unassigned", where,
                                    "has no assignment point: no region takes a material by "
                                    "default (D15)"))
            continue
        if len(inside) > 1:
            problems.append(Problem("region_twice", where,
                                    f"holds the assignments at "
                                    f"{[m.assignments[k].point for k in inside]}: one per region"))
            continue
        regions.append(Region(outline, holes, inside[0]))
    for k, a in enumerate(m.assignments):
        if k not in held:
            problems.append(Problem("assignment_outside", f"assignment at {a.point}",
                                    "lies in no region (or on a boundary)"))
    if problems:
        raise _Fail(problems)
    return Geometry(points, segs, tuple(regions))


def problems(m: md.Model) -> list[Problem]:
    """The geometric problems of a model whose structure is valid."""
    try:
        _build(m)
    except _Fail as fail:
        return fail.problems
    return []


def build(m: md.Model) -> Geometry:
    """The points, segments and regions of a valid model (ModelError with
    every problem otherwise)."""
    md.validate(m)
    return _build(m)


def region_area(geo: Geometry, r: int) -> float:
    """The area of a region, its arcs and holes included."""
    arcs = _arcs(geo.points, geo.segments)
    region = geo.regions[r]
    return (g._ring_area(region.outline, geo.points, arcs)
            + sum(g._ring_area(h, geo.points, arcs) for h in region.holes))
