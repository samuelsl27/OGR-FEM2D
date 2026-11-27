# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.11 (spec 005, T14 to T16) — the validation cases through the queries
(``POST-LINEA`` of their fichas), with the tolerances their esperado.json
fixed before measuring (D10, T13; a failing case is never edited to pass).

Each case is calculated into a results file, opened, and queried as its
``comparaciones_consulta`` says: along a line, and on a boundary of the
model. Every row is compared with the closed solution at its place, the
error absolute and over the scale the case names.

* **005** (VER-STR-01): Kirsch (1898), in Jaeger, Cook and Zimmerman (2007),
  §8.4, Eqs. (8.90)-(8.92), hydrostatic: sigma_theta = p0 (1 + a^2/r^2),
  sigma_r = p0 (1 - a^2/r^2), u_r = p0 a^2 / (2 G r); the radius r = a to
  5a and the wall of the hole;
* **006** (VER-STR-04): Michell (1902), in Timoshenko and Goodier (1951),
  §34, Eq. (f), on the axis of the strip from z = 0.25 to 5 m;
* **007** (VER-STR-09): Lamé (1852), in Timoshenko and Goodier (1951),
  §121, Eqs. (197)-(198), the hollow sphere with u_R(21 m) = 0, which is
  the model (spec 002, comprobaciones, sphere_fixed_outer): the radius at
  45 degrees from R = a to 5 m and the arc of the cavity.
"""
from __future__ import annotations

import tempfile

import _cases_model as cm
import _query_references as refs
import _results
from ogr_fem2d.model import ogr_file
from ogr_fem2d.results import queries as qy

C005, C006, C007 = refs.C005, refs.C006, refs.C007


def _rows(view, m, query, quantity):
    if query["tipo"] == "linea":
        return qy.line(view, quantity, [query["desde"], query["hasta"]], query["n"]).rows
    return qy.on_boundary(view, quantity, m, query["contorno"], query["n_por_segmento"],
                          query["distancia"]).rows


def _check(name, keep=lambda query, x, y: True):
    """Every query of the case within its tolerance; the worst errors."""
    c = cm.case(name)
    spec = c["comparaciones_consulta"]
    m = ogr_file.read(cm.path(name))
    reference = refs.errors(name)
    worst = {}
    with tempfile.TemporaryDirectory() as d:
        view = qy.View(_results.calculated(m, d), spec["fase"])
        for query in spec["consultas"]:
            for mq in query["magnitudes"]:
                rows = [r for r in _rows(view, m, query, mq["magnitud"]) if keep(query, r.x, r.y)]
                assert rows and all(r.value is not None for r in rows), (query["tipo"], mq)
                error = max(reference(mq["magnitud"], mq["unidad_tolerancia"], r.x, r.y, r.value)
                            for r in rows)
                worst[(query["tipo"], mq["magnitud"])] = error
                assert error <= mq["tolerancia_absoluta"], (name, query["tipo"], mq["magnitud"], error)
    return worst


class TestCase005:
    def test_the_radius_and_the_wall(self):
        assert len(_check(C005)) == 4


class TestCase006:
    def test_the_axis_of_the_strip(self):
        assert len(_check(C006)) == 2


class TestCase007:
    def test_the_radius_and_the_cavity(self):
        assert len(_check(C007, refs.keep_007)) == 6
