# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The models of the validation cases that have a ``modelo.ogrfem2d`` (spec 004,
D4), and the comparisons of cases 006 and 007 (not a test file: the runner
only collects test_*.py; the study of spec 004 uses it too).

* **005**, Kirsch with the general mesh (validacion/casos/005-...): the
  square of half-side 100 m with the hole of radius 1 m in four arcs, the
  hole excavated in the stage; the mesh of its esperado.json;
* **006**, the strip load (validacion/casos/006-...): the half of the
  half-space of 200 x 200 m, a vertex at (1, 0), the load on (1, 0) -> (0, 0);
  a window [0, w] x [-w, 0] of size h, the strip segment divided into pieces
  of h, a bound of 50 h on every side;
* **007**, the spherical cavity (validacion/casos/007-...): the quarter of
  the corona 1 <= R <= 21 m in the meridian plane, the cavity a region
  excavated in the stage; a window [0, w] x [0, w] of size h, the nodes of
  the excavation's boundary spread with pieces of about h, a bound of 50 h.

Every value is in kPa (D5): the cases are written in MPa, and their values
are integers, so the factor 1000 is exact. The comparisons convert the
engine's stresses back to MPa, the unit of the closed forms of specs 001 and
002, and to compression positive (D6), here and nowhere else.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import _kirsch_mesh as km
import _sphere
import _strip
from ogr_fem2d.engine import initial_stress as ini
from ogr_fem2d.mesh import geometry as g
from ogr_fem2d.model import model as md
from ogr_fem2d.model import translate

CASES = Path(__file__).resolve().parents[1] / "validacion" / "casos"
KPA = 1000.0                      # kPa per MPa
B = md.Boundary


def case(name: str) -> dict:
    return json.loads((CASES / name / "esperado.json").read_text(encoding="utf-8"))


def path(name: str) -> Path:
    return CASES / name / "modelo.ogrfem2d"


# -------------------------------------------------------------------- 005
def model_005() -> md.Model:
    c = case("005-kirsch-malla-general")["modelo"]
    half, a, mesh = c["geometria"]["semilado_exterior"], c["geometria"]["a"], c["malla"]
    w, h = mesh["ventana"]["semilado"], mesh["ventana"]["h"]
    p0 = KPA * c["tension_inicial"]["p0"]
    return md.Model(
        summary=md.Summary("Caso 005: Kirsch con malla general", "", "2026-11-23",
                           "validacion/casos/005-kirsch-malla-general"),
        units="metric_mpa",
        boundaries=(B("ext", md.EXTERNAL, ((-half, -half), (half, -half), (half, half), (-half, half)),
                      True, name="Exterior"),
                    B("hole", md.EXCAVATION, ((a, 0.0), (0.0, a), (-a, 0.0), (0.0, -a)), True,
                      tuple(md.SegmentAttr(k, (0.0, 0.0)) for k in range(4)), name="Hueco")),
        materials=(md.Material("rock", "Roca", KPA * c["material"]["E"], c["material"]["nu"]),),
        stages=(md.Stage("1", "Excavación"),),
        assignments=(md.Assignment((0.5 * half, 0.0), "rock", (False,)),
                     md.Assignment((0.0, 0.0), "rock", (True,))),
        field=md.ConstantField(p0, p0, p0, 0.0),
        mesh_settings=g.MeshSettings(boundary_nodes=mesh["nudos_hueco"], max_size=mesh["cota_maxima"],
                                     quality_bound=mesh["B"],
                                     windows=(g.Window(((-w, -w), (w, -w), (w, w), (-w, w)), h),)))


def errors_005(m: md.Model, engine, outcome) -> dict:
    """The worst errors of the case, with the engine's stresses in MPa."""
    from dataclasses import replace
    mpa = replace(outcome, stresses=[None if s is None else tuple(v / KPA for v in s)
                                     for s in outcome.stresses])
    return km.worst_errors(_AsMesh(m), engine, mpa, km.P0, km.P0)


class _AsMesh:
    """The stored mesh where tests/_kirsch_mesh.py expects the mesher's."""

    def __init__(self, m):
        self.nodes = m.mesh.nodes
        self._b = {b.name: b for b in m.mesh.boundaries}

    def boundary(self, name):
        return self._b[name]


# -------------------------------------------------------------------- 006
def model_006(h: float, window: float = 6.0, max_factor: float = 50.0) -> md.Model:
    c = case("006-carga-en-faja-malla-general")["modelo"]
    w, d, b = c["geometria"]["W"], c["geometria"]["D"], c["geometria"]["b"]
    q = KPA * c["carga"]["q"]
    ext = B("ext", md.EXTERNAL, ((0.0, -d), (w, -d), (w, 0.0), (b, 0.0), (0.0, 0.0)), True,
            (md.SegmentAttr(3, divisions=math.ceil(b / h)),), name="Exterior")
    return md.Model(
        summary=md.Summary("Caso 006: carga en faja con malla general", "", "2026-11-23",
                           "validacion/casos/006-carga-en-faja-malla-general"),
        units="metric_mpa",
        boundaries=(ext,),
        materials=(md.Material("soil", "Semiespacio", KPA * c["material"]["E"], c["material"]["nu"]),),
        stages=(md.Stage("1", "Carga"),),
        assignments=(md.Assignment((0.5 * w, -0.5 * d), "soil", (False,)),),
        conditions=(md.Condition(md.FREE, md.Span("ext", (w, 0.0), (0.0, 0.0)), active=(True,),
                                 name="Superficie"),
                    md.Condition(md.X, md.Span("ext", (w, -d), (w, 0.0)), active=(True,),
                                 name="Lateral"),
                    md.Condition(md.X, md.Span("ext", (0.0, 0.0), (0.0, -d)), active=(True,),
                                 name="Simetría")),
        loads=(md.DistributedLoad(md.Span("ext", (b, 0.0), (0.0, 0.0)), q, q, factors=(1.0,),
                                  name="Faja"),),
        mesh_settings=g.MeshSettings(boundary_nodes=4, max_size=max_factor * h,
                                     windows=(g.Window(((0.0, 0.0), (0.0, -window), (window, -window),
                                                        (window, 0.0)), h),)))


