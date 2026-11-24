# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A field of the results ready to be drawn: triangles, their values, and the
range of the legend (spec 006, RF-5, D11), without Qt.

``field(view, quantity, level)`` subdivides every active element into
triangles and gives each new vertex its position and its value through the
element's own shape functions (Zienkiewicz and Taylor 2000, Eq. 14.27, as
the queries of spec 005):

* the subdivision is regular in the area coordinates: ``2**level`` parts
  per side, ``4**level`` triangles per element (``level`` 2 by default:
  16). The positions go through the isoparametric map, so a curved side of
  a T6 is drawn curved, on its arc;
* the values of a stress or a strain are those recovered at the nodes, per
  material (spec 005, D5), interpolated with the shape functions; those of
  a displacement, the finite-element field. At the nodes the value drawn is
  the recovered one; a field that the element holds exactly (linear in a
  T3, quadratic in a T6) is drawn exactly at every vertex;
* every element has its own vertices: the picture is continuous inside a
  material and keeps the jump at a contact between two (spec 005, D9);
* ``absolute`` draws the absolute value (spec 005, what it leaves to 006).

The picture is an image, not a number: what is compared with a source are
the queries (spec 005), which interpolate exactly at the point asked; the
picture interpolates linearly inside each small triangle.

``value_range`` gives the range of the legend: ``auto_stage`` (the stage's
smallest and greatest value drawn), ``auto_all`` (those of every stage) or
``custom`` (as given). It is the whole range, extremes included: a peak of
stress at the wall of a tunnel is what is looked for, and a percentile
would hide it (OGR Slip2D fits its factors of safety to the 98th
percentile, for outliers of another kind). The bands, the palette and their
colours are the interface's (``ogr-gui``, ADR-0005).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..engine.reference import solver
from . import quantities as qt
from .queries import View

AUTO_STAGE, AUTO_ALL, CUSTOM = "auto_stage", "auto_all", "custom"
RANGE_MODES = (AUTO_STAGE, AUTO_ALL, CUSTOM)
DEFAULT_LEVEL = 2


@dataclass(frozen=True)
class Field:
    """What is drawn: per element ``S`` vertices and ``T`` triangles."""
    quantity: str
    stage: int
    level: int
    absolute: bool
    xy: np.ndarray          # (V, 2)
    triangles: np.ndarray   # (T, 3), indices into xy
    values: np.ndarray      # (V,)
    element: np.ndarray     # (T,) the element of each triangle
    material: np.ndarray    # (T,)


def subdivision(level: int) -> tuple[np.ndarray, np.ndarray]:
    """The regular subdivision of the triangle in area coordinates: its
    vertices (S, 3) and its triangles (T, 3), anticlockwise as the
    element's corners 1, 2, 3."""
    if not (isinstance(level, int) and 0 <= level <= 6):
        raise ValueError(f"level {level!r} is not an integer from 0 to 6")
    n = 2 ** level
    index = {}
    bary = []
    for j in range(n + 1):              # along L3
        for i in range(n + 1 - j):      # along L2
            index[(i, j)] = len(bary)
            bary.append((1.0 - (i + j) / n, i / n, j / n))
    tris = []
    for j in range(n):
        for i in range(n - j):
            tris.append((index[(i, j)], index[(i + 1, j)], index[(i, j + 1)]))
            if i + j < n - 1:
                tris.append((index[(i + 1, j)], index[(i + 1, j + 1)], index[(i, j + 1)]))
    return np.array(bary), np.array(tris, dtype=np.int64)


def field(view: View, quantity: str, level: int = DEFAULT_LEVEL,
          absolute: bool = False) -> Field:
    """The triangles of ``quantity`` in the stage of ``view`` (see the
    module's notes); no triangle for an inactive element."""
    q = qt.get(quantity)
    mesh = view.mesh
    elements = np.flatnonzero(view.active)
    conn = mesh.elements[elements]
    shape = solver.SHAPES[conn.shape[1]]
    bary, tris = subdivision(level)
    n = np.array([shape.shape_functions(*b) for b in bary])          # (S, nn)
    xy = np.einsum("sn,enk->esk", n, mesh.nodes[conn])                 # (E, S, 2)
    if q.kind == qt.DISPLACEMENT:
        at_nodes = view.displacement()[conn]                           # (E, nn, 2)
    else:
        at_nodes = view.recovered(q.kind).values[elements]             # (E, nn, 4)
    tensor = np.einsum("sn,enc->esc", n, at_nodes)
    values = qt.of(quantity, tensor.reshape(-1, tensor.shape[-1]))
    if absolute:
        values = np.abs(values)
    s = len(bary)
    triangles = (tris[None, :, :] + s * np.arange(len(elements))[:, None, None]).reshape(-1, 3)
    per = len(tris)
    return Field(quantity, view.stage, level, absolute, xy.reshape(-1, 2), triangles,
                 np.asarray(values, dtype=float), np.repeat(elements, per),
                 np.repeat(mesh.element_material[elements], per))


def _min_max(values) -> tuple[float, float] | None:
    ok = values[~np.isnan(values)]
    if not len(ok):
        return None
    return float(ok.min()), float(ok.max())


def value_range(view: View, quantity: str, mode: str = AUTO_STAGE, level: int = DEFAULT_LEVEL,
                absolute: bool = False, low: float | None = None,
                high: float | None = None) -> tuple[float, float]:
    """The (smallest, greatest) of the legend (see the module's notes)."""
    if mode not in RANGE_MODES:
        raise ValueError(f"mode {mode!r} is not one of {RANGE_MODES}")
    if mode == CUSTOM:
        if low is None or high is None or not low < high:
            raise ValueError(f"a custom range needs low < high (got {low!r}, {high!r})")
        return float(low), float(high)
    if low is not None or high is not None:
        raise ValueError(f"low and high are for a custom range; {mode!r} would ignore them "
                         "(rule 7)")
    stages = [view.stage] if mode == AUTO_STAGE else range(view.results.n_stages)
    found = []
    for k in stages:
        v = view if k == view.stage else View(view.results, k)
        got = _min_max(field(v, quantity, level, absolute).values)
        if got is not None:
            found.append(got)
    if not found:
        raise ValueError(f"{quantity!r} has no value to draw in the stages asked")
    return min(lo for lo, _ in found), max(hi for _, hi in found)
