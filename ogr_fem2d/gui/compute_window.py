# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The calculation's window (spec 006, T30; RF-9 to RF-11, RF-18; D9; the
guide, §4, §5 and §14).

A window beside the model, not in front of it: the calculation runs in a
child process (``analysis_run``), so the model window goes on while it
runs, and this one follows it by asking ``job_get`` every
``POLL_MS``. It shows:

* **the queue**: every job of the workspace (``job_list``), newest last,
  with its model, its kind, its state and its time; the one chosen is the
  one followed below. The core runs one job at a time: a second
  calculation while one runs is refused with its reason (``Busy``);
* **the progress**: the stage (of how many, with its name), and of a stage
  solved its steps and its last iteration (D9: in elasticity, one step of
  one iteration);
* **Cancel**, which stops it as D9 says: between two stages within the
  grace (the stages solved are written, and the results say
  ``cancelled``), or by killing its process tree. The cancel waits for the
  grace off the window's thread, so the window does not stand still;
* **the log**: each stage as it starts and as it ends, kept for every job
  of the session (RF-11). The progress is read, not heard, so a stage that
  started and ended between two readings is written with what is known of
  it (solved), never left out;
* **the summary** at the end (guide §5): what was solved and where it was
  written; of a stage that could not be solved, which stage, by its name,
  and what the engine said (RF-11); of a cancel, what stayed.

Every text of the window is said through ``tr()``; the engine's own words
in a failure are quoted as they are.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import threading
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QHBoxLayout, QHeaderView, QLabel,
                               QPlainTextEdit, QProgressBar, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)

from ogr_ui.i18n import tr

from .. import api
from ..results import calculate as calc
from ..results import store

#: how often a running job is asked where it is (ms)
POLL_MS = 100

FINAL = ("done", "failed", "cancelled", "crashed")

#: a job's kind and state, as the queue says them
KIND_TEXT = {"analysis": "Calculation", "mesh": "Meshing"}
STATE_TEXT = {"queued": "Queued", "running": "Running", "done": "Done", "failed": "Failed",
              "cancelled": "Cancelled", "crashed": "Crashed"}

COLUMNS = ("Model", "Kind", "State", "Time (s)")


