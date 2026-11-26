# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
What a calculation does in its child process (spec 006, T13; RF-9 to RF-11;
D9), on the core's jobs (``ogr_core.api.jobs``).

``run_calculation(ctx)`` is the job's target, defined here at the top of a
module so that it travels to the child by name. It receives the model
(``ctx.data["model"]``) and the path of its file, and calls
``results.calculate`` with:

* ``progress``: each step of the way as the job's progress (``done`` of
  ``total`` stages, and the event, the stage, its steps and its iteration
  as extra fields), which ``job_get`` shows while it runs;
* ``should_stop``: the job's ``stop`` file, which a cancel with a grace
  writes; asked between stages, it ends the calculation ``cancelled``
  with the stages solved written (spec 005, D7), and the job too. A stage
  that does not end within the grace is killed with its process tree, and
  then the ``.h5`` before stays, as the results file is written to a
  temporary and moved at the end (spec 005, D13); ``on_end`` removes that
  temporary.

The job ends ``done`` also when a stage could not be solved (``incomplete``):
its summary says which stage and the engine's error (RF-11).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from pathlib import Path

import ogr_fem2d
from ogr_core.api.jobs import JobCancelled

from ..results import calculate as calc
from ..results import store

#: The time a cancelled calculation has to stop by itself, between two
#: stages, before its process tree is killed (D9). It moves no number.
CANCEL_GRACE_S = 5.0


def variant(name: str):
    if name == "reference":
        from ..engine.reference.solver import REFERENCE
        return REFERENCE
    from ..engine.compiled import RUST
    return RUST


def run_calculation(ctx):
    data = ctx.data
    m, path = data["model"], Path(data["model_path"])

    def progress(p: calc.Progress) -> None:
        done = p.stage + 1 if p.event == calc.DONE else p.stage
        ctx.progress(done, p.stages, event=p.event, stage=p.stage_id, stage_name=p.stage_name,
                     solved=p.solved, step=p.steps, iteration=p.iteration, status=p.status)

    done = calc.calculate(m, path, variant(ctx.params.get("variant", "reference")),
                          should_stop=ctx.should_stop, progress=progress)
    if done.status == store.CANCELLED:
        raise JobCancelled(done.reason)
    summary = {"results": str(done.path), "status": done.status, "stages": done.stages,
               "stopped_at": done.stopped_at, "reason": done.reason}
    return summary, summary


def run_mesh(ctx):
    """Meshing in the child (decided on 2026-11-25: with the meshes of the
    cases it took 2 to 4 s, and the window stood still): the model's mesh,
    as ``mesh_generate`` makes it, which ``mesh_collect`` puts in the model.
    The mesher has no point to stop at, so a cancel kills it at once; the
    model is untouched until the mesh is collected."""
    from ..model import translate
    ctx.progress(0, 1, event="meshing")
    mesh = translate.mesh(ctx.data["model"]).mesh
    summary = {"nodes": len(mesh.nodes), "elements": len(mesh.elements)}
    return mesh, summary


def provenance() -> dict:
    """Who ran the calculation, added to the core's provenance of a job."""
    return {"program": f"OGR FEM2D {ogr_fem2d.__version__}"}


def tmp_of(job) -> Path | None:
    p = job.params.get("results")
    return None if not p else Path(p + ".tmp")


def on_end(job) -> None:
    """A killed calculation leaves the ``.h5`` before; its temporary goes."""
    t = tmp_of(job)
    if t is not None and t.exists():
        try:
            t.unlink()
        except OSError:
            pass
