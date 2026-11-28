# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.15 (spec 006, T37; spec 005, RF-13) — the query at every node, in a
time that grows with the mesh and not with its square.

Invariants protected:

* **the same rows**: bit for bit and in the same order as the query gave
  them before (the materials of each node looked for among every key, the
  form written below as the oracle), on a contact of two materials and with
  excavated elements, for a stress and a strain;
* **case 006 (35 401 nodes) in seconds**: it took 24 s before for one stress,
  and 56 s with case 005, the window standing still all that time.
"""
from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import numpy as np

import _cases_model
import _results
from ogr_fem2d.engine.compiled import RUST
from ogr_fem2d.model import ogr_file
from ogr_fem2d.results import calculate as calc
from ogr_fem2d.results import queries as qy
from ogr_fem2d.results import recovery

SLOWER = 5.0 if os.environ.get("CI") else 1.0


def _as_before(view, quantity):
    """The rows of a stress or a strain at every node, as the query wrote
    them up to v0.0.15 (the oracle)."""
    from ogr_fem2d.results import quantities as qt
    m = view.mesh
    rec = view.recovered(qt.get(quantity).kind)
    value = qt.of(quantity, rec.values)
    first: dict = {}
    for e in np.flatnonzero(view.active):
        mat = int(m.element_material[e])
        for a, node in enumerate(m.elements[e]):
            key = (int(node), mat)
            if key not in first:
                first[key] = (float(value[e, a]), int(e), recovery.SOURCES[int(rec.source[e, a])])
    with_value = {node for node, _ in first}
    rows = []
    for i, (x, y) in enumerate(m.nodes):
        if i not in with_value:
            rows.append(qy.Row(i, float(x), float(y), None, None, reason="removed"))
            continue
        for (node, mat) in sorted(k for k in first if k[0] == i):
            v, e, source = first[(node, mat)]
            rows.append(qy.Row(i, float(x), float(y), None, v, e, mat, source))
    return tuple(rows)


class TestTheSameRows:
    def test_a_contact_and_an_excavation(self):
        seen = set()
        for model in (_results.loaded_layers(), _results.excavated_tunnel(2)):
            with tempfile.TemporaryDirectory() as d:
                results = _results.calculated(model, d)
                for k in range(results.n_stages):
                    view = qy.View(results, k)
                    for quantity in ("sigma_xx", "sigma_1", "eps_v"):
                        got = qy.all_nodes(view, quantity).rows
                        want = _as_before(view, quantity)
                        assert got == want, (k, quantity)
                        if len({r.point for r in got}) < len(got):
                            seen.add("contact")
                        if any(r.reason == "removed" for r in got):
                            seen.add("removed")
        assert seen == {"contact", "removed"}               # both were asked


class TestInSeconds:
    def test_case_006(self):
        m = ogr_file.read(_cases_model.path("006-carga-en-faja-malla-general"))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "modelo.ogrfem2d"
            ogr_file.write(m, p)
            calc.calculate(m, p, RUST)
            view = qy.View(calc.open_results(p, m).results, 0)
            view.recovered("stress")                      # the recovery is not what is timed
            t = time.perf_counter()
            rows = qy.all_nodes(view, "sigma_1").rows
            took = time.perf_counter() - t
            print(f"every node of case 006, sigma_1: {took:.2f} s, {len(rows)} rows")
            assert len(rows) >= len(view.mesh.nodes) == 35401
            assert took <= 2.0 * SLOWER, took
