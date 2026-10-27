# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The common interface of the three variants of the engine: Python reference,
NumPy vectorised and Rust (spec 001, RF-3; ADR-0001).

The boundary is ONE CALL PER GLOBAL ITERATION (ADR-0001, D7): Python sets up
the stage, solves the linear systems and drives steps and iterations; once
per iteration it asks the variant, "given the displacement increment of the
step, update the stress of every integration point from the converged state
of the step start, and give back the internal forces and the tangent
stiffness". Everything that is per integration point is the variant's.

What crosses it, as NumPy arrays of float64 (int64 for indices), so that the
three variants receive exactly the same numbers:

* once per stage, ``Geometry``: for every integration point the k nodes of
  its element (k = 3 or 6, one kind per model; spec 002, T4), dN/dx and dN/dy
  of its k shape functions, and its weight w det J / 2
  (solver.integration_points computes them); and the material of every
  point as one row of ``MATERIAL_COLUMNS``;
* per iteration, the stresses at the step start (n, 4) — sigma_xx, sigma_yy,
  sigma_zz, tau_xy, tension positive — and the displacement increment of the
  step (n_dofs,).

What comes back, ``PointsUpdate``: the stresses (n, 4), the internal forces
(n_dofs,), whether each point is plastic (n,), its consistent tangent
(n, 3, 3), and the tangent stiffness of each point, weight B^T D B, as a
2k x 2k block (n, 4k^2), row-major in the dofs (u1, v1, ..., uk, vk) of its
nodes; ``stiffness_pattern`` gives the global row and column of each value,
so the solver assembles K_T with one sparse constructor.

A point whose stress cannot be updated raises solver.StateUpdateError with
its element and point, in every variant (RF-4).

``integrate`` is the constitutive integration alone, for the identity at a
material point and for the measure of criterion 5 of ADR-0001.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

#: Columns of the material table: kind (0 elastic, 1 Mohr-Coulomb), E, nu,
#: cohesion, phi and psi (radians). Elastic rows leave the last three at 0.
MATERIAL_COLUMNS = ("kind", "young", "poisson", "cohesion", "phi", "psi")
ELASTIC, MOHR_COULOMB = 0, 1


@dataclass(frozen=True)
class Geometry:
    """The integration points of a stage, as arrays (n points)."""
    n_dofs: int
    nodes: np.ndarray          # (n, k) int64, k = 3 or 6
    dndx: np.ndarray           # (n, k)
    dndy: np.ndarray           # (n, k)
    weight: np.ndarray         # (n,)
    element: np.ndarray        # (n,) int64, the element of each point
    index: np.ndarray          # (n,) int64, its place in the element's rule
    xy: np.ndarray             # (n, 2), where the point is
    materials: np.ndarray      # (n, 6), one row of MATERIAL_COLUMNS per point


@dataclass(frozen=True)
class PointsUpdate:
    """What one iteration gives back."""
    stresses: np.ndarray       # (n, 4)
    internal_forces: np.ndarray  # (n_dofs,)
    plastic: np.ndarray        # (n,) bool
    tangents: np.ndarray       # (n, 3, 3)
    stiffness: np.ndarray      # (n, 4 k^2)


@dataclass(frozen=True)
class Integration:
    """The constitutive integration alone."""
    stresses: np.ndarray       # (n, 4)
    plastic: np.ndarray        # (n,) bool
    tangents: np.ndarray       # (n, 3, 3)


class Prepared(Protocol):
    """A variant set up for one stage."""

    def internal_forces(self, stresses: np.ndarray) -> np.ndarray:
        """int B^T sigma dA, assembled (n_dofs,)."""

    def integrate(self, start: np.ndarray, strains: np.ndarray) -> Integration:
        """Stress update of every point from ``start`` (n, 4) with the strain
        increments ``strains`` (n, 3) = (d_eps_xx, d_eps_yy, d_gamma_xy)."""

    def update(self, start: np.ndarray, du: np.ndarray) -> PointsUpdate:
        """THE call per global iteration."""


class Variant(Protocol):
    name: str

    def prepare(self, geometry: Geometry) -> Prepared:
        ...


def material_row(material) -> tuple[float, ...]:
    """The row of MATERIAL_COLUMNS of a material object of the reference
    (elastic.Elastic or mohr_coulomb.MohrCoulomb)."""
    if hasattr(material, "cohesion"):
        return (float(MOHR_COULOMB), material.young, material.poisson,
                material.cohesion, material.phi, material.psi)
    return (float(ELASTIC), material.young, material.poisson, 0.0, 0.0, 0.0)


def stiffness_pattern(geometry: Geometry) -> tuple[np.ndarray, np.ndarray]:
    """Global (rows, cols) of the (n, 4 k^2) stiffness values: for point p,
    value 2k i + j sits at (dof_i, dof_j), dofs = (2 n1, 2 n1 + 1, ...)."""
    m = 2 * geometry.nodes.shape[1]
    dofs = np.empty((len(geometry.nodes), m), dtype=np.int64)
    dofs[:, 0::2] = 2 * geometry.nodes
    dofs[:, 1::2] = 2 * geometry.nodes + 1
    rows = np.repeat(dofs, m, axis=1)        # dof_i repeated over j
    cols = np.tile(dofs, (1, m))             # dof_j cycling within i
    return rows.ravel(), cols.ravel()
