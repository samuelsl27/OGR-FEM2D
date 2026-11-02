# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.2 (spec 002, T13) — the Rust variant with triangles of three and of
six nodes, in plane strain and in axisymmetry, computes what the Python
reference computes (RF-10; criterion of spec 002: «Referencia y Rust
idénticos a ~1e-10»). The reference is the oracle (ADR-0001); the agreement
is measured as max |rust - reference| / max |reference| of each array.

Invariants protected:

* **at the integration points**, for each of the four kinds (T3 and T6, plane
  strain and axisymmetry): the one call per iteration (stresses, internal
  forces, plastic flags, tangents, point stiffnesses), the constitutive
  integration alone and the internal forces of given stresses, from a seeded
  random state, agree to 1e-10. With three-node triangles in plane strain
  and Mohr-Coulomb, with points that yield, too: the engine refuses that
  model (D6, model.py), but below it Rust and the reference compute the
  same;
* **the layout the solver assembles**, independently of the reference: the
  tangents are 3 x 3 in plane strain and 4 x 4 in axisymmetry, and the
  point stiffnesses placed by interface.stiffness_pattern add up to
  sum weight B^T D B built here with the whole B of each point, three rows
  (Zienkiewicz and Taylor 2000, Eq. 2.4) or four, with eps_theta = N_a / r
  under u_a (Eq. 5.6);
* **on a mesh through the engine** (analysis.run): the three-node triangle
  in plane strain (the strip load, tests/_strip.py, coarse) and in
  axisymmetry (the spherical cavity, tests/_sphere.py, coarse) give the
  same displacements, stresses and reactions, to 1e-10, after the same
  number of iterations;
* **the cases of spec 002**: 003 (T6, axisymmetry) and 004 (T6, plane
  strain), with the mesh and domain they fix, give with Rust the reference's
  displacements, stresses and reactions to 1e-10.

