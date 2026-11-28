# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.16 (spec 007, T4; RF-5, RF-6, D3) — the three ways of stepping a stage:
equal steps, the load factors given (de Souza Neto et al. 2008, §5.4.1:
the load factors are input data) and the automatic size of Crisfield
(1991), §9.5, Eq. (9.40) with n = 1/2: dl_n = dl_o (I_d / I_o)^(1/2), with
a first, a largest and a smallest size.

Invariants protected:

* **elasticity does not see them**: one stage of the block of
  test_analysis_v002 ends at the same displacement (1e-15 of it) with one
  step, with a list of factors and with the automatic size;
* **Eq. (9.40) is what the automatic size does**: in the excavation of the
  ring with Mohr-Coulomb, every increment after a converged one has the
  size of (9.40) from that one's size and iterations, clipped to
  [smallest, largest] and to the end of the stage; the last ends at 1; and
  the stage's ``steps`` is the number of increments that converged;
* **each setting moves the number** (rule 7): in the same excavation the
  list of factors against four equal steps, and I_d, the first, the
  largest and the smallest size against the automatic default here; with
  psi = 0 and 30 degrees;
* **a bad setting is refused with its reason**: a list empty, not
  increasing, out of (0, 1] or not ending at 1; sizes out of order; both
  ways at once; and the engine's model validation says it too.
"""
from __future__ import annotations

import math
import random
from dataclasses import replace

import _hole
import test_analysis_v002 as v002
from ogr_fem2d.engine import analysis
from ogr_fem2d.engine import model as em
from ogr_fem2d.engine.reference import mohr_coulomb as mc
from ogr_fem2d.engine.reference import solver

closed = _hole.closed
RING = (21.0, 12, 4, 1.2)
AUTO = solver.Automatic(3, 0.1, 0.5)


def _ring(psi_degrees, steps=1, max_iterations=25, **kw):
    material = mc.MohrCoulomb(closed.E, closed.NU, closed.COH, closed.PHI,
                              math.radians(psi_degrees))
    mesh, m = _hole.model(*RING, material)
    return solver.solve_stage(m, [_hole.FIELD] * (3 * len(mesh.elements)),
                              [0.0] * (2 * len(mesh.nodes)), steps, 1e-10, max_iterations, 8,
                              **kw)


def _gap(a, b):
    return max(abs(x - y) for x, y in zip(a.displacement, b.displacement))


class TestElasticity:
    def test_the_three_ways_end_at_the_same_place(self):
        b = v002._blocks.block(True)
        loads = v002.random_loads(b, random.Random(6))
        stage = v002.stage(b, restraints=v002.rollers(b), nodal_loads=loads)
        _, one = v002.block_model(True, [stage])
        ref = analysis.run(one)[0]
        scale = max(abs(u) for u in ref.displacement)
        for way in (dict(factors=(0.2, 0.5, 1.0)), dict(automatic=solver.Automatic(3, 0.1, 0.4))):
            out = analysis.run(replace(one, stages=(replace(one.stages[0], **way),)))[0]
            assert _gap(out, ref) <= 1e-15 * scale * 10, way
            ends = [inc.end for inc in out.increments]
            if "factors" in way:
                assert ends == list(way["factors"]), ends      # analysis passes them on
            else:
                assert ends[0] == 0.1 and ends[-1] == 1.0 and len(ends) > 2, ends


class TestEquation940:
    def test_every_size_follows_it(self):
        for psi in (0.0, 30.0):
            for auto in (AUTO, solver.Automatic(6, 0.1, 0.5), solver.Automatic(3, 0.1, 0.25, 0.2)):
                r = _ring(psi, automatic=auto)
                incs = r.increments
                assert incs[0].start == 0.0 and incs[0].end == auto.first
                assert incs[-1].end == 1.0
                for a, b in zip(incs, incs[1:]):
                    if a.status == solver.CUT:
                        continue
                    size = a.end - a.start
                    want = min(auto.largest, max(auto.smallest,
                                                 size * math.sqrt(auto.desired_iterations
                                                                  / a.iterations)))
                    assert math.isclose(b.end, min(1.0, a.end + want), rel_tol=1e-14), (psi, a, b)
                assert r.steps == sum(1 for inc in incs if inc.status != solver.CUT)

    def test_with_cuts_too(self):
        # 6 iterations allowed, psi = 30: some increments are cut, and the stage's
        # steps are the converged ones only
        r = _ring(30.0, max_iterations=6, automatic=solver.Automatic(3, 0.5, 1.0))
        assert r.cuts >= 1
        assert r.steps == len(r.increments) - r.cuts


class TestEachSettingMovesTheNumber:
    def test_the_list_of_factors(self):
        for psi in (0.0, 30.0):
            assert _gap(_ring(psi, factors=[0.1, 0.3, 0.6, 1.0]), _ring(psi, steps=4)) > 1e-6

    def test_the_automatic_sizes(self):
        for psi in (0.0, 30.0):
            base = _ring(psi, automatic=AUTO)
            for changed in (replace(AUTO, desired_iterations=6), replace(AUTO, first=0.05),
                            replace(AUTO, largest=0.25)):
                assert _gap(_ring(psi, automatic=changed), base) > 1e-6, (psi, changed)
            # the smallest acts where (9.40) proposes less than it
            low = solver.Automatic(3, 0.1, 0.25)
            assert _gap(_ring(psi, automatic=replace(low, smallest=0.2)),
                        _ring(psi, automatic=low)) > 1e-6, psi


class TestRefusals:
    def test_bad_settings_say_why(self):
        bad = {
            "empty": dict(factors=[]),
            "increase": dict(factors=[0.5, 0.3, 1.0]),
            "must increase": dict(factors=[0.5, 0.5, 1.0]),
            "(0, 1]": dict(factors=[0.0, 0.5, 1.0]),
            "last load factor must be 1": dict(factors=[0.2, 0.6]),
            "smallest <= largest": dict(automatic=solver.Automatic(3, 0.1, 0.5, 0.6)),
            "first <= largest": dict(automatic=solver.Automatic(3, 0.6, 0.5)),
            "desired_iterations": dict(automatic=solver.Automatic(0.5, 0.1, 0.5)),
            "not both": dict(factors=[1.0], automatic=AUTO),
        }
        for words, kw in bad.items():
            try:
                _ring(0.0, **kw)
            except ValueError as err:
                assert words in str(err), (words, str(err))
            else:
                raise AssertionError(f"accepted: {kw}")

    def test_the_engine_model_says_it(self):
        b = v002._blocks.block(True)
        _, one = v002.block_model(True, [v002.stage(b, restraints=v002.rollers(b))])
        for kw, where in ((dict(factors=(0.4, 0.2, 1.0)), "factors"),
                          (dict(automatic=solver.Automatic(3, 0.0, 0.5)), "automatic"),
                          (dict(factors=(1.0,), automatic=AUTO), "steps")):
            m = replace(one, stages=(replace(one.stages[0], **kw),))
            try:
                em.validate(m)
            except em.InputError as err:
                assert any(p.where.endswith(where) for p in err.problems), err
            else:
                raise AssertionError(f"accepted: {kw}")
