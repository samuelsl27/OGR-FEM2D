# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.13 (spec 006, T13) — calculating a model as a job in a child process
(RF-9 to RF-12; D9).

Invariants protected:

* **the child's results are the engine's**: the ``.h5`` a job writes is
  valid for the model, and its stages are ``analysis.run``'s, bit for bit;
  its last progress is the end, every stage done;
* **a cancel within the grace stops between stages**: the job ends
  ``cancelled``, not killed, and the ``.h5`` says ``cancelled`` with the
  stages solved; **a cancel without grace kills the tree**: the ``.h5``
  before stays as it was, and no temporary is left;
* **cancelling and calculating again is calculating once**, bit for bit;
* **a stage that cannot be solved is said**: the job ends ``done`` with
  the results ``incomplete``, the stage and the engine's error;
* **what would fail at once is refused before a process starts**, saying
  why (RF-12): no file, changes not in the file, no mesh, a mesh of another
  geometry, a material without E or nu; and a second job while one runs.
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import replace
from pathlib import Path

import _models
import _results
from ogr_core.api import Busy, Conflict, InvalidArgument, NotFound

from ogr_fem2d import api
from ogr_fem2d.api.workspace import Held
from ogr_fem2d.engine import analysis
from ogr_fem2d.model import model as md
from ogr_fem2d.model import ogr_file, translate
from ogr_fem2d.results import calculate as calc
from ogr_fem2d.results import store


def _refused(fn, kind, *words):
    try:
        fn()
    except kind as err:
        for w in words:
            assert w in str(err) or w in str(getattr(err, "details", "")), (w, str(err))
        return err
    raise AssertionError(f"accepted; expected {kind.__name__}")


class _Case:
    """A model saved in a folder, open in a workspace that is shut down after."""

    def __init__(self, m: md.Model):
        self.m = m
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "modelo.ogrfem2d"
        ogr_file.write(m, self.path)
        self.ws = api.workspace(workdir=self.dir.name)
        self.pid = api.call(self.ws, "project_open", path="modelo.ogrfem2d")["project_id"]

    def call(self, name, /, **kw):
        return api.call(self.ws, name, **kw)

    def outcomes(self):
        r = calc.open_results(self.path).read_anyway()
        return r.header, [r.outcome(k) for k in range(r.n_stages)]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.ws.shutdown()
        self.dir.cleanup()


def _three():
    return _results.excavated_tunnel(3)


class TestTheChildsResults:
    def test_the_engines_bit_for_bit(self):
        with _Case(_three()) as c:
            got = c.call("analysis_run", project_id=c.pid, wait=120)
            assert got["state"] == "done" and got["summary"]["status"] == store.COMPLETE
            assert got["summary"]["stages"] == 3 and got["provenance"]["program"].startswith("OGR")
            assert calc.open_results(c.path).status == calc.VALID
            _h, outs = c.outcomes()
            assert outs == analysis.run(translate.to_engine(c.m))
            last = c.call("job_get", job_id=got["job_id"])
            prog = json.loads((c.ws.jobs.get(got["job_id"]).folder / "progress.json")
                              .read_text(encoding="utf-8"))
            assert (prog["done"], prog["total"], prog["event"], prog["status"]) == \
                (3, 3, calc.FINISHED, store.COMPLETE)
            assert last["state"] == "done"


class TestCancel:
    def test_within_the_grace_between_stages(self):
        with _Case(_three()) as c:
            job = c.call("analysis_run", project_id=c.pid)["job_id"]
            st = c.call("job_cancel", job_id=job, grace_s=60.0)
            assert (st["state"], st["killed"]) == ("cancelled", False), st
            h, outs = c.outcomes()
            assert h.status == store.CANCELLED and 1 <= len(outs) < 3
            assert outs == analysis.run(translate.to_engine(c.m))[:len(outs)]
            # calculating again is calculating once
            again = c.call("analysis_run", project_id=c.pid, wait=120)
            assert again["summary"]["status"] == store.COMPLETE
            assert c.outcomes()[1] == analysis.run(translate.to_engine(c.m))

    def test_the_default_grace_stops_between_stages(self):
        with _Case(_three()) as c:
            job = c.call("analysis_run", project_id=c.pid)["job_id"]
            st = c.call("job_cancel", job_id=job)
            assert (st["state"], st["killed"]) == ("cancelled", False), st

    def test_without_grace_the_tree_is_killed(self):
        with _Case(_three()) as c:
            c.call("analysis_run", project_id=c.pid, wait=120)
            before = c.path.with_suffix(".h5").read_bytes()
            job = c.call("analysis_run", project_id=c.pid)["job_id"]
            st = c.call("job_cancel", job_id=job, grace_s=0.0)
            assert (st["state"], st["killed"]) == ("cancelled", True), st
            assert c.path.with_suffix(".h5").read_bytes() == before
            assert not Path(str(c.path.with_suffix(".h5")) + ".tmp").exists()


