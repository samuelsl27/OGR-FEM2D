# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.2 (spec 002, T6) — restraints, imposed displacements in totals and
reactions, stage after stage (analysis.run over model.EngineModel).

Invariants protected:

* **global equilibrium** (RF-5): in every stage, with any nodal loads, the
  external forces and the reactions add up to zero in x and in y, and so
  does their moment, in plane strain with three- and six-node triangles
  (the internal forces of any stress field are self-equilibrated). In
  axisymmetry the identity holds along the axis only: the radial internal
  forces of the hoop stress do not cancel;
* **loads in totals** (D2): a second stage with twice the load of the first
  ends where one stage with twice the load ends; a stage with the same
  load changes nothing and is not solved (its difference is rounding,
  solver.NO_LOAD), while a real load of 1e-9 of the forces in play is
  solved, and converges although its residual cannot go below the rounding
  of those forces (the rounding floor of solver.py);
* **imposed displacements in totals** (D2): imposing -1 mm and then -3 mm
  ends where imposing -3 mm at once ends; the compressed block is then in
  the exact uniform state, sigma_y = E eps_y / (1 - nu^2) with sigma_x = 0,
  and the reactions on the top add up to sigma_y times its width;
* **a load on a restrained dof** goes into its reaction, R = f_int - f_ext,
  and the equilibrium still holds;
* **the axis** (D1 bis): in axisymmetry the nodes at r = 0 are held in u_r
  by the engine, which says so; the result is the one obtained holding them
  by hand, and u_r is zero there;
* **restraints that are not enough** are found before solving, and the free
  motion is named: a translation, a rotation about the node that holds it,
  or, in axisymmetry, the translation along the axis;
* **what is not there yet** (inactive elements, T9) is refused, not
  ignored; a bad input is refused
  with the validation of T2.
