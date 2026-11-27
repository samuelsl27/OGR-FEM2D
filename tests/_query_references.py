# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The closed solutions of the queries of cases 005, 006 and 007 (their
``comparaciones_consulta``), as the error of one row over the scale its
esperado.json names (not a test file: the queries' validation, spec 005,
and the cases through the interface, spec 006, both use it).

* **005** (VER-STR-01): Kirsch (1898), in Jaeger, Cook and Zimmerman (2007),
  §8.4, Eqs. (8.90)-(8.92), hydrostatic: sigma_theta = p0 (1 + a^2/r^2),
  sigma_r = p0 (1 - a^2/r^2), u_r = p0 a^2 / (2 G r);
* **006** (VER-STR-04): Michell (1902), in Timoshenko and Goodier (1951),
  §34, Eq. (f), on the axis of the strip;
* **007** (VER-STR-09): Lamé (1852), in Timoshenko and Goodier (1951),
  §121, Eqs. (197)-(198), the hollow sphere with u_R(21 m) = 0, which is
  the model (spec 002, comprobaciones, sphere_fixed_outer); on the cavity,
  only the points on the arc (those of the straight stretches are in the
  excavated cavity).

Values are in the units kept (m, kPa), compression positive as the
queries give them; ``EXACT[name]()`` is the closed form at (x, y) and the
scales of the case's tolerances.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

import _cases_model as cm
import _sphere
import _strip

C005 = "005-kirsch-malla-general"
C006 = "006-carga-en-faja-malla-general"
C007 = "007-cavidad-esferica-malla-general"


def exact_005():
    """sigma_1, sigma_3 and u of case 005 at (x, y), and its scales."""
    c = cm.case(C005)["modelo"]
    p0, a = cm.KPA * c["tension_inicial"]["p0"], c["geometria"]["a"]
    shear = cm.KPA * c["material"]["E"] / (2.0 * (1.0 + c["material"]["nu"]))
    radial = {"sigma_1": lambda r: p0 * (1.0 + a * a / r ** 2),
              "sigma_3": lambda r: p0 * (1.0 - a * a / r ** 2),
              "u": lambda r: p0 * a * a / (2.0 * shear * r)}

    def exact(quantity, x, y):
        return radial[quantity](math.hypot(x, y))
    return exact, {"p0": p0, "u_r(a)": radial["u"](a)}


def exact_006():
    def exact(quantity, x, y):
        s1, s3, _ = _strip.closed.strip_principal(x, -y)
        return cm.KPA * {"sigma_1": s1, "sigma_3": s3}[quantity]
    return exact, {"q": cm.KPA * _strip.Q}


def exact_007():
    b = cm.case(C007)["modelo"]["geometria"]["b"]
    closed = _sphere.closed

    def exact(quantity, x, y):
        s_r, s_t, u = closed.sphere_fixed_outer(math.hypot(x, y), b)
        if quantity == "u":
            return u
        return cm.KPA * {"sigma_1": s_t, "sigma_z": s_t, "sigma_3": s_r}[quantity]
    return exact, {"P0": cm.KPA * closed.P0, "u_R(a)": closed.sphere_fixed_outer(closed.A, b)[2]}


EXACT = {C005: exact_005, C006: exact_006, C007: exact_007}


def errors(name):
    """``error(quantity, unit, x, y, value)``: absolute, over the case's scale."""
    exact, scale = EXACT[name]()

    def error(quantity, unit, x, y, value):
        return abs(value - exact(quantity, x, y)) / scale[unit]
    return error


def keep_007(query, x, y) -> bool:
    return query["tipo"] == "linea" or abs(math.hypot(x, y) - _sphere.closed.A) < 1e-9


KEEP = {C007: keep_007}
