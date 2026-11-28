# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.16 (spec 007, T9; RF-7, RF-8, D5) — the line search of Crisfield, M. A.
(1991), Non-linear Finite Element Analysis of Solids and Structures, vol. 1,
§9.2, pp. 254-265, on the full Newton direction of solver.solve_stage.

Invariants protected:

* **SEARCH is the book's** (pp. 256-261, Figs. 9.2-9.3): from a first trial
  with ratio -1.4, linear interpolation gives "a new estimate for the step
  length of about 0.42" (Fig. 9.2a, p. 256); with no negative ratio it
  extrapolates, at most amp times the largest step so far and never past
  eta_max; an interpolation is moved at least 0.2 of the way; the smallest
  step length reached twice running, or the largest, is the failure
  ICO = 2; each parameter moves the step it returns (rule 7);
* **it changes nothing where it is not asked for or not needed**: without
  it, the numbers of the solver are those of before (the suite); with it,
  an elastic stage takes no search and ends where it ended;
* **it finds equilibrium where Newton alone did not** (RF-8): the 21 m ring
  with 16 x 48 and psi = 0, which no combination of steps and cuts solved
  (changelog v0.0.16, T2), converges with no cut and its u_r(a) is within
  the 2 % of spec 001, D3, of the exact solution of the finite ring
  (salencon_edge_finite) — 0.117 % when this test was written, continuing
  the nested family (1.13 % with 24 x 8);
* **and the footing of case 008** on its coarsest mesh, 5 steps a stage and
  8 cuts, which failed in its first stage, solves its first eight stages;
* **a failed search is a failed increment**: LineSearchError is cut like the
  others, and once the cuts are used up it leaves the stage with its factor
  reached (case 002 on 16 x 64 with psi = 0, still unsolved: changelog);
* **a bad setting is refused with its reason**, by the solver and by the
  engine's model;