The refusal of Mohr-Coulomb in axisymmetry by Rust (D6) is in
test_axisymmetry_v002.py; the module being built from the current sources,
in test_rust_variant_v001.py.
"""
from __future__ import annotations

import math

import numpy as np

import _blocks
import _sphere
import _strip
import test_validation_cases_v002 as cases
from ogr_fem2d.engine import interface
from ogr_fem2d.engine.compiled import RUST
from ogr_fem2d.engine.reference import mohr_coulomb as mc
from ogr_fem2d.engine.reference import solver
from ogr_fem2d.engine.reference.elastic import Elastic

TOLERANCE = 1e-10
E, NU = 20000.0, 0.2
KINDS = [(six, analysis) for six in (False, True)
         for analysis in (solver.PLANE_STRAIN, solver.AXISYMMETRIC)]


def relative(want, got) -> float:
    want, got = np.asarray(want, dtype=float), np.asarray(got, dtype=float)
    assert want.shape == got.shape, (want.shape, got.shape)
    return float(np.abs(got - want).max() / np.abs(want).max())


def block_model(six: bool, analysis: str, law) -> solver.Model:
    """A 3 x 2 block of distorted triangles; in axisymmetry, moved off the
    axis by 0.5 m. The interior nodes are shifted so that no two elements
    have the same B."""
    b = _blocks.block(six)
    rng = np.random.default_rng(11)
    nodes = []
    for x, y in b.nodes:
        inside = 0.0 < x < 2.0 and 0.0 < y < 1.5
        dx, dy = (0.08 * rng.standard_normal(2)) if inside else (0.0, 0.0)
        nodes.append((x + dx + (0.5 if analysis == solver.AXISYMMETRIC else 0.0), y + dy))
    return solver.Model(nodes, b.elements, [law] * len(b.elements), frozenset(), analysis)


def state(model: solver.Model, n_points: int, seed: int):
    rng = np.random.default_rng(seed)
    start = -1.0 + 0.2 * rng.standard_normal((n_points, 4))
    du = 1e-3 * rng.standard_normal(2 * len(model.nodes))
    return start, du


def full_b(p: solver.IntegrationPoint) -> np.ndarray:
    """B of one point, written out from its derivatives: rows eps_x, eps_y,
    (eps_theta,) gamma_xy (Eqs. 2.4 and 5.6)."""
    k = len(p.nodes)
    hoop = bool(p.n_over_r)
    b = np.zeros((4 if hoop else 3, 2 * k))
    shear = 3 if hoop else 2
    b[0, 0::2] = p.dndx
    b[1, 1::2] = p.dndy
    b[shear, 0::2] = p.dndy
    b[shear, 1::2] = p.dndx
    if hoop:
        b[2, 0::2] = p.n_over_r
    return b


class TestAtThePoints:

    def check_the_same(self, model, seed):
        points = solver.integration_points(model)
        g = solver.geometry(model, points)
        start, du = state(model, len(points), seed)
        ref, rust = solver.REFERENCE.prepare(g), RUST.prepare(g)
        a, b = ref.update(start, du), rust.update(start, du)
        for name in ("stresses", "internal_forces", "tangents", "stiffness"):
            err = relative(getattr(a, name), getattr(b, name))
            assert err <= TOLERANCE, (name, err)
        assert np.array_equal(a.plastic, b.plastic)
        strains = np.array([p.strain(list(du)) for p in points])
        x, y = ref.integrate(start, strains), rust.integrate(start, strains)
        for name in ("stresses", "tangents"):
            assert relative(getattr(x, name), getattr(y, name)) <= TOLERANCE, name
        assert np.array_equal(x.plastic, y.plastic)
        assert relative(ref.internal_forces(start), rust.internal_forces(start)) <= TOLERANCE
        return a

    def test_elastic_in_the_four_kinds(self):
        for six, analysis in KINDS:
            self.check_the_same(block_model(six, analysis, Elastic(E, NU)), 3)

    def test_mohr_coulomb_with_three_node_triangles_in_plane_strain(self):
        law = mc.MohrCoulomb(E, NU, 0.05, math.radians(30.0), math.radians(10.0))
        update = self.check_the_same(block_model(False, solver.PLANE_STRAIN, law), 4)
        assert update.plastic.any(), "no point yielded: the return is not compared"


class TestTheLayout:

    def test_the_point_stiffnesses_add_up_to_b_t_d_b(self):
        for six, analysis in KINDS:
            model = block_model(six, analysis, Elastic(E, NU))
            points = solver.integration_points(model)
            g = solver.geometry(model, points)
            start, du = state(model, len(points), 5)
            up = RUST.prepare(g).update(start, du)
            c = 4 if analysis == solver.AXISYMMETRIC else 3
            k = 6 if six else 3
            assert up.tangents.shape == (len(points), c, c), (six, analysis)
            assert up.stiffness.shape == (len(points), 4 * k * k), (six, analysis)
            rows, cols = interface.stiffness_pattern(g)
            mine = np.zeros((g.n_dofs, g.n_dofs))
            np.add.at(mine, (rows, cols), up.stiffness.ravel())
            want = np.zeros_like(mine)
            for p, d in zip(points, up.tangents):
                b = full_b(p)
                dofs = [2 * n + j for n in p.nodes for j in (0, 1)]
                want[np.ix_(dofs, dofs)] += p.weight * b.T @ d @ b
            assert relative(want, mine) <= TOLERANCE, (six, analysis)


def check_the_same_stage(run, label):
    """``run(variant)`` -> (mesh, model, outcome) with that variant."""
    _, _, ref = run(None)
    _, _, rust = run(RUST)
    assert ref.solved and rust.solved, label
    assert len(ref.history) == len(rust.history), (label, ref.history, rust.history)
    assert relative(ref.displacement, rust.displacement) <= TOLERANCE, label
    assert relative(ref.stresses, rust.stresses) <= TOLERANCE, label
    assert ref.reactions.keys() == rust.reactions.keys(), label
    nodes = sorted(ref.reactions)
    assert relative([ref.reactions[n] for n in nodes],
                    [rust.reactions[n] for n in nodes]) <= TOLERANCE, label


class TestOnAMesh:

    def test_three_node_triangles_in_plane_strain(self):
        check_the_same_stage(lambda v: _strip.solve(25.0, 25.0, 0.5, 1.5, 3, variant=v),
                             "strip, T3")

    def test_three_node_triangles_in_axisymmetry(self):
        b = cases.case("003-cavidad-esferica-elastica")["modelo"]["geometria"]["b"]
        check_the_same_stage(lambda v: _sphere.excavate(b, 8, 2, 1.69, 3, variant=v),
                             "sphere, T3")


class TestTheCases:

    def test_003_with_rust(self):
        c = cases.case("003-cavidad-esferica-elastica")
        mesh, stage = c["modelo"]["malla"], c["modelo"]["fase"]
        b = c["modelo"]["geometria"]["b"]
        check_the_same_stage(
            lambda v: _sphere.excavate(b, mesh["n_radial"], mesh["n_theta"], mesh["crecimiento"],
                                       6 if mesh["elemento"] == "T6" else 3, variant=v,
                                       steps=stage["escalones"], tolerance=stage["tolerancia"],
                                       max_iterations=stage["iteraciones_max"]),
            "case 003")

    def test_004_with_rust(self):
        c = cases.case("004-carga-en-faja-elastica")
        geometry, mesh = c["modelo"]["geometria"], c["modelo"]["malla"]
        check_the_same_stage(
            lambda v: _strip.solve(geometry["W"], geometry["D"], mesh["h0"], mesh["crecimiento"],
                                   6 if mesh["elemento"] == "T6" else 3, variant=v),
            "case 004")
