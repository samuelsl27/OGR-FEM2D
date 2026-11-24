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

import math
import tempfile

import _cases_model as cm
import _results
import _sphere
import _strip
from ogr_fem2d.model import ogr_file
from ogr_fem2d.results import queries as qy

C005 = "005-kirsch-malla-general"
C006 = "006-carga-en-faja-malla-general"
C007 = "007-cavidad-esferica-malla-general"


def _rows(view, m, query, quantity):
    if query["tipo"] == "linea":
        return qy.line(view, quantity, [query["desde"], query["hasta"]], query["n"]).rows
    return qy.on_boundary(view, quantity, m, query["contorno"], query["n_por_segmento"],
                          query["distancia"]).rows


def _check(name, reference, keep=lambda query, row: True):
    """Every query of the case within its tolerance; the worst errors."""
    c = cm.case(name)
    spec = c["comparaciones_consulta"]
    m = ogr_file.read(cm.path(name))
    worst = {}
    with tempfile.TemporaryDirectory() as d:
        view = qy.View(_results.calculated(m, d), spec["fase"])
        for query in spec["consultas"]:
            for mq in query["magnitudes"]:
                rows = [r for r in _rows(view, m, query, mq["magnitud"]) if keep(query, r)]
                assert rows and all(r.value is not None for r in rows), (query["tipo"], mq)
                error = max(reference(mq["magnitud"], mq["unidad_tolerancia"], r) for r in rows)
                worst[(query["tipo"], mq["magnitud"])] = error
                assert error <= mq["tolerancia_absoluta"], (name, query["tipo"], mq["magnitud"], error)
    return worst


class TestCase005:
    def test_the_radius_and_the_wall(self):
        c = cm.case(C005)["modelo"]
        p0, a = cm.KPA * c["tension_inicial"]["p0"], c["geometria"]["a"]
        shear = cm.KPA * c["material"]["E"] / (2.0 * (1.0 + c["material"]["nu"]))
        exact = {"sigma_1": lambda r: p0 * (1.0 + a * a / r ** 2),
                 "sigma_3": lambda r: p0 * (1.0 - a * a / r ** 2),
                 "u": lambda r: p0 * a * a / (2.0 * shear * r)}
        scale = {"p0": p0, "u_r(a)": exact["u"](a)}

        def reference(quantity, unit, row):
            return abs(row.value - exact[quantity](math.hypot(row.x, row.y))) / scale[unit]

        worst = _check(C005, reference)
        assert len(worst) == 4


class TestCase006:
    def test_the_axis_of_the_strip(self):
        def reference(quantity, unit, row):
            s1, s3, _ = _strip.closed.strip_principal(row.x, -row.y)
            want = {"sigma_1": s1, "sigma_3": s3}[quantity]
            return abs(row.value / cm.KPA - want) / _strip.Q

        assert len(_check(C006, reference)) == 2


class TestCase007:
    def test_the_radius_and_the_cavity(self):
        b = cm.case(C007)["modelo"]["geometria"]["b"]
        closed = _sphere.closed

        def reference(quantity, unit, row):
            s_r, s_t, u = closed.sphere_fixed_outer(math.hypot(row.x, row.y), b)
            if quantity == "u":
                return abs(row.value - u) / closed.sphere_fixed_outer(closed.A, b)[2]
            want = {"sigma_1": s_t, "sigma_z": s_t, "sigma_3": s_r}[quantity]
            return abs(row.value / cm.KPA - want) / closed.P0

        def on_the_arc(query, row):
            return query["tipo"] == "linea" or abs(math.hypot(row.x, row.y) - closed.A) < 1e-9

        assert len(_check(C007, reference, on_the_arc)) == 6
