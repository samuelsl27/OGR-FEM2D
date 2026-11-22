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
  point inside every void (a hole of a region that no region fills), so the
  triangulation knows what to mesh.

The domain the triangulation sees is that of the chords: the polygon of the
discretized nodes. A seed is found without new dependencies: along a
horizontal line halfway between two heights of the polygon's vertices, the
widest interval inside it (crossings of the rings, odd-even), its middle;
then checked inside with the exact winding numbers of ``geometry``.

D13: the refinement may add vertices on a chord of an arc (Shewchuk 2002a,
§3.1: it splits encroached subsegments at their middle). ``onto_arcs`` takes
each such vertex radially onto its circle; the jacobian of the elements that
use it is then checked (``checks``, RF-13), and the mesh says how many moved
(rule 12).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

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


def interior_point(rings: Sequence[Sequence[int]], pts: Sequence[Point]) -> Point:
    """A point strictly inside the set of rings (outline and holes, by odd
    and even crossings): the middle of the widest interval inside, along the
    lines halfway between consecutive heights of the vertices."""
    heights = sorted({pts[i][1] for ring in rings for i in ring})
    best = None
    for lo, hi in zip(heights, heights[1:]):
        y = 0.5 * (lo + hi)
        xs = _crossings(y, rings, pts)
        for x0, x1 in zip(xs[0::2], xs[1::2]):
            if best is None or x1 - x0 > best[0]:
                best = (x1 - x0, (0.5 * (x0 + x1), y))
    if best is None or best[0] <= 0.0:
        raise SeedError("no interior point")
    return best[1]


def _inside(p: Point, rings, pts, holes_from: int = 1) -> bool:
    """Strictly inside the first ring and outside the others (exact winding
    numbers of straight chords)."""
    ws = [g._winding(p, tuple(ring), pts, {}) for ring in rings]
    return ws[0] != 0 and all(w == 0 for w in ws[holes_from:])


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
        p = interior_point(rings, pts)
        if not _inside(p, rings, pts):
            raise SeedError(f"region {r}: the point found is not strictly inside")
        seeds.append((p, r, region.material))
    filled = {frozenset(g._key(i, j) for i, j in g._ring_edges(region.outline))
              for region in m.regions}
    voids = []
    for region in m.regions:
        for hole in region.holes:
            if frozenset(g._key(i, j) for i, j in g._ring_edges(hole)) not in filled:
                ring = _ring_chain(m, disc, hole)
                p = interior_point([ring], pts)
                voids.append(p)
    arcs = {k: s.arc.centre for k, s in enumerate(segs) if s.arc is not None}
    return PSLG(tuple(pts), tuple(pieces), tuple(seeds), tuple(voids), arcs)


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
