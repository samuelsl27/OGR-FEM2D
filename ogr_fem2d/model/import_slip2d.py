# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Opening a ``.ogr`` of OGR Slip2D: its model converted to a FEM model, with a
report of what came, what did not and what was put by default (spec 004,
RF-14, D1, D16; ADR-0004; how the reference program opens a limit
equilibrium file, M02 §5.2 of the interface analysis).

The file is read by the core this program pins (``Project.load``): a file
that core cannot open gives the core's error. Then:

* **the geometry**: the regions the core resolves from the external and the
  material boundaries (``Project.resolve_regions``, the planar subdivision of
  Slip2D itself), turned into boundaries that meet only at shared vertices
  (D15): the sides used by one region make the external boundary, the sides
  shared by two make material boundaries, open chains or closed rings. The
  regions of the FEM model are then those of Slip2D, the same areas;
* **the materials**: id, name, colour and unit weight. **No E nor nu** (D16):
  they are not invented, and the model is not translated to the engine until
  they are given. Their strength (c, phi, Hoek-Brown...) does not come: no
  law of this version uses it (spec 008);
* **the assignments**: a point inside every region, with the material
  Slip2D gives it (by a click of its own, inherited, or the first material
  by Slip2D's default: the report says which regions had no click of their
  own);
* **the loads**: distributed loads and line loads on the external boundary,
  a vertex inserted at every end that was not one. A distributed load runs
  forward along the external boundary; its NORMAL is turned into this
  program's (into the ground, D6), its sign changed where Slip2D's pointed
  out of the ground, and the report says so. A line load NORMAL or at an
  angle to the boundary is turned into an angle from the horizontal, from
  the segment it lies on; at a corner it cannot be, and does not come;
* **the conditions**, as the reference program: the sides and the bottom of
  the external boundary fixed (segments on its smallest and largest x, and
  on its smallest y), the rest, the surface, free;
* one stage, the field stress constant and zero (the gravitational one of a
  slope is the real-surface one of spec 009), the mesh settings by default.

What does not come is listed: water, tension cracks and the other
boundaries of limit equilibrium, supports, seismic loading, searches and
methods, statistics, the seepage mesh and results.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from pathlib import Path

from ogr_core.geometry.boundary_type import BoundaryType
from ogr_core.loads.loads import LoadDistribution, LoadOrientation
from ogr_core.project.project import Project

from . import model as md

EXTERNAL_ID = "external"

#: How near a point of the core's subdivision, or the end of a load, has to be to a
#: vertex to be it, relative to the size of the model.
SNAP = 1e-7


@dataclass
class Report:
    """What opening the file did."""
    brought: list[str] = field(default_factory=list)
    not_brought: list[str] = field(default_factory=list)
    defaults: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)


def _key(p) -> tuple[float, float]:
    return (float(p[0]), float(p[1]))


class _Snap:
    """The vertices the user drew: a point of the core's subdivision
    within ``tol`` of one of them is taken as it (shapely gives them back
    moved in the last digits, ~1e-9 of the model's size)."""

    def __init__(self, vertices, tol):
        self.vertices = sorted(set(vertices))
        self.tol = tol

    def __call__(self, p):
        p = _key(p)
        best = min(self.vertices, key=lambda v: math.dist(v, p), default=None)
        if best is not None and math.dist(best, p) <= self.tol:
            return best
        return p


def _ring(poly, snap=_key) -> list[tuple[float, float]]:
    pts = [snap((v.x, v.y)) for v in poly.vertices]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts.pop()
    return pts


def _area(ring) -> float:
    return 0.5 * sum(ring[k][0] * ring[(k + 1) % len(ring)][1]
                     - ring[(k + 1) % len(ring)][0] * ring[k][1] for k in range(len(ring)))


def _inside_point(region) -> tuple[float, float]:
    from shapely.geometry import Polygon
    shell = _ring(region.polygon)
    holes = [_ring(h) for h in getattr(region, "holes", None) or ()]
    p = Polygon(shell, holes).representative_point()
    return (float(p.x), float(p.y))


