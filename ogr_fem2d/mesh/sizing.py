# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The size bound of the refinement (spec 003, RF-5 to RF-7, D5 and D9).

Ruppert's algorithm accepts an upper bound on the edge lengths (or areas) of
the triangles that is a function of their position; triangles above it are
split whether they are skinny or not, and as long as the bound is everywhere
above a positive constant the refinement still terminates (Shewchuk 2002a,
§3.1, p. 11). The bound here is the smallest of those that cover a point:

* the global one: the h of a uniform mesh (given, or from a number of
  elements, ``discretize.uniform_size``), or the optional max_size of a
  graded one (none: the grading of the refinement alone, D5);
* the size of every window or polygon that contains the point, its outline
  included (D9: a local bound, not centroids inserted).

Where it is evaluated for a triangle (its centroid, its circumcentre) is the
refinement's business; this is the function.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from . import geometry as g
from .discretize import uniform_size

Point = tuple[float, float]


def _in_polygon(p: Point, poly: tuple[Point, ...]) -> bool:
    """Inside a simple polygon of either orientation, or on its outline
    (exact)."""
    ring = tuple(range(len(poly)))
    for k in range(len(poly)):
        if g._on_closed_segment(p, poly[k], poly[(k + 1) % len(poly)]):
            return True
    return g._winding(p, ring, poly, {}) != 0


@dataclass(frozen=True)
class SizeBound:
    """The bound at a point: ``global_size`` (None: no bound) and the
    windows, (polygon, size)."""
    global_size: float | None
    windows: tuple[tuple[tuple[Point, ...], float], ...]

    def __call__(self, x: float, y: float) -> float:
        """The bound at (x, y); math.inf where there is none."""
        best = math.inf if self.global_size is None else self.global_size
        for poly, size in self.windows:
            if size < best and _in_polygon((x, y), poly):
                best = size
        return best

    @property
    def floor(self) -> float | None:
        """The smallest bound anywhere: positive, as the termination needs."""
        sizes = [s for _p, s in self.windows]
        if self.global_size is not None:
            sizes.append(self.global_size)
        return min(sizes) if sizes else None


def size_bound(m: g.MeshInput) -> SizeBound:
    """The bound of a valid input's settings."""
    st = m.settings
    if st.kind == g.UNIFORM:
        global_size = uniform_size(m)
    else:
        global_size = None if st.max_size is None else float(st.max_size)
    windows = tuple((tuple(w.polygon), float(w.size)) for w in st.windows)
    return SizeBound(global_size, windows)
