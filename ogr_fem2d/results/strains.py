# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The strains at the integration points, B u (spec 005, D6).

The engine gives the displacements of every stage, in totals, but not the
strains; they follow from them exactly, with the B matrix of every point
that the engine itself builds (``reference/solver.integration_points``,
from Zienkiewicz and Taylor 2000, Eqs. 2.2-2.4, and in axisymmetry Eqs.
5.5-5.6, with eps_theta = u / r). Nothing is chosen here: the B is the
engine's, point by point, and the product is written with NumPy so that the
84 198 points of case 005 take a fraction of a second.

* ``PointGeometry``: what B u needs of every point (its nodes, dN/dx, dN/dy
  and, in axisymmetry, N/r), and its coordinates, in the engine's order
  (element by element, then the element's rule);
* ``strains``: B u for a displacement, in the ENGINE'S sign (lengthening
  positive, as its strain): (eps_x, eps_y, gamma_xy) in plane strain and
  (eps_r, eps_z, eps_theta, gamma_rz) in axisymmetry, the order of
  ``IntegrationPoint.strain``; the shear is the engineering one. The
  user's sign is put by model/conventions.py (D1).

The points of an element that is not active in the stage get NaN: they have
no strain, as they have no stress (RF-9).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..engine.reference import solver
from ..engine.reference.quadrature import AXISYMMETRIC


@dataclass(frozen=True)
class PointGeometry:
    analysis: str
    nodes: np.ndarray          # (P, n): the nodes of each point's element
    dndx: np.ndarray           # (P, n)
    dndy: np.ndarray           # (P, n)
    n_over_r: np.ndarray       # (P, n) in axisymmetry; (P, 0) in plane strain
    xy: np.ndarray             # (P, 2)
    element: np.ndarray        # (P,)
    per_element: int

    @property
    def components(self) -> int:
        return 4 if self.analysis == AXISYMMETRIC else 3


def geometry(nodes, elements, analysis: str) -> PointGeometry:
    """The points of the mesh, with the engine's own B."""
    model = solver.Model(list(nodes), [tuple(e) for e in elements], [None] * len(elements),
                         frozenset(), analysis)
    points = solver.integration_points(model)
    n = len(elements[0])
    axi = analysis == AXISYMMETRIC
    return PointGeometry(
        analysis,
        np.array([p.nodes for p in points], dtype=np.int64).reshape(len(points), n),
        np.array([p.dndx for p in points], dtype=float).reshape(len(points), n),
        np.array([p.dndy for p in points], dtype=float).reshape(len(points), n),
        (np.array([p.n_over_r for p in points], dtype=float).reshape(len(points), n) if axi
         else np.zeros((len(points), 0))),
        np.array([p.xy for p in points], dtype=float).reshape(len(points), 2),
        np.array([p.element for p in points], dtype=np.int64),
        len(points) // len(elements))


def strains(g: PointGeometry, displacement, active=None) -> np.ndarray:
    """B u at every point, the engine's sign; NaN at the points of the
    elements that are not ``active`` (one flag per element; None, all)."""
    u = np.asarray(displacement, dtype=float).reshape(-1)
    ux, uy = u[0::2][g.nodes], u[1::2][g.nodes]
    out = np.empty((len(g.element), g.components))
    out[:, 0] = np.sum(g.dndx * ux, axis=1)
    out[:, 1] = np.sum(g.dndy * uy, axis=1)
    out[:, -1] = np.sum(g.dndy * ux + g.dndx * uy, axis=1)
    if g.components == 4:
        out[:, 2] = np.sum(g.n_over_r * ux, axis=1)
    if active is not None:
        out[~np.asarray(active, dtype=bool)[g.element]] = np.nan
    return out
