# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.13 (spec 006, T11) — the operations on a whole model and its history
(RF-6 to RF-8), on the core's framework (``ogr_core.api``, ADR-0005).

Invariants protected:

* **nothing unknown is taken in silence** (RF-7): an operation, an argument
  it does not take, a value out of its options or of the wrong type, each
  refused with its name and the closest known ones; the errors carry their
  code (rule 2);
* **an edit is one undo step, all or nothing** (RF-8): several settings in
  one call, one step; undone, the model is the one before, the same
  object; redone, the one after; an edit that changes nothing leaves no
  step; one the model refuses leaves the model as it was and no step, and
  the error names every problem with its rule;
* **open, save and close keep the file and the model together**: a
  ``.ogrfem2d`` opened is the file's model; saved elsewhere and opened
  again, the same model (fingerprint); "unsaved" follows the edits and the
  saves; another existing file is not replaced unless told to; closing
  with unsaved changes is refused unless told to;
* **a conversion says what it did**: a ``.ogr`` of OGR Slip2D and a
  ``.dxf`` come as new models without a file, with their report;
* **the summary and the validation say why a model cannot be calculated**:
  no mesh, a material without E or nu.
"""
from __future__ import annotations

import tempfile
from dataclasses import replace
from pathlib import Path

import ezdxf

import _cases_model
import _models
from ogr_core.api import Conflict, InvalidArgument, NotFound, OgrApiError
from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
from ogr_core.materials import Material
from ogr_core.materials.builtin_models import MohrCoulomb
from ogr_core.project.project import Project

from ogr_fem2d import api
from ogr_fem2d.api.workspace import Held
from ogr_fem2d.engine.reference.quadrature import AXISYMMETRIC
from ogr_fem2d.model import fingerprint, ogr_file
from ogr_fem2d.model import model as md


def _refused(fn, kind, *words):
    try:
        fn()
    except kind as err:
        text = str(err)
        for w in words:
            assert w in text, (w, text)
        return err
    raise AssertionError(f"accepted; expected {kind.__name__}")


def _with(m: md.Model):
    ws = api.workspace()
    return ws, ws.add(Held(m)).id


class TestNothingUnknown:
    def test_operations_arguments_and_values(self):
        ws = api.workspace()
        _refused(lambda: api.call(ws, "project_nwe"), NotFound, "'project_nwe'", "project_new")
        _refused(lambda: api.call(ws, "project_new", nmae="x"), NotFound, "'nmae'", "name")
        _refused(lambda: api.call(ws, "project_new", analysis="3d"), NotFound, "'3d'",
                 "plane_strain")
        _refused(lambda: api.call(ws, "project_new", units="furlongs"), NotFound, "'furlongs'")
        _refused(lambda: api.call(ws, "project_new", name=3), InvalidArgument, "name must be text")
        _refused(lambda: api.call(ws, "project_history", action="redo", steps="many"),
                 OgrApiError, "steps")
        err = _refused(lambda: api.call(ws, "project_history", action="back"), NotFound, "'back'")
        assert err.to_dict()["message_code"] == "api.unknown"


class TestUndo:
    def test_one_step_all_or_nothing(self):
        ws, pid = _with(_models.tunnel())
        before = ws.get(pid).project.model
        api.call(ws, "project_settings", project_id=pid, units="metric_mpa", title="Túnel",
                 author="UPCT")
        after = ws.get(pid).project.model
        assert (after.units, after.summary.title, after.summary.author) == \
            ("metric_mpa", "Túnel", "UPCT")
        h = api.call(ws, "project_history", project_id=pid)
        assert h["undo"] == ["Project settings"] and h["redo"] == []
        api.call(ws, "project_history", project_id=pid, action="undo")
        assert ws.get(pid).project.model is before
        api.call(ws, "project_history", project_id=pid, action="redo")
        assert ws.get(pid).project.model is after

    def test_nothing_changed_no_step_and_refused_no_step(self):
        ws, pid = _with(_models.tunnel())
        api.call(ws, "project_settings", project_id=pid, units=md.DEFAULT_UNITS)
        assert api.call(ws, "project_history", project_id=pid)["undo"] == []
        before = ws.get(pid).project.model
        err = _refused(lambda: api.call(ws, "project_settings", project_id=pid,
                                        analysis=AXISYMMETRIC, title="Nuevo"),
                       InvalidArgument, "left_of_axis")
        assert err.details["problems"][0]["rule"] == "left_of_axis"
        assert err.to_dict()["message_code"] == "fem.model.invalid"
        assert ws.get(pid).project.model is before
        assert api.call(ws, "project_history", project_id=pid)["undo"] == []

        # an edit that changes the model and then fails leaves it as it was
        def half(held):
            held.model = replace(held.model, units="metric_mpa")
            raise RuntimeError("half way")
        _refused(lambda: ws.mutate(pid, "half", half), RuntimeError, "half way")
        assert ws.get(pid).project.model is before


class TestFiles:
    def test_open_save_close(self):
        case = _cases_model.path("006-carga-en-faja-malla-general")
        with tempfile.TemporaryDirectory() as d:
            ws = api.workspace(workdir=d)
            got = api.call(ws, "project_open", path=str(case))
            pid = got["project_id"]
            m = ws.get(pid).project.model
            assert m == ogr_file.read(case) and got["converted_from"] is None
            assert api.call(ws, "project_list")["projects"][0]["unsaved"] is False
            api.call(ws, "project_save", project_id=pid, path="copia")
            assert Path(ws.get(pid).path) == Path(d).resolve() / "copia.ogrfem2d"
            again = api.call(ws, "project_open", path="copia.ogrfem2d")["project_id"]
            assert fingerprint.document_fingerprint(ws.get(again).project.model) == \
                fingerprint.document_fingerprint(m)
            api.call(ws, "project_settings", project_id=again, title="Otra")
            assert ws.get(again).unsaved()
            _refused(lambda: api.call(ws, "project_close", project_id=again), Conflict,
                     "unsaved changes")
            api.call(ws, "project_save", project_id=again)          # its own file
            assert not ws.get(again).unsaved()
            # a model being drawn is saved, and opened again says what is unfinished
            empty = api.call(ws, "project_new", name="Vacío")["project_id"]
            api.call(ws, "project_save", project_id=empty, path="vacio")
            got = api.call(ws, "project_open", path="vacio.ogrfem2d")
            assert [p["rule"] for p in got["problems"]] == ["external"]
            other = ws.add(Held(replace(_models.tunnel(), summary=md.Summary("Otro")))).id
            _refused(lambda: api.call(ws, "project_save", project_id=other, path="copia"),
                     Conflict)
            api.call(ws, "project_save", project_id=other, path="copia", overwrite=True)
            assert ogr_file.read(Path(d) / "copia.ogrfem2d").summary.title == "Otro"
            _refused(lambda: api.call(ws, "project_save", project_id=other, path="x.ogr"),
                     InvalidArgument, ".ogrfem2d")
            api.call(ws, "project_settings", project_id=other, title="Cambiado")
            assert api.call(ws, "project_close", project_id=other,
                            discard_changes=True)["discarded_changes"] is True
            assert other not in [p["project_id"] for p in api.call(ws, "project_list")["projects"]]

    def test_a_new_model_has_no_file(self):
        ws = api.workspace()
        pid = api.call(ws, "project_new", name="Nuevo")["project_id"]
        _refused(lambda: api.call(ws, "project_save", project_id=pid), InvalidArgument, "no file")

    def test_conversions_say_what_they_did(self):
        with tempfile.TemporaryDirectory() as d:
            ogr = Path(d) / "talud.ogr"
            p = Project("talud")
            V = Vertex
            p.add_boundary(Boundary(polyline=Polyline([V(0, 0), V(40, 0), V(40, 20), V(0, 20)],
                                                      closed=True), btype=BoundaryType.EXTERNAL))
            clay = Material(name="arcilla", strength=MohrCoulomb(cohesion=10, friction_angle=25),
                            unit_weight=19)
            p.materials = [clay]
            p.assign_material_at(5, 5, clay.id)
            p.save(ogr)
            dxf = Path(d) / "plano.dxf"
            doc = ezdxf.new()
            doc.modelspace().add_lwpolyline([(0, 0), (10, 0), (10, 10), (0, 10)], close=True,
                                            dxfattribs={"layer": "External"})
            doc.saveas(dxf)
            ws = api.workspace(workdir=d)
            for path in (ogr, dxf):
                got = api.call(ws, "project_open", path=str(path))
                assert got["path"] is None and got["converted_from"] == str(path.resolve())
                assert set(got["report"]) == {"brought", "not_brought", "defaults", "changed"}
                assert got["report"]["brought"], got["report"]
                assert ws.get(got["project_id"]).path is None
            _refused(lambda: api.call(ws, "project_open", path="talud.txt"), NotFound)
            (Path(d) / "notas.txt").write_text("x", encoding="utf-8")
            _refused(lambda: api.call(ws, "project_open", path="notas.txt"), InvalidArgument,
                     ".ogrfem2d")


class TestWhyNot:
    def test_summary_and_validation(self):
        ws, pid = _with(_models.tunnel())
        v = api.call(ws, "project_validate", project_id=pid)
        assert (v["ready"], v["mesh"], v["problems"]) == (False, "none", [])
        ws, pid = _with(_models.meshed(_models.tunnel()))
        assert api.call(ws, "project_validate", project_id=pid)["ready"] is True
        api.call(ws, "project_settings", project_id=pid, title="Sin cambiar la malla")
        assert api.call(ws, "project_validate", project_id=pid)["mesh"] == "current"
        ws, pid = _with(replace(_models.meshed(_models.tunnel()), materials=(md.Material("rock"),)))
        v = api.call(ws, "project_validate", project_id=pid)
        assert v["ready"] is False and v["materials_incomplete"] == ["rock"]
        s = api.call(ws, "project_summary", project_id=pid)
        assert s["mesh"]["state"] == "current" and s["materials"][0]["complete"] is False
