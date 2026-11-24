# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.11 (spec 005, T8) — the values at the nodes, by superconvergent patch
recovery material by material (RF-8, RF-9; D5; Zienkiewicz and Taylor 2000,
§14.4).

Invariants protected:

* **a field the patch polynomial holds comes back exact at every node a
  patch determines** (Eqs. 14.28-14.31: the least-squares fit of data that
  are a polynomial of the degree p reproduces it): a quadratic field with
  six-node triangles, on the curved mesh of a tunnel, boundary and hole
  included; only the corners of the square, in an element with no interior
  corner node, take their element's own field (D5);
* **the gravitational field** of two strata (linear in depth within each
  material, with a jump of the horizontal stress at the contact) comes back
  exact on both sides of the contact; with the materials mixed in one patch
  (a mutation), it does not;
* **a constant field with three-node triangles** comes back exact;
* **the rule of Fig. 14.8**: an interior corner node takes the value of its
  own patch, the polynomial fitted to the points of the elements that have
  it;
* **a material one element thick** has no interior node: its nodes take
  the field of their own elements, and their source says so;
* **an inactive element** takes no part (its points may hold anything) and
  has no value (NaN, source none).
"""
from __future__ import annotations

import numpy as np

import _models
from ogr_fem2d.engine import mesh_structured as ms
from ogr_fem2d.mesh import geometry as g
from ogr_fem2d.model import translate
from ogr_fem2d.results import recovery as rc
from ogr_fem2d.results import strains as st


def _quadratic(xy):
    x, y = xy[..., 0], xy[..., 1]
    return np.stack([1.0 + 2.0 * x - y + 0.5 * x * x + 0.3 * x * y - 0.2 * y * y,
                     -3.0 + 0.1 * x * x - 0.7 * y * y], axis=-1)


def _at_nodes(r, nodes, elements):
    return np.asarray(nodes)[np.asarray(elements)]          # (E, n, 2)


class TestExactFields:
    def test_a_quadratic_field_on_the_curved_mesh_of_a_tunnel(self):
        m = _models.meshed(_models.tunnel()).mesh
        geo = st.geometry(m.nodes, m.elements, "plane_strain")
        r = rc.recover(m.nodes, m.elements, [0] * len(m.elements), [True] * len(m.elements),
                       geo.xy, geo.element, _quadratic(geo.xy))
        want = _quadratic(_at_nodes(r, m.nodes, m.elements))
        spr = r.source == rc.SPR
        assert np.allclose(r.values[spr], want[spr], rtol=0.0, atol=1e-9)
        # the nodes no patch reaches are nodes of an element whose three
        # corners are all on the boundary (a corner of the square): they take
        # their element's own field, of degree p - 1 (D5)
        sides = {}
        for el in m.elements:
            for i, j in ((0, 1), (1, 2), (2, 0)):
                key = tuple(sorted((el[i], el[j])))
                sides[key] = sides.get(key, 0) + 1
        on_boundary = {n for key, c in sides.items() if c == 1 for n in key}
        cornered = {n for el in m.elements if all(c in on_boundary for c in el[:3]) for n in el}
        for e, a in zip(*np.nonzero(~spr)):
            assert m.elements[e][a] in cornered, (e, a)
        assert 0 < (~spr).sum() < 10

    def test_the_gravitational_field_on_both_sides_of_the_contact(self):
        m = _models.meshed(_models.layers())
        engine = translate.to_engine(m)
        geo = st.geometry(engine.nodes, engine.elements, engine.analysis)
        stress = np.array(engine.initial_stresses)
        mat = np.array(engine.element_material)
        r = rc.recover(engine.nodes, engine.elements, mat, [True] * len(mat), geo.xy, geo.element,
                       stress)
        at = _at_nodes(r, engine.nodes, engine.elements)
        for k in (0, 1):
            pts = mat[geo.element] == k
            line = rc.fit(geo.xy[pts], stress[pts], 1, geo.xy[pts].mean(axis=0))
            assert np.allclose(line(geo.xy[pts]), stress[pts], rtol=0, atol=1e-8)  # linear indeed
            got = r.values[mat == k].reshape(-1, 4)
            want = line(at[mat == k].reshape(-1, 2))
            assert np.allclose(got, want, rtol=0.0, atol=1e-7), k
        # the horizontal stress jumps at the contact: one node, two values
        contact = [n for n, (_x, y) in enumerate(engine.nodes) if y == -4.0]
        both = [(e, a) for e, el in enumerate(engine.elements) for a, n in enumerate(el) if n == contact[3]]
        values = {int(mat[e]): r.values[e, a, 0] for e, a in both}
        assert len(values) == 2 and abs(values[0] - values[1]) > 1.0

    def test_a_constant_field_with_three_node_triangles(self):
        t = _models.tunnel()
        t = _models.replace(t, mesh_settings=_models.replace(t.mesh_settings, nodes_per_element=3))
        engine = translate.to_engine(_models.meshed(t))
        geo = st.geometry(engine.nodes, engine.elements, engine.analysis)
        stress = np.array(engine.initial_stresses)
        r = rc.recover(engine.nodes, engine.elements, engine.element_material,
                       [True] * len(engine.elements), geo.xy, geo.element, stress)
        assert np.allclose(r.values, stress[0], rtol=1e-12)


class TestTheRules:
    MESH = ms.rectangle([0.0, 0.6, 1.3, 2.0, 2.4], [0.0, 0.5, 1.2, 2.0, 2.5], 6)

    def test_an_interior_corner_node_takes_its_own_patch(self):
        mesh = self.MESH
        geo = st.geometry(mesh.nodes, mesh.elements, "plane_strain")
        data = np.random.default_rng(3).uniform(-1, 1, size=(len(geo.element), 1))
        r = rc.recover(mesh.nodes, mesh.elements, [0] * len(mesh.elements),
                       [True] * len(mesh.elements), geo.xy, geo.element, data)
        node = mesh.nodes.index((1.3, 1.2))
        patch = [e for e, el in enumerate(mesh.elements) if node in el[:3]]
        idx = np.concatenate([np.arange(3 * e, 3 * e + 3) for e in patch])
        own = rc.fit(geo.xy[idx], data[idx], 2, np.array(mesh.nodes[node]))(np.array([mesh.nodes[node]]))
        for e in patch:
            a = list(mesh.elements[e]).index(node)
            assert np.allclose(r.values[e, a], own[0], rtol=0, atol=1e-13)

    def test_a_material_one_element_thick(self):
        mesh = ms.rectangle([0.0, 1.0, 2.0, 3.0], [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0], 6)
        geo = st.geometry(mesh.nodes, mesh.elements, "plane_strain")
        centre_y = [np.mean([mesh.nodes[n][1] for n in el[:3]]) for el in mesh.elements]
        mat = [1 if 2.0 < y < 3.0 else 0 for y in centre_y]
        linear = lambda xy: np.stack([2.0 + xy[..., 0] - 3.0 * xy[..., 1]], axis=-1)
        r = rc.recover(mesh.nodes, mesh.elements, mat, [True] * len(mat), geo.xy, geo.element,
                       linear(geo.xy))
        thin = np.array(mat) == 1
        assert np.all(r.source[thin] == rc.ELEMENT) and r.notes["nodes_by_element"] > 0
        assert np.any(r.source[~thin] == rc.SPR)
        assert np.allclose(r.values, linear(_at_nodes(r, mesh.nodes, mesh.elements)), atol=1e-10)

    def test_an_inactive_element_takes_no_part(self):
        mesh = self.MESH
        geo = st.geometry(mesh.nodes, mesh.elements, "plane_strain")
        data = _quadratic(geo.xy)
        active = [True] * len(mesh.elements)
        active[7] = False
        data[geo.element == 7] = 1e9                            # whatever it holds
        r = rc.recover(mesh.nodes, mesh.elements, [0] * len(active), active, geo.xy, geo.element, data)
        assert np.all(np.isnan(r.values[7])) and np.all(r.source[7] == rc.NONE)
        live = r.source == rc.SPR
        want = _quadratic(_at_nodes(r, mesh.nodes, mesh.elements))
        assert np.allclose(r.values[live], want[live], atol=1e-9) and live.sum() > 0
        assert np.all(np.abs(r.values[~np.isnan(r.values)]) < 1e3)    # nothing of the 1e9
