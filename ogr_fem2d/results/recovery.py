# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
From the integration points to the nodes: superconvergent patch recovery,
material by material (spec 005, RF-8, RF-9; D5).

Source: Zienkiewicz, O. C. and Taylor, R. L. (2000). *The Finite Element
Method*, 5th ed., vol. 1, §14.3-14.4, pp. 375-380:

* averaging the element values at the nodes "is not the best for triangles
  and for higher order elements such averaging is inadequate" (§14.3, p.
  376); the recovery here is the superconvergent patch recovery (SPR) of
  §14.4.1;
* each component sigma_i is fitted, over a patch of elements, by a
  polynomial of the degree p of the displacements, sigma* = p a (Eq.
  14.28), minimising the sum of squares at the n sampling points (Eq.
  14.29): a = A^-1 b, A = sum p_k^T p_k, b = sum p_k^T sigma_i(x_k, y_k)
  (Eqs. 14.30-14.31). Here p = [1, x, y] for three-node triangles and
  [1, x, y, x^2, xy, y^2] for six-node ones, in coordinates local to the
  patch (centred on its node and divided by its size, so that A is well
  conditioned: the fit is the same polynomial);
* the patch is assembled at an interior corner node with the elements that
  have it, and determines that node and, with six-node triangles, the
  mid-side nodes of the sides that leave it (Fig. 14.8, p. 378, read on the
  page: the black nodes);
* "on external boundaries and indeed on interfaces where stresses are
  discontinuous the nodal values should be calculated from interior
  patches" (p. 379 and Fig. 14.9): a node on the boundary of the material
  takes the values of the interior patches whose elements have it;
* "as some nodes belong to more than one patch, average values are best
  obtained" (p. 379): a node determined by several patches takes the mean.

The sampling points are the engine's integration points. For the
three-node triangle they are the optimal ones of Fig. 14.6 (the centroid);
for the six-node triangle the three mid-side points of the engine (spec
002, D1) are those of the minimal quadrature, not the optimal ones, and
the seven of axisymmetry are neither (changelog v0.0.11, T7): the fit is
the same, the superconvergence the text promises is not.

Material by material (D5): the patches are made of the ACTIVE elements of
one material, so a node on a contact has one value per material, each from
its side (RF-8), and no element that is not active in the stage takes part
(RF-9).

Own proposal, which the source does not treat (D5): a node that no patch
determines (a material one element thick has no interior node) takes the
field of each of its elements of the material, fitted to the element's own
points with a polynomial of degree p - 1 (the degree of the stresses of
the element) and evaluated at the node, averaged; its source says so
(``ELEMENT``). A patch with fewer points than coefficients, or whose A has
a condition number above 1e10, is not fitted.

The result is per element node, ``values[e, a]``: continuous within a
material, a value per material at a contact; NaN for the elements that are
not active.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np

NONE, SPR, ELEMENT = 0, 1, 2
SOURCES = {NONE: "none", SPR: "spr", ELEMENT: "element"}
MAX_CONDITION = 1e10

#: the corners of each side of a triangle and its mid-side node (six nodes)
SIDES = ((0, 1, 3), (1, 2, 4), (2, 0, 5))


@dataclass(frozen=True)
class Recovered:
    values: np.ndarray            # (E, n, c), NaN for the inactive elements
    source: np.ndarray            # (E, n) of NONE, SPR, ELEMENT
    notes: dict = field(default_factory=dict)


def basis(x, y, degree: int) -> np.ndarray:
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    terms = [np.ones_like(x)]
    if degree >= 1:
        terms += [x, y]
    if degree >= 2:
        terms += [x * x, x * y, y * y]
    return np.stack(terms, axis=-1)


def fit(points, values, degree: int, centre):
    """The polynomial of Eqs. (14.28)-(14.31) through ``points`` (k, 2),
    ``values`` (k, c), in coordinates centred on ``centre``; None if A is
    singular or ill-conditioned. Returns a function of (m, 2) points."""
    pts = np.asarray(points, dtype=float) - centre
    size = float(np.max(np.hypot(pts[:, 0], pts[:, 1]))) if len(pts) else 0.0
    size = size if size > 0.0 else 1.0
    p = basis(pts[:, 0] / size, pts[:, 1] / size, degree)
    if len(p) < p.shape[1]:
        return None
    a = p.T @ p                                         # Eq. (14.31)
    if not np.isfinite(a).all() or np.linalg.cond(a) > MAX_CONDITION:
        return None
    coef = np.linalg.solve(a, p.T @ np.asarray(values, dtype=float))   # Eq. (14.30)

    def at(xy):
        q = np.asarray(xy, dtype=float) - centre
        return basis(q[:, 0] / size, q[:, 1] / size, degree) @ coef
    return at