"""
from __future__ import annotations

import random
from dataclasses import replace

import _blocks
from ogr_fem2d.engine import analysis
from ogr_fem2d.engine import model as m
from ogr_fem2d.engine.reference.elastic import Elastic

E, NU = 20000.0, 0.2
ROCK = m.Material(Elastic(E, NU))


def block_model(six, stages, analysis_kind=m.PLANE_STRAIN, **kw):
    b = _blocks.block(six, **kw)
    return b, m.EngineModel(analysis_kind, tuple(b.nodes), tuple(b.elements), (ROCK,),
                            (0,) * len(b.elements), tuple(stages))


def rollers(b, left=True):
    out = [m.Restraint(n, True, False) for n in b.left()] if left else []
    for n in b.bottom():
        out.append(m.Restraint(n, n in b.left() and left, True))
    return tuple(out)


def stage(b, **kw):
    return m.Stage(active=(True,) * len(b.elements), tolerance=1e-12, **kw)


def resultants(b, outcome, loads):
    """Sum of external force plus reaction, in x and y, and its moment."""
    fx = fy = mo = 0.0
    forces = {}
    for f in loads:
        forces[f.node] = (forces.get(f.node, (0.0, 0.0))[0] + f.fx,
                          forces.get(f.node, (0.0, 0.0))[1] + f.fy)
    for n, (rx, ry) in outcome.reactions.items():
        forces[n] = (forces.get(n, (0.0, 0.0))[0] + rx, forces.get(n, (0.0, 0.0))[1] + ry)
    for n, (gx, gy) in forces.items():
        x, y = b.nodes[n]
        fx, fy, mo = fx + gx, fy + gy, mo + x * gy - y * gx
    return fx, fy, mo


def random_loads(b, rng, scale=1.0):
    nodes = rng.sample(range(len(b.nodes)), 5)
    return tuple(m.NodalLoad(n, scale * rng.uniform(-1, 1), scale * rng.uniform(-1, 1))
                 for n in nodes)


class TestEquilibrium:

    def test_reactions_balance_the_loads_in_every_stage(self):
        rng = random.Random(11)
        for six in (False, True):
            b = _blocks.block(six)
            loads1, loads2 = random_loads(b, rng), random_loads(b, rng)
            _, model = block_model(six, [stage(b, restraints=rollers(b), nodal_loads=loads1),
                                         stage(b, restraints=rollers(b), nodal_loads=loads2)])
            for outcome, loads in zip(analysis.run(model), (loads1, loads2)):
                fx, fy, mo = resultants(b, outcome, loads)
                assert max(abs(fx), abs(fy), abs(mo)) < 1e-10, (six, fx, fy, mo)

    def test_in_axisymmetry_along_the_axis(self):
        rng = random.Random(5)
        for six in (False, True):
            b = _blocks.block(six)
            loads = tuple(m.NodalLoad(n, 0.0 if b.nodes[n][0] == 0.0 else rng.uniform(-1, 1),
                                      rng.uniform(-1, 1))
                          for n in rng.sample(range(len(b.nodes)), 5))
            _, model = block_model(six, [stage(b, restraints=rollers(b, left=False),
                                               nodal_loads=loads)], m.AXISYMMETRIC)
            outcome = analysis.run(model)[0]
            _, fy, _ = resultants(b, outcome, loads)
            assert abs(fy) < 1e-10, (six, fy)


class TestTotals:

    def test_loads_are_totals(self):
        rng = random.Random(2)
        b = _blocks.block(True)
        loads = random_loads(b, rng)
        twice = tuple(m.NodalLoad(f.node, 2 * f.fx, 2 * f.fy) for f in loads)
        _, two = block_model(True, [stage(b, restraints=rollers(b), nodal_loads=loads),
                                    stage(b, restraints=rollers(b), nodal_loads=twice),
                                    stage(b, restraints=rollers(b), nodal_loads=twice)])
        _, one = block_model(True, [stage(b, restraints=rollers(b), nodal_loads=twice)])
        out, ref = analysis.run(two), analysis.run(one)[0]
        assert max(abs(x - y) for x, y in zip(out[1].displacement, ref.displacement)) < 1e-15
        assert out[1].solved and not out[2].solved
        assert out[2].displacement == out[1].displacement
        for n, (rx, ry) in out[1].reactions.items():
            assert max(abs(rx - out[2].reactions[n][0]), abs(ry - out[2].reactions[n][1])) < 1e-12
        # the threshold is rounding (solver.NO_LOAD), not a small real load
        nudge = tuple(m.NodalLoad(f.node, f.fx * (1 + 1e-9), f.fy * (1 + 1e-9)) for f in twice)
        _, small = block_model(True, [stage(b, restraints=rollers(b), nodal_loads=twice),
                                      stage(b, restraints=rollers(b), nodal_loads=nudge)])
        assert analysis.run(small)[1].solved

    def test_imposed_displacements_are_totals(self):
        w, h = 2.0, 1.5
        for six in (False, True):
            b = _blocks.block(six, w=w, h=h)
            top = [n for n, (_, y) in enumerate(b.nodes) if y == h]
            imp = lambda v: tuple(m.ImposedDisplacement(n, 1, v) for n in top)
            _, steps = block_model(six, [stage(b, restraints=rollers(b), imposed=imp(-0.001)),
                                         stage(b, restraints=rollers(b), imposed=imp(-0.003))])
            # the second, in four steps: each takes its share of the increment
            _, steps = block_model(six, [stage(b, restraints=rollers(b), imposed=imp(-0.001)),
                                         replace(stage(b, restraints=rollers(b), imposed=imp(-0.003)),
                                                 steps=4)])
            _, once = block_model(six, [stage(b, restraints=rollers(b), imposed=imp(-0.003))])
            out, ref = analysis.run(steps)[1], analysis.run(once)[0]
            assert max(abs(x - y) for x, y in zip(out.displacement, ref.displacement)) < 1e-15
            eps_y = -0.003 / h
            sigma_y = E * eps_y / (1 - NU ** 2)
            for s in out.stresses:
                assert abs(s[1] - sigma_y) < 1e-9 and abs(s[0]) < 1e-9 and abs(s[3]) < 1e-9
            top_force = sum(out.reactions[n][1] for n in top)
            assert abs(top_force - sigma_y * w) < 1e-9, (six, top_force, sigma_y * w)

    def test_a_load_on_a_restrained_dof_goes_into_its_reaction(self):
        b = _blocks.block(False)
        corner = b.bottom()[1]                              # held in y
        loads = (m.NodalLoad(corner, 0.0, 5.0), m.NodalLoad(b.at(3, 2), 0.3, -1.0))
        _, model = block_model(False, [stage(b, restraints=rollers(b), nodal_loads=loads)])
        _, bare = block_model(False, [stage(b, restraints=rollers(b), nodal_loads=loads[1:])])
        out, ref = analysis.run(model)[0], analysis.run(bare)[0]
        assert abs(out.reactions[corner][1] - (ref.reactions[corner][1] - 5.0)) < 1e-12
        assert out.displacement == ref.displacement
        assert max(abs(x) for x in resultants(b, out, loads)) < 1e-10


class TestTheAxis:

    def test_the_engine_holds_the_axis_and_says_so(self):
        for six in (False, True):
            b = _blocks.block(six)
            top = [n for n, (_, y) in enumerate(b.nodes) if y == 1.5]
            imposed = tuple(m.ImposedDisplacement(n, 1, -0.002) for n in top)
            bottom = tuple(m.Restraint(n, False, True) for n in b.bottom())
            _, auto = block_model(six, [stage(b, restraints=bottom, imposed=imposed)],
                                  m.AXISYMMETRIC)
            _, hand = block_model(six, [stage(b, restraints=rollers(b), imposed=imposed)],
                                  m.AXISYMMETRIC)
            out, ref = analysis.run(auto)[0], analysis.run(hand)[0]
            assert set(out.axis_held) == set(b.left()), out.axis_held
            assert max(abs(x - y) for x, y in zip(out.displacement, ref.displacement)) < 1e-15
            assert all(out.displacement[2 * n] == 0.0 for n in b.left())
            _, plane = block_model(six, [stage(b, restraints=rollers(b), imposed=imposed)])
            assert analysis.run(plane)[0].axis_held == ()


class TestNotEnoughRestraints:

    def _refused(self, model):
        try:
            analysis.run(model)
        except analysis.InsufficientRestraintError as err:
            return err.motions
        raise AssertionError("an unrestrained model was solved")

    def test_the_free_motion_is_named(self):
        b = _blocks.block(False)
        load = (m.NodalLoad(b.at(3, 2), 0.0, -1.0),)
        bottom_y = tuple(m.Restraint(n, False, True) for n in b.bottom())
        motions = self._refused(block_model(False, [stage(b, restraints=bottom_y,
                                                          nodal_loads=load)])[1])
        assert motions == ["translation along (+1.000, +0.000)"], motions
        corner = b.at(3, 2)
        x, y = b.nodes[corner]
        pin = (m.Restraint(corner, True, True),)
        motions = self._refused(block_model(False, [stage(b, restraints=pin, nodal_loads=load)])[1])
        assert motions == [f"rotation about ({x:.6g}, {y:.6g})"], motions
        motions = self._refused(block_model(False, [stage(b, nodal_loads=load)],
                                            m.AXISYMMETRIC)[1])
        assert motions == ["translation along the axis (y = z)"], motions


class TestRefused:

    def test_what_is_not_there_yet_and_bad_input(self):
        b = _blocks.block(False)
        base = block_model(False, [stage(b, restraints=rollers(b))])[1]
        dug = replace(base, stages=(replace(base.stages[0], active=(False,) + (True,) * 11),))
        for model, task in ((dug, "T9"),):
            try:
                analysis.run(model)
            except NotImplementedError as err:
                assert task in str(err)
            else:
                raise AssertionError(f"{task} was not refused")
        try:
            analysis.run(replace(base, element_material=(0, 9) + (0,) * 10))
        except m.InputError as err:
            assert "element_material" in str(err)
        else:
            raise AssertionError("a bad input was solved")
