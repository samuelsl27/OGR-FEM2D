# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The models a caller has open, over the core's ``Workspace`` (spec 006, T11;
ADR-0005).

The core's workspace was written for a model that is changed in place (the
limit-equilibrium ``Project``). Here a model is a value: an edit gives a
new one (spec 004). So a handle holds a ``Held``, the box with the model of
the moment, and:

* ``Step`` is the undo step (``Workspace(undo_step=...)``): it runs the
  edit, keeps the model before and after, says whether it changed
  anything, and undoing or redoing puts one or the other back in the box,
  the same objects (the same fingerprint, bit for bit);
* the hash that says "unsaved changes" is the model's document fingerprint
  (spec 004, D12), which changes with everything the file keeps;
* the hints name ``project_new`` and ``project_open``.

``edit(ws, project_id, description, change)`` is how an operation edits:
``change`` is a function from the model to a new one (``model/edit.py``,
``stages.py``, ``cuts.py``), and the whole of it is one undo step, all or
nothing. A ``ModelError`` comes out as an ``InvalidArgument`` with every
problem in its details (``model_errors``).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import contextlib
from collections.abc import Callable

from ogr_core.api import InvalidArgument, Workspace, WorkspaceNames

from ..model import fingerprint, ogr_file
from ..model import model as md
from .messages import say


class Held:
    """The model of an open handle, as the core's workspace holds it."""

    def __init__(self, model: md.Model):
        self.model = model

    @property
    def name(self) -> str:
        return self.model.summary.title


class Step:
    """One edit as one undo step (see the module's notes)."""

    def __init__(self, description: str, fn: Callable[[Held], object], attrs=None):
        self.description = description
        self.fn = fn
        self.result = None
        self.changed = False
        self._done = False
        self.before = self.after = None

    def execute(self, held: Held) -> None:
        if self._done:                       # redo
            held.model = self.after
            return
        before = held.model
        try:
            self.result = self.fn(held)
        except BaseException:
            held.model = before              # all or nothing
            raise
        self.before, self.after = before, held.model
        self.changed = self.after != self.before
        self._done = True

    def undo(self, held: Held) -> None:
        held.model = self.before


def document_hash(held: Held) -> str:
    return fingerprint.document_fingerprint(held.model)


NAMES = WorkspaceNames(new_op="project_new", open_op="project_open")


def jobs_options() -> dict:
    """The core's jobs, with this program's target, its tree for the
    child, its provenance, its clean-up and its grace (D9)."""
    from ogr_core.api.jobs import JobHooks
    from pathlib import Path
    from . import worker
    root = Path(__file__).resolve().parents[2]
    return {"target": worker.run_calculation, "pythonpath": [str(root)],
            "hooks": JobHooks(on_end=worker.on_end, provenance=worker.provenance),
            "cancel_grace_s": worker.CANCEL_GRACE_S}


def make(workdir=None, **kwargs) -> Workspace:
    """A workspace for the operations of this program."""
    kwargs.setdefault("jobs_options", jobs_options())
    return Workspace(workdir=workdir, undo_step=Step, document_hash=document_hash, names=NAMES,
                     **kwargs)


def problems_of(err: md.ModelError) -> list[dict]:
    return [{"rule": p.rule, "where": p.where, "message": p.message} for p in err.problems]


@contextlib.contextmanager
def model_errors():
    """A ``ModelError`` (or a file the reader refuses) as an
    ``InvalidArgument`` naming every problem (RF-7)."""
    try:
        yield
    except (md.ModelError, ogr_file.FileFormatError) as err:
        found = problems_of(err)
        first = f"{found[0]['where']}: {found[0]['message']} [{found[0]['rule']}]"
        code = "fem.model.invalid" if isinstance(err, md.ModelError) else "fem.file.invalid"
        raise InvalidArgument(say(code, count=len(found), first=first),
                              hint=say("fem.model.invalid.hint"),
                              details={"problems": found}) from None


def edit(ws: Workspace, project_id, description: str,
         change: Callable[[md.Model], md.Model]):
    """Apply ``change`` to the model of ``project_id`` as one undo step;
    the handle and the new model."""
    handle = ws.get(project_id)

    def run(held: Held):
        with model_errors():
            held.model = change(held.model)
        return held.model

    model = ws.mutate(handle.id, description, run)
    return handle, model
