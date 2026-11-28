# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.16 (spec 007, T3) — what the loop of a stage tells and how it stops:
the progress by iteration and the stop between iterations (D10), every
increment with how it ended and the load factor a failed stage reached
(D2), the mark of the rounding floor (D12), and a singular tangent as one
more failure of an increment (the anomaly of T2, de Souza Neto et al. 2008,
Fig. 5.2: a zero pivot is among the failures that cut the increment).

Invariants protected:

* **progress decides nothing**: with it and without it, the same numbers
  bit for bit (the excavation of the coarse ring with Mohr-Coulomb and cuts,
  and three stages of analysis.run); it hears every iteration, in the order
  of the history, with the cuts made so far;
* **the stop**: ``should_stop`` saying so before the k-th correction stops
  the stage with Cancelled after exactly k iterations; through
  analysis.stages, the stages before it are given;
* **the increments**: every one tried, with its status; the cut ones are
  halved and retried from their start; the iterations of each are those of
  the history;
* **the factor reached** (D2): a stage that fails once its cuts are used up
  says the load factor converged so far and the smallest increment tried
  (the 21 m ring with 16 x 48 and psi = 0 of the T2 diagnosis, 5 steps and
  4 cuts: it stops at 0.95, and the smallest increment is 0.2 / 2^4);
* **the rounding floor** (D12): a stage whose load is 1e-9 of the forces in
  play (test_analysis_v002) converges by the floor and says so; a stage
  that reaches its tolerance does not;
* **a singular tangent** is cut like the other failures and, once the cuts
  are used up, leaves the stage as SingularTangentError with its factor
  reached; calculate writes it as a stage that failed (incomplete), not as
  a program error. Two kinds (T5a): degrees of freedom with no stiffness at
  all (case 002 on 16 x 64 with psi = 1 degree: nodes whose points are all
  at the apex), found before SuperLU, which on macOS crashes on them; and a
  mechanism with every row stiff (the footing of case 008), which SuperLU
  reports.
