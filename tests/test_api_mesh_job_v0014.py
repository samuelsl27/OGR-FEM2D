# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.14 (decided on 2026-11-25) — meshing as a job in a child process:
``mesh_generate(background=True)``, ``mesh_collect``, and the window's
meshing on them (spec 006, T25's finding: with the meshes of the cases the
window stood still 2 to 4 s).

Invariants protected:

* **the child's mesh is the mesh**: collected, it is the one the
  operation makes in the process, bit for bit, and one step to undo;
* **the model is untouched until it is collected**: a model edited while
  the job ran is refused (mesh again), and a cancelled job leaves the
  model as it was;
* **what would fail at once is refused before a process starts** (no
  nodes on the excavations, a model the mesher refuses);
* a job that is not done, or not of meshing, is not collected;
* **the window meshes through the job**: its dialog is shown while the
  child works, its Cancel stops it, and the model gets the same mesh.
"""
from __future__ import annotations

import os
from dataclasses import replace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

import _models  # noqa: E402
from ogr_core.api import Conflict, InvalidArgument  # noqa: E402
from ogr_fem2d import api  # noqa: E402
from ogr_fem2d.api.workspace import Held  # noqa: E402
from ogr_fem2d.gui.main_window import MainWindow  # noqa: E402
from ogr_fem2d.model import translate  # noqa: E402

APP = QApplication.instance() or QApplication([])
MODEL = replace(_models.layers(), mesh=None)


def _refused(fn, kind, *words):
    try:
        fn()
    except kind as err:
        for w in words:
            assert w in str(err) or w in str(getattr(err, "details", "")), (w, str(err))
        return err
    raise AssertionError(f"accepted; expected {kind.__name__}")


class _Ws:
    def __enter__(self):
        self.ws = api.workspace()
        self.pid = self.ws.add(Held(MODEL)).id
        return self

    def call(self, name, /, **kw):
        return api.call(self.ws, name, **kw)

    def __exit__(self, *exc):
        self.ws.shutdown()


class TestTheJob:
    def test_the_childs_mesh_is_the_mesh(self):
        with _Ws() as w:
            got = w.call("mesh_generate", project_id=w.pid, background=True, wait=120)
            assert got["state"] == "done", got
            assert w.ws.get(w.pid).project.model.mesh is None        # not yet
            done = w.call("mesh_collect", job_id=got["job_id"])
            m = w.ws.get(w.pid).project.model
            here = translate.mesh(MODEL).mesh
            assert (m.mesh.nodes, m.mesh.elements, m.mesh.source) == (
                here.nodes, here.elements, here.source)
            assert done["nodes"] == len(here.nodes) and done["elements"] == len(here.elements)
            undo, _redo = w.call("project_history", project_id=w.pid)["undo"], None
            assert undo[-1] == "Mesh"
            _refused(lambda: w.call("mesh_collect", job_id=got["job_id"]), Conflict,
                     "changed while")                     # collected: the model is another
            # what would fail at once, before a process starts
            w.call("mesh_settings", project_id=w.pid, clear=["boundary_nodes"])
            _refused(lambda: w.call("mesh_generate", project_id=w.pid, background=True),
                     InvalidArgument, "boundary_nodes")
            assert len(w.ws.jobs.jobs) == 1

    def test_edited_while_meshing_and_cancelled(self):
        with _Ws() as w:
            job = w.call("mesh_generate", project_id=w.pid, background=True)["job_id"]
            _refused(lambda: w.call("mesh_collect", job_id=job), Conflict, "has not made")
            w.call("project_settings", project_id=w.pid, title="otro")
            api.call(w.ws, "job_get", job_id=job, wait=120)
            _refused(lambda: w.call("mesh_collect", job_id=job), Conflict, "changed while")
            assert w.ws.get(w.pid).project.model.mesh is None
            job = w.call("mesh_generate", project_id=w.pid, background=True)["job_id"]
            st = w.call("job_cancel", job_id=job, grace_s=0.0)
            assert st["state"] == "cancelled", st
            _refused(lambda: w.call("mesh_collect", job_id=job), Conflict, "cancelled")
            assert w.ws.get(w.pid).project.model.mesh is None


class TestTheWindow:
    def test_meshes_through_the_job_and_cancels(self):
        w = MainWindow()
        try:
            w.act_new()
            w.session.ws.get(w.session.handle.id).project.model = MODEL   # noqa: the fixture
            w.session.call("project_settings", title="capas")            # a step: redrawn
            assert w.mesh() is None
            assert w.mesh_dialog.isHidden()                          # shown, then closed
            assert w.session.model.mesh.nodes == translate.mesh(MODEL).mesh.nodes
            assert "Meshed:" in w.statusBar().currentMessage()
            w.act_mesh_reset()
            # Cancel: the dialog asks the job to stop; the model is as it was
            w.wait_job = lambda job, every_ms=100: (w.mesh_dialog.reject(),
                                                     type(w).wait_job(w, job))[1]
            said = w.mesh()
            assert said is not None and "cancelled" in said, said
            assert w.session.model.mesh is None
        finally:
            w.confirm_discard = lambda: True
            w.close()