def _geometry(regions, snap):
    """The external loop and the material chains of a partition into
    regions (their rings share vertices exactly)."""
    count: dict[tuple, int] = {}
    directed = []
    for r in regions:
        rings = [_ring(r.polygon, snap)] + [_ring(h, snap) for h in getattr(r, "holes", None) or ()]
        for k, ring in enumerate(rings):
            if (k == 0) != (_area(ring) > 0.0):
                ring = ring[::-1]                 # outline anticlockwise, holes clockwise
            for i in range(len(ring)):
                a, b = ring[i], ring[(i + 1) % len(ring)]
                key = (min(a, b), max(a, b))
                count[key] = count.get(key, 0) + 1
                directed.append((a, b))
    outer_next = {}
    for a, b in directed:
        if count[(min(a, b), max(a, b))] == 1:
            outer_next[a] = b
    start = min(outer_next)
    loop, p = [start], outer_next[start]
    while p != start:
        loop.append(p)
        p = outer_next[p]
    if _area(loop) < 0.0:
        loop = [loop[0]] + loop[:0:-1]
    on_loop = set(loop)
    adjacent: dict[tuple, list] = {}
    inner = sorted(k for k, c in count.items() if c == 2)
    for a, b in inner:
        adjacent.setdefault(a, []).append(b)
        adjacent.setdefault(b, []).append(a)
    for v in adjacent:
        adjacent[v].sort()
    used: set = set()
    chains = []
    ends = sorted(v for v in adjacent if len(adjacent[v]) != 2 or v in on_loop)
    for e in ends:
        for nb in adjacent[e]:
            if (min(e, nb), max(e, nb)) in used:
                continue
            chain, prev, cur = [e], e, nb
            used.add((min(e, nb), max(e, nb)))
            while True:
                chain.append(cur)
                if cur in ends:
                    break
                nxt = next(x for x in adjacent[cur] if x != prev)
                used.add((min(cur, nxt), max(cur, nxt)))
                prev, cur = cur, nxt
            chains.append((chain, False))
    for a, b in inner:
        if (a, b) in used:
            continue
        ring, cur = [a], b
        used.add((a, b))
        while cur != a:
            ring.append(cur)
            nxt = next(x for x in adjacent[cur] if (min(cur, x), max(cur, x)) not in used)
            used.add((min(cur, nxt), max(cur, nxt)))
            cur = nxt
        chains.append((ring, True))
    return loop, chains


def _on_segment(p, a, b, tol) -> bool:
    ax, ay, bx, by = a[0], a[1], b[0], b[1]
    length = math.hypot(bx - ax, by - ay)
    if length == 0.0:
        return False
    cross = (bx - ax) * (p[1] - ay) - (by - ay) * (p[0] - ax)
    t = ((p[0] - ax) * (bx - ax) + (p[1] - ay) * (by - ay)) / (length * length)
    return abs(cross) / length <= tol and 0.0 < t < 1.0


def _insert(loop: list, p, tol) -> tuple[list, int | None, tuple]:
    """The loop with ``p`` as a vertex (a vertex within ``tol`` is taken
    as p), the index of the segment it was inserted into (None if it was a
    vertex already), and the vertex; ValueError if p is not on the loop."""
    p = _key(p)
    near = min(loop, key=lambda v: math.dist(v, p))
    if math.dist(near, p) <= tol:
        return loop, None, near
    for i in range(len(loop)):
        a, b = loop[i], loop[(i + 1) % len(loop)]
        if _on_segment(p, a, b, tol):
            return loop[:i + 1] + [p] + loop[i + 1:], i, p
    raise ValueError(p)


def _length(loop, i, j) -> float:
    n, s, k = len(loop), 0.0, i
    while k != j:
        s += math.dist(loop[k], loop[(k + 1) % n])
        k = (k + 1) % n
    return s


def _scale(loop) -> float:
    xs, ys = [p[0] for p in loop], [p[1] for p in loop]
    return math.hypot(max(xs) - min(xs), max(ys) - min(ys)) or 1.0


