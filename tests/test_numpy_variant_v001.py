# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.1 (spec 001, T11) — the NumPy variant (poc/vectorized.py) computes what
the Python reference computes, at a material point and on a mesh.

The reference is validated against closed-form solutions (T4-T9); this
variant is checked against the reference, the oracle (ADR-0001). Tolerance:
1e-10 relative, criterion 1 of ADR-0001 for the compiled variant, applied
here too. The same operations in another order differ by rounding, about
1e-15 at a point and 1e-13 on a mesh when the test was written.

Invariants protected:

* **material point**: for a seeded cloud of starting stresses and strain
  increments over psi = 0, 15 and 30 degrees, with elastic points mixed in,
  the stresses, the plastic flags and the consistent tangents equal the
  reference's, and the cloud covers every region (elastic, plane, both edges,
  apex); and so for states on the surface with increments of 1e-9, where
  only the tolerance of the return decides;
* **the refusal**: the apex with psi = 0 raises StateUpdateError naming the
  same element and point as the reference;
* **mesh**: the excavation of the 21 m ring, psi = 0 and 15 degrees (the
  second with a non-symmetric tangent), gives the same displacements,
  stresses, plastic zone and number of iterations of every increment.
"""
from __future__ import annotations

import math

import numpy as np

import _hole
from ogr_fem2d.engine import interface
from ogr_fem2d.engine.reference import mohr_coulomb as mc
from ogr_fem2d.engine.reference import solver
from poc.vectorized import NUMPY

E, NU, C, PHI = 10000.0, 0.2, 3.45, math.radians(30.0)


def _cloud(n=3000, seed=3):
    rng = np.random.default_rng(seed)
    psi = rng.choice([0.0, 15.0, 30.0], n)
    kind = np.where(rng.random(n) < 0.1, interface.ELASTIC, interface.MOHR_COULOMB)
    materials = np.array([[k, E, NU, C if k else 0.0, PHI if k else 0.0,
                           math.radians(p) if k else 0.0] for k, p in zip(kind, psi)])
    start = np.column_stack([rng.uniform(-40.0, 5.0, (n, 3)), rng.uniform(-10.0, 10.0, n)])
    strains = rng.uniform(-3e-3, 3e-3, (n, 3))
    return materials, start, strains


def _geometry(materials):
    n = len(materials)
    return interface.Geometry(0, np.zeros((n, 6), np.int64), np.zeros((n, 6)),
                              np.zeros((n, 6)), np.zeros(n), np.arange(n),
                              np.zeros(n, np.int64), np.zeros((n, 2)), materials)


def _reference(materials, start, strains):
    """The reference point by point; None where it refuses."""
    out = []
    for row, s0, eps in zip(materials, start, strains):
        material = solver._material_of(row)
        try:
            out.append(solver.update_stress(material, tuple(s0), tuple(eps))
                       + (mc.update(material, tuple(s0), tuple(eps)).region
                          if row[0] == interface.MOHR_COULOMB else "elastic",))
        except mc.ReturnMappingError:
            out.append(None)
    return out


class TestMaterialPoint:
    def test_a_cloud_over_every_region(self):
        materials, start, strains = _cloud()
        ref = _reference(materials, start, strains)
        ok = np.array([r is not None for r in ref])
        got = NUMPY.prepare(_geometry(materials[ok])).integrate(start[ok], strains[ok])
        kept = [r for r in ref if r is not None]
        ref_s = np.array([r[0] for r in kept])
        ref_p = np.array([r[1] for r in kept])
        ref_t = np.array([r[2] for r in kept])
        assert np.abs(got.stresses - ref_s).max() <= 1e-10 * 40.0
        assert np.array_equal(got.plastic, ref_p)
        assert np.abs(got.tangents - ref_t).max() <= 1e-10 * E
        regions = {r[3] for r in kept}
        assert regions == {"elastic", "plane", "right edge", "left edge", "apex"}, regions
        assert (~ok).any()                      # and some refusals to test below

    def test_states_on_the_surface(self):
        # Starting ON the yield surface (the stresses the reference returned
        # to it) with strain increments of 1e-9: the trial lies within about
        # 1e-7 of the surface, where only the tolerance of the return decides
        # between elastic and plastic. The variant must decide as the
        # reference does (mohr_coulomb.TOLERANCE).
        materials, start, strains = _cloud(seed=11)
        ref = _reference(materials, start, strains)
        on = [i for i, r in enumerate(ref) if r is not None and r[1]]
        materials = materials[on]
        start = np.array([ref[i][0] for i in on])
        strains = np.random.default_rng(12).uniform(-1e-9, 1e-9, (len(on), 3))
        ref = _reference(materials, start, strains)
        ok = np.array([r is not None for r in ref])
        got = NUMPY.prepare(_geometry(materials[ok])).integrate(start[ok], strains[ok])
        kept = [r for r in ref if r is not None]
        flags = np.array([r[1] for r in kept])
        assert np.array_equal(got.plastic, flags)
        assert flags.any() and not flags.all()
        assert np.abs(got.stresses - np.array([r[0] for r in kept])).max() <= 1e-10 * 40.0

    def test_the_apex_with_psi_zero_is_refused_at_the_same_point(self):
        materials, start, strains = _cloud()
        ref = _reference(materials, start, strains)
        first = next(i for i, r in enumerate(ref) if r is None)
        g = _geometry(materials)
        try:
            NUMPY.prepare(g).integrate(start, strains)
        except solver.StateUpdateError as err:
            assert (err.element, err.point) == (int(g.element[first]), 0)
            assert "apex" in err.reason
            return
        raise AssertionError("the apex with psi = 0 was not refused")


class TestMesh:
    def test_the_ring_gives_the_same_stage(self):
        for psi in (0.0, 15.0):
            m = mc.MohrCoulomb(E, NU, C, PHI, math.radians(psi))
            _mesh, ref = _hole.excavate(21.0, 12, 4, 1.2, m, 5, 1e-10, 25)
            _mesh, got = _hole.excavate(21.0, 12, 4, 1.2, m, 5, 1e-10, 25,
                                        variant=NUMPY)
            u_ref, u_got = np.array(ref.displacement), np.array(got.displacement)
            assert np.abs(u_got - u_ref).max() <= 1e-10 * np.abs(u_ref).max()
            s_ref, s_got = np.array(ref.stresses), np.array(got.stresses)
            assert np.abs(s_got - s_ref).max() <= 1e-10 * _hole.P0
            assert got.plastic == ref.plastic and any(ref.plastic)
            assert [(s, i) for s, i, _ in got.history] == [(s, i) for s, i, _ in ref.history]