* **its searches are counted** in each increment (rule 12).
"""
from __future__ import annotations

import math
import random
from dataclasses import replace

import _footing as ft
import _hole
import test_analysis_v002 as v002
from ogr_fem2d.engine import analysis
from ogr_fem2d.engine import model as em
from ogr_fem2d.engine.compiled import RUST
from ogr_fem2d.engine.reference import mohr_coulomb as mc
from ogr_fem2d.engine.reference import solver

LS = solver.LineSearch()
closed = _hole.closed
MC0 = mc.MohrCoulomb(closed.E, closed.NU, closed.COH, closed.PHI, 0.0)


class TestSearch:
    def test_the_example_of_figure_9_2a(self):
        eta, bound = solver.search([0.0, 1.0], [1.0, -1.4], LS, 0)
        assert abs(eta - 1.0 / 2.4) < 1e-15 and round(eta, 2) == 0.42 and bound == 0

    def test_extrapolation_and_its_bounds(self):
        # ratio 0.6 at eta = 1 (Fig. 9.2b): the line through (0, 1) and
        # (1, 0.6) crosses zero at 2.5
        eta, bound = solver.search([0.0, 1.0], [1.0, 0.6], LS, 0)
        assert abs(eta - 2.5) < 1e-15 and bound == 0
        # nearly flat: limited to amp times the largest step so far (Fig. 9.2c)
        eta, _ = solver.search([0.0, 1.0], [1.0, 0.99], LS, 0)
        assert eta == LS.amplification * 1.0
        # and never past eta_max; there the counter goes to 1, then to 2
        eta, bound = solver.search([0.0, 1.0, 5.0, 25.0], [1.0, 0.99, 0.98, 0.97], LS, 0)
        assert eta == LS.largest and bound == 1
        eta, bound = solver.search([0.0, 1.0, 5.0, 25.0], [1.0, 0.99, 0.98, 0.97], LS, 1)
        assert bound == 2
        # equal ratios: no line to extrapolate, the bound
        eta, _ = solver.search([0.0, 1.0], [1.0, 1.0], LS, 0)
        assert eta == LS.amplification

    def test_interpolation_moves_at_least_a_fifth(self):
        # the crossing between (0, 1) and (1, -0.01) would be at 0.990; a
        # ratio of -100 puts it at 0.0099, below 0.2 of the way: 0.2
        eta, _ = solver.search([0.0, 1.0], [1.0, -100.0], LS, 0)
        assert abs(eta - 0.2) < 1e-15
        # the smallest step: from (0.0, 1), (0.01, ...) below eta_min
        tight = replace(LS, smallest=0.5)
        eta, bound = solver.search([0.0, 1.0], [1.0, -1.4], tight, 0)
        assert eta == 0.5 and bound == 1
        eta, bound = solver.search([0.0, 1.0], [1.0, -1.4], tight, 1)
        assert bound == 2

    def test_each_parameter_moves_the_step(self):
        base = solver.search([0.0, 1.0], [1.0, 0.99], LS, 0)[0]
        assert solver.search([0.0, 1.0], [1.0, 0.99], replace(LS, amplification=3.0), 0)[0] != base
        assert solver.search([0.0, 1.0], [1.0, 0.99], replace(LS, largest=2.0), 0)[0] != base
        low = solver.search([0.0, 1.0], [1.0, -1.4], LS, 0)[0]
        assert solver.search([0.0, 1.0], [1.0, -1.4], replace(LS, smallest=0.6), 0)[0] != low


class TestWhereItIsNotNeeded:
    def test_an_elastic_stage_takes_no_search(self):
        b = v002._blocks.block(True)
        loads = v002.random_loads(b, random.Random(8))
        _, model = v002.block_model(True, [v002.stage(b, restraints=v002.rollers(b),
                                                      nodal_loads=loads)])
        plain = analysis.run(model)[0]
        searched = analysis.run(replace(model, stages=(replace(model.stages[0],
                                                               line_search=LS),)))[0]
        assert searched.displacement == plain.displacement
        assert all(inc.searches == 0 for inc in searched.increments)


def _ring(args, cuts, **kw):
    mesh, m = _hole.model(*args, MC0)
    return mesh, solver.solve_stage(m, [_hole.FIELD] * (3 * len(mesh.elements)),
                                    [0.0] * (2 * len(mesh.nodes)), 5, 1e-10, 25, cuts, RUST, **kw)


class TestWhereNewtonAloneFailed:
    def test_the_ring_of_16_by_48_with_psi_zero(self):
        args = (21.0, 48, 16, 1.2 ** 0.25)
        try:
            _ring(args, 8)
        except solver.INCREMENT_FAILURES:
            pass
        else:
            raise AssertionError("it converges without the line search: T2 changed")
        mesh, result = _ring(args, 0, line_search=LS)
        assert result.cuts == 0 and sum(inc.searches for inc in result.increments) > 0
        exact = closed.salencon_edge_finite(21.0, 0.0)["u_a"]
        error = max(abs(_hole.radial_inward(mesh, result, n) / exact - 1.0) for n in mesh.hole)
        assert error < 0.02, error

    def test_the_footing_of_case_008(self):
        mesh = ft.mesh_for(30.0, 30.0, 0.5, 1.5 ** 0.5)
        delta_e = ft.elastic_settlement(mesh, RUST)
        settlements = [f * delta_e for f in (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0)]
        settings = dict(ft.STUDY, steps=5, max_cuts=8)
        out, err = ft.stages(ft.rigid(mesh, settlements, settings), RUST)
        assert out == [] and err is not None              # without it: not the first stage
        out, err = ft.stages(ft.rigid(mesh, settlements, dict(settings, line_search=LS)), RUST)
        assert err is None and len(out) == len(settlements), err
        pressures = [ft.pressure(mesh, o) for o in out]
        assert all(b > a for a, b in zip(pressures, pressures[1:]))
        assert sum(inc.searches for o in out for inc in o.increments) > 0


class TestAFailedSearch:
    def test_is_cut_and_said(self):
        args = (100.0, 64, 16, 1.69 ** (1 / 8))           # case 002 on 16 x 64, psi = 0
        try:
            _ring(args, 8, line_search=LS)
        except solver.LineSearchError as err:
            assert err.reached is not None and 0.8 <= err.reached < 1.0, err.reached
            # the step length bound reached twice running (Fig. 9.5, ICO = 2)
            assert "twice" in err.reason, err.reason
        else:
            raise AssertionError("case 002 on 16 x 64 with psi = 0 converged: update the changelog")


class TestUphill:
    def test_an_uphill_direction_is_not_searched(self):
        """Fig. 9.5: s_0 = dp . g_0 >= 0 abandons the search (eta = 1). A
        variant whose tangent is minus the elastic stiffness (every point
        said plastic) makes every correction after the first uphill: the
        increment runs out of iterations, with no search in it."""
        class Uphill:
            name = "uphill"

            def prepare(self, g):
                inner = solver.REFERENCE.prepare(g)

                class Prepared:
                    internal_forces = staticmethod(inner.internal_forces)
                    integrate = staticmethod(inner.integrate)

                    def update(self, start, du):
                        r = inner.update(start, du)
                        return type(r)(r.stresses, r.internal_forces,
                                       r.plastic | True, r.tangents, -r.stiffness)
                return Prepared()
        # an imposed displacement: its update comes first, so the first
        # correction already uses the variant's tangent
        b = v002._blocks.block(True, w=2.0, h=1.5)
        top = [n for n, (_, y) in enumerate(b.nodes) if y == 1.5]
        imposed = tuple(em.ImposedDisplacement(n, 1, -0.001) for n in top)
        _, model = v002.block_model(True, [v002.stage(b, restraints=v002.rollers(b),
                                                      imposed=imposed)])
        stage = replace(model.stages[0], line_search=LS, max_iterations=4, max_cuts=0,
                        tolerance=1e-14)
        try:
            analysis.run(replace(model, stages=(stage,)), Uphill())
        except solver.INCREMENT_FAILURES as err:
            # not searched: the iterations run out (searching it, the search
            # itself would fail)
            assert type(err) is solver.NotConvergedError, err
        else:
            raise AssertionError("converged with an uphill tangent")


class TestRefusals:
    def test_bad_settings_say_why(self):
        args = (21.0, 4, 2, 1.5)
        for bad, words in ((replace(LS, tolerance=1.0), "(0, 1)"),
                           (replace(LS, largest=0.9), "1 < largest"),
                           (replace(LS, searches=9), "8")):
            try:
                _ring(args, 0, line_search=bad)
            except ValueError as err:
                assert words in str(err), (words, str(err))
            else:
                raise AssertionError(f"accepted {bad}")
        b = v002._blocks.block(True)
        _, one = v002.block_model(True, [v002.stage(b, restraints=v002.rollers(b))])
        m = replace(one, stages=(replace(one.stages[0], line_search=replace(LS, searches=0)),))
        try:
            em.validate(m)
        except em.InputError as err:
            assert any(p.where.endswith("line_search") for p in err.problems), err
        else:
            raise AssertionError("the engine's model accepted 0 searches")