def open_slip2d(path) -> tuple[md.Model, Report]:
    """The FEM model of a ``.ogr`` of OGR Slip2D, and what was done."""
    project = Project.load(Path(path))
    report = Report()
    regions = project.resolve_regions()
    if not regions:
        raise md.ModelError([md.Problem("external", "file",
                                        "the Slip2D model has no external boundary or no "
                                        "regions")])
    drawn = [(v.x, v.y) for b in project.boundaries
             if b.btype in (BoundaryType.EXTERNAL, BoundaryType.MATERIAL)
             for v in b.polyline.vertices]
    xs, ys = [p[0] for p in drawn], [p[1] for p in drawn]
    tol = SNAP * (math.hypot(max(xs) - min(xs), max(ys) - min(ys)) or 1.0)
    loop, chains = _geometry(regions, _Snap(drawn, tol))

    # the loads, inserting their ends in the external loop
    loads_in = []
    for ld in project.distributed_loads:
        try:
            loop, ins0, s = _insert(loop, (ld.start.x, ld.start.y), tol)
            loop, ins1, e = _insert(loop, (ld.end.x, ld.end.y), tol)
        except ValueError:
            report.not_brought.append(f"distributed load {ld.name or ld.id}: its ends are not on "
                                      "the external boundary")
            continue
        for ins, q in ((ins0, s), (ins1, e)):
            if ins is not None:
                report.changed.append(f"a vertex inserted in the external boundary at {q}, an end "
                                      f"of the distributed load {ld.name or ld.id}")
        loads_in.append((ld, s, e))
    points_in = []
    for ld in project.line_loads:
        try:
            loop, seg, q = _insert(loop, (ld.point.x, ld.point.y), tol)
        except ValueError:
            report.not_brought.append(f"line load {ld.name or ld.id}: its point is not on the "
                                      "external boundary")
            continue
        if seg is not None:
            report.changed.append(f"a vertex inserted in the external boundary at {q}, the point "
                                  f"of the line load {ld.name or ld.id}")
        points_in.append((ld, seg, q))
    n = len(loop)

    materials = tuple(md.Material(mat.id, mat.name, None, None, float(mat.unit_weight),
                                  md.FIELD_STRESS, mat.color) for mat in project.materials)
    clicks = [(a["x"], a["y"]) for a in project.region_assignments]
    assignments = []
    for r in regions:
        if r.material_id is None:
            report.not_brought.append("a region with no material in Slip2D")
            continue
        assignments.append(md.Assignment(_inside_point(r), r.material_id, (False,)))
        if not any(r.contains(x, y) for x, y in clicks):
            report.defaults.append(
                f"the region with material {r.material_id!r} at {assignments[-1].point} had no "
                "assignment of its own in Slip2D (inherited, or Slip2D's first material)")

    boundaries = [md.Boundary(EXTERNAL_ID, md.EXTERNAL, tuple(loop), True, name="External")]
    for k, (chain, closed) in enumerate(chains):
        boundaries.append(md.Boundary(f"material {k + 1}", md.MATERIAL, tuple(chain), closed,
                                      name=f"Material boundary {k + 1}"))

    # the distributed loads, forward along the loop
    loads = []
    for ld, s, e in loads_in:
        i, j = loop.index(s), loop.index(e)
        v0 = ld.magnitude_1
        v1 = ld.magnitude_1 if (ld.distribution == LoadDistribution.CONSTANT
                                or ld.magnitude_2 is None) else ld.magnitude_2
        angle = ld.angle_deg
        if _length(loop, i, j) > _length(loop, j, i):
            i, j, v0, v1 = j, i, v1, v0
            swapped = True
        else:
            swapped = False
        orientation = ld.orientation.value
        name = ld.name or ld.id
        if ld.orientation == LoadOrientation.NORMAL_TO_BOUNDARY:
            a, b = loop[i], loop[(i + 1) % n]
            tx, ty = b[0] - a[0], b[1] - a[1]
            into = (-ty, tx)                       # left of a forward side of an anticlockwise loop
            dx, dy = ld.direction_vector()
            if dx * into[0] + dy * into[1] < 0.0:
                v0, v1 = -v0, -v1
                report.changed.append(f"distributed load {name}: Slip2D's normal pointed out of "
                                      "the ground; brought with the sign changed (D6)")
            angle = 0.0
        elif ld.orientation == LoadOrientation.ANGLE_TO_BOUNDARY and swapped:
            angle = angle + 180.0
            report.changed.append(f"distributed load {name}: runs the other way round the "
                                  "external boundary; its angle to the boundary + 180 degrees")
        elif ld.orientation in (LoadOrientation.VERTICAL, LoadOrientation.HORIZONTAL):
            angle = 0.0
        loads.append(md.DistributedLoad(md.Span(EXTERNAL_ID, loop[i], loop[j]), v0, v1,
                                        orientation, angle, (1.0,), name))
    for ld, seg, p in points_in:
        name = ld.name or ld.id
        if ld.orientation in (LoadOrientation.VERTICAL, LoadOrientation.HORIZONTAL):
            loads.append(md.PointLoad(p, ld.magnitude, ld.orientation.value, 0.0, (1.0,), name))
        elif ld.orientation == LoadOrientation.ANGLE_FROM_HORIZONTAL:
            loads.append(md.PointLoad(p, ld.magnitude, md.ANGLE_FROM_HORIZONTAL, ld.angle_deg,
                                      (1.0,), name))
        elif seg is None:
            report.not_brought.append(f"line load {name}: {ld.orientation.value} at a corner of "
                                      "the boundary, where the boundary has no one direction")
        else:
            k = loop.index(p)
            a, b = loop[k - 1], loop[(k + 1) % n]
            if a[0] > b[0]:
                a, b = b, a                        # the ground's left-to-right tangent
            length = math.dist(a, b)
            tx, ty = (b[0] - a[0]) / length, (b[1] - a[1]) / length
            nx, ny = ty, -tx                       # into the ground, Slip2D's convention
            if ld.orientation == LoadOrientation.NORMAL_TO_BOUNDARY:
                dx, dy = nx, ny
            else:
                r = math.radians(ld.angle_deg)
                dx, dy = tx * math.cos(r) - ty * math.sin(r), tx * math.sin(r) + ty * math.cos(r)
            angle = math.degrees(math.atan2(dy, dx))
            loads.append(md.PointLoad(p, ld.magnitude, md.ANGLE_FROM_HORIZONTAL, angle, (1.0,), name))
            report.changed.append(f"line load {name}: {ld.orientation.value} turned into an angle "
                                  f"of {angle:.6g} degrees from the horizontal")

    # the conditions, as the reference program: sides and bottom fixed
    xs, ys = [p[0] for p in loop], [p[1] for p in loop]
    xmin, xmax, ymin = min(xs), max(xs), min(ys)
    surface = []
    for k in range(n):
        a, b = loop[k], loop[(k + 1) % n]
        side = (a[0] == b[0] and a[0] in (xmin, xmax)) or (a[1] == b[1] == ymin)
        surface.append(not side)
    conditions = []
    if not all(surface):
        start = surface.index(False)
        runs, run = [], None
        for i in range(1, n + 1):
            k = (start + i) % n
            if surface[k]:
                run = [k] if run is None else run + [k]
            elif run:
                runs.append(run)
                run = None
        if run:
            runs.append(run)
        for run in runs:
            conditions.append(md.Condition(md.FREE, md.Span(EXTERNAL_ID, loop[run[0]],
                                                            loop[(run[-1] + 1) % n]),
                                           active=(True,), name="Surface"))
    report.defaults.append("conditions: the sides and the bottom of the external boundary "
                           "fixed in x and y, the surface free (as the reference program)")
    report.defaults.append("materials: E and nu not given; the model is not translated to the "
                           "engine until they are (D16)")
    report.defaults.append("field stress: none (constant, zero); the gravitational field under "
                           "the real ground surface is spec 009")
    report.defaults.append("one stage; the mesh settings by default (graded, six-node "
                           "triangles, B = sqrt 2), boundary_nodes to be given")
    report.brought += [f"{len(boundaries)} boundaries (1 external, {len(chains)} material)",
                       f"{len(materials)} materials (name, colour, unit weight)",
                       f"{len(assignments)} regions with their material",
                       f"{len(loads)} loads"]
    report.not_brought.append("the strength of the materials (no law of this version uses it, "
                              "spec 008) and their pore pressure settings")
    other = {}
    for b in project.boundaries:
        if b.btype not in (BoundaryType.EXTERNAL, BoundaryType.MATERIAL):
            other[b.btype.name] = other.get(b.btype.name, 0) + 1
    for name, count in sorted(other.items()):
        report.not_brought.append(f"{count} boundaries of type {name}")
    if project.supports:
        report.not_brought.append(f"{len(project.supports)} supports")
    if project.water_pressure_grid is not None or project.fem_mesh is not None:
        report.not_brought.append("the water pressure grid, the seepage mesh and its results")
    report.not_brought.append("the analysis settings: methods, searches, seismic loading, "
                              "statistics")

    model = md.Model(
        summary=md.Summary(title=project.name, notes=f"Opened from the OGR Slip2D model {Path(path).name}"),
        boundaries=tuple(boundaries), materials=materials,
        stages=(md.Stage("1", "Stage 1"),), assignments=tuple(assignments),
        conditions=tuple(conditions), loads=tuple(loads))
    return md.validate(model), report
