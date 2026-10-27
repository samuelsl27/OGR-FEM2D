# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The Rust variant of the engine behind the common interface (spec 001, T12):
a thin layer over the compiled module ogr_fem2d._engine (rust/src/lib.rs).

The module is built with maturin (``maturin develop --release`` in the
project's environment, or the wheel). Importing this file without it raises
ImportError, so tests/_variants.py notices that the variant is missing.

All the work per integration point is in Rust; here only the arrays are put
in the layout the module expects (contiguous float64 and int64) and a point
the module could not update is turned into the engine's StateUpdateError,
with its element and point, as the other variants report it.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import numpy as np

from ogr_fem2d import _engine
from ogr_fem2d.engine import interface
from ogr_fem2d.engine.reference.solver import StateUpdateError

_REFUSED = ("return to the apex with psi = 0 (or phi = 0): the flow rule "
            "produces no volumetric plastic strain, so no state satisfies it "
            "(de Souza Neto et al. 2008, p. 300)")


def _f64(a) -> np.ndarray:
    return np.ascontiguousarray(a, dtype=np.float64)


class _Prepared:
    def __init__(self, g: interface.Geometry):
        if g.nodes.shape[1] != 6:
            # spec 002: the three-node triangle reaches Rust in task T13
            raise NotImplementedError("the Rust variant has only the six-node "
                                      "triangle so far (spec 002, T13)")
        self.g = g
        self.nodes = np.ascontiguousarray(g.nodes, dtype=np.int64)
        self.dndx, self.dndy = _f64(g.dndx), _f64(g.dndy)
        self.weight, self.materials = _f64(g.weight), _f64(g.materials)

    def _check(self, failed: int) -> None:
        if failed >= 0:
            raise StateUpdateError(int(self.g.element[failed]),
                                   int(self.g.index[failed]), None, None,
                                   _REFUSED)

    def internal_forces(self, stresses):
        return _engine.internal_forces(self.nodes, self.dndx, self.dndy,
                                       self.weight, _f64(stresses),
                                       self.g.n_dofs)

    def integrate(self, start, strains):
        stresses, plastic, tangents, failed = _engine.integrate(
            self.materials, _f64(start), _f64(strains))
        self._check(failed)
        return interface.Integration(stresses, plastic, tangents)

    def update(self, start, du):
        stresses, f_int, plastic, tangents, stiffness, failed = _engine.update(
            self.nodes, self.dndx, self.dndy, self.weight, self.materials,
            _f64(start), _f64(du))
        self._check(failed)
        return interface.PointsUpdate(stresses, f_int, plastic, tangents,
                                      stiffness)


class RustVariant:
    """The Rust variant behind the common interface (spec 001, T12)."""
    name = "rust"

    def prepare(self, g: interface.Geometry) -> _Prepared:
        return _Prepared(g)


RUST = RustVariant()
