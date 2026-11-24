# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.12 (spec 006, T8) — a field of the results ready to be drawn (RF-5,
D11).

Invariants protected:

* **the subdivision is the triangle's**: (n + 1)(n + 2)/2 vertices and 4**level
  triangles that fill it, every one anticlockwise;
* **at the nodes, the value drawn is the recovered one** (spec 005, D5),
  and the displacement the nodal one;
* **a field the element holds is drawn exactly at every vertex**, against
  its closed form (rule 1): in a laterally restrained column of two strata
  under a uniform load q, sigma_yy = q + sum(gamma h) down the column, and
  sigma_xx = K gamma-depth of the field plus nu / (1 - nu) q of the load,
  each stratum with its own K and nu;
* **materials are not mixed**: at the contact each side keeps its own
  sigma_xx (86.06 above, 69.33 below), the jump the field has;
* **a curved side is drawn curved**: the wall of the hole, on the T6's
  quadratic side, within 1e-5 of the arc, its nodes on it;
* **an inactive element is not drawn**, and ``absolute`` draws |value|;
* **the range of the legend is the whole range**: the stage's, every
  stage's, or the one given; asked wrongly, refused.
"""
from __future__ import annotations

import math
import tempfile

import numpy as np

import _models
import _results
from ogr_fem2d.model import stages
from ogr_fem2d.results import drawing, quantities as qt
from ogr_fem2d.results.queries import View

Q, G1, G2, C = 100.0, 18.0, 24.0, -4.0          # the loaded layers of _results


_DIRS = []                     # the results files live while the tests read them


def _view(m, stage=0):
    _DIRS.append(tempfile.TemporaryDirectory())
    return View(_results.calculated(m, _DIRS[-1].name), stage)


LAYERS = _view(_results.loaded_layers())


def _sigma_yy(y):
    return np.where(y >= C, Q + G1 * (-y), Q + G1 * (-C) + G2 * (C - y))


def _sigma_xx(y, top):
    depth_field = np.where(top, G1 * (-y), G1 * (-C) + G2 * (C - y))
    k, nu = np.where(top, 0.6, 0.5), np.where(top, 0.3, 0.25)
    return k * depth_field + nu / (1.0 - nu) * Q


class TestSubdivision:
    def test_it_fills_the_triangle(self):
        for level in range(4):
            bary, tris = drawing.subdivision(level)
            n = 2 ** level
            assert len(bary) == (n + 1) * (n + 2) // 2 and len(tris) == 4 ** level
            assert np.allclose(bary.sum(axis=1), 1.0)
            p = bary[:, 1:]                                  # (L2, L3)
            a, b, c = p[tris[:, 0]], p[tris[:, 1]], p[tris[:, 2]]
            area = 0.5 * ((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1])
                          - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0]))
            assert (area > 0).all() and abs(area.sum() - 0.5) <= 1e-12

    def test_refused(self):
        for bad in (-1, 7, 1.5):
            try:
                drawing.subdivision(bad)
            except ValueError:
                pass
            else:
                raise AssertionError(bad)


class TestTriangles:
    def test_they_cover_the_model_once(self):
        # the layers are 20 x 10 m: the triangles drawn, every one
        # anticlockwise, add up to 200 m2
        for level in (0, 2):
            f = drawing.field(LAYERS, "sigma_1", level=level)
            a, b, c = (f.xy[f.triangles[:, k]] for k in range(3))
            area = 0.5 * ((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1])
                          - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0]))
            assert (area > 0).all() and abs(area.sum() - 200.0) <= 1e-9


class TestValues:
    def test_at_the_nodes_the_recovered(self):
        f = drawing.field(LAYERS, "sigma_1", level=1)
        rec = LAYERS.recovered(qt.STRESS)
        # level 1: the six vertices of each element are its nodes, in the order
        # corner 1, mid 1-2, corner 2, mid 3-1, mid 2-3, corner 3
        order = [0, 3, 1, 5, 4, 2]
        per = 6
        expected = qt.of("sigma_1", rec.values[f.element[::4]][:, order].reshape(-1, 4))
        assert np.allclose(f.values.reshape(-1, per), expected.reshape(-1, per), rtol=0, atol=1e-9)
        u = drawing.field(LAYERS, "u_y", level=1)
        nodes = LAYERS.mesh.elements[u.element[::4]][:, order].reshape(-1)
        assert np.array_equal(u.values, qt.of("u_y", LAYERS.displacement()[nodes]))

    def test_a_field_the_element_holds_exactly(self):
        f = drawing.field(LAYERS, "sigma_yy", level=3)
        assert np.allclose(f.values, _sigma_yy(f.xy[:, 1]), rtol=0, atol=1e-8)
        g = drawing.field(LAYERS, "sigma_xx", level=3)
        top = np.repeat(g.material[::64] == 0, 45)
        assert np.allclose(g.values, _sigma_xx(g.xy[:, 1], top), rtol=0, atol=1e-8)

    def test_materials_are_not_mixed(self):
        g = drawing.field(LAYERS, "sigma_xx", level=2)
        at = np.abs(g.xy[:, 1] - C) <= 1e-12
        vertex_material = np.repeat(g.material[::16], 15)
        above = g.values[at & (vertex_material == 0)]
        below = g.values[at & (vertex_material == 1)]
        assert len(above) and len(below)
        assert np.allclose(above, 0.6 * 72.0 + 0.3 / 0.7 * Q, atol=1e-8)
        assert np.allclose(below, 0.5 * 72.0 + 0.25 / 0.75 * Q, atol=1e-8)


class TestTheElements:
    def test_inactive_not_drawn_and_curved_sides(self):
        view = _view(_results.excavated_tunnel())
        f = drawing.field(view, "sigma_1", level=2)
        assert set(np.unique(f.element)) == set(np.flatnonzero(view.active))
        r = np.hypot(f.xy[:, 0], f.xy[:, 1])
        # the wall is drawn on the T6's quadratic side, within 1e-5 of the arc;
        # drawn straight, its pieces of 10 degrees would come in to cos 5 deg,
        # 0.9962, between the nodes
        assert r.min() >= 1.0 - 1e-5
        assert (np.abs(r - 1.0) <= 1e-12).sum() >= 36   # the corners and mid nodes, on it

    def test_absolute(self):
        f = drawing.field(LAYERS, "u_y")
        a = drawing.field(LAYERS, "u_y", absolute=True)
        assert (f.values < 0).any() and np.array_equal(a.values, np.abs(f.values))


class TestRange:
    def test_stage_all_and_custom(self):
        f = drawing.field(LAYERS, "sigma_1")
        assert drawing.value_range(LAYERS, "sigma_1") == (f.values.min(), f.values.max())
        assert drawing.value_range(LAYERS, "sigma_1", drawing.CUSTOM, low=0.0, high=500.0) == (0.0, 500.0)
        # two stages, the load taken off in the second: 316 then 216 kPa at the bottom
        two = stages.set_load_factor(_models.with_stages(_results.loaded_layers(), 2), 0, "2", 0.0)
        second = _view(two, 1)
        one = drawing.value_range(second, "sigma_1")
        first = drawing.value_range(View(second.results, 0), "sigma_1")
        both = drawing.value_range(second, "sigma_1", drawing.AUTO_ALL)
        assert abs(one[1] - 216.0) <= 1e-8 and abs(first[1] - 316.0) <= 1e-8
        assert both == (min(one[0], first[0]), max(one[1], first[1])) and both != one

    def test_refused(self):
        for kw in ({"mode": "percentile"}, {"mode": drawing.CUSTOM, "low": 2.0, "high": 1.0},
                   {"mode": drawing.AUTO_STAGE, "low": 0.0}):
            try:
                drawing.value_range(LAYERS, "sigma_1", **kw)
            except ValueError:
                pass
            else:
                raise AssertionError(kw)
