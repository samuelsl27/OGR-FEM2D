# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The input of the mesher and its validation (spec 003, RF-1; the schema,
field by field, in docs/malla/entrada.md).

The mesher receives a geometry and the settings of the mesh:

* points, shared by index: two regions that meet use the same point, so the
  boundary between them is one segment of both;
* material regions: an outline, anticlockwise, and holes, clockwise (the
  convention of ``ogr_core.geometry.regions.MaterialRegion``), as rings of
  point indices; an excavation is a region like any other, and is meshed;
* the attributes of the segments that have any: an arc (spec 003, D3), a
  forced number of divisions (D10), and whether it bounds an excavation
  (D5); a segment is the side between two consecutive points of a ring;
* the settings: graded or uniform mesh, three- or six-node triangles, the
  quality bound B and the size controls (D5, D9).

A segment may meet another only at an end point they share. That is the
definition of the planar straight line graph a Delaunay refinement meshes
(Shewchuk 2002a, §1, p. 1: "a segment may intersect vertices and other
segments only at its endpoints"), and it is what keeps the mesh conforming
across regions. Straight segments are checked with exact arithmetic (floats
are rationals); arcs, analytically, with a tolerance relative to the size of
the model.

An arc is given by its centre alone: the arc of a segment is the MINOR arc
of the circle through its two points, the one on the side of the chord away
from the centre, so it subtends less than 180 degrees. A wider arc is split
by a point of its own (spec 003, D4: the mid-side node of a six-node triangle
goes to the middle of the arc).

validate() checks everything at once and raises MeshInputError with every
problem found, each naming the point, region, segment or setting at fault
and the rule it breaks (``Problem.rule``, one of RULES).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction

from ..engine.model import Problem
from ..engine.reference.quadrature import AXISYMMETRIC, PLANE_STRAIN

ANALYSES = (PLANE_STRAIN, AXISYMMETRIC)
GRADED = "graded"
UNIFORM = "uniform"
KINDS = (GRADED, UNIFORM)

#: The bound B on the circumradius-to-shortest-edge ratio of every triangle.
#: B = sqrt(2) is Ruppert's: no angle below arcsin(1/2B) = 20.7 degrees
#: (Shewchuk 2002a, §2, p. 5), and the refinement terminates for any B of at
#: least sqrt(2) (theorem 4, p. 16). A smaller B has no such guarantee, and
#: the mesher must always terminate (spec 003, RF-9): it is refused.
DEFAULT_QUALITY_BOUND = math.sqrt(2.0)

#: Relative tolerance of the checks that involve arcs (square roots), times
#: the diagonal of the bounding box of the points.
ARC_TOL = 1e-9

Point = tuple[float, float]


# ------------------------------------------------------------------ schema
@dataclass(frozen=True)
class Arc:
    """The minor arc, about ``centre``, between the two points of a
    segment."""
    centre: Point


@dataclass(frozen=True)
class SegmentSpec:
    """The attributes of the segment between points ``a`` and ``b`` (in
    either order): an arc, a forced number of divisions, and whether it
    bounds an excavation (it then takes the nodes of a graded mesh)."""
    a: int
    b: int
    arc: Arc | None = None
    divisions: int | None = None
    excavation: bool = False


@dataclass(frozen=True)
class Region:
    """A material region: its outline (anticlockwise) and its holes
    (clockwise), as rings of point indices, and the index of its material,
    which the mesher carries to every element of the region."""
    outline: tuple[int, ...]
    holes: tuple[tuple[int, ...], ...] = ()
    material: int = 0


@dataclass(frozen=True)
class Window:
    """A zone of the mesh, a polygon (rectangle or not, in either
    orientation), whose elements are no longer than ``size`` (spec 003, RF-7
    and D9)."""
    polygon: tuple[Point, ...]
    size: float


@dataclass(frozen=True)
class MeshSettings:
    """How the geometry is meshed. Every value here changes the mesh, and
    the mesh says which ones it was made with (rule 12).

    * ``kind``: ``"graded"`` or ``"uniform"`` (the radial mesh, spec 003 D8,
      is not built from a geometry and has its own settings);
    * ``nodes_per_element``: 3 or 6;
    * ``quality_bound``: B, at least sqrt(2);
    * graded: ``boundary_nodes``, the nodes spread over the excavation
      segments, or over the outer boundary when there is no excavation, and
      ``max_size``, an optional bound on the length of every edge (D5);
    * uniform: ``size``, the bound on the length of every edge, or
      ``elements``, an approximate number of elements to derive it from
      (D5), one of the two;
    * ``windows``: zones with a smaller bound (D9)."""
    kind: str = GRADED
    nodes_per_element: int = 6
    quality_bound: float = DEFAULT_QUALITY_BOUND
    boundary_nodes: int | None = None
    max_size: float | None = None
    size: float | None = None
    elements: int | None = None
    windows: tuple[Window, ...] = ()


@dataclass(frozen=True)
class MeshInput:
    """Everything the mesher receives."""
    analysis: str
    points: tuple[Point, ...]
    regions: tuple[Region, ...]
    segments: tuple[SegmentSpec, ...] = ()
    settings: MeshSettings = MeshSettings()


@dataclass(frozen=True)
class Segment:
    """A segment of the geometry as the mesher sees it: its two points, in
    the direction of its first ring, its attributes, and the rings that use
    it, as (region, ring), ring 0 being the outline and k the hole k - 1.
    A segment used by one ring only is on the outer boundary of the meshed
    domain."""
    a: int
    b: int
    arc: Arc | None
    divisions: int | None
    excavation: bool
    rings: tuple[tuple[int, int], ...]

    @property
    def outer(self) -> bool:
        return len(self.rings) == 1


# ---------------------------------------------------------------- problems
#: The rules validate() enforces, by name; docs/malla/entrada.md says why.
RULES = (
    "analysis", "points", "duplicate_point", "left_of_axis",
    "no_region", "ring", "material", "shared_edge",
    "unknown_segment", "segment_twice", "divisions", "arc",
    "orientation", "crossing", "arc_crossing", "hole", "overlap",
    "loose_point", "element_kind", "mesh_kind", "quality_bound",
    "graded_nodes", "max_size", "uniform_size", "window",
)


class MeshInputError(ValueError):
    """The input of the mesher breaks the schema: every problem found."""

    def __init__(self, problems: list[Problem]):
        self.problems = problems
        super().__init__("the mesher input is not valid:\n"
                         + "\n".join(f"  {p}" for p in problems))


# ------------------------------------------------------- exact predicates
def _finite(*values) -> bool:
    return all(isinstance(v, (int, float)) and not isinstance(v, bool)
               and math.isfinite(v) for v in values)


def _orient(a: Point, b: Point, c: Point) -> int:
    """The sign of the area of (a, b, c): +1 anticlockwise, -1 clockwise, 0
    collinear, computed exactly (a float is a rational, and so is every
    product and difference of them)."""
    t1 = (b[0] - a[0]) * (c[1] - a[1])
    t2 = (b[1] - a[1]) * (c[0] - a[0])
    det = t1 - t2
    if abs(det) > 1e-10 * (abs(t1) + abs(t2)):
        return 1 if det > 0 else -1
    fa = (Fraction(a[0]), Fraction(a[1]))
    v = ((Fraction(b[0]) - fa[0]) * (Fraction(c[1]) - fa[1])
         - (Fraction(b[1]) - fa[1]) * (Fraction(c[0]) - fa[0]))
    return (v > 0) - (v < 0)


def _on_closed_segment(p: Point, a: Point, b: Point) -> bool:
    """p lies on the closed segment ab (exactly)."""
    return (_orient(a, b, p) == 0
            and min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
            and min(a[1], b[1]) <= p[1] <= max(a[1], b[1]))


def _straight_meet(i: tuple[int, int], j: tuple[int, int], pts) -> bool:
    """The straight segments of point indices i and j meet somewhere other
    than at a point index they share."""
    p1, p2 = pts[i[0]], pts[i[1]]
    q1, q2 = pts[j[0]], pts[j[1]]
    if (max(p1[0], p2[0]) < min(q1[0], q2[0]) or max(q1[0], q2[0]) < min(p1[0], p2[0])
            or max(p1[1], p2[1]) < min(q1[1], q2[1])
            or max(q1[1], q2[1]) < min(p1[1], p2[1])):
        return False
    o1, o2 = _orient(p1, p2, q1), _orient(p1, p2, q2)
    o3, o4 = _orient(q1, q2, p1), _orient(q1, q2, p2)
    if o1 * o2 < 0 and o3 * o4 < 0:
        return True
    for k, seg in ((j[0], i), (j[1], i), (i[0], j), (i[1], j)):
        if k in seg:
            continue                      # an end point both segments use
        if _on_closed_segment(pts[k], pts[seg[0]], pts[seg[1]]):
            return True
    return False


# ------------------------------------------------------------------- arcs
class _ArcGeo:
    """The minor arc of a segment, ready for the intersection tests."""

    def __init__(self, a: Point, b: Point, centre: Point):
        self.a, self.b, self.c = a, b, centre
        self.r = 0.5 * (math.dist(a, centre) + math.dist(b, centre))
        mx, my = 0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1])
        dx, dy = mx - centre[0], my - centre[1]
        d = math.hypot(dx, dy)
        self.mid = (centre[0] + self.r * dx / d, centre[1] + self.r * dy / d)
        #: +1 if the arc bulges to the left of a -> b, -1 to the right
        self.side = 1 if _cross(a, b, self.mid) > 0 else -1
        self.chord = math.dist(a, b)
        self.theta = 2.0 * math.asin(min(1.0, self.chord / (2.0 * self.r)))

    def on_open_arc(self, x: Point, tol: float) -> bool:
        """A point of the circle lies on the arc, away from its ends: on the
        arc's side of the chord by more than ``tol`` (which leaves out the
        ends, both on the chord)."""
        return self.side * _cross(self.a, self.b, x) > tol * self.chord

    def segment_area(self) -> float:
        """The area between the arc and its chord, R^2/2 (theta - sin theta)."""
        return 0.5 * self.r ** 2 * (self.theta - math.sin(self.theta))

    def inside_segment(self, p: Point) -> bool:
        """p lies between the arc and its chord."""
        return (math.dist(p, self.c) < self.r
                and self.side * _cross(self.a, self.b, p) > 0.0)

    def min_x(self) -> float:
        """The smallest x of the arc: the leftmost point of the circle if the
        arc passes through it, else an end point."""
        left = (self.c[0] - self.r, self.c[1])
        if self.side * _cross(self.a, self.b, left) > 0.0:
            return left[0]
        return min(self.a[0], self.b[0])


