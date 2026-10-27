# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.1 (spec 001, T10) — the common interface of the variants of the engine
(ogr_fem2d.engine.interface): every variant keeps its contract, the solver
goes through it with one call per global iteration, and the validation cases
run with any variant.

Invariants protected:

* **the variants the repository promises are there** (tests/_variants.py,
  EXPECTED): a missing one fails here, it is not skipped;
* **the contract**, for every variant, on a small model with both laws
  (Mohr-Coulomb elements and elastic ones): the shapes and types of what
  comes back; update() is integrate() with the strains B du, plus the
  internal forces of the stresses it returns, plus weight B^T D B of the
  tangents it returns, laid out as stiffness_pattern() says (checked against
  B^T D B built here with the whole B matrix; the plastic tangents are not
  symmetric, psi < phi, so a transposed layout would show);
* **one call per global iteration** (ADR-0001): a variant that only counts
  and delegates to the reference sees exactly one update() per iteration of
  the history, and the solver gives the same result through it;
* **the cases run with any variant**: case 001 through the counting variant,
  and both cases through every variant other than the reference.
"""
from __future__ import annotations

import math

import numpy as np

import _hole
import _variants
import test_validation_cases_v001 as cases
from ogr_fem2d.engine import interface
from ogr_fem2d.engine.reference import mohr_coulomb as mc
from ogr_fem2d.engine.reference import solver
from ogr_fem2d.engine.reference.elastic import Elastic

MC30 = mc.MohrCoulomb(10000.0, 0.2, 3.45, math.radians(30.0), math.radians(30.0))
#: non-associated, so its tangent is NOT symmetric and a transposed layout of
#: the stiffness values would show
MC15 = mc.MohrCoulomb(10000.0, 0.2, 3.45, math.radians(30.0), math.radians(15.0))
ELASTIC = Elastic(10000.0, 0.2)


def _mixed_model():
    """The coarse ring, non-associated Mohr-Coulomb with every fourth
    element elastic."""
    mesh, model = _hole.model(21.0, 4, 2, 1.5, MC15)
    materials = [ELASTIC if e % 4 == 3 else MC15 for e in range(len(mesh.elements))]
    return mesh, solver.Model(model.nodes, model.elements, materials,
                              model.restrained)


def _state(mesh, model):
    """A plastic state: the converged end of the excavation, and a seeded
    displacement increment on top of it."""
    result = solver.solve_stage(model, [_hole.FIELD] * (3 * len(mesh.elements)),
                                [0.0] * (2 * len(mesh.nodes)), 3, 1e-10, 25)
    start = np.array(result.stresses)
    rng = np.random.default_rng(5)
    du = 2e-3 * rng.standard_normal(2 * len(mesh.nodes))
    return start, du


class TestTheVariants:
    def test_the_promised_variants_are_there(self):
        assert set(_variants.EXPECTED) <= set(_variants.available())


class TestTheContract:
    def test_every_variant_keeps_it(self):
        mesh, model = _mixed_model()
        points = solver.integration_points(model)
        g = solver.geometry(model, points)
        start, du = _state(mesh, model)
        n, n_dofs = len(points), g.n_dofs
        rows, cols = interface.stiffness_pattern(g)
        for name, variant in _variants.available().items():
            prepared = variant.prepare(g)
            up = prepared.update(start, du)
            assert up.stresses.shape == (n, 4), name
            assert up.internal_forces.shape == (n_dofs,), name
            assert up.plastic.shape == (n,) and up.plastic.dtype == bool, name
            assert up.tangents.shape == (n, 3, 3), name
            assert up.stiffness.shape == (n, 144), name
            assert up.plastic.any() and not up.plastic.all(), name
            # update = integrate with B du
            strains = np.array([p.strain(list(du)) for p in points])
            alone = prepared.integrate(start, strains)
            assert np.array_equal(alone.plastic, up.plastic), name
            assert np.allclose(alone.stresses, up.stresses, rtol=0, atol=1e-12 * 30), name
            assert np.allclose(alone.tangents, up.tangents, rtol=0, atol=1e-9), name
            # + the internal forces of its stresses
            f = prepared.internal_forces(up.stresses)
            assert np.allclose(f, up.internal_forces, rtol=0,
                               atol=1e-12 * np.abs(f).max()), name
            # + weight B^T D B of its tangents, where the pattern says: built
            # here independently, with the whole B (Eq. 2.4) and products
            mine = np.zeros((n_dofs, n_dofs))
            np.add.at(mine, (rows, cols), up.stiffness.ravel())
            ref = np.zeros((n_dofs, n_dofs))
            for p, d in zip(points, up.tangents):
                b = np.zeros((3, 12))
                b[0, 0::2] = p.dndx
                b[1, 1::2] = p.dndy
                b[2, 0::2] = p.dndy
                b[2, 1::2] = p.dndx
                dofs = [2 * nd + c for nd in p.nodes for c in (0, 1)]
                ref[np.ix_(dofs, dofs)] += p.weight * b.T @ d @ b
            assert np.allclose(mine, ref, rtol=0, atol=1e-10 * np.abs(ref).max()), name
            # the tangent of a non-associated plastic point is not symmetric,
            # so the check above sees a transposed layout
            asym = max(np.abs(d - d.T).max() for d in up.tangents[up.plastic])
            assert asym > 1e-3 * np.abs(up.tangents).max(), name


class _Counting:
    """A variant that delegates to the reference and counts the calls."""
    name = "counting"

    def __init__(self):
        self.updates = 0

    def prepare(self, g):
        inner = solver.REFERENCE.prepare(g)
        outer = self

        class Prepared:
            def internal_forces(self, stresses):
                return inner.internal_forces(stresses)

            def integrate(self, start, strains):
                return inner.integrate(start, strains)

            def update(self, start, du):
                outer.updates += 1
                return inner.update(start, du)

        return Prepared()


class TestOneCallPerIteration:
    def test_one_update_per_iteration_and_the_same_result(self):
        counting = _Counting()
        # all Mohr-Coulomb: the last step yields and needs several iterations
        mesh, model = _hole.model(21.0, 4, 2, 1.5, MC30)
        n_points = 3 * len(mesh.elements)
        args = (model, [_hole.FIELD] * n_points, [0.0] * (2 * len(mesh.nodes)),
                3, 1e-10, 25)
        through = solver.solve_stage(*args, variant=counting)
        direct = solver.solve_stage(*args)
        iterations = sum(1 for _s, it, _r in through.history if it > 0)
        assert counting.updates == iterations > 3
        assert through.displacement == direct.displacement
        assert through.stresses == direct.stresses


class TestCasesWithAnyVariant:
    def test_case_001_through_the_interface(self):
        counting = _Counting()
        cases.check_001(counting)
        assert counting.updates >= 1

    def test_both_cases_with_every_other_variant(self):
        for name, variant in _variants.available().items():
            if name == "reference":
                continue            # test_validation_cases_v001 runs it
            cases.check_001(variant)
            cases.check_002(variant)
