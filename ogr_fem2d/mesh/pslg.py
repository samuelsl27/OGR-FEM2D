# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
What FEM2D hands to the core's quality triangulation, and what it does with
the arcs afterwards (spec 003, D2, D3 and D13).

The planar straight line graph (PSLG; Shewchuk 2002a, §1):

* the vertices: the points of the discretization (step 1), input points
  first;
* the segments: every piece between two consecutive nodes of a discretized
  segment, labelled with the index of its segment in ``geometry.segments``,
  so the pieces of an arc keep the arc;
* a seed per region, a point strictly inside it with its material, and a
  point inside every void (a hole of a region that no region fills: one
  that holds no seed; until v0.0.9, one whose ring was no region's outline,
  which took for a void a hole filled by two regions), so the triangulation
  knows what to mesh;
* the corners of every window (D9) that fall strictly inside the meshed
  domain, as loose vertices, after the nodes of step 1, window by window. The
  core evaluates the size bound at the three vertices and the centroid of
  each triangle (its reply of 2026-11-23), so a window smaller than the
  triangle over it could fall between those four points and not be seen
  (measured: a window of 0.4 m with size 0.05 left the mesh unchanged). With
  its corners as vertices, the triangles that touch them see the bound, and
  the refinement carries it inwards. Decided by the owner on 2026-11-23.

A seed must lie strictly inside the polygon of the discretized nodes (the
chords) and in no cap, the region between a piece of an arc and its chord:
the core refuses a seed or a void point there (``refine.seed_in_arc``,
``refine.void_in_arc``, OGR-Core 0.2.6). The caps of an outline bulge out of
the polygon, but those of a circular hole bulge into it (found in T12, a
thin ring between two circles: the middle of the widest interval of the
chords fell in a cap). It is found without new dependencies: along every
horizontal line halfway between two heights of the vertices, the line is cut
at its crossings with the chords and with the circles of the caps; of the
intervals whose middle is inside the polygon and out of every cap, the
widest gives the point, checked again exactly (winding numbers of the
chords; the cap with exact orientation and distance, as the core does).

D13: the refinement may add vertices on a chord of an arc (Shewchuk 2002a,
§3.1: it splits encroached subsegments at their middle). ``onto_arcs`` takes
each such vertex radially onto its circle; the jacobian of the elements that
use it is then checked (``checks``, RF-13), and the mesh says how many moved
(rule 12).

D13 is replaced by D14 (2026-11-22): moving those vertices can turn over the
thin elements against the chord when its sagitta is near the element size
(found in T12, kept in tests/test_mesh_pslg_v008.py). The core is asked to
split a piece of an arc at the middle of the arc instead, during the
refinement (Pav and Walkington, after Boivin and Ollivier-Gooch 2002), so
that no vertex is left on a chord. ``onto_arcs`` stays as the record of the
finding, and is not part of the mesher.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction

from . import geometry as g
from .discretize import Discretization

Point = tuple[float, float]


@dataclass(frozen=True)
class PSLG:
    vertices: tuple[Point, ...]
    segments: tuple[tuple[int, int, int], ...]          # (u, v, label)
    seeds: tuple[tuple[Point, int, int], ...]           # (point, region, material)
    voids: tuple[Point, ...]
    arcs: Mapping[int, Point]                           # label -> centre


class SeedError(ValueError):
    """No point strictly inside a ring set was found (a region too thin for
    the floating point of its coordinates)."""


def _ring_chain(m: g.MeshInput, disc: Discretization, ring) -> list[int]:
    """The discretized nodes of a ring, in the ring's direction."""
    by_key = {g._key(ds.segment.a, ds.segment.b): ds for ds in disc.segments}
    out = []
    for i, j in g._ring_edges(ring):
        ds = by_key[g._key(i, j)]
        nodes = list(ds.nodes) if ds.segment.a == i else list(reversed(ds.nodes))
        out.extend(nodes[:-1])
    return out