class ComputeWindow(QDialog):
    """The queue, the progress, Cancel, the log and the summary."""

    #: (job_id, final state) when a job this window follows ends
    job_ended = Signal(str, str)
    #: the results of the followed job asked for (guide §5: a button to go to them)
    results_wanted = Signal()

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle(tr("Calculation"))
        self.setModal(False)
        self.followed: Optional[str] = None
        #: job -> the stages of the model it calculates: [(id, name)]
        self._stages: dict[str, list] = {}
        #: job -> its log lines; how many stages it logged as done; the
        #: stages it logged as started; its last progress
        self._log: dict[str, list] = {}
        self._logged_done: dict[str, int] = {}
        self._started: dict[str, set] = {}
        self._progress: dict[str, dict] = {}
        #: job -> its final status, its summary text, whether its cancel killed it
        self._ended: dict[str, dict] = {}
        self._summary: dict[str, str] = {}
        self._killed: dict[str, bool] = {}
        self._cancelling: set = set()
        self._rows: list[str] = []

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(tr("Queue")))
        self.queue = QTableWidget(0, len(COLUMNS))
        self.queue.setHorizontalHeaderLabels([tr(c) for c in COLUMNS])
        self.queue.verticalHeader().hide()
        self.queue.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.queue.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.queue.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.queue.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.queue.setMaximumHeight(120)
        self.queue.itemSelectionChanged.connect(self._chosen)
        lay.addWidget(self.queue)

        self.stage_label = QLabel()
        self.bar = QProgressBar()
        self.step_label = QLabel()
        lay.addWidget(self.stage_label)
        lay.addWidget(self.bar)
        lay.addWidget(self.step_label)

        lay.addWidget(QLabel(tr("Log")))
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        lay.addWidget(self.log, 1)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self.summary)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.btn_cancel = QPushButton(tr("Cancel the Calculation"))
        self.btn_cancel.clicked.connect(self.cancel)
        self.btn_close = QPushButton(tr("Close"))
        self.btn_close.setToolTip(tr("Closes this window; a calculation goes on: "
                                     "Window > Calculation shows it again."))
        self.btn_close.clicked.connect(self.hide)
        self.btn_results = QPushButton(tr("Interpret"))
        self.btn_results.setToolTip(tr("Shows the results: Analysis > Interpret."))
        self.btn_results.clicked.connect(self.results_wanted.emit)
        buttons.addWidget(self.btn_results)
        buttons.addWidget(self.btn_cancel)
        buttons.addWidget(self.btn_close)
        lay.addLayout(buttons)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.resize(560, 480)
        self._show_followed()

    # ------------------------------------------------------------ following
    def follow(self, job_id: str, model=None) -> None:
        """Follow a job just started (of ``model``: its stages' names)."""
        m = model if model is not None else self.session.model
        if m is not None:
            self._stages[job_id] = [(s.id, s.name) for s in m.stages]
        self.followed = job_id
        self._say(job_id, tr("Calculation started (%d stages).") % len(self._stages.get(job_id, ())))
        self.poll()
        if job_id not in self._ended:
            self.timer.start(POLL_MS)

    def running(self) -> list[str]:
        """The jobs of the workspace not yet ended."""
        return [j["job_id"] for j in api.call(self.session.ws, "job_list")["jobs"]
                if j["state"] not in FINAL]

    def poll(self) -> None:
        """Ask every job not ended where it is; follow the followed one."""
        jobs = api.call(self.session.ws, "job_list")["jobs"]
        going = False
        for j in jobs:
            jid = j["job_id"]
            if j["state"] not in FINAL:
                going = True
            if jid not in self._stages or jid in self._ended:
                continue                        # not followed here, or said already
            st = api.call(self.session.ws, "job_get", job_id=jid)
            if st["state"] in FINAL:
                self._end(jid, st)
            elif st.get("progress"):
                self._heard(jid, st["progress"])
        self._fill_queue(api.call(self.session.ws, "job_list")["jobs"])
        self._show_followed()
        if not going:
            self.timer.stop()

    def wait(self, every_ms: int = POLL_MS) -> None:
        """Until no job is going on, with the window going on (for a test,
        and for closing)."""
        from PySide6.QtCore import QEventLoop
        loop = QEventLoop()
        timer = QTimer()

        def ask():
            self.poll()
            if not self.running():
                loop.quit()
        timer.timeout.connect(ask)
        timer.start(every_ms)
        ask()
        if self.running():
            loop.exec()
        timer.stop()
        # a job may end between poll() and running(): one reading more says its end
        # (the CI of 2026-11-27, macOS: the summary was still empty)
        self.poll()

    # ------------------------------------------------------------ cancelling
    def cancel(self) -> None:
        """Cancel the followed job (D9: the grace between stages, then the
        process tree), waiting for the grace off the window's thread."""
        job = self.followed
        if job is None or job in self._ended or job in self._cancelling:
            return
        self._cancelling.add(job)
        self._say(job, tr("Cancelling: the stage being solved ends, or the process is stopped."))
        ws = self.session.ws

        def stop():
            try:
                st = api.call(ws, "job_cancel", job_id=job)
                self._killed[job] = bool(st.get("killed"))
            except Exception as err:            # noqa: BLE001 - said in the log
                self._killed[job] = False
                self._log.setdefault(job, []).append(str(err))
        threading.Thread(target=stop, daemon=True).start()
        self._show_followed()
        self.timer.start(POLL_MS)

    def stop_all(self) -> None:
        """Stop every job at once (the program is closing: it asked first)."""
        for jid in self.running():
            st = api.call(self.session.ws, "job_cancel", job_id=jid, grace_s=0.0)
            self._killed[jid] = bool(st.get("killed"))
        self.poll()

    # ------------------------------------------------------------ hearing
    def stage_name(self, job: str, k: int) -> str:
        stages = self._stages.get(job, [])
        if 0 <= k < len(stages):
            sid, name = stages[k]
            return f"{k + 1} ({name})" if name else f"{k + 1} ({sid})"
        return str(k + 1)

    def _say(self, job: str, line: str) -> None:
        self._log.setdefault(job, []).append(line)

    def _done_up_to(self, job: str, done: int, detail: Optional[dict] = None) -> None:
        """Log every stage done up to ``done`` not yet logged; the last with
        its steps and iteration when they are known."""
        for k in range(self._logged_done.get(job, 0), done):
            if detail is not None and k == done - 1:
                if detail.get("solved"):
                    self._say(job, tr("Stage %s solved: %d steps, last iteration %d.") % (
                        self.stage_name(job, k), detail.get("step", 0),
                        detail.get("iteration", 0)))
                else:
                    self._say(job, tr("Stage %s: nothing changes in it, nothing to solve.")
                              % self.stage_name(job, k))
            else:
                self._say(job, tr("Stage %s solved.") % self.stage_name(job, k))
        self._logged_done[job] = max(done, self._logged_done.get(job, 0))

    def _heard(self, job: str, prog: dict) -> None:
        self._progress[job] = prog
        event, done = prog.get("event"), int(prog.get("done", 0))
        if event == calc.DONE:
            self._done_up_to(job, done, prog)
        elif event == calc.STARTED:
            self._done_up_to(job, done)
            if done not in self._started.setdefault(job, set()):
                self._started[job].add(done)
                self._say(job, tr("Stage %s of %d: solving...") % (
                    self.stage_name(job, done), int(prog.get("total", 0))))

    def _end(self, job: str, st: dict) -> None:
        self._ended[job] = st
        state, s = st["state"], st.get("summary") or {}
        if state == "done":
            written = int(s.get("stages", 0))
            self._done_up_to(job, written)
            text = self._summary_done(job, s)
        elif state == "cancelled":
            killed = self._killed.get(job)
            text = (tr("Cancelled: its process was stopped during a stage, and the results "
                       "before it stay as they were.") if killed else
                    tr("Cancelled between two stages: the stages solved are written, and "
                       "the results say they are cancelled.") if killed is False else
                    tr("Cancelled."))
        elif state == "failed":
            text = tr("The calculation failed: %s") % (st.get("error") or "")
        else:
            text = tr("The calculation's process ended without saying why: %s") % (
                st.get("error") or st.get("log_tail") or "")
            if st.get("log_tail"):
                self._say(job, st["log_tail"])
        self._summary[job] = text
        self._say(job, text)
        self._cancelling.discard(job)
        self.job_ended.emit(job, state)

    def _summary_done(self, job: str, s: dict) -> str:
        status, written = s.get("status"), int(s.get("stages", 0))
        where = s.get("results", "")
        if status == store.COMPLETE:
            return tr("Complete: the %d stages are solved, written in %s.") % (written, where)
        if status == store.INCOMPLETE:
            stopped = s.get("stopped_at")
            reason = str(s.get("reason", ""))
            engine = reason.split(": ", 1)[1] if reason.startswith("stage ") and ": " in reason \
                else reason
            return tr("Incomplete: stage %s could not be solved; the %d stages before it are "
                      "written in %s. The engine says: %s") % (
                self.stage_name(job, int(stopped or 0)), written, where, engine)
        return tr("Cancelled between two stages: the stages solved are written, and the "
                  "results say they are cancelled.")

    # ------------------------------------------------------------ showing
    def _fill_queue(self, jobs: list) -> None:
        self._rows = [j["job_id"] for j in jobs]
        self.queue.blockSignals(True)
        self.queue.setRowCount(len(jobs))
        for r, j in enumerate(jobs):
            jid = j["job_id"]
            st = self._ended.get(jid) or {}
            try:
                h = self.session.ws.get(j["project_id"])
                name = h.project.model.summary.title or (h.path.stem if h.path else jid)
            except Exception:                   # noqa: BLE001 - a model closed since
                name = j["project_id"]
            kind = self.session.ws.jobs.get(jid).kind
            cells = (name, tr(KIND_TEXT.get(kind, kind)), tr(STATE_TEXT.get(j["state"], j["state"])),
                     "%.1f" % st["elapsed_s"] if "elapsed_s" in st else "")
            for c, text in enumerate(cells):
                self.queue.setItem(r, c, QTableWidgetItem(text))
            if jid == self.followed:
                self.queue.selectRow(r)
        self.queue.blockSignals(False)

    def _chosen(self) -> None:
        rows = self.queue.selectionModel().selectedRows()
        if rows and rows[0].row() < len(self._rows):
            self.followed = self._rows[rows[0].row()]
            self._show_followed()

    def _show_followed(self) -> None:
        job = self.followed
        ended = job in self._ended
        going = job is not None and not ended
        self.btn_cancel.setEnabled(going and job not in self._cancelling)
        self.btn_cancel.setToolTip("" if going else tr("No calculation is running."))
        st = self._ended.get(job) or {}
        # a job done has its summary, with the stages it wrote
        self.btn_results.setEnabled((st.get("summary") or {}).get("stages", 0) > 0)
        if job is None:
            self.stage_label.setText(tr("No calculation yet: Analysis > Compute."))
            self.bar.setRange(0, 1)
            self.bar.setValue(0)
            self.step_label.setText("")
            self.log.setPlainText("")
            self.summary.setText("")
            return
        prog = self._progress.get(job, {})
        total = int(prog.get("total") or len(self._stages.get(job, ())) or 1)
        done = int(prog.get("done", 0))
        if ended and (self._ended[job].get("summary") or {}).get("stages") is not None:
            done = int(self._ended[job]["summary"]["stages"])
        self.bar.setRange(0, total)
        self.bar.setValue(min(done, total))
        if going and job in self._cancelling:
            self.stage_label.setText(tr("Cancelling..."))
        elif going and prog.get("event") == calc.STARTED:
            self.stage_label.setText(tr("Stage %s of %d: solving...") % (
                self.stage_name(job, done), total))
        elif going:
            self.stage_label.setText(tr("Starting the calculation..."))
        else:
            self.stage_label.setText(tr(STATE_TEXT.get(self._ended[job]["state"], "")))
        if prog.get("event") == calc.DONE and prog.get("solved"):
            self.step_label.setText(tr("Stage %s: %d steps, last iteration %d.") % (
                self.stage_name(job, done - 1), prog.get("step", 0), prog.get("iteration", 0)))
        else:
            self.step_label.setText("")
        self.log.setPlainText("\n".join(self._log.get(job, [])))
        self.summary.setText(self._summary.get(job, ""))

    def log_text(self, job: Optional[str] = None) -> str:
        return "\n".join(self._log.get(job or self.followed, []))

    def summary_text(self, job: Optional[str] = None) -> str:
        return self._summary.get(job or self.followed, "")
