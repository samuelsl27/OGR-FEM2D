# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.9 (spec 004, T15 to T17) — the validation cases through their
``modelo.ogrfem2d`` (D4): opened, translated, solved and compared with the
value and tolerance their esperado.json fixes (a failing case is never
edited to pass).

Invariants protected:

* **case 005 through the model is the case written by hand**: the file opens
  to a model whose mesher input is exactly the one tests/_kirsch_mesh.py
  writes; its stored mesh is the mesher's of that input, bit for bit (a
  mesher that changed would say so here, rule 9); its engine input is the
  one written by hand from the case's description in kPa, bit for bit; and
  solved, it meets the 0.5 % of the case (Kirsch 1898, in JCZ 2007, §8.4);
* **every file is what this program writes**: read and written again, the
  same bytes; built again from tests/_cases_model.py and meshed, the same
  model, bit for bit, but the notes of its mesh, to rounding (their angles
  come from the system's math.acos);
* **case 006** (Michell 1902, in T&G 1951, §34), the strip load with the load
  and the conditions on the geometry, meets 0.01 q in sigma_1 and sigma_3 at
  every integration point of its band, on the mesh its study fixed;
* **case 007** (Lamé 1852, in T&G 1951, §121), the spherical cavity in
  axisymmetry with arcs and an excavated region, meets 0.5 % in sigma_t and
  u_R, on the mesh its study fixed.
"""
from __future__ import annotations

from dataclasses import replace
from functools import lru_cache

import _cases_model as cm
import _kirsch_mesh as km
from ogr_fem2d.engine import analysis
from ogr_fem2d.engine import initial_stress as ini
from ogr_fem2d.engine import model as em
from ogr_fem2d.engine.reference.elastic import Elastic
from ogr_fem2d.mesh import mesher
from ogr_fem2d.model import ogr_file, translate

C005 = "005-kirsch-malla-general"
C006 = "006-carga-en-faja-malla-general"
C007 = "007-cavidad-esferica-malla-general"


@lru_cache(maxsize=None)
def _opened(name):
    return ogr_file.read(cm.path(name))


@lru_cache(maxsize=None)
def _hand_mesh_005():
    spec = cm.case(C005)["modelo"]["malla"]
    return mesher.mesh(km.geometry(spec["ventana"]["h"], spec["cota_maxima"]))


def _hand_engine_005():
    """The engine input of case 005 as its caso.md describes it, in kPa: the
    hand-made mesh, one elastic material, the hydrostatic field of 30 MPa,
    the outer square fixed, the hole's elements inactive."""
    mesh = _hand_mesh_005()
    c = cm.case(C005)["modelo"]
    law = Elastic(cm.KPA * c["material"]["E"], c["material"]["nu"])
    restraints = tuple(em.Restraint(n, True, True) for n in km._nodes_of(mesh, km.OUTER))
    stage = em.Stage(active=tuple(r == 0 for r in mesh.element_region), restraints=restraints)
    base = em.EngineModel("plane_strain", mesh.nodes, mesh.elements, (em.Material(law),),
                          (0,) * len(mesh.elements), (stage,))
    p0 = cm.KPA * c["tension_inicial"]["p0"]
    return em.EngineModel(base.analysis, base.nodes, base.elements, base.materials,
                          base.element_material, base.stages, ini.constant_field(base, p0, p0, p0, 0.0))


class TestCase005:
    def test_the_mesher_input_is_the_hand_written_one(self):
        spec = cm.case(C005)["modelo"]["malla"]
        assert translate.to_mesh_input(_opened(C005)) == km.geometry(spec["ventana"]["h"],
                                                                      spec["cota_maxima"])

    def test_the_stored_mesh_is_the_mesher_s(self):
        stored, hand = _opened(C005).mesh, _hand_mesh_005()
        assert stored.nodes == hand.nodes and stored.elements == hand.elements
        assert stored.element_region == hand.element_region
        assert stored.boundaries == hand.boundaries

    def test_the_engine_input_is_the_hand_written_one(self):
        assert translate.to_engine(_opened(C005)) == _hand_engine_005()

    def test_005_through_the_model(self):
        m = _opened(C005)
        engine = translate.to_engine(m)
        out = analysis.run(engine)[0]
        worst = cm.errors_005(m, engine, out)
        tolerance = cm.case(C005)["tolerancia_relativa"]
        assert abs(worst["sigma_theta"]) <= tolerance and abs(worst["u_r"]) <= tolerance, worst


class TestTheFiles:
    def test_read_and_written_again_the_same_bytes(self):
        """The same bytes but the line of ``written_by``: the files were written
        by the version of their spec, and a later version writes its own name
        (found when v0.0.10 raised the pin: the content is the identity, not
        who wrote it, D12)."""
        def body(text):
            return [line for line in text.splitlines() if not line.startswith('  "written_by": ')]

        for name in (C005, C006, C007):
            written = cm.path(name).read_bytes().decode("utf-8")
            again = ogr_file.dumps(_opened(name))
            assert body(again) == body(written), name
            assert sum(line.startswith('  "written_by": "OGR FEM2D ') for line in written.splitlines()) == 1

    def test_built_again_the_same_model(self):
        """The model and its mesh, bit for bit; the notes of the mesh to
        rounding: the quality summary takes its angles from math.acos, and
        the library of another system or Python may round the last digit
        another way (found in the CI of v0.0.9: Python 3.11 against the files
        written with 3.14). The notes are a record of how the mesh was made,
        out of the model's fingerprint (D12); the nodes and the elements are
        not, and they are the same bit for bit everywhere (spec 003, D11)."""
        built = {C005: translate.mesh(cm.model_005())}
        for name, builder in ((C006, cm.model_006), (C007, cm.model_007)):
            mesh = cm.case(name)["modelo"]["malla"]
            built[name] = translate.mesh(builder(mesh["ventana"]["h"], mesh["ventana"]["semilado"],
                                                 mesh["cota_maxima"] / mesh["ventana"]["h"]))
        for name, m in built.items():
            opened = _opened(name)
            assert replace(opened, mesh=replace(opened.mesh, notes={})) ==                 replace(m, mesh=replace(m.mesh, notes={})), name
            _close(opened.mesh.notes, m.mesh.notes, name)


def _close(a, b, where):
    """Two JSON values equal but for floats, which agree to 1e-12."""
    if isinstance(a, dict):
        assert isinstance(b, dict) and a.keys() == b.keys(), where
        for k in a:
            _close(a[k], b[k], f"{where}, {k}")
    elif isinstance(a, list):
        assert isinstance(b, list) and len(a) == len(b), where
        for x, y in zip(a, b):
            _close(x, y, where)
    elif isinstance(a, float) and isinstance(b, float):
        assert abs(a - b) <= 1e-12 * max(1.0, abs(a)), (where, a, b)
    else:
        assert a == b, (where, a, b)


class TestCase006:
    def test_006_michell_through_the_model(self):
        m = _opened(C006)
        engine = translate.to_engine(m)
        out = analysis.run(engine)[0]
        e1, e3, count = cm.errors_006(engine, out)
        tolerance = cm.case(C006)["tolerancia_absoluta"]
        assert count > 0 and e1 <= tolerance and e3 <= tolerance, (e1, e3, count)


class TestCase007:
    def test_007_lame_through_the_model(self):
        m = _opened(C007)
        engine = translate.to_engine(m)
        out = analysis.run(engine)[0]
        sigma_t, u, points, nodes = cm.errors_007(m, engine, out)
        tolerance = cm.case(C007)["tolerancia_relativa"]
        assert points > 0 and nodes > 0 and sigma_t <= tolerance and u <= tolerance, (sigma_t, u)
