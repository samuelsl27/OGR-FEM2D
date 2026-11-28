# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.15 (spec 006, T30) — the calculation's window: the queue, the
progress by stage, Cancel, the log and the summary (RF-9 to RF-12, RF-18;
D9; the guide, §4, §5 and §14).

Invariants protected:

* **the window's calculation is the operation's**: its ``.h5`` is valid for
  the model and its stages are the engine's, bit for bit;
* **every stage is in the log, once**, even those that started and ended
  between two readings; the summary says what was solved and where;
* **Cancel stops the process**, within D9's grace between stages (the
  results say ``cancelled``), and the window does not wait for it;
* **closing with a calculation running asks once**: no leaves it running,
  yes stops it for real;
* **a failure names the object**: a stage that cannot be solved, by its
  number and name, with the engine's words; a refusal before starting, by
  the object of the model and its rule's sentence;
* **Compute is offered only with a mesh of the model**, and says why not;
  a model not saved is saved first, when the person says so.
"""
from __future__ import annotations

import os
import tempfile
import time
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import _models  # noqa: E402
import _results  # noqa: E402
from _settings import recent_kept  # noqa: E402
from ogr_fem2d.engine import analysis  # noqa: E402
from ogr_fem2d.gui.main_window import MainWindow  # noqa: E402
from ogr_fem2d.model import model as md  # noqa: E402
from ogr_fem2d.model import ogr_file, translate  # noqa: E402
from ogr_fem2d.results import calculate as calc  # noqa: E402
from ogr_fem2d.results import store  # noqa: E402

APP = QApplication.instance() or QApplication([])


class _Open:
    """A model saved in a folder and open in a window, closed after."""

    def __init__(self, m: md.Model):
        self.m = m

    def __enter__(self):
        self._recent = recent_kept()
        self._recent.__enter__()
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "modelo.ogrfem2d"
        ogr_file.write(self.m, self.path)
        self.w = MainWindow()
        self.w.open_path(str(self.path))
        return self

    def __exit__(self, *exc):
        self.w.confirm_discard = lambda: True
        self.w.confirm_stop_calculation = lambda: True
        self.w.close()
        self.dir.cleanup()
        self._recent.__exit__(*exc)

    def job(self):
        return self.w.session.ws.jobs.get(self.w.compute_window.followed)


def _three():
    return _results.excavated_tunnel(3)


class TestCalculating:
    def test_the_operations_calculation_and_its_log(self):
        with _Open(_three()) as o:
            assert o.w.actions_by_key["compute"].isEnabled()
            assert o.w.compute() is None
            win = o.w.compute_window
            assert not win.isHidden()
            ticks = []
            ticker = QTimer()
            ticker.timeout.connect(lambda: ticks.append(time.perf_counter()))
            ticker.start(10)
            win.wait()
            ticker.stop()
            gaps = [b - a for a, b in zip(ticks, ticks[1:])]
            assert len(ticks) > 20 and max(gaps) < 0.25, max(gaps)     # it never stood still
            opened = calc.open_results(o.path, o.m)
            assert opened.status == calc.VALID
            r = opened.results
            assert r.header.engine_variant == "rust"         # the compiled engine, by default
            assert [r.outcome(k) for k in range(r.n_stages)] == \
                analysis.run(translate.to_engine(o.m))
            log = win.log_text()
            for k, s in enumerate(o.m.stages, 1):
                said = f"{k} ({s.name})"
                assert sum(line.startswith(f"Stage {said}") and "solv" in line
                           and "solving" not in line for line in log.splitlines()) == 1, log
            assert win.summary_text().startswith("Complete: the 3 stages are solved")
            # the path as the job resolved it: on Windows a temporary folder may be named
            # short (RUNNER~1) and the job says it long (the CI of 2026-11-27)
            assert str(o.path.with_suffix(".h5").resolve()) in win.summary_text(), \
                win.summary_text()
            assert o.w.statusBar().currentMessage() == win.summary_text()
            assert [win.queue.item(0, c).text() for c in (1, 2)] == ["Calculation", "Done"]
            assert win.bar.value() == win.bar.maximum() == 3
            assert win.btn_results.isEnabled()               # guide §5: go to the results
            win.btn_results.click()
            assert not o.w.interpret_window.isHidden()

    def test_a_stage_heard_says_its_steps(self):
        with _Open(_three()) as o:
            win = o.w.compute_window
            win._stages["j"] = [(s.id, s.name) for s in o.m.stages]
            win._heard("j", {"event": calc.STARTED, "done": 0, "total": 3})
            win._heard("j", {"event": calc.DONE, "done": 2, "total": 3, "solved": True,
                             "step": 4, "iteration": 7})
            win._heard("j", {"event": calc.DONE, "done": 3, "total": 3, "solved": False})
            assert win.log_text("j").splitlines() == [
                "Stage 1 (Stage 1) of 3: solving...", "Stage 1 (Stage 1) solved.",
                "Stage 2 (Stage 2) solved: 4 steps, last iteration 7.",
                "Stage 3 (Stage 3): nothing changes in it, nothing to solve."]


class TestOneStage:
    def test_is_said_in_the_singular(self):
        """The frozen program's self-test said "the 1 stages are solved"
        (T36): one stage is said in the singular, a whole sentence of its
        own (each with its Spanish)."""
        with _Open(_results.excavated_tunnel(1)) as o:
            o.w.compute()
            win = o.w.compute_window
            win.wait()
            assert win.summary_text().startswith("Complete: the stage is solved, written in "), \
                win.summary_text()
            assert win.log_text().splitlines()[0] == "Calculation started (1 stage)."
            said = win._summary_done(win.followed, {"status": store.INCOMPLETE, "stages": 1,
                                                    "results": "m.h5", "stopped_at": 1,
                                                    "reason": "stage 's2': X: y"})
            assert said.startswith("Incomplete: stage ") and \
                "; the stage before it is written in m.h5. The engine says: X: y" in said, said
            two = win._summary_done(win.followed, {"status": store.COMPLETE, "stages": 2,
                                                   "results": "m.h5"})
            assert two == "Complete: the 2 stages are solved, written in m.h5."


class TestWaiting:
    def test_an_end_between_two_readings_is_said(self):
        """The CI of 2026-11-27 (macOS): the job ended after ``poll`` read it
        running and before ``running`` asked; the wait ended with no summary."""
        with _Open(_three()) as o:
            o.w.compute()
            win = o.w.compute_window
            real, first = win.poll, []

            def poll():
                real()
                if not first:                      # the end falls just after this reading
                    first.append(True)
                    while o.job().status()["state"] not in ("done", "failed", "cancelled"):
                        time.sleep(0.02)
            win.poll = poll
            win.wait()
            assert win.summary_text().startswith("Complete: the 3 stages are solved"), \
                win.summary_text()


class TestCancelAnsweredLate:
    def test_the_summary_waits_for_the_answer(self):
        """The CI of 2026-11-27 (macOS): the job ended cancelled before
        ``job_cancel`` answered, and the summary said only "Cancelled."."""
        from ogr_fem2d.gui import compute_window as cw
        with _Open(_three()) as o:
            o.w.compute()
            win = o.w.compute_window
            real = cw.api.call

            def late(ws, op, **kw):
                got = real(ws, op, **kw)
                if op == "job_cancel":              # the answer comes after the end
                    while real(ws, "job_get", job_id=kw["job_id"])["state"] != "cancelled":
                        time.sleep(0.02)
                    time.sleep(0.3)
                return got
            cw.api.call = late
            try:
                win.cancel()
                win.wait()
            finally:
                cw.api.call = real
            assert o.job().status()["state"] == "cancelled"
            assert win.summary_text().startswith("Cancelled between two stages"), \
                win.summary_text()


class TestCancel:
    def test_cancel_stops_it_and_the_window_goes_on(self):
        with _Open(_three()) as o:
            o.w.compute()
            win = o.w.compute_window
            t0 = time.perf_counter()
            win.cancel()
            assert time.perf_counter() - t0 < 0.5          # the grace is waited off the thread
            assert not win.btn_cancel.isEnabled()
            win.wait()
            assert o.job().proc.poll() is not None
            assert o.job().status()["state"] == "cancelled"
            assert win.summary_text().startswith("Cancelled between two stages"), \
                win.summary_text()
            h = calc.open_results(o.path).read_anyway().header
            assert h.status == store.CANCELLED
            assert not win.btn_results.isEnabled()


class TestClosing:
    def test_asks_once_and_stops_it(self):
        with _Open(_three()) as o:
            asked = []
            o.w.confirm_stop_calculation = lambda: asked.append(1) or False
            o.w.compute()
            job = o.job()
            o.w.close()
            assert asked == [1]
            assert job.status()["state"] == "running"        # no: it goes on
            o.w.confirm_stop_calculation = lambda: asked.append(2) or True
            o.w.confirm_discard = lambda: asked.append("discard") or True
            o.w.close()
            assert asked == [1, 2]                           # once each time; nothing unsaved
            assert job.proc.poll() is not None
            assert job.status()["state"] == "cancelled"


    def test_a_shared_session_has_it_stopped_too(self):
        """A window on a session it does not own (an agent's, D8) does not
        shut it down: closing stops the calculation itself."""
        from ogr_fem2d.gui.session import Session
        with tempfile.TemporaryDirectory() as d, recent_kept():
            path = Path(d) / "modelo.ogrfem2d"
            ogr_file.write(_three(), path)
            s = Session()
            try:
                w = MainWindow(session=s)
                w.open_path(str(path))
                w.compute()
                job = s.ws.jobs.get(w.compute_window.followed)
                w.confirm_stop_calculation = lambda: True
                w.close()
                assert job.proc.poll() is not None and job.status()["state"] == "cancelled"
                assert w.compute_window.summary_text().startswith(
                    "Cancelled: its process was stopped"), w.compute_window.summary_text()
            finally:
                s.close()


class TestFailures:
    def test_a_stage_that_cannot_be_solved(self):
        free = md.Condition(md.FREE, md.Span("ext"), active=(False, True, True))
        with _Open(replace(_three(), conditions=(free,))) as o:
            o.w.compute()
            o.w.compute_window.wait()
            said = o.w.compute_window.summary_text()
            assert said.startswith("Incomplete: stage 2 (Stage 2) could not be solved; the "
                                   "stage before it is written in "), said
            assert "InsufficientRestraintError" in said and "stage '2'" not in said

    def test_refused_before_starting_names_the_object(self):
        m = replace(_three(), materials=(replace(_three().materials[0], E=None),)
                    + _three().materials[1:])
        with _Open(m) as o:
            said = o.w.compute()
            mat = m.materials[0]
            assert said.startswith(f"Not calculated: material {mat.id!r}"), said
            assert "A material has no E or no ν" in said
            assert o.w.session.call("job_list")["jobs"] == []


class TestOffered:
    def test_only_with_the_models_mesh(self):
        with _Open(replace(_three(), mesh=None)) as o:
            act = o.w.actions_by_key["compute"]
            assert not act.isEnabled() and "There is no mesh" in act.statusTip()
        with _Open(_three()) as o:
            o.w.session.call("mesh_settings", quality_bound=1.9)
            act = o.w.actions_by_key["compute"]
            assert not act.isEnabled() and "another geometry" in act.statusTip()

    def test_saved_first_when_said(self):
        with _Open(_three()) as o:
            o.w.session.call("project_settings", title="otro")
            o.w.confirm_save_to_compute = lambda: False
            assert o.w.compute() is None
            assert o.w.session.call("job_list")["jobs"] == [] and o.w.session.unsaved
            o.w.confirm_save_to_compute = lambda: True
            assert o.w.compute() is None
            assert not o.w.session.unsaved
            o.w.compute_window.wait()
            assert ogr_file.read(o.path).summary.title == "otro"
            assert calc.open_results(o.path).status == calc.VALID
