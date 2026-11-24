# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The queries of a results file (spec 005, RF-11 to RF-13 and RF-15; D9,
D12, D14).

Every value is a field quantity of the catalogue (``quantities``), in the
user's convention (D1) and in the stored units (m, kN, kPa; the table
converts, D15). Each row says where its value comes from (H6):

* ``point``: the value at an integration point, as the engine gave it;
* ``fe``: a displacement, the finite-element field, its shape functions
  times the nodal values;
* ``spr``: a stress or a strain from the values recovered at the nodes
  (``recovery``, D5), interpolated with the element's shape functions
  (Zienkiewicz and Taylor 2000, Eq. 14.27); ``element`` when some node took
  its element's own field, ``spr+element`` when both;
* no value, with the reason: ``excavated`` (in an element not active in the
  stage), ``outside`` (in no element), ``removed`` (a node without an active
  element: it keeps its displacement but has no stress).

A stress or a strain is recovered and interpolated as a TENSOR, and the
quantity (sigma_1, q, ...) is computed from the tensor at the point: the
principal stress of the interpolated tensor, not the interpolation of the
principal stresses.

Where a point is on a contact between materials, a stress or a strain has
one row per material, in the order of the materials, at the same distance:
the jump is shown, not averaged (D9). A displacement, continuous, has one.

``View(results, stage)`` keeps what the queries of a stage share (the
locator, the tensors, the recovered values); the functions take it.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ..engine.reference import solver
from ..model import conventions
from . import locate, quantities as qt, recovery, store

POINT, FE = "point", "fe"


@dataclass(frozen=True)
class Row:
    point: int                      # the index of the queried point
    x: float
    y: float
    distance: float | None          # along the query; None where it has no sense
    value: float | None
    element: int | None = None
    material: int | None = None
    source: str = ""
    reason: str = ""


@dataclass(frozen=True)
class Query:
    quantity: str
    stage: int
    stage_id: str
    rows: tuple[Row, ...]
    what: str                       # "line", "boundary", "nodes", "points", "history"
    method: str                     # how the values were obtained

    @property
    def unit(self) -> str:
        return qt.get(self.quantity).unit

    @property
    def convention(self) -> str:
        return qt.get(self.quantity).convention

    def values(self) -> list[float | None]:
        return [r.value for r in self.rows]


def locator(results: store.Results) -> locate.Locator:
    """The locator of the mesh of ``results``, made once and kept with it
    (no state outside the object, rule 5)."""
    if getattr(results, "_locator", None) is None:
        mesh = results.mesh()
        results._locator = locate.Locator(mesh.nodes, mesh.elements)
    return results._locator


class View:
    """A stage of a results file, as the queries need it."""

    def __init__(self, results: store.Results, stage: int):
        self.results, self.stage = results, stage
        self.mesh = results.mesh()
        self.analysis = results.header.analysis
        self.info = results.stage_info(stage)
        self.active = results.field(stage, "active").astype(bool)
        self.locator = locator(results)
        self.shape = solver.SHAPES[self.mesh.elements.shape[1]]
        self._cache: dict = {}

    # ------------------------------------------------ the user's tensors
    def displacement(self) -> np.ndarray:
        if "u" not in self._cache:
            self._cache["u"] = conventions.user_displacement(
                self.results.field(self.stage, "displacement"))
        return self._cache["u"]

    def tensor(self, kind: str) -> np.ndarray:
        """The user's stress or strain (P, 4) at the points."""
        if kind not in self._cache:
            if kind == qt.STRESS:
                t = conventions.user_stress(self.results.field(self.stage, "stress"))
            else:
                t = qt.strain4(conventions.user_strain(self.results.field(self.stage, "strain")),
                               self.analysis)
            self._cache[kind] = t
        return self._cache[kind]

    def recovered(self, kind: str) -> recovery.Recovered:
        key = ("recovered", kind)
        if key not in self._cache:
            m = self.mesh
            self._cache[key] = recovery.recover(m.nodes, m.elements, m.element_material,
                                                self.active, m.points, m.point_element,
                                                self.tensor(kind))
        return self._cache[key]

    # ------------------------------------------------ values at a point
    def at(self, quantity: str, x: float, y: float):
        """[(value, element, material, source)] at (x, y), one per material
        for a stress or a strain, one for a displacement; or the reason
        there is none."""
        kind = qt.get(quantity).kind
        status, hits = self.locator.find(x, y, self.active)
        if status != locate.IN:
            return status
        material = self.mesh.element_material
        out, seen = [], set()
        for e, lc in hits:
            mat = int(material[e])
            if mat in seen:
                continue
            seen.add(mat)
            n = np.asarray(self.shape.shape_functions(*lc))
            nodes = self.mesh.elements[e]
            if kind == qt.DISPLACEMENT:
                tensor, source = n @ self.displacement()[nodes], FE
            else:
                rec = self.recovered(kind)
                tensor = n @ rec.values[e]
                kinds = sorted({recovery.SOURCES[int(s)] for s in rec.source[e]})
                source = "+".join(kinds)
            out.append((float(qt.of(quantity, tensor)), int(e), mat, source))
            if kind == qt.DISPLACEMENT:
                break
        return out


