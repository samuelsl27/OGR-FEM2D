# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.1 (spec 001, T7 and D7) — the stage of the reference engine: load
steps, full Newton iterations with the consistent tangent, and a convergence
history that tells the truth, including when it does not converge.

Invariants protected:

* **the excavation load is the initial-stress term** of Zienkiewicz and
  Taylor (2000), Eq. (2.13b): the internal forces of the uniform field
  stress are zero at every free node not on the hole ("identically zero
  after assembly" for a self-equilibrating stress, p. 25), and on the hole
  their resultant is the field stress times the chord of the arc, P0 a in x
  and in y: for a uniform stress, int sigma.n ds over any curve is sigma
  applied to its rotated chord, whatever the curvature of the edges;
* **loads in totals** (spec 001, D2): the stage goes from the force of its
  starting stresses to the TOTAL given. Giving as total half the in-situ
  force on the hole (an internal pressure of P0/2 left) moves the hole
  exactly half as much as leaving it free (elastic, so linear); giving the
  in-situ force itself is a stage with no load, and is refused;
* **the history is the bookkeeping of the steps**: iteration 0 of every
  step measures the load just added, 1/n of the stage, to within the
  tolerance the previous step left (no drift between steps); the last entry
  of each step is within tolerance;
* **elastic**: one correction solves a step (the elastic stiffness IS the
  tangent), and n steps give the same answer as one;
* **the tangent stiffness is assembled right**: with elastic tangents, the
  point-by-point assembly of K_T equals the element-by-element stiffness of
  t6.stiffness, two routes to one matrix;
* **Newton converges quadratically** (de Souza Neto et al. 2008, §4.2.4):
  in every plastic step the last correction cuts the relative residual to
  at most its previous value to the power 1.5. With a wrong tangent (the
  elastic one, say) the convergence is linear and this fails;
* **increment cutting** (§5.4.3): a stage that fails without cuts converges
  with them, to the equilibrium that 16 equal steps reach; the cuts allowed
  are successive ones, and when they run out the error comes out;
* **no convergence is detected and reported** (RF-6): with too few
  iterations allowed, NotConvergedError carries the step and the whole
  history, and no result is returned;
* **a failed point update is located** (RF-4): the apex with psi = 0, which
  the Mohr-Coulomb refuses, comes out with its element, point, step and
  iteration;
* **bad input is refused**: a degenerate element names itself, and the
  stage parameters are checked.
"""
from __future__ import annotations

import math

import _hole
from ogr_fem2d.engine.reference import element_t6 as t6
from ogr_fem2d.engine.reference import mohr_coulomb as mc
from ogr_fem2d.engine.reference import solver
from ogr_fem2d.engine.reference.elastic import Elastic

ELASTIC = Elastic(10000.0, 0.2)
MC0 = mc.MohrCoulomb(10000.0, 0.2, 3.45, math.radians(30.0), 0.0)
COARSE = (21.0, 4, 2, 1.5)                     # b, n_radial, n_theta, growth


def _hole_force(mesh, model):
    points = solver.integration_points(model)
    n_dofs = 2 * len(mesh.nodes)
    return solver.internal_forces(points, [_hole.FIELD] * len(points), n_dofs)


class TestTheExcavationLoad:
    def test_zero_off_the_hole_and_p0_times_the_chord_on_it(self):
        mesh, model = _hole.model(*COARSE, ELASTIC)
        f = _hole_force(mesh, model)
        hole = set(mesh.hole)
        scale = _hole.P0 * _hole.A
        for n in range(len(mesh.nodes)):
            for c in (0, 1):
                dof = 2 * n + c
                if n not in hole and dof not in model.restrained:
                    assert abs(f[dof]) < 1e-12 * scale, (n, c, f[dof])
        # The field stress -P0 I on the hole, whose outward normal (of the
        # domain) points to the centre: the domain is pushed outward, and the
        # internal force is the reaction of the removed core: P0 a in x and
        # in y. The two end nodes of the hole also lie on an axis edge, whose
        # normal is -y (x axis) or -x (y axis): the node at (0, a) gets, in
        # x, the share of the straight radial edge from a to r_1, P0 (r_1 -
        # a)/6 (the corner share of a quadratic edge with its mid-side node
        # in the middle), and the node at (a, 0) the same in y.
        edge = _hole.P0 * (mesh.radii[1] - mesh.radii[0]) / 6.0
        fx = sum(f[2 * n] for n in mesh.hole)
        fy = sum(f[2 * n + 1] for n in mesh.hole)
        assert abs(fx - (_hole.P0 * _hole.A + edge)) < 1e-12 * scale, fx
        assert abs(fy - (_hole.P0 * _hole.A + edge)) < 1e-12 * scale, fy


class TestLoadsInTotals:
    def _wall(self, mesh, result):
        return [_hole.radial_inward(mesh, result, n) for n in mesh.hole]

    def test_half_the_in_situ_force_left_moves_the_hole_half(self):
        mesh, model = _hole.model(*COARSE, ELASTIC)
        f = _hole_force(mesh, model)
        n_points = 3 * len(mesh.elements)
        free = solver.solve_stage(model, [_hole.FIELD] * n_points,
                                  [0.0] * len(f), 1, 1e-10, 5)
        half = solver.solve_stage(model, [_hole.FIELD] * n_points,
                                  [0.5 * x for x in f], 1, 1e-10, 5)
        for u_free, u_half in zip(self._wall(mesh, free),
                                  self._wall(mesh, half)):
            assert u_free > 0.0
            assert abs(u_half - 0.5 * u_free) < 1e-10 * u_free

    def test_the_in_situ_force_itself_is_no_load(self):
        mesh, model = _hole.model(*COARSE, ELASTIC)
        f = _hole_force(mesh, model)
        try:
            solver.solve_stage(model, [_hole.FIELD] * (3 * len(mesh.elements)),
                               f, 1, 1e-10, 5)
        except ValueError as err:
            assert "no load" in str(err)
            return
        raise AssertionError("a stage without load was solved")


class TestHistory:
    def test_each_step_starts_at_its_share_and_ends_within_tolerance(self):
        tol = 1e-6
        _mesh, result = _hole.excavate(*COARSE, MC0, 4, tol, 2000)
        assert result.steps == 4 and result.tolerance == tol
        by_step = {}
        for step, iteration, relative in result.history:
            by_step.setdefault(step, []).append((iteration, relative))
        assert sorted(by_step) == [1, 2, 3, 4]
        plastic_steps = 0
        for step, entries in by_step.items():
            assert [i for i, _ in entries] == list(range(len(entries)))
            assert abs(entries[0][1] - 0.25) <= tol, (step, entries[0])
            assert entries[-1][1] <= tol
            plastic_steps += len(entries) > 2
        assert plastic_steps >= 1          # the case does yield
        assert any(result.plastic)

    def test_elastic_one_correction_per_step_and_steps_do_not_matter(self):
        mesh, one = _hole.excavate(*COARSE, ELASTIC, 1, 1e-10, 5)
        _, five = _hole.excavate(*COARSE, ELASTIC, 5, 1e-10, 5)
        for result in (one, five):
            iterations = {}
            for step, iteration, _rel in result.history:
                iterations[step] = iteration
            assert set(iterations.values()) == {1}
            assert not any(result.plastic)
        scale = max(abs(u) for u in one.displacement)
        assert max(abs(a - b) for a, b in
                   zip(one.displacement, five.displacement)) < 1e-12 * scale


class TestNewton:
    def test_point_assembly_equals_element_assembly(self):
        mesh, model = _hole.model(*COARSE, ELASTIC)
        points = solver.integration_points(model)
        d = solver.plane_strain_matrix(ELASTIC.young, ELASTIC.poisson)
        n_dofs = 2 * len(mesh.nodes)
        by_points = solver.tangent_stiffness(points, [d] * len(points),
                                             n_dofs).toarray()
        by_elements = solver.stiffness(model).toarray()
        scale = abs(by_elements).max()
        assert abs(by_points - by_elements).max() < 1e-12 * scale

    def test_quadratic_convergence_in_the_plastic_steps(self):
        for psi in (0.0, 30.0):
            m = mc.MohrCoulomb(10000.0, 0.2, 3.45, math.radians(30.0),
                               math.radians(psi))
            _mesh, result = _hole.excavate(*COARSE, m, 4, 1e-10, 30)
            steps = {}
            for step, iteration, relative in result.history:
                steps.setdefault(step, []).append(relative)
            checked = 0
            for step, residuals in steps.items():
                if len(residuals) < 4:          # elastic: one correction
                    continue
                # the last pair still above the rounding floor of the
                # residual (about 1e-14 of the load), in the Newton range
                pairs = [(a, b) for a, b in zip(residuals[1:], residuals[2:])
                         if b > 1e-13 and a < 1e-2]
                assert pairs, (psi, step, residuals)
                before, last = pairs[-1]
                assert last <= before ** 1.5, (psi, step, residuals)
                checked += 1
            assert checked >= 1, (psi, steps)


class TestIncrementCutting:
    """de Souza Neto et al. (2008), §5.4.3: a failed increment is split in
    two and restarted from the last converged state. The setting moves the
    result (rule 7): without cuts the stage fails, with them it converges.

    It is NOT asserted that the result equals that of some number of equal
    steps: the Mohr-Coulomb result depends on the steps when a point already
    on the plane ends an increment on an edge (the backward-Euler return is
    exact only within one region), changelog v0.0.1."""

    def test_cuts_turn_a_failure_into_a_converged_stage(self):
        try:
            _hole.excavate(*COARSE, MC0, 1, 1e-10, 4)
        except solver.NotConvergedError:
            pass
        else:
            raise AssertionError("expected no convergence in 4 iterations")
        _mesh, cut = _hole.excavate(*COARSE, MC0, 1, 1e-10, 4, max_cuts=3)
        assert cut.cuts >= 1
        reasons = [why for _a, _b, why in cut.increments]
        assert sum(why.startswith("cut:") for why in reasons) == cut.cuts
        # every cut halves its increment, and is retried from its start
        for (a, b, why), (a2, b2, _) in zip(cut.increments, cut.increments[1:]):
            if why.startswith("cut:"):
                assert (a2, b2) == (a, 0.5 * (a + b)), (a, b, a2, b2)
        # the converged increments tile [0, 1] with no gap
        done = [(a, b) for a, b, why in cut.increments if why == "converged"]
        assert done[0][0] == 0.0 and done[-1][1] == 1.0
        assert all(b1 == a2 for (_, b1), (a2, _) in zip(done, done[1:]))
        # and the last iteration of the stage is within tolerance
        assert cut.history[-1][2] <= 1e-10

    def test_the_cuts_allowed_are_successive_ones(self):
        # the apex with psi = 0 is refused whatever the increment: the cuts
        # run out and the located error comes out
        model = _one_element_model(MC0)
        target = (100.0, 100.0, 40.0, 0.0)
        load = t6.internal_forces(model.nodes, [target] * 3)
        try:
            solver.solve_stage(model, [(0.0, 0.0, 0.0, 0.0)] * 3, load, 1,
                               1e-8, 10, max_cuts=2)
        except solver.StateUpdateError as err:
            assert err.step == 3          # the first try and two cuts
            assert "apex" in err.reason
            return
        raise AssertionError("the apex with psi = 0 was not refused")


class TestNoConvergence:
    def test_too_few_iterations_raise_with_the_history(self):
        try:
            _hole.excavate(*COARSE, MC0, 2, 1e-8, 3)
        except solver.NotConvergedError as err:
            history = err.history
            assert err.step == history[-1][0]
            assert history[-1][1] == 3              # the last allowed
            assert history[-1][2] > 1e-8
            # the steps before the failing one each ended converged
            last = {}
            for step, _it, rel in history:
                last[step] = rel
            assert all(last[s] <= 1e-8 for s in last if s < err.step)
            assert "did not converge" in str(err)
            return
        raise AssertionError("no NotConvergedError with 3 iterations allowed")


def _one_element_model(material):
    corners = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
    (x1, y1), (x2, y2), (x3, y3) = corners
    nodes = corners + [((x1 + x2) / 2, (y1 + y2) / 2),
                       ((x2 + x3) / 2, (y2 + y3) / 2),
                       ((x3 + x1) / 2, (y3 + y1) / 2)]
    # rigid-body motions only: node 0 fixed, node 1 held in y
    return solver.Model(nodes, [(0, 1, 2, 3, 4, 5)], [material],
                        frozenset({0, 1, 3}))


class TestLocatedFailure:
    def test_the_apex_with_psi_zero_names_element_point_and_step(self):
        model = _one_element_model(MC0)
        # A uniform biaxial tension far beyond c cot(phi): its nodal forces
        # stretch the element uniformly, and the trial stress returns to
        # the apex, which psi = 0 refuses.
        target = (100.0, 100.0, 40.0, 0.0)
        load = t6.internal_forces(model.nodes, [target] * 3)
        try:
            solver.solve_stage(model, [(0.0, 0.0, 0.0, 0.0)] * 3, load, 1,
                               1e-8, 10)
        except solver.StateUpdateError as err:
            assert (err.element, err.step, err.iteration) == (0, 1, 1)
            assert err.point in (0, 1, 2)
            assert "apex" in err.reason
            return
        raise AssertionError("the apex with psi = 0 was not refused")


class TestBadInput:
    def test_a_degenerate_element_names_itself(self):
        mesh, model = _hole.model(*COARSE, ELASTIC)
        elements = list(model.elements)
        e = elements[5]
        elements[5] = (e[1], e[0], e[2], e[3], e[5], e[4])   # inverted
        bad = solver.Model(model.nodes, elements, model.materials,
                           model.restrained)
        try:
            solver.integration_points(bad)
        except ValueError as err:
            assert "element 5" in str(err)
            return
        raise AssertionError("an inverted element was accepted")

    def test_stage_parameters(self):
        mesh, model = _hole.model(*COARSE, ELASTIC)
        n_points = 3 * len(mesh.elements)
        zero = [0.0] * (2 * len(mesh.nodes))
        for args in ((0, 1e-8, 5), (1, 0.0, 5), (1, 1e-8, 0), (1, 1e-8, 5, -1)):
            try:
                solver.solve_stage(model, [_hole.FIELD] * n_points, zero, *args)
            except ValueError:
                continue
            raise AssertionError(f"accepted {args}")
        try:
            solver.solve_stage(model, [_hole.FIELD] * (n_points - 1), zero,
                               1, 1e-8, 5)
        except ValueError:
            return
        raise AssertionError("accepted a missing initial stress")