class TestTheTargetInProcess:
    """The job's target and its clean-up, called here (what the child and
    the parent do around ``calculate``)."""

    class _Ctx:
        def __init__(self, m, path, stop=False):
            self.data, self.params = {"model": m, "model_path": str(path)}, {}
            self.heard, self._stop = [], stop

        def progress(self, done, total, **extra):
            self.heard.append((done, total, extra["event"]))

        def should_stop(self):
            return self._stop

    def test_progress_by_stage_and_the_stop(self):
        from ogr_core.api.jobs import JobCancelled
        from ogr_fem2d.api import worker
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "modelo.ogrfem2d"
            ogr_file.write(_three(), path)
            ctx = self._Ctx(_three(), path)
            payload, summary = worker.run_calculation(ctx)
            assert summary["status"] == store.COMPLETE and payload == summary
            assert ctx.heard == [(0, 3, calc.STARTED), (1, 3, calc.DONE), (1, 3, calc.STARTED),
                                 (2, 3, calc.DONE), (2, 3, calc.STARTED), (3, 3, calc.DONE),
                                 (3, 3, calc.FINISHED)]
            _refused(lambda: worker.run_calculation(self._Ctx(_three(), path, stop=True)),
                     JobCancelled, "stopped before stage '2'")

    def test_a_killed_job_leaves_no_temporary(self):
        from ogr_fem2d.api import worker
        with tempfile.TemporaryDirectory() as d:
            h5 = Path(d) / "modelo.h5"
            tmp = Path(str(h5) + ".tmp")
            tmp.write_bytes(b"half")
            job = type("J", (), {"params": {"results": str(h5)}})()
            worker.on_end(job)
            assert not tmp.exists()
            worker.on_end(job)                       # and nothing to remove is fine


class TestAStageThatFails:
    def test_said_with_its_stage(self):
        free = md.Condition(md.FREE, md.Span("ext"), active=(False, True, True))
        with _Case(replace(_three(), conditions=(free,))) as c:
            got = c.call("analysis_run", project_id=c.pid, wait=120)
            s = got["summary"]
            assert got["state"] == "done" and s["status"] == store.INCOMPLETE
            assert s["stopped_at"] == 1 and "'2'" in s["reason"]
            assert "InsufficientRestraintError" in s["reason"]


class TestRefusedBeforeStarting:
    def test_why(self):
        ws = api.workspace()
        try:
            pid = ws.add(Held(_models.meshed(_models.tunnel()))).id
            _refused(lambda: api.call(ws, "analysis_run", project_id=pid), InvalidArgument,
                     "no file")
        finally:
            ws.shutdown()
        with _Case(_three()) as c:
            c.call("project_settings", project_id=c.pid, title="cambiado")
            _refused(lambda: c.call("analysis_run", project_id=c.pid), Conflict, "not in its file")
        for m, rule in ((_models.tunnel(), "the model has no mesh"),
                        (edit_settings(_three()), "mesh_stale"),
                        (replace(_three(), materials=(md.Material("rock"),)), "material_incomplete")):
            with _Case(m) as c:
                _refused(lambda: c.call("analysis_run", project_id=c.pid), InvalidArgument, rule)
        with _Case(_three()) as c:
            c.call("analysis_run", project_id=c.pid)
            _refused(lambda: c.call("analysis_run", project_id=c.pid), Busy)
            _refused(lambda: c.call("job_get", job_id="j_nope"), NotFound, "'j_nope'")
            _refused(lambda: c.call("analysis_run", project_id=c.pid, variant="gpu"), NotFound,
                     "'gpu'")


def edit_settings(m):
    from ogr_fem2d.model import edit
    return edit.set_mesh_settings(m, boundary_nodes=40)