def _cross(a: Point, b: Point, c: Point) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _arc_meets_straight(arc: _ArcGeo, p: Point, q: Point, tol: float) -> bool:
    """The arc and the straight segment pq meet away from the arc's ends."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    fx, fy = p[0] - arc.c[0], p[1] - arc.c[1]
    aa = dx * dx + dy * dy
    bb = dx * fx + dy * fy
    cc = fx * fx + fy * fy - arc.r ** 2
    disc = bb * bb - aa * cc
    if disc < -tol * arc.r * aa:
        return False
    root = math.sqrt(max(0.0, disc))
    length = math.sqrt(aa)
    for t in ((-bb - root) / aa, (-bb + root) / aa):
        if -tol / length <= t <= 1.0 + tol / length:
            if arc.on_open_arc((p[0] + t * dx, p[1] + t * dy), tol):
                return True
    return False


def _arc_meets_arc(u: _ArcGeo, v: _ArcGeo, tol: float) -> bool:
    """Two arcs meet away from their ends."""
    d = math.dist(u.c, v.c)
    if d <= tol and abs(u.r - v.r) <= tol:
        # the same circle: they overlap if an end of one is inside the other,
        # or if they are the same arc between different points
        return (u.on_open_arc(v.a, tol) or u.on_open_arc(v.b, tol)
                or v.on_open_arc(u.a, tol) or v.on_open_arc(u.b, tol)
                or u.on_open_arc(v.mid, tol))
    if d <= tol or d > u.r + v.r + tol or d < abs(u.r - v.r) - tol:
        return False
    a = (u.r ** 2 - v.r ** 2 + d * d) / (2.0 * d)
    h = math.sqrt(max(0.0, u.r ** 2 - a * a))
    ex, ey = (v.c[0] - u.c[0]) / d, (v.c[1] - u.c[1]) / d
    bx, by = u.c[0] + a * ex, u.c[1] + a * ey
    for s in (-1.0, 1.0):
        x = (bx - s * h * ey, by + s * h * ex)
        if u.on_open_arc(x, tol) and v.on_open_arc(x, tol):
            return True
    return False


# ------------------------------------------------------------- the rings
def _ring_edges(ring: tuple[int, ...]):
    return [(ring[k], ring[(k + 1) % len(ring)]) for k in range(len(ring))]


def _key(i: int, j: int) -> tuple[int, int]:
    return (i, j) if i < j else (j, i)


def _ring_area(ring, pts, arcs: dict) -> float:
    """The signed area enclosed by a ring, its arcs included: the shoelace
    of the chords plus, for each arc, the area between arc and chord, added
    when the arc bulges to the right of the ring's direction (outward of an
    anticlockwise ring) and taken away when it bulges to the left."""
    area = 0.0
    for i, j in _ring_edges(ring):
        area += pts[i][0] * pts[j][1] - pts[j][0] * pts[i][1]
    area *= 0.5
    for i, j in _ring_edges(ring):
        geo = arcs.get(_key(i, j))
        if geo is not None:
            direction = 1 if geo.a == pts[i] else -1      # ring runs a->b or b->a
            area += -direction * geo.side * geo.segment_area()
    return area


def _winding(p: Point, ring, pts, arcs: dict) -> int:
    """The winding number of a ring about p. The chords' winding (Sunday's
    crossing rule, exact for any polygon) is corrected by every arc whose
    segment holds p: the loop arc a->b, chord b->a goes round that segment
    anticlockwise when the arc bulges to the right of a->b, so it adds +1,
    and -1 when it bulges to the left."""
    w = 0
    for i, j in _ring_edges(ring):
        a, b = pts[i], pts[j]
        if a[1] <= p[1]:
            if b[1] > p[1] and _orient(a, b, p) > 0:
                w += 1
        elif b[1] <= p[1] and _orient(a, b, p) < 0:
            w -= 1
    for i, j in _ring_edges(ring):
        geo = arcs.get(_key(i, j))
        if geo is not None and geo.inside_segment(p):
            direction = 1 if geo.a == pts[i] else -1
            w += -direction * geo.side
    return w


def _inside_region(p: Point, region: Region, pts, arcs) -> bool:
    if _winding(p, region.outline, pts, arcs) == 0:
        return False
    return all(_winding(p, h, pts, arcs) == 0 for h in region.holes)


def _edge_midpoint(i: int, j: int, pts, arcs) -> Point:
    geo = arcs.get(_key(i, j))
    if geo is not None:
        return geo.mid
    return (0.5 * (pts[i][0] + pts[j][0]), 0.5 * (pts[i][1] + pts[j][1]))


def _rings(m: MeshInput):
    """(region, ring, points) of every ring: ring 0 is the outline."""
    for r, region in enumerate(m.regions):
        yield r, 0, region.outline
        for k, hole in enumerate(region.holes):
            yield r, k + 1, hole


def _ring_name(r: int, k: int) -> str:
    return f"region {r}, outline" if k == 0 else f"region {r}, hole {k - 1}"


# -------------------------------------------------------------- segments
def segments(m: MeshInput) -> tuple[Segment, ...]:
    """The segments of a valid input, in the order of their first
    appearance going round the rings (outline first, then the holes, region
    by region): the same input gives the same order (spec 003, D11)."""
    specs = {_key(s.a, s.b): s for s in m.segments}
    order: dict[tuple[int, int], list] = {}
    for r, k, ring in _rings(m):
        for i, j in _ring_edges(ring):
            key = _key(i, j)
            if key not in order:
                order[key] = [i, j, []]
            order[key][2].append((r, k))
    out = []
    for key, (i, j, rings) in order.items():
        spec = specs.get(key)
        out.append(Segment(i, j, spec.arc if spec else None,
                           spec.divisions if spec else None,
                           spec.excavation if spec else False, tuple(rings)))
    return tuple(out)


def graded_targets(segs) -> tuple[Segment, ...]:
    """The segments the nodes of a graded mesh are spread over (spec 003,
    D5): the excavation segments, or the outer boundary when there is no
    excavation; those with a forced number of divisions keep it."""
    excavation = [s for s in segs if s.excavation]
    chosen = excavation if excavation else [s for s in segs if s.outer]
    return tuple(s for s in chosen if s.divisions is None)


def region_area(m: MeshInput, r: int) -> float:
    """The area of a region of a valid input, its arcs and holes included."""
    arcs = _arcs(m)
    region = m.regions[r]
    return (_ring_area(region.outline, m.points, arcs)
            + sum(_ring_area(h, m.points, arcs) for h in region.holes))


def _arcs(m: MeshInput) -> dict:
    out = {}
    for s in m.segments:
        if s.arc is not None:
            out[_key(s.a, s.b)] = _ArcGeo(m.points[s.a], m.points[s.b], s.arc.centre)
    return out


# ------------------------------------------------------------ validation
def _settings_problems(m: MeshInput, add) -> None:
    st = m.settings
    if st.nodes_per_element not in (3, 6):
        add("element_kind", "settings",
            f"nodes_per_element {st.nodes_per_element!r} is not 3 or 6")
    if st.kind not in KINDS:
        add("mesh_kind", "settings", f"kind {st.kind!r} is not one of {KINDS}")
    if not (_finite(st.quality_bound) and st.quality_bound >= DEFAULT_QUALITY_BOUND):
        add("quality_bound", "settings",
            f"B = {st.quality_bound!r}: the refinement is guaranteed to terminate "
            "only with B >= sqrt(2) (Shewchuk 2002a, theorem 4)")
    if st.kind == GRADED:
        if st.size is not None or st.elements is not None:
            add("uniform_size", "settings",
                "size and elements are for a uniform mesh; a graded mesh would "
                "ignore them (rule 7)")
        if st.max_size is not None and not (_finite(st.max_size) and st.max_size > 0.0):
            add("max_size", "settings", f"max_size {st.max_size!r} is not a length > 0")
    elif st.kind == UNIFORM:
        given = [v for v in (st.size, st.elements) if v is not None]
        if len(given) != 1:
            add("uniform_size", "settings",
                "a uniform mesh needs exactly one of size and elements")
        elif st.size is not None and not (_finite(st.size) and st.size > 0.0):
            add("uniform_size", "settings", f"size {st.size!r} is not a length > 0")
        elif st.elements is not None and not (
                isinstance(st.elements, int) and not isinstance(st.elements, bool)
                and st.elements >= 1):
            add("uniform_size", "settings", f"elements {st.elements!r} is not an integer >= 1")
        if st.boundary_nodes is not None:
            add("graded_nodes", "settings",
                "boundary_nodes is for a graded mesh; a uniform one would ignore it (rule 7)")
        if st.max_size is not None:
            add("max_size", "settings",
                "max_size is for a graded mesh; a uniform one has its size (rule 7)")
    for w, window in enumerate(st.windows):
        where = f"window {w}"
        poly = window.polygon
        if not (_finite(window.size) and window.size > 0.0):
            add("window", where, f"size {window.size!r} is not a length > 0")
        if len(poly) < 3 or not all(len(q) == 2 and _finite(*q) for q in poly):
            add("window", where, "needs at least three points of two finite numbers")
            continue
        area = 0.5 * sum(poly[k][0] * poly[(k + 1) % len(poly)][1]
                         - poly[(k + 1) % len(poly)][0] * poly[k][1]
                         for k in range(len(poly)))
        idx = list(range(len(poly)))
        edges = _ring_edges(tuple(idx))
        simple = all(not _straight_meet(e, f, poly)
                     for x, e in enumerate(edges) for f in edges[x + 1:])
        if area == 0.0 or not simple:
            add("window", where, "the polygon has no area or crosses itself")


def _point_problems(m: MeshInput, add) -> bool:
    ok = True
    if len(m.points) < 3:
        add("points", "model", "fewer than three points")
        ok = False
    seen: dict[tuple[float, float], int] = {}
    for n, p in enumerate(m.points):
        if len(p) != 2 or not _finite(*p):
            add("points", f"point {n}", f"{p!r} is not two finite numbers")
            ok = False
            continue
        key = (float(p[0]), float(p[1]))
        if key in seen:
            add("duplicate_point", f"point {n}",
                f"same place as point {seen[key]}: two regions meeting there "
                "would not share it")
            ok = False
        else:
            seen[key] = n
        if m.analysis == AXISYMMETRIC and p[0] < 0.0:
            add("left_of_axis", f"point {n}",
                f"x = r = {p[0]!r} < 0: in axisymmetry the axis is x = 0 and the "
                "model lies on x >= 0")
    return ok


def _ring_problems(m: MeshInput, add) -> bool:
    ok = True
    if not m.regions:
        add("no_region", "model", "no regions")
        return False
    n = len(m.points)
    for r, region in enumerate(m.regions):
        if not (isinstance(region.material, int) and not isinstance(region.material, bool)
                and region.material >= 0):
            add("material", f"region {r}", f"material {region.material!r} is not an index >= 0")
    for r, k, ring in _rings(m):
        where = _ring_name(r, k)
        if len(ring) < 3:
            add("ring", where, "fewer than three points")
            ok = False
        elif not all(isinstance(i, int) and 0 <= i < n for i in ring):
            add("ring", where, f"points {[i for i in ring if not (isinstance(i, int) and 0 <= i < n)]} do not exist")
            ok = False
        elif len(set(ring)) != len(ring):
            add("ring", where, "repeats a point")
            ok = False
    return ok


def _segment_problems(m: MeshInput, add, uses: dict) -> bool:
    ok = True
    for key, rings in uses.items():
        if len(rings) > 2:
            add("shared_edge", f"segment {key[0]}-{key[1]}",
                f"used by {len(rings)} rings: a segment bounds at most two")
            ok = False
        elif len(rings) == 2 and rings[0][2] == rings[1][2]:
            add("shared_edge", f"segment {key[0]}-{key[1]}",
                f"{_ring_name(*rings[0][:2])} and {_ring_name(*rings[1][:2])} run it the "
                "same way: they overlap")
            ok = False
    seen = set()
    scale = _scale(m)
    for s in m.segments:
        key = _key(s.a, s.b)
        where = f"segment {s.a}-{s.b}"
        if key not in uses:
            add("unknown_segment", where, "is not a side of any ring")
            ok = False
            continue
        if key in seen:
            add("segment_twice", where, "has its attributes given twice")
            ok = False
        seen.add(key)
        if s.divisions is not None and not (
                isinstance(s.divisions, int) and not isinstance(s.divisions, bool)
                and s.divisions >= 1):
            add("divisions", where, f"divisions {s.divisions!r} is not an integer >= 1")
        if s.arc is not None:
            c = s.arc.centre
            a, b = m.points[s.a], m.points[s.b]
            if len(c) != 2 or not _finite(*c):
                add("arc", where, f"centre {c!r} is not two finite numbers")
                ok = False
                continue
            ra, rb = math.dist(a, c), math.dist(b, c)
            if abs(ra - rb) > ARC_TOL * max(ra, rb, scale):
                add("arc", where,
                    f"its points are at {ra!r} and {rb!r} from the centre: not on one circle")
                ok = False
            elif abs(_cross(a, b, c)) <= ARC_TOL * scale * math.dist(a, b):
                add("arc", where,
                    "the centre is on the chord: a half circle or more must be split by a "
                    "point (spec 003, D4)")
                ok = False
    return ok


def _scale(m: MeshInput) -> float:
    pts = [p for p in m.points if len(p) == 2 and _finite(*p)]
    if not pts:
        return 1.0
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return math.hypot(max(xs) - min(xs), max(ys) - min(ys)) or 1.0


def _geometry_problems(m: MeshInput, add, uses: dict) -> None:
    pts = m.points
    arcs = _arcs(m)
    tol = ARC_TOL * _scale(m)

    if m.analysis == AXISYMMETRIC:
        for key, geo in arcs.items():
            if geo.min_x() < -tol:
                add("left_of_axis", f"segment {key[0]}-{key[1]}",
                    f"the arc reaches x = {geo.min_x():.6g} < 0 (the axis is x = 0)")

    for r, k, ring in _rings(m):
        area = _ring_area(ring, pts, arcs)
        if (k == 0 and area <= 0.0) or (k > 0 and area >= 0.0):
            add("orientation", _ring_name(r, k),
                f"signed area {area:.6g}: an outline goes anticlockwise and a hole "
                "clockwise")

    keys = list(uses)
    crossed = False
    for x, e in enumerate(keys):
        for f in keys[x + 1:]:
            ge, gf = arcs.get(e), arcs.get(f)
            if ge is None and gf is None:
                if _straight_meet(e, f, pts):
                    add("crossing", f"segments {e[0]}-{e[1]} and {f[0]}-{f[1]}",
                        "meet away from a point they share (a segment may meet another "
                        "only at a shared end point: Shewchuk 2002a, §1)")
                    crossed = True
            else:
                if ge is not None and gf is not None:
                    hit = _arc_meets_arc(ge, gf, tol)
                elif ge is not None:
                    hit = _arc_meets_straight(ge, pts[f[0]], pts[f[1]], tol)
                else:
                    hit = _arc_meets_straight(gf, pts[e[0]], pts[e[1]], tol)
                if hit:
                    add("arc_crossing", f"segments {e[0]}-{e[1]} and {f[0]}-{f[1]}",
                        "an arc meets another segment away from their shared ends")
                    crossed = True
    used = {i for _r, _k, ring in _rings(m) for i in ring}
    loose = [n for n in range(len(pts)) if n not in used]
    for n in loose:
        for key in keys:
            geo = arcs.get(key)
            on = (_on_closed_segment(pts[n], pts[key[0]], pts[key[1]]) if geo is None
                  else abs(math.dist(pts[n], geo.c) - geo.r) <= tol and geo.on_open_arc(pts[n], tol))
            if on:
                add("loose_point", f"point {n}",
                    f"belongs to no ring but lies on segment {key[0]}-{key[1]}")
                crossed = True
    if crossed:
        return     # the containment tests below assume no segment meets another

    for r, region in enumerate(m.regions):
        for k, hole in enumerate(region.holes):
            for i, j in _ring_edges(hole):
                p = _edge_midpoint(i, j, pts, arcs)
                if _winding(p, region.outline, pts, arcs) == 0 or any(
                        _winding(p, other, pts, arcs) != 0
                        for kk, other in enumerate(region.holes) if kk != k):
                    add("hole", _ring_name(r, k + 1),
                        "is not inside its outline, or overlaps another hole")
                    break
    for r, region in enumerate(m.regions):
        own = {_key(i, j) for _rr, _kk, ring in _rings_of(region) for i, j in _ring_edges(ring)}
        for s, other in enumerate(m.regions):
            if s == r:
                continue
            for _rr, _kk, ring in _rings_of(other):
                for i, j in _ring_edges(ring):
                    if _key(i, j) in own:
                        continue
                    if _inside_region(_edge_midpoint(i, j, pts, arcs), region, pts, arcs):
                        add("overlap", f"region {s} and region {r}",
                            f"segment {i}-{j} of region {s} lies inside region {r}")
                        break
                else:
                    continue
                break
    for n in loose:
        if not any(_inside_region(pts[n], region, pts, arcs) for region in m.regions):
            add("loose_point", f"point {n}", "belongs to no ring and lies in no region")


def _rings_of(region: Region):
    yield 0, 0, region.outline
    for k, hole in enumerate(region.holes):
        yield 0, k + 1, hole


def problems(m: MeshInput) -> list[Problem]:
    """Every problem of the input, in the order found (empty when valid)."""
    out: list[Problem] = []
    add = lambda rule, where, message: out.append(Problem(rule, where, message))

    if m.analysis not in ANALYSES:
        add("analysis", "model", f"analysis {m.analysis!r} is not one of {ANALYSES}")
    _settings_problems(m, add)
    points_ok = _point_problems(m, add)
    rings_ok = _ring_problems(m, add)
    if not (points_ok and rings_ok):
        return out
    uses: dict[tuple[int, int], list] = {}
    for r, k, ring in _rings(m):
        for i, j in _ring_edges(ring):
            uses.setdefault(_key(i, j), []).append((r, k, i < j))
    segments_ok = _segment_problems(m, add, uses)
    if m.settings.kind == GRADED and segments_ok:
        targets = graded_targets(segments(m))
        nodes = m.settings.boundary_nodes
        if not targets:
            if nodes is not None:
                add("graded_nodes", "settings",
                    "every segment that would take boundary_nodes has its divisions "
                    "forced: the value would do nothing (rule 7)")
        elif not (isinstance(nodes, int) and not isinstance(nodes, bool) and nodes >= 1):
            add("graded_nodes", "settings",
                f"boundary_nodes {nodes!r}: a graded mesh needs the number of nodes on "
                "its excavations (or on its outer boundary), an integer >= 1")
        elif nodes < len(targets):
            add("graded_nodes", "settings",
                f"{nodes} nodes for {len(targets)} segments: each needs at least one "
                "division")
    if segments_ok:
        _geometry_problems(m, add, uses)
    return out


def validate(m: MeshInput) -> MeshInput:
    """The input itself when it is valid; MeshInputError with every problem
    otherwise (spec 003, RF-1)."""
    found = problems(m)
    if found:
        raise MeshInputError(found)
    return m
