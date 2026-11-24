# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.11 (spec 005, T2) — the strains at the integration points, B u with the
engine's B (D3, D6).

Invariants protected:

* **the patch test** (Zienkiewicz and Taylor 2000, ch. 2 and §10): a
  displacement linear in x and y, imposed at the nodes, gives the exact
  strain at every point: eps_x = du/dx, eps_y = dv/dy, gamma_xy = du/dy +
  dv/dx (JCZ 2007, Eqs. 2.181-2.185, engineering shear), and in axisymmetry
  eps_theta = u / r (Z&T Eqs. 5.5-5.6) at the point. With T3 and T6, in
  plane strain and in axisymmetry, and on the curved T6 of a tunnel;
* **the engine's B**: the vectorised product is IntegrationPoint.strain of
  the engine, point by point, to rounding;
* **the inactive elements have no strain** (NaN at their points, RF-9);
* **the user's sign and the factor 2** of gamma_max (D3): a pure shear gamma
  gives gamma_max = gamma, twice the tensorial one; a shortening is positive.
"""
from __future__ import annotations

import numpy as np

import _models
from ogr_fem2d.engine import mesh_structured as ms
from ogr_fem2d.engine.reference import solver
from ogr_fem2d.model import conventions
from ogr_fem2d.results import quantities as qt
from ogr_fem2d.results import strains as st

A = (0.002, 3e-4, -1e-4)       # u = a0 + a1 x + a2 y
B = (-0.001, 2e-4, 5e-4)       # v = b0 + b1 x + b2 y


def _linear(nodes):
    u = np.empty(2 * len(nodes))
    for k, (x, y) in enumerate(nodes):
        u[2 * k] = A[0] + A[1] * x + A[2] * y
        u[2 * k + 1] = B[0] + B[1] * x + B[2] * y
    return u


def _check_patch(nodes, elements, analysis):
    g = st.geometry(nodes, elements, analysis)
    e = st.strains(g, _linear(nodes))
    assert np.allclose(e[:, 0], A[1], rtol=0, atol=1e-15)
    assert np.allclose(e[:, 1], B[2], rtol=0, atol=1e-15)
    assert np.allclose(e[:, -1], A[2] + B[1], rtol=0, atol=1e-15)
    if analysis == "axisymmetric":
        x, y = g.xy[:, 0], g.xy[:, 1]
        assert np.allclose(e[:, 2], (A[0] + A[1] * x + A[2] * y) / x, rtol=1e-12, atol=0)
    return g, e


class TestThePatch:
    def test_t3_and_t6_in_plane_strain(self):
        for n in (3, 6):
            m = ms.rectangle([0.0, 0.7, 1.5, 3.0], [-2.0, -0.8, 0.0], n)
            _check_patch(m.nodes, m.elements, "plane_strain")

    def test_t3_and_t6_in_axisymmetry(self):
        for n in (3, 6):
            m = ms.rectangle([0.5, 0.9, 1.6, 3.0], [-2.0, -0.8, 0.0], n)
            g, e = _check_patch(m.nodes, m.elements, "axisymmetric")
            # the volumetric strain counts the hoop strain (JCZ Eq. 2.231)
            ev = qt.strain_quantity("eps_v", qt.strain4(conventions.user_strain(e), "axisymmetric"))
            x, y = g.xy[:, 0], g.xy[:, 1]
            assert np.allclose(ev, -(A[1] + B[2] + (A[0] + A[1] * x + A[2] * y) / x), rtol=1e-12)

    def test_the_curved_t6_of_a_tunnel(self):
        m = _models.meshed(_models.tunnel())
        _check_patch(m.mesh.nodes, m.mesh.elements, "plane_strain")


class TestTheEnginesB:
    def test_point_by_point(self):
        m = _models.meshed(_models.tunnel())
        nodes, elements = m.mesh.nodes, m.mesh.elements
        rng = np.random.default_rng(5)
        u = rng.uniform(-1e-3, 1e-3, size=2 * len(nodes))
        e = st.strains(st.geometry(nodes, elements, "plane_strain"), u)
        model = solver.Model(list(nodes), list(elements), [None] * len(elements), frozenset())
        for k, p in enumerate(solver.integration_points(model)):
            assert np.allclose(e[k], p.strain(list(u)), rtol=1e-12, atol=1e-18), k

    def test_the_inactive_elements_have_none(self):
        m = ms.rectangle([0.0, 1.0, 2.0], [0.0, 1.0], 6)
        g = st.geometry(m.nodes, m.elements, "plane_strain")
        active = [True] * len(m.elements)
        active[1] = False
        e = st.strains(g, _linear(m.nodes), active)
        assert np.all(np.isnan(e[g.element == 1])) and not np.any(np.isnan(e[g.element != 1]))


class TestTheUsersSign:
    def test_gamma_max_is_the_engineering_one(self):
        gamma = 4e-4
        m = ms.rectangle([0.0, 1.0, 2.0], [0.0, 1.0], 6)
        u = np.empty(2 * len(m.nodes))
        for k, (x, y) in enumerate(m.nodes):
            u[2 * k], u[2 * k + 1] = 0.5 * gamma * y, 0.5 * gamma * x
        e = conventions.user_strain(st.strains(st.geometry(m.nodes, m.elements, "plane_strain"), u))
        e4 = qt.strain4(e, "plane_strain")
        assert np.allclose(qt.strain_quantity("gamma_max", e4), gamma, rtol=1e-12)
        assert np.allclose(qt.strain_quantity("eps_v", e4), 0.0, atol=1e-18)

    def test_a_shortening_is_positive(self):
        m = ms.rectangle([0.0, 1.0, 2.0], [0.0, 1.0], 3)
        u = np.zeros(2 * len(m.nodes))
        u[0::2] = [-1e-3 * x for x, _ in m.nodes]            # shortening along x
        e = conventions.user_strain(st.strains(st.geometry(m.nodes, m.elements, "plane_strain"), u))
        e4 = qt.strain4(e, "plane_strain")
        assert np.allclose(qt.strain_quantity("eps_xx", e4), 1e-3, rtol=1e-12)
        assert np.allclose(qt.strain_quantity("eps_v", e4), 1e-3, rtol=1e-12)
        assert np.all(qt.strain_quantity("eps_z", e4) == 0.0)
