# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.16 (spec 007, T5) — case 008, the strip footing on Tresca
(validacion/casos/008-prandtl-zapata-tresca; ficha VER-STR-05), as the
engine sees it. What this file protects grows with the tasks of spec 007:
T5 the model and the identity of the two variants of the engine; T6 the
plateau against (2 + pi) c; T8 the stage above collapse.

Invariants protected (T5):

* **the model is the case**: the material, the strip, the restraints and
  the two variants of esperado.json and caso.md (the strip nodes held in y
  only in (a), the load only on 0 <= x <= b in (b), the pressure of (b)
  integrated over b is q b);
* **Rust is the reference** (ADR-0001, criterion 1): on the coarsest mesh of
  the study, two rigid stages to 0.2 of the elastic settlement (past first
  yield at the edge of the strip) and a flexible one at 0.7 (2 + pi) c give
  the same displacements, stresses and reactions to 1e-12 relative, and the
  same increments.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import _footing as ft
from ogr_fem2d.engine.compiled import RUST
from ogr_fem2d.engine.reference import solver

CASE = Path(__file__).resolve().parents[1] / "validacion" / "casos" / "008-prandtl-zapata-tresca"
COARSE = (30.0, 30.0, 0.5, 1.5 ** 0.5)          # W, D, h0, g: the first mesh of the study


def _expected():
    return json.loads((CASE / "esperado.json").read_text(encoding="utf-8"))


class TestTheModelIsTheCase:
    def test_material_strip_and_restraints(self):
        e = _expected()
        mat = e["modelo"]["material"]
        assert (ft.E, ft.NU, ft.C) == (mat["E"], mat["nu"], mat["c"])
        assert ft.TRESCA.phi == mat["phi"] == 0.0 and ft.TRESCA.psi == mat["psi"] == 0.0
        assert ft.B == e["modelo"]["geometria"]["b"]
        assert abs(ft.P_LIM - e["valor_esperado"]["valor"]) < 1e-15
        mesh = ft.mesh_for(*COARSE)
        model = ft.rigid(mesh, [0.01])
        stage = model.stages[0]
        top = ft.footing_nodes(mesh)
        assert top and all(mesh.nodes[n][1] == 0.0 and mesh.nodes[n][0] <= ft.B for n in top)
        assert {(i.node, i.component, i.value) for i in stage.imposed} == {(n, 1, -0.01) for n in top}
        held = {r.node: (r.x, r.y) for r in stage.restraints}
        for n in top:
            assert not held.get(n, (False, False))[1]          # v is imposed, not held
            assert held.get(n, (False, False))[0] == (mesh.nodes[n][0] == 0.0)   # smooth
        for n in mesh.boundary["bottom"]:
            assert held[n] == (True, True)
        for n in mesh.boundary["right"]:
            assert held[n][0]

    def test_the_flexible_load_is_q_over_b(self):
        from ogr_fem2d.engine import analysis
        mesh = ft.mesh_for(*COARSE)
        model = ft.flexible(mesh, [0.2])
        f = analysis.stage_load(model, 0)
        assert abs(sum(f[1::2]) + 0.2 * ft.B) < 1e-12           # q b, downward
        assert abs(sum(f[0::2])) < 1e-12
        loaded = {n for n in range(len(mesh.nodes)) if f[2 * n + 1] != 0.0}
        assert all(mesh.nodes[n][1] == 0.0 and mesh.nodes[n][0] <= ft.B for n in loaded)


class TestRustIsTheReference:
    def test_both_variants(self):
        mesh = ft.mesh_for(*COARSE)
        delta_e = ft.elastic_settlement(mesh, RUST)
        # pushed down, the footing settles and the ground pushes back: the
        # case's signs (pressure and settlement positive downward)
        assert delta_e > 0.0
        # small stages, past first yield: the reference in Python is slow,
        # and larger increments do not converge (changelog v0.0.16, T5b)
        settings = dict(ft.STUDY, steps=4)
        for model in (ft.rigid(mesh, [0.1 * delta_e, 0.2 * delta_e], settings),
                      ft.flexible(mesh, [0.7 * ft.P_LIM], settings)):
            ref, ref_err = ft.stages(model, solver.REFERENCE)
            rust, rust_err = ft.stages(model, RUST)
            assert ref_err is None and rust_err is None, (ref_err, rust_err)
            assert any(any(o.plastic) for o in ref)                # past first yield
            assert ft.settlement(mesh, ref[-1]) > 0.0
            for a, b in zip(ref, rust):
                ua, ub = np.array(a.displacement), np.array(b.displacement)
                assert np.abs(ua - ub).max() <= 1e-12 * np.abs(ua).max()
                sa, sb = np.array(a.stresses), np.array(b.stresses)
                assert np.abs(sa - sb).max() <= 1e-12 * np.abs(sa).max()
                ra = np.array([a.reactions[n] for n in sorted(a.reactions)])
                rb = np.array([b.reactions[n] for n in sorted(b.reactions)])
                assert np.abs(ra - rb).max() <= 1e-12 * np.abs(ra).max()
                assert [(i.start, i.end, i.status) for i in a.increments] == \
                    [(i.start, i.end, i.status) for i in b.increments]
