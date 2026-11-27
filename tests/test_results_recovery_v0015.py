# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.15 (spec 006, T32) — the recovery with lighter bookkeeping is the
recovery: the same values, sources and notes as v0.0.14's, bit for bit.

The recovery itself is validated against its source in
``test_results_recovery_v0011.py`` (Zienkiewicz and Taylor 2000, §14.4);
here only the change of v0.0.15 is held, against the code before it, on
meshes of three- and six-node triangles, two materials, a material one
element thick and inactive elements.
"""
from __future__ import annotations

import time

import numpy as np

import _models
import _recovery_v0014 as before
from ogr_fem2d.engine import mesh_structured as ms
from ogr_fem2d.model import translate
from ogr_fem2d.results import recovery as rc
from ogr_fem2d.results import strains as st


def _same(*args):
    a, b = rc.recover(*args), before.recover(*args)
    assert np.array_equal(a.values, b.values, equal_nan=True)
    assert np.array_equal(a.source, b.source)
    assert a.notes == b.notes
    return a


def _inputs(nodes, elements, mat, active, seed):
    geo = st.geometry(nodes, elements, "plane_strain")
    data = np.random.default_rng(seed).uniform(-1e3, 1e3, size=(len(geo.element), 4))
    return nodes, elements, mat, active, geo.xy, geo.element, data


class TestBitForBit:
    def test_structured_meshes(self):
        for n in (3, 6):
            mesh = ms.rectangle([0.0, 0.6, 1.3, 2.0, 2.4], [0.0, 0.5, 1.2, 2.0, 2.5, 3.1], n)
            k = len(mesh.elements)
            centre_y = [np.mean([mesh.nodes[i][1] for i in el[:3]]) for el in mesh.elements]
            thin = [1 if 1.2 < y < 2.0 else 0 for y in centre_y]      # one element thick
            active = [e % 7 != 3 for e in range(k)]
            for mat, act in (([0] * k, [True] * k), (thin, [True] * k), (thin, active)):
                r = _same(*_inputs(mesh.nodes, mesh.elements, mat, act, 11 + n))
                assert (r.source == rc.SPR).any()
            assert (r.source == rc.ELEMENT).any() and (r.source == rc.NONE).any()

    def test_a_general_mesh_of_two_materials(self):
        m = translate.mesh(_models.layers()).mesh
        engine = translate.to_engine(_models.meshed(_models.layers()))
        mat = list(engine.element_material)
        active = [True] * len(mat)
        active[5] = active[40] = False
        _same(*_inputs(m.nodes, m.elements, mat, active, 5))

    def test_faster(self):
        m = translate.mesh(_models.tunnel(h=0.15)).mesh
        args = _inputs(m.nodes, m.elements, [0] * len(m.elements), [True] * len(m.elements), 2)
        t = time.perf_counter()
        rc.recover(*args)
        now = time.perf_counter() - t
        t = time.perf_counter()
        before.recover(*args)
        then = time.perf_counter() - t
        print(f"recovery of {len(m.elements)} elements: {now:.3f} s, before {then:.3f} s")
        assert now < then
