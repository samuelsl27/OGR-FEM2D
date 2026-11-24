# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.13 (spec 006, T12) — the operations that edit a model and its mesh
(RF-6, RF-7, RF-8, RF-12).

Invariants protected:

* **a case is built from nothing by the operations**: case 006, drawn,
  given its material, conditions, load and mesh settings and meshed through
  them, is the model of its ``modelo.ogrfem2d`` (its model fingerprint,
  which includes the mesh, spec 004 D12): the operations reach everything a
  case needs and change nothing on the way;
* **every edit of ``model/edit.py`` has its operation** (the table below,
  counted against the module), and every stage edit of ``stages.py``;
* **a drawing with its cuts is one undo step**: the vertices put in both
  boundaries are listed, and undoing takes them out of both;
* **the mesh stays and is said stale** after an edit of the geometry or of
  the settings; the first step (``mesh_discretize``) changes nothing;
  ``mesh_reset`` takes it away;
* **a stage edit acts from its stage on**, as the stage edits of spec 004;
* **what is asked wrongly is refused by name**: a kind of boundary, of
  condition or of load that does not exist, a stretch and a vertex at once
  or neither, a point load on a boundary, a stage that does not exist.
"""
from __future__ import annotations

import inspect

import _cases_model
import _models
from ogr_core.api import InvalidArgument, NotFound

from ogr_fem2d import api
from ogr_fem2d.api.workspace import Held
from ogr_fem2d.model import edit, fingerprint, ogr_file, stages
from ogr_fem2d.model import model as md

#: the operation that reaches each public edit (the next_* give ids inside them)
EDITS = {
    "add_boundary": "boundary_add", "delete_boundary": "boundary_edit",
    "rename_boundary": "boundary_edit", "set_boundary_kind": "boundary_edit",
    "set_closed": "boundary_edit", "translate_boundary": "boundary_edit",
    "move_vertex": "boundary_edit", "insert_vertex": "boundary_edit",
    "delete_vertex": "boundary_edit", "set_arc": "boundary_edit", "set_divisions": "boundary_edit",
    "add_material": "material_set", "set_material": "material_set",
    "delete_material": "material_delete", "set_field": "field_set",
    "add_condition": "condition_set", "set_condition": "condition_set",
    "delete_condition": "condition_delete", "set_default_restraint": "condition_default",
    "add_distributed_load": "load_set", "add_point_load": "load_set", "set_load": "load_set",
    "delete_load": "load_delete", "set_mesh_settings": "mesh_settings",
    "set_analysis": "project_settings", "set_units": "project_settings",
    "set_summary": "project_settings",
    "next_id": "boundary_add", "next_material_id": "material_set", "next_stage_id": "stage_add",
}
STAGE_EDITS = {"insert_stage": "stage_add", "delete_stage": "stage_delete",
               "rename_stage": "stage_rename", "set_excavated": "region_excavate",
               "assign_material": "material_assign", "set_condition_active": "condition_stage",
               "set_condition_factor": "condition_stage", "set_load_factor": "load_stage"}


def _refused(fn, kind, *words):
    try:
        fn()
    except kind as err:
        for w in words:
            assert w in str(err), (w, str(err))
        return err
    raise AssertionError(f"accepted; expected {kind.__name__}")


def _model(ws, pid):
    return ws.get(pid).project.model


class TestCase006FromNothing:
    def test_the_operations_build_the_case(self):
        ws = api.workspace()
        def c(name, /, **kw):
            return api.call(ws, name, project_id=pid, **kw)
        pid = api.call(ws, "project_new", name="Caso 006", units="metric_mpa")["project_id"]
        c("stage_rename", stage="1", name="Carga")
        c("boundary_add", type="external", boundary="ext", name="Exterior",
          points_xy=[[0, -200], [200, -200], [200, 0], [1, 0], [0, 0]])
        c("boundary_edit", boundary="ext", op="set_divisions", segment=3, divisions=8)
        soil = c("material_set", name="Semiespacio", E=2.0e7, nu=0.2)["material"]
        c("material_assign", material=soil, x=100, y=-100)
        for kind, start, end, name in (("free", [200, 0], [0, 0], "Superficie"),
                                       ("x", [200, -200], [200, 0], "Lateral"),
                                       ("x", [0, 0], [0, -200], "Simetría")):
            c("condition_set", kind=kind, boundary="ext", start=start, end=end, name=name)
        c("load_set", kind="distributed", boundary="ext", start=[1, 0], end=[0, 0],
          magnitude=1000.0, name="Faja")
        c("mesh_settings", boundary_nodes=4, max_size=6.25,
          windows=[{"polygon": [[0, 0], [0, -6], [6, -6], [6, 0]], "size": 0.125}])
        got = c("mesh_generate")
        case = ogr_file.read(_cases_model.path("006-carga-en-faja-malla-general"))
        assert got["elements"] == len(case.mesh.elements)
        m = _model(ws, pid)
        assert fingerprint.model_fingerprint(m) == fingerprint.model_fingerprint(case)
        # the names, which the model's fingerprint leaves out (spec 004, D12)
        names = lambda x: ([b.name for b in x.boundaries], [y.name for y in x.materials],
                           [s.name for s in x.stages], [k.name for k in x.conditions],
                           [k.name for k in x.loads])
        assert names(m) == names(case)
        # changing a material changes it, it does not add one
        c("material_set", material=soil, E=3.0e7)
        assert [x.E for x in _model(ws, pid).materials] == [3.0e7]


class TestEveryEditHasItsOperation:
    def test_counted(self):
        public = {n for n, f in inspect.getmembers(edit, inspect.isfunction)
                  if not n.startswith("_") and f.__module__ == edit.__name__}
        assert public == set(EDITS), sorted(public ^ set(EDITS))
        mods = {n for n, f in inspect.getmembers(stages, inspect.isfunction)
                if not n.startswith("_") and f.__module__ == stages.__name__}
        assert mods == set(STAGE_EDITS), sorted(mods ^ set(STAGE_EDITS))
        assert set(EDITS.values()) | set(STAGE_EDITS.values()) <= set(api.OPERATIONS)


class TestCutsAndUndo:
    def test_a_drawing_with_its_cuts_is_one_step(self):
        ws = api.workspace()
        pid = ws.add(Held(_models.tunnel())).id
        before = _model(ws, pid)
        got = api.call(ws, "boundary_add", project_id=pid, type="stage",
                       points_xy=[[-10, 0.5], [10, 0.5]])
        assert {x["boundary"] for x in got["cuts"]} == {"stg1", "hole", "ext"}
        assert len(_model(ws, pid).boundary("hole").vertices) == 6
        assert api.call(ws, "project_history", project_id=pid)["undo"] == ["Add boundary"]
        api.call(ws, "project_history", project_id=pid, action="undo")
        assert _model(ws, pid) is before
        circle = api.call(ws, "boundary_circle", project_id=pid, type="excavation",
                          centre=[5, 5], radius=1.0)
        assert circle["cuts"] == [] and len(_model(ws, pid).boundary(circle["boundary"]).segments) == 4


class TestTheMesh:
    def test_stale_discretize_reset(self):
        ws = api.workspace()
        pid = ws.add(Held(_models.meshed(_models.tunnel()))).id
        mesh = _model(ws, pid).mesh
        d = api.call(ws, "mesh_discretize", project_id=pid)
        assert _model(ws, pid).mesh is mesh and sum(s["divisions"] for s in d["segments"]
                                                    if abs(s["from"][0]) <= 1.0) == 36
        api.call(ws, "boundary_edit", project_id=pid, boundary="ext", op="translate", dx=1.0)
        assert _model(ws, pid).mesh is mesh
        assert api.call(ws, "project_validate", project_id=pid)["mesh"] == "stale"
        api.call(ws, "mesh_generate", project_id=pid)
        assert api.call(ws, "project_validate", project_id=pid)["mesh"] == "current"
        api.call(ws, "mesh_settings", project_id=pid, boundary_nodes=48)
        assert api.call(ws, "project_validate", project_id=pid)["mesh"] == "stale"
        assert api.call(ws, "mesh_reset", project_id=pid)["mesh"] == "none"


class TestStages:
    def test_from_its_stage_on(self):
        ws = api.workspace()
        pid = ws.add(Held(_models.tunnel())).id
        def c(name, /, **kw):
            return api.call(ws, name, project_id=pid, **kw)
        c("stage_add", name="Excavación")
        c("stage_add", name="Fin")
        c("region_excavate", x=0.0, y=0.0, stage="2")
        assert _model(ws, pid).assignments[1].excavated == (True, True, True)  # the tunnel's
        m = _model(ws, pid)
        c("load_set", kind="point", vertex=[10, 10], magnitude=5.0)
        c("load_stage", load=0, stage="2", factor=2.0)
        assert _model(ws, pid).loads[0].factors == (1.0, 2.0, 2.0)
        c("condition_set", kind="x", boundary="ext", start=[10, -10], end=[10, 10])
        c("condition_stage", condition=0, stage="3", active=False)
        assert _model(ws, pid).conditions[0].active == (True, True, False)
        c("stage_delete", stage="2")
        assert [s.name for s in _model(ws, pid).stages] == ["Stage 1", "Fin"]
        assert m is not _model(ws, pid)


class TestRefused:
    def test_by_name(self):
        ws = api.workspace()
        pid = ws.add(Held(_models.tunnel())).id
        def c(name, /, **kw):
            return api.call(ws, name, project_id=pid, **kw)
        _refused(lambda: c("boundary_add", type="joint", points_xy=[[0, 0], [1, 1]]), NotFound,
                 "'joint'", "excavation")
        _refused(lambda: c("condition_set", kind="z", vertex=[10, 10]), NotFound, "'z'")
        _refused(lambda: c("condition_set", kind="x"), InvalidArgument, "one of the two")
        _refused(lambda: c("condition_set", kind="x", boundary="ext", vertex=[10, 10]),
                 InvalidArgument, "one of the two")
        _refused(lambda: c("load_set", kind="point", boundary="ext", vertex=[10, 10],
                           magnitude=1.0), InvalidArgument, "vertex")
        _refused(lambda: c("load_set", kind="distributed", vertex=[10, 10], magnitude=1.0),
                 InvalidArgument, "stretch")
        _refused(lambda: c("region_excavate", x=0, y=0, stage="9"), NotFound, "'9'")
        _refused(lambda: c("boundary_edit", boundary="ext", op="explode"), NotFound, "'explode'")
        err = _refused(lambda: c("material_set", material="rock", nu=0.5), InvalidArgument, "nu")
        assert err.details["problems"][0]["rule"] == "material"
        _refused(lambda: c("boundary_edit", boundary="hole", op="delete_vertex", index=0),
                 InvalidArgument, "arc_vertex")