def _crossings(y: float, rings, pts) -> list[float]:
    """x of every crossing of the line at height y with the rings (half-open
    in y, so a vertex at y is counted once)."""
    xs = []
    for ring in rings:
        for k in range(len(ring)):
            a, b = pts[ring[k]], pts[ring[(k + 1) % len(ring)]]
            if (a[1] > y) != (b[1] > y):
                xs.append(a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]))
    return sorted(xs)


Cap = tuple[Point, Point, Point]                 # (a, b, centre) of a piece of arc


def in_cap(p: Point, cap: Cap) -> bool:
    """p in the region between the chord ab and its minor arc about c:
    strictly on the arc's side of the chord's line (the chord itself is the
    segment's), and in the closed disc through a. Exact, like the core's
    test (``refine._in_cap``), so that what is accepted here is accepted
    there."""
    a, b, c = cap
    side = -g._orient(a, b, c)
    if g._orient(a, b, p) != side:
        return False
    cx, cy, px, py, ax, ay = (Fraction(v) for v in (*c, *p, *a))
    return (px - cx) ** 2 + (py - cy) ** 2 <= (ax - cx) ** 2 + (ay - cy) ** 2


def _circle_crossings(y: float, caps: Sequence[Cap]) -> list[float]:
    out = []
    for a, _b, c in caps:
        r2 = (a[0] - c[0]) * (a[0] - c[0]) + (a[1] - c[1]) * (a[1] - c[1])
        h2 = r2 - (y - c[1]) * (y - c[1])
        if h2 > 0.0:
            h = math.sqrt(h2)
            out += [c[0] - h, c[0] + h]
    return out


def interior_point(rings: Sequence[Sequence[int]], pts: Sequence[Point],
                   caps: Sequence[Cap] = ()) -> Point:
    """A point strictly inside the set of rings (outline and holes, by odd
    and even crossings) and in none of ``caps``: the middle of the widest
    such interval, along the lines halfway between consecutive heights of
    the vertices, checked exactly."""
    heights = sorted({pts[i][1] for ring in rings for i in ring})
    found = []
    for lo, hi in zip(heights, heights[1:]):
        y = 0.5 * (lo + hi)
        xs = _crossings(y, rings, pts)
        cuts = sorted(set(xs + _circle_crossings(y, caps)))
        for x0, x1 in zip(cuts, cuts[1:]):
            x = 0.5 * (x0 + x1)
            if x1 > x0 and sum(1 for v in xs if v < x) % 2 == 1:
                found.append((-(x1 - x0), y, x))
    for _w, y, x in sorted(found):
        q = (x, y)
        if _inside(q, rings, pts) and not any(in_cap(q, cap) for cap in caps):
            return q
    raise SeedError("no interior point")


def _inside(p: Point, rings, pts, holes_from: int = 1) -> bool:
    """Strictly inside the first ring and outside the others (exact winding
    numbers of straight chords)."""
    ws = [g._winding(p, tuple(ring), pts, {}) for ring in rings]
    return ws[0] != 0 and all(w == 0 for w in ws[holes_from:])


def _caps(m: g.MeshInput, disc: Discretization, rings) -> list[Cap]:
    """The caps of the pieces of every arc on ``rings`` (rings of point
    indices of the input)."""
    pts = disc.points
    by_key = {g._key(ds.segment.a, ds.segment.b): ds for ds in disc.segments}
    out = []
    for ring in rings:
        for i, j in g._ring_edges(ring):
            ds = by_key[g._key(i, j)]
            if ds.segment.arc is not None:
                c = ds.segment.arc.centre
                out += [(pts[u], pts[v], c) for u, v in zip(ds.nodes, ds.nodes[1:])]
    return out