def method_of(quantity: str) -> str:
    if qt.get(quantity).kind == qt.DISPLACEMENT:
        return "finite-element field (shape functions)"
    return ("superconvergent patch recovery per material (Zienkiewicz and Taylor 2000, §14.4), "
            "interpolated with the shape functions (Eq. 14.27)")


def _rows_at(view: View, quantity: str, points, distances) -> list[Row]:
    rows = []
    for i, ((x, y), d) in enumerate(zip(points, distances)):
        got = view.at(quantity, x, y)
        if isinstance(got, str):
            rows.append(Row(i, x, y, d, None, reason=got))
            continue
        for value, e, mat, source in got:
            rows.append(Row(i, x, y, d, value, e, mat, source))
    return rows


# --------------------------------------------------------------- the line
def spread(vertices, n: int | None):
    """The points of a polyline and their distance from the first: its
    vertices (``n`` None), or ``n`` >= 2 points at equal distances along
    the whole of it, both ends included."""
    v = [(float(x), float(y)) for x, y in vertices]
    if len(v) < 2:
        raise ValueError("a line needs two points or more")
    lengths = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(v, v[1:])]
    if any(L == 0.0 for L in lengths):
        raise ValueError("two consecutive points of the line are the same")
    cumulative = [0.0]
    for L in lengths:
        cumulative.append(cumulative[-1] + L)
    if n is None:
        return v, cumulative
    if n < 2:
        raise ValueError("a line needs n >= 2 points")
    total = cumulative[-1]
    points, distances = [], []
    for i in range(n):
        d = total * i / (n - 1)
        k = min(max(0, np.searchsorted(cumulative, d, side="right") - 1), len(lengths) - 1)
        t = (d - cumulative[k]) / lengths[k]
        a, b = v[k], v[k + 1]
        points.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
        distances.append(d)
    points[-1] = v[-1]                       # the end exactly
    return points, distances


def line(view: View, quantity: str, vertices, n: int | None = None) -> Query:
    """The quantity along a line or a polyline (RF-11)."""
    points, distances = spread(vertices, n)
    return Query(quantity, view.stage, view.info["id"],
                 tuple(_rows_at(view, quantity, points, distances)), "line", method_of(quantity))


# --------------------------------------------- every node and every point
def all_nodes(view: View, quantity: str) -> Query:
    """The quantity at every node (RF-13): a displacement once per node; a
    stress or a strain once per node and material, or without value at a
    node with no active element."""
    m = view.mesh
    kind = qt.get(quantity).kind
    rows = []
    if kind == qt.DISPLACEMENT:
        values = qt.of(quantity, view.displacement())
        for i, (x, y) in enumerate(m.nodes):
            rows.append(Row(i, float(x), float(y), None, float(values[i]), source=FE))
        return Query(quantity, view.stage, view.info["id"], tuple(rows), "nodes", method_of(quantity))
    rec = view.recovered(kind)
    value = qt.of(quantity, rec.values)                         # (E, n)
    first: dict = {}
    for e in np.flatnonzero(view.active):
        mat = int(m.element_material[e])
        for a, node in enumerate(m.elements[e]):
            key = (int(node), mat)
            if key not in first:
                first[key] = (float(value[e, a]), int(e), recovery.SOURCES[int(rec.source[e, a])])
    with_value = {node for node, _ in first}
    for i, (x, y) in enumerate(m.nodes):
        if i not in with_value:
            rows.append(Row(i, float(x), float(y), None, None, reason="removed"))
            continue
        for (node, mat) in sorted(k for k in first if k[0] == i):
            v, e, source = first[(node, mat)]
            rows.append(Row(i, float(x), float(y), None, v, e, mat, source))
    return Query(quantity, view.stage, view.info["id"], tuple(rows), "nodes", method_of(quantity))


def all_points(view: View, quantity: str) -> Query:
    """The quantity at every integration point, the engine's value (RF-13).
    A displacement is not a quantity of the points: ``all_nodes``."""
    kind = qt.get(quantity).kind
    if kind == qt.DISPLACEMENT:
        raise ValueError(f"{quantity!r} is a displacement: it is at the nodes (all_nodes)")
    m = view.mesh
    values = qt.of(quantity, view.tensor(kind))
    rows = []
    for i, ((x, y), e) in enumerate(zip(m.points, m.point_element)):
        if view.active[e]:
            rows.append(Row(i, float(x), float(y), None, float(values[i]), int(e),
                            int(m.element_material[e]), POINT))
        else:
            rows.append(Row(i, float(x), float(y), None, None, int(e), int(m.element_material[e]),
                            reason="excavated"))
    return Query(quantity, view.stage, view.info["id"], tuple(rows), "points",
                 "the integration points, as the engine gave them")