def recover(nodes, elements, element_material, active, points_xy, point_element,
            values) -> Recovered:
    """The values at the nodes of every active element, material by
    material, of ``values`` (P, c) at the integration points.

    v0.0.15 (spec 006, T32): the same fits, the same sums in the same
    order, with the bookkeeping in plain integers and the values gathered
    at once; with the mesh of case 005 it took 1.15 s and the first drawing
    of a stage waited for it. A test holds it to the v0.0.14 one, bit for
    bit."""
    nodes = np.asarray(nodes, dtype=float)
    elements = np.asarray(elements, dtype=np.int64)
    material = np.asarray(element_material)
    active = np.asarray(active, dtype=bool)
    points_xy = np.asarray(points_xy, dtype=float)
    values = np.asarray(values, dtype=float)
    n_el, n_per = elements.shape
    degree = 2 if n_per == 6 else 1
    comps = values.shape[1]
    point_element = np.asarray(point_element)
    per = len(point_element) // n_el
    out = np.full((n_el, n_per, comps), np.nan)
    source = np.full((n_el, n_per), NONE, dtype=np.int8)
    notes = {"patches": 0, "patches_refused": 0, "nodes_by_element": 0}
    el = elements.tolist()
    own_points = np.arange(per)

    for mat in sorted(set(material[active].tolist())):
        zone = np.flatnonzero(active & (material == mat)).tolist()
        # the sides of the zone, and those with one element: the boundary
        side_count: dict = defaultdict(int)
        for e in zone:
            ne = el[e]
            for a, b, _m in SIDES:
                p, q = ne[a], ne[b]
                side_count[(p, q) if p < q else (q, p)] += 1
        boundary = set()
        for e in zone:
            ne = el[e]
            for a, b, m in SIDES:
                p, q = ne[a], ne[b]
                if side_count[(p, q) if p < q else (q, p)] == 1:
                    boundary.update((p, q))
                    if n_per == 6:
                        boundary.add(ne[m])
        around: dict = defaultdict(list)
        for e in zone:
            for a in range(3):
                around[el[e][a]].append(e)
        total: dict = {}
        count: dict = defaultdict(int)

        for centre_node in sorted(around):
            if centre_node in boundary:
                continue
            patch = around[centre_node]
            idx = (np.asarray(patch)[:, None] * per + own_points).ravel()
            poly = fit(points_xy[idx], values[idx], degree, nodes[centre_node])
            if poly is None:
                notes["patches_refused"] += 1
                continue
            notes["patches"] += 1
            determined = {centre_node}
            for e in patch:
                ne = el[e]
                local = ne[:3].index(centre_node)
                if n_per == 6:
                    for a, b, m in SIDES:
                        if local in (a, b):
                            determined.add(ne[m])
                determined.update(n for n in ne if n in boundary)
            ordered = sorted(determined)
            got = poly(nodes[ordered])
            for node, value in zip(ordered, got):
                if node in total:
                    total[node] = total[node] + value
                else:
                    total[node] = value.copy()
                count[node] += 1

        # the nodes no patch determined: the field of their own elements
        fallback: dict = {}
        for e in zone:
            missing = [a for a in range(n_per) if el[e][a] not in total]
            if not missing:
                continue
            idx = np.arange(e * per, (e + 1) * per)
            own = fit(points_xy[idx], values[idx], degree - 1, points_xy[idx].mean(axis=0))
            if own is None:                       # degree - 1 = 0 or 1 always fits here
                own = fit(points_xy[idx], values[idx], 0, points_xy[idx].mean(axis=0))
            for a in missing:
                node = el[e][a]
                fallback.setdefault(node, []).append(own(nodes[[node]])[0])
        for node, got in fallback.items():
            total[node], count[node] = np.mean(got, axis=0), 1
        notes["nodes_by_element"] += len(fallback)

        # each node's value once (the same division), then gathered by element node
        at_node = {node: total[node] / count[node] for node in total}
        z = np.asarray(zone, dtype=np.int64)
        conn = elements[z]                                            # (Z, n)
        used = np.unique(conn)
        index = np.full(int(used.max()) + 1, -1, dtype=np.int64)
        index[used] = np.arange(len(used))
        table = np.array([at_node[int(n)] for n in used])             # (U, c)
        out[z] = table[index[conn]]
        by_element = np.zeros(len(index), dtype=bool)
        by_element[[n for n in fallback if n < len(index)]] = True
        source[z] = np.where(by_element[conn], ELEMENT, SPR)
    return Recovered(out, source, notes)
