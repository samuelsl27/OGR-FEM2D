# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A point in its element (spec 005, RF-10; D11).

The elements of a mesh with arcs are curved six-node triangles: a point
between the chord and the arc of a side is in the element whose side is the
arc, not in its neighbour across the chord. So the test is the element's
own isoparametric map, inverted by the engine (``reference/loads.
local_coordinates``, Newton from the centroid), and the point is in the
element when its area coordinates are all >= -1e-9 (rounding, the engine's
INSIDE) and the map takes them back to the point.

To find the candidates fast, a uniform grid of the boxes of the elements,
each box widened by 1 % of its diagonal (a side curved within one piece of
10 degrees bulges far less than that out of the box of its six nodes).

``Locator.find(x, y, active)``:

* ``("in", [(element, (L1, L2, L3)), ...])``: every ACTIVE element that
  contains the point, in the order of their indices. A point on a side or a
  node shared by several gives them all: the caller keeps one per material
  (D9, D11);
* ``("excavated", [])``: the point is only in elements that are not active
  in the stage;
* ``("outside", [])``: in no element of the mesh.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

from ..engine.reference import loads, solver

INSIDE = loads.INSIDE
IN, EXCAVATED, OUTSIDE = "in", "excavated", "outside"


class Locator:
    def __init__(self, nodes, elements):
        self.nodes = np.asarray(nodes, dtype=float)
        self.elements = [tuple(int(n) for n in e) for e in elements]
        self.shape = solver.SHAPES[len(self.elements[0])]
        xy = self.nodes[np.asarray(self.elements)]                      # (E, n, 2)
        low, high = xy.min(axis=1), xy.max(axis=1)
        pad = 0.01 * np.hypot(*(high - low).T)[:, None]
        self.low, self.high = low - pad, high + pad
        size = float(np.sqrt(np.mean(np.prod(self.high - self.low, axis=1))))
        self.cell = size if size > 0.0 else 1.0
        self.origin = self.low.min(axis=0)
        self.grid: dict[tuple[int, int], list[int]] = defaultdict(list)
        for e in range(len(self.elements)):
            i0, j0 = self._cell(self.low[e])
            i1, j1 = self._cell(self.high[e])
            for i in range(i0, i1 + 1):
                for j in range(j0, j1 + 1):
                    self.grid[(i, j)].append(e)

    def _cell(self, p) -> tuple[int, int]:
        return (math.floor((p[0] - self.origin[0]) / self.cell),
                math.floor((p[1] - self.origin[1]) / self.cell))

    def contains(self, e: int, x: float, y: float) -> tuple[float, float, float] | None:
        """The area coordinates of (x, y) in element ``e``, or None."""
        xy = [tuple(self.nodes[n]) for n in self.elements[e]]
        try:
            lc = loads.local_coordinates(self.shape, xy, x, y)
        except (ValueError, ZeroDivisionError, ArithmeticError):
            return None
        if not all(math.isfinite(v) for v in lc) or min(lc) < -INSIDE:
            return None
        n = self.shape.shape_functions(*lc)
        px = sum(n[a] * xy[a][0] for a in range(len(n)))
        py = sum(n[a] * xy[a][1] for a in range(len(n)))
        scale = max(self.high[e] - self.low[e])
        if math.hypot(px - x, py - y) > 1e-9 * scale:
            return None                        # Newton stopped short of the point
        return lc

    def find(self, x: float, y: float, active=None):
        candidates = self.grid.get(self._cell((x, y)), [])
        hits = []
        for e in sorted(candidates):
            if not (self.low[e][0] <= x <= self.high[e][0] and self.low[e][1] <= y <= self.high[e][1]):
                continue
            lc = self.contains(e, x, y)
            if lc is not None:
                hits.append((e, lc))
        if active is not None:
            live = [(e, lc) for e, lc in hits if active[e]]
            if live:
                return IN, live
            return (EXCAVATED, []) if hits else (OUTSIDE, [])
        return (IN, hits) if hits else (OUTSIDE, [])