"""
from __future__ import annotations

import math
import random
import tempfile
from dataclasses import replace
from pathlib import Path

import numpy as np

import _hole
import _results
import test_analysis_v002 as v002
from ogr_fem2d.engine import analysis
from ogr_fem2d.engine import model as em
from ogr_fem2d.engine.compiled import RUST
from ogr_fem2d.engine.reference import mohr_coulomb as mc
from ogr_fem2d.engine.reference import solver
from ogr_fem2d.model import ogr_file
from ogr_fem2d.results import calculate as calc
from ogr_fem2d.results import store

closed = _hole.closed
MC0 = mc.MohrCoulomb(closed.E, closed.NU, closed.COH, closed.PHI, 0.0)
COARSE = (21.0, 4, 2, 1.5)              # b, n_radial, n_theta, growth (test_solver_v001)


def _ring(**kw):
    """The coarse ring, Mohr-Coulomb psi = 0, one step and 4 iterations
    allowed so that some increments are cut (test_solver_v001)."""
    return _excavate(COARSE, MC0, 1, 1e-10, 4, 6, solver.REFERENCE, **kw)


def _excavate(mesh_args, material, steps, tolerance, max_iterations, max_cuts, variant,
              progress=None, should_stop=None):
    mesh, m = _hole.model(*mesh_args, material)
    n_points = 3 * len(mesh.elements)
    return mesh, solver.solve_stage(m, [_hole.FIELD] * n_points, [0.0] * (2 * len(mesh.nodes)),
                                    steps, tolerance, max_iterations, max_cuts, variant,
                                    progress=progress, should_stop=should_stop)


class TestProgress:
    def test_it_decides_nothing_and_hears_every_iteration(self):
        heard = []
        mesh, quiet = _ring()
        _mesh, told = _ring(progress=heard.append)
        assert told.displacement == quiet.displacement
        assert told.stresses == quiet.stresses and told.history == quiet.history
        assert quiet.cuts >= 1
        assert [(h.increment, h.iteration, h.residual) for h in heard] == told.history
        # the cuts so far, and each increment's load factors
        cuts_seen = [h.cuts for h in heard]
        assert cuts_seen == sorted(cuts_seen) and cuts_seen[-1] == told.cuts
        by_number = {h.increment: (h.start, h.end) for h in heard}
        assert list(by_number.values()) == [(inc.start, inc.end) for inc in told.increments]

    def test_stages_bit_for_bit_with_and_without(self):
        b = v002._blocks.block(True)
        loads = v002.random_loads(b, random.Random(4))
        twice = tuple(em.NodalLoad(f.node, 2 * f.fx, 2 * f.fy) for f in loads)
        _, model = v002.block_model(True, [v002.stage(b, restraints=v002.rollers(b), nodal_loads=f)
                                           for f in (loads, twice, loads)])
        heard = []
        quiet = analysis.run(model)
        told = analysis.run(model, progress=lambda k, it: heard.append((k, it)))
        assert [o.displacement for o in told] == [o.displacement for o in quiet]
        assert [o.stresses for o in told] == [o.stresses for o in quiet]
        assert sorted({k for k, _ in heard}) == [0, 1, 2]


class TestStop:
    def test_it_stops_before_the_kth_correction(self):
        for k in (1, 3, 5):
            asked = []

            def stop(k=k):
                asked.append(True)
                return len(asked) == k
            try:
                _ring(should_stop=stop)
            except solver.Cancelled:
                pass
            else:
                raise AssertionError("not stopped")
            assert len(asked) == k

    def test_the_stages_before_it_are_given(self):
        b = v002._blocks.block(True)
        loads = v002.random_loads(b, random.Random(4))
        twice = tuple(em.NodalLoad(f.node, 2 * f.fx, 2 * f.fy) for f in loads)
        _, model = v002.block_model(True, [v002.stage(b, restraints=v002.rollers(b), nodal_loads=f)
                                           for f in (loads, twice)])
        calls = []

        def stop():
            calls.append(True)
            return len(calls) > 1            # the first stage's only correction goes
        done = []
        try:
            for outcome in analysis.stages(model, should_stop=stop):
                done.append(outcome)
        except solver.Cancelled:
            pass
        else:
            raise AssertionError("not stopped")
        assert len(done) == 1 and done[0].solved


class TestIncrements:
    def test_every_increment_with_its_status_and_iterations(self):
        _mesh, cut = _ring()
        assert {inc.status for inc in cut.increments} == {solver.CUT, solver.CONVERGED}
        for number, inc in enumerate(cut.increments, start=1):
            corrections = sum(1 for n, it, _r in cut.history if n == number and it > 0)
            if inc.status == solver.CONVERGED:
                assert inc.iterations == corrections and inc.reason == ""
            else:
                # cut after its 4 corrections, or earlier by a point refused
                assert inc.iterations <= 4 and inc.reason


class TestFactorReached:
    def test_a_failed_stage_says_how_far_it_got(self):
        ring = (21.0, 48, 16, 1.2 ** 0.25)          # the 16 x 48 of the T2 diagnosis
        heard = []
        try:
            _excavate(ring, MC0, 5, 1e-10, 25, 4, RUST, progress=heard.append)
        except solver.INCREMENT_FAILURES as err:
            # the last increment that converged ends where the stage got to
            converged_ends = [h.end for h in heard
                              if h.iteration > 0 and h.residual <= 1e-10]
            assert err.reached == max(converged_ends), (err.reached, max(converged_ends))
            assert math.isclose(err.reached, 0.95, abs_tol=1e-12), err.reached
            assert math.isclose(err.smallest, 0.2 / 2 ** 4, rel_tol=1e-12), err.smallest
            return
        raise AssertionError("the 16 x 48 ring with psi = 0 converged: the T2 diagnosis changed")


class TestRoundingFloor:
    def test_the_floor_is_said_and_only_when_it_decides(self):
        b = v002._blocks.block(True)
        loads = v002.random_loads(b, random.Random(2))
        twice = tuple(em.NodalLoad(f.node, 2 * f.fx, 2 * f.fy) for f in loads)
        nudge = tuple(em.NodalLoad(f.node, f.fx * (1 + 1e-9), f.fy * (1 + 1e-9)) for f in twice)
        _, small = v002.block_model(True, [v002.stage(b, restraints=v002.rollers(b), nodal_loads=twice),
                                           v002.stage(b, restraints=v002.rollers(b), nodal_loads=nudge)])
        first, second = analysis.run(small)
        assert [inc.status for inc in first.increments] == [solver.CONVERGED]
        assert [inc.status for inc in second.increments] == [solver.FLOOR]
        assert second.history[-1][2] > second.tolerance


def _singular(psi_degrees=1.0):
    ring = (100.0, 64, 16, 1.69 ** (1 / 8))          # case 002 on 16 x 64
    material = mc.MohrCoulomb(closed.E, closed.NU, closed.COH, closed.PHI, math.radians(psi_degrees))
    return ring, material


class TestSingularTangent:
    def test_it_is_cut_and_then_said(self):
        ring, material = _singular()
        try:
            _mesh, result = _excavate(ring, material, 5, 1e-10, 25, 0, RUST)
        except solver.SingularTangentError as err:
            # nodes with every point at the apex: found before SuperLU, which
            # on macOS crashes on such a matrix (solver.factorise_tangent)
            assert err.reached == 0.8 and "no stiffness" in err.reason, err.reason
        else:
            raise AssertionError("case 002 with psi = 1 no longer meets a singular tangent")
        # with cuts it is one more failure of an increment: cut, and retried
        try:
            _mesh, result = _excavate(ring, material, 5, 1e-10, 25, 4, RUST)
        except solver.INCREMENT_FAILURES as err:
            assert err.reached >= 0.8
        else:
            assert any(inc.status == solver.CUT and "singular" in inc.reason
                       for inc in result.increments)

    def test_with_no_empty_row_superlu_says_it(self):
        """The footing of case 008 on its coarsest mesh, 5 steps to a quarter
        of the elastic settlement and no cut: the tangent is singular with
        every degree of freedom stiff (a mechanism, not an empty row), and
        SuperLU says so through its ordinary return. On every platform of the
        CI, a stage that failed, not a crash (T5a)."""
        import _footing as ft
        from ogr_fem2d.engine.compiled import RUST
        mesh = ft.mesh_for(30.0, 30.0, 0.5, 1.5 ** 0.5)
        delta_e = ft.elastic_settlement(mesh, RUST)
        out, err = ft.stages(ft.rigid(mesh, [0.25 * delta_e], dict(ft.STUDY, max_cuts=0)), RUST)
        assert out == [] and isinstance(err, solver.SingularTangentError), err
        assert "no stiffness" not in err.reason, err.reason

    def test_calculate_writes_it_as_a_stage_that_failed(self):
        class Singular:
            """The reference, with every point plastic and no stiffness: the
            tangent of every correction is singular."""
            name = "singular"

            def prepare(self, g):
                inner = solver.REFERENCE.prepare(g)

                class Prepared:
                    internal_forces = staticmethod(inner.internal_forces)
                    integrate = staticmethod(inner.integrate)

                    def update(self, start, du):
                        r = inner.update(start, du)
                        return type(r)(r.stresses, r.internal_forces, np.ones_like(r.plastic),
                                       r.tangents, np.zeros_like(r.stiffness))
                return Prepared()

        m = _results.loaded_layers()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "modelo.ogrfem2d"
            ogr_file.write(m, path)
            done = calc.calculate(m, path, variant=Singular())
            assert done.status == store.INCOMPLETE, done
            assert "SingularTangentError" in done.reason, done.reason
