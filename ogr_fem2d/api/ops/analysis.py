# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Calculating a model, as a job in a child process (spec 006, T13; RF-9 to
RF-12): ``analysis_run`` starts it, ``job_get`` says where it is (with its
progress by stage, step and iteration while it runs), ``job_cancel`` stops
it, ``job_list`` lists them. The names are OGR Slip2D's.

Before a job starts, what would make it fail at once is refused here,
saying why (RF-12): a model whose file is not its state (never saved, or
changed since: the results are written beside the file, with the file's
fingerprint), a model that is not valid, without a mesh or with the mesh of
another geometry, or with a material without E or nu.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Optional

from ogr_core.api import Conflict, InvalidArgument, unknown
from ogr_core.api.coerce import coerce_value

from ...model import translate
from ...results import calculate as calc
from ..messages import say
from ..registry import OPERATIONS
from ..workspace import model_errors

VARIANTS = ("reference", "rust")


@OPERATIONS.operation("analysis_run", toolset="analysis")
def analysis_run(ws, project_id: Optional[str] = None, variant: str = "reference",
                 wait: float = 0.0) -> dict:
    """Calculate the model in a child process that can be cancelled; it
    writes <model>.h5 beside the model's file. Returns the job_id (and, with
    ``wait`` seconds, the job's state when it ends or the wait does)."""
    if variant not in VARIANTS:
        raise unknown("engine variant", variant, list(VARIANTS))
    wait = coerce_value(wait, float, "wait")
    handle = ws.get(project_id)
    with ws.reading(handle.id, "analysis") as held:
        if handle.path is None:
            raise InvalidArgument(say("fem.run.no_file", model=handle.id),
                                  hint=say("fem.run.no_file.hint"))
        if handle.unsaved():
            raise Conflict(say("fem.run.unsaved", model=handle.id),
                           hint=say("fem.run.unsaved.hint"))
        m = held.model
        with model_errors():
            translate.to_engine(m)                  # what would fail at once
        results = str(calc.results_path(handle.path))
        job = ws.jobs.start("analysis", {"model": m, "model_path": str(handle.path)}, handle.id,
                            handle.document_hash(), {"variant": variant, "results": results})
    out = {"job_id": job.id, "project_id": handle.id, "results": results}
    if wait > 0:
        job.wait(wait)
        out.update(_status(job))
    else:
        out["state"] = job.status()["state"]
    return out


def _status(job) -> dict:
    st = job.status()
    if st.get("state") in ("done",) and job.summary() is not None:
        st["summary"] = job.summary()
    return st


@OPERATIONS.operation("job_get", toolset="analysis")
def job_get(ws, job_id: str, wait: float = 0.0) -> dict:
    """Where a job is: running (with its progress), done (with its summary:
    the results' status, the stages written and why it stopped), failed,
    cancelled or crashed (with the end of its log)."""
    job = ws.jobs.get(job_id)
    wait = coerce_value(wait, float, "wait")
    if wait > 0:
        job.wait(wait)
    return _status(job)


@OPERATIONS.operation("job_cancel", toolset="analysis")
def job_cancel(ws, job_id: str, grace_s: Optional[float] = None) -> dict:
    """Stop a job: between two stages within the grace (the stages solved
    are written, ``cancelled``), or by killing its process tree (the
    results file before stays)."""
    job = ws.jobs.get(job_id)
    st = job.cancel(None if grace_s is None else coerce_value(grace_s, float, "grace_s"))
    st["killed"] = job.killed
    return st


@OPERATIONS.operation("job_list", toolset="analysis")
def job_list(ws) -> dict:
    """Every job of this workspace, newest last."""
    return {"jobs": [{"job_id": j.id, "project_id": j.project_id, "state": j.status()["state"]}
                     for j in ws.jobs.jobs.values()]}
