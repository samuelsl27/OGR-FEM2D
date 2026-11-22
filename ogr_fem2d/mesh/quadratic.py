# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
From three-node to six-node triangles (spec 003, RF-10, D4).

The quality triangulation is made of straight triangles: Delaunay refinement
does not treat curves (Shewchuk 2002a, p. 1). The six-node triangle is made
afterwards, one mid-side node per side, shared by the two elements of the
side:

* on a straight side, its middle point;
* on a side that is a piece of an arc of the geometry, the middle of that
  piece of arc: c + R (m - c) / |m - c|, m being the middle of the chord
  (the arc is the minor one: less than 180 degrees). That is the construction
  of the radial mesh of spec 001 (``engine/mesh_radial.py``), validated
  there: the isoparametric side then passes through three points of the
  circle, and its distance from the chord at the middle is the sagitta.

Node order of every element (Zienkiewicz and Taylor 2000, p. 182, fig.
8.15(b), the order of ``engine/reference/element_t6.py``): the three corners
anticlockwise, then the mid-side nodes of sides 0-1, 1-2 and 2-0. Numbering:
the corners keep their numbers; the mid-side nodes follow, in the order their
side is first met going through the elements and their sides, so the same
mesh gives the same nodes (D11).

Whether the curved element is valid (its jacobian) is checked elsewhere
(``checks.py``, RF-13).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

Point = tuple[float, float]


def edge_key(i: int, j: int) -> tuple[int, int]:
    """The undirected key of the side between nodes i and j."""
    return (i, j) if i < j else (j, i)


@dataclass(frozen=True)
class QuadraticMesh:
    """Six-node triangles: the nodes (corners first, then the mid-side
    nodes), the elements, and the mid-side node of every side."""
    nodes: tuple[Point, ...]
    elements: tuple[tuple[int, int, int, int, int, int], ...]
    mid_of: Mapping[tuple[int, int], int]


def arc_middle(a: Point, b: Point, centre: Point) -> Point:
    """The middle of the minor arc from a to b about ``centre``."""
    r = 0.5 * (math.dist(a, centre) + math.dist(b, centre))
    mx, my = 0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1])
    dx, dy = mx - centre[0], my - centre[1]
    d = math.hypot(dx, dy)
    return (centre[0] + r * dx / d, centre[1] + r * dy / d)


def promote(nodes: Sequence[Point], triangles: Sequence[tuple[int, int, int]],
            arc_edges: Mapping[tuple[int, int], Point] | None = None) -> QuadraticMesh:
    """The six-node mesh of a three-node one. ``arc_edges`` maps the key of
    every side that is a piece of an arc (``edge_key``) to the arc's centre."""
    arc_edges = arc_edges or {}
    out_nodes = list(nodes)
    mid_of: dict[tuple[int, int], int] = {}
    elements = []
    for tri in triangles:
        mids = []
        for k in range(3):
            i, j = tri[k], tri[(k + 1) % 3]
            key = edge_key(i, j)
            if key not in mid_of:
                a, b = nodes[i], nodes[j]
                centre = arc_edges.get(key)
                if centre is None:
                    p = (0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1]))
                else:
                    p = arc_middle(a, b, centre)
                mid_of[key] = len(out_nodes)
                out_nodes.append(p)
            mids.append(mid_of[key])
        elements.append((tri[0], tri[1], tri[2], mids[0], mids[1], mids[2]))
    return QuadraticMesh(tuple(out_nodes), tuple(elements), dict(mid_of))