def build(m: g.MeshInput, disc: Discretization) -> PSLG:
    """The PSLG of a valid input and its discretization."""
    pts = disc.points
    segs = g.segments(m)
    label_of = {g._key(s.a, s.b): k for k, s in enumerate(segs)}
    pieces = []
    for ds in disc.segments:
        label = label_of[g._key(ds.segment.a, ds.segment.b)]
        pieces += [(u, v, label) for u, v in zip(ds.nodes, ds.nodes[1:])]
    seeds = []
    for r, region in enumerate(m.regions):
        rings = [_ring_chain(m, disc, region.outline)] + [_ring_chain(m, disc, h)
                                                           for h in region.holes]
        try:
            p = interior_point(rings, pts, _caps(m, disc, (region.outline, *region.holes)))
        except SeedError:
            raise SeedError(f"region {r}: no point strictly inside it and out of the caps "
                            "of its arcs") from None
        seeds.append((p, r, region.material))
    # a hole is a void when no region is inside it: the seed of every
    # region is strictly inside its outline, so a hole filled by one region
    # or by several holds their seeds (spec 004, T5: a hole filled by two
    # regions, an excavation split in two by a stage boundary, was taken
    # for a void because no single outline was the hole's ring)
    voids = []
    for region in m.regions:
        for hole in region.holes:
            ring = _ring_chain(m, disc, hole)
            if not any(_inside(p, [ring], pts) for p, _r, _mat in seeds):
                voids.append(interior_point([ring], pts, _caps(m, disc, (hole,))))
    arcs = {k: s.arc.centre for k, s in enumerate(segs) if s.arc is not None}
    vertices = list(pts) + window_corners(m, disc, pieces)
    return PSLG(tuple(vertices), tuple(pieces), tuple(seeds), tuple(voids), arcs)


def window_corners(m: g.MeshInput, disc: Discretization, pieces) -> list[Point]:
    """The corners of the windows that are strictly inside a region of the
    domain of chords, not on a piece, in no cap of an arc (the core refuses
    a vertex there; a corner within a sagitta of the boundary is left out)
    and not already a vertex, in the order of the windows and of their
    corners written one way (``geometry.canonical_polygon``), each once."""
    pts = disc.points
    rings_of = [[_ring_chain(m, disc, region.outline)]
                + [_ring_chain(m, disc, h) for h in region.holes] for region in m.regions]
    caps = _caps(m, disc, [ring for region in m.regions
                           for ring in (region.outline, *region.holes)])
    seen = set(pts)
    out = []
    for window in m.settings.windows:
        for corner in g.canonical_polygon(window.polygon):      # as written or not (T29)
            p = (float(corner[0]), float(corner[1]))
            if p in seen:
                continue
            if any(g._on_closed_segment(p, pts[u], pts[v]) for u, v, _lab in pieces):
                continue
            if any(in_cap(p, cap) for cap in caps):
                continue
            if any(_inside(p, rings, pts) for rings in rings_of):
                out.append(p)
                seen.add(p)
    return out


def onto_arcs(points: Sequence[Point], chains: Mapping[int, Sequence[Sequence[int]]],
              arcs: Mapping[int, Point]) -> tuple[tuple[Point, ...], tuple[int, ...]]:
    """D13: every vertex strictly inside a chord of an arc, taken radially
    onto the arc's circle. ``chains[label]`` lists, for each piece of that
    segment, the vertices along it from end to end as the triangulation left
    them. Returns the new points and the vertices moved."""
    out = list(points)
    moved = []
    for label, pieces in chains.items():
        centre = arcs.get(label)
        if centre is None:
            continue
        for chain in pieces:
            a, b = points[chain[0]], points[chain[-1]]
            r = 0.5 * (math.dist(a, centre) + math.dist(b, centre))
            for v in chain[1:-1]:
                p = points[v]
                d = math.dist(p, centre)
                out[v] = (centre[0] + r * (p[0] - centre[0]) / d,
                          centre[1] + r * (p[1] - centre[1]) / d)
                moved.append(v)
    return tuple(out), tuple(sorted(set(moved)))