def errors_006(engine, outcome, x_max=0.25, z_min=0.25, z_max=5.0) -> tuple[float, float, int]:
    """The worst |sigma_1 - Michell| and |sigma_3 - Michell| over q, at the
    integration points with x <= x_max and z_min <= z <= z_max."""
    points = ini.integration_point_coordinates(engine)
    e1 = e3 = 0.0
    count = 0
    for (x, y), s in zip(points, outcome.stresses):
        if s is None or x > x_max or not z_min <= -y <= z_max:
            continue
        s1, s3 = _strip.principal_compressive(tuple(v / KPA for v in s))
        m1, m3, _ = _strip.closed.strip_principal(x, -y)
        e1, e3 = max(e1, abs(s1 - m1) / _strip.Q), max(e3, abs(s3 - m3) / _strip.Q)
        count += 1
    return e1, e3, count


# -------------------------------------------------------------------- 007
def model_007(h: float, window: float = 3.0, max_factor: float = 50.0) -> md.Model:
    c = case("007-cavidad-esferica-malla-general")["modelo"]
    a, b = c["geometria"]["a"], c["geometria"]["b"]
    p0 = KPA * c["tension_inicial"]["p0"]
    ext = B("ext", md.EXTERNAL, ((0.0, 0.0), (a, 0.0), (b, 0.0), (0.0, b), (0.0, a)), True,
            (md.SegmentAttr(2, (0.0, 0.0)),), name="Exterior")
    cavity = B("cavity", md.EXCAVATION, ((0.0, 0.0), (a, 0.0), (0.0, a)), True,
               (md.SegmentAttr(1, (0.0, 0.0)),), name="Cavidad")
    nodes = math.ceil((2.0 * a + 0.5 * math.pi * a) / h)
    return md.Model(
        analysis=md.AXISYMMETRIC,
        summary=md.Summary("Caso 007: cavidad esférica con malla general", "", "2026-11-23",
                           "validacion/casos/007-cavidad-esferica-malla-general"),
        units="metric_mpa",
        boundaries=(ext, cavity),
        materials=(md.Material("rock", "Roca", KPA * c["material"]["E"], c["material"]["nu"]),),
        stages=(md.Stage("1", "Excavación"),),
        assignments=(md.Assignment((0.3 * b, 0.3 * b), "rock", (False,)),
                     md.Assignment((0.3 * a, 0.3 * a), "rock", (True,))),
        field=md.ConstantField(p0, p0, p0, 0.0),
        conditions=(md.Condition(md.Y, md.Span("ext", (0.0, 0.0), (b, 0.0)), active=(True,),
                                 name="Simetría"),
                    md.Condition(md.FREE, md.Span("ext", (0.0, b), (0.0, 0.0)), active=(True,),
                                 name="Eje")),
        mesh_settings=g.MeshSettings(boundary_nodes=nodes, max_size=max_factor * h,
                                     windows=(g.Window(((0.0, 0.0), (window, 0.0), (window, window),
                                                        (0.0, window)), h),)))


def errors_007(m: md.Model, engine, outcome) -> tuple[float, float, int, int]:
    """The worst relative errors of sigma_t (meridian and hoop) at the
    integration points of the active elements with a side on the cavity, and
    of u_R at the nodes on R = a, against the infinite medium (the case's
    reference)."""
    ctx = translate.context(m)
    seg = ctx.segment_of[("cavity", 1)]
    bd = ctx.mesh_boundary[seg]
    active = engine.stages[0].active
    elements = sorted({e for sides in bd.sides for e, _k in sides if active[e]})
    points = ini.integration_point_coordinates(engine)
    per = len(points) // len(engine.elements)
    closed = _sphere.closed
    sigma_t = 0.0
    count = 0
    for e in elements:
        for k in range(e * per, (e + 1) * per):
            stress = tuple(v / KPA for v in outcome.stresses[k])
            big_r, _sr, merid, hoop, _t = _sphere.spherical_compressive(points[k], stress)
            want = closed.sphere_infinite(big_r)[1]
            sigma_t = max(sigma_t, abs(merid / want - 1.0), abs(hoop / want - 1.0))
            count += 1
    nodes = list(bd.nodes) + list(bd.mids)
    u_want = closed.sphere_infinite(closed.A)[2]
    u = 0.0
    for n in nodes:
        x, y = engine.nodes[n]
        r = math.hypot(x, y)
        inward = -(outcome.displacement[2 * n] * x + outcome.displacement[2 * n + 1] * y) / r
        u = max(u, abs(inward / u_want - 1.0))
    return sigma_t, u, count, len(nodes)
