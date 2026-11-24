# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The model a window shows, over the operations (spec 006, part C; RF-6,
RF-8; D13).

The window never edits a model itself: it calls the operations of
``ogr_fem2d.api`` through a ``Session``, as the command line and an agent
do, so H5 (an agent builds the same model with the same operations) holds
by construction and every edit is one step of the same history. After an
operation that may have changed what is shown, the session tells its
listeners, and the window draws again.

No Qt here.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import inspect
from collections.abc import Callable
from pathlib import Path

from .. import api
from ..model import model as md

#: operations that change what a window shows without being edits
#: (``mutates``): they open, close or save a model, or move through its history
SHOWN = ("project_new", "project_open", "project_save", "project_close", "project_history")


class Session:
    """A workspace and the model of one window in it."""

    def __init__(self, workdir=None, ws=None):
        self.ws = ws if ws is not None else api.workspace(
            workdir=None if workdir is None else Path(workdir))
        self.project_id: str | None = None
        self._listeners: list[Callable[[str], None]] = []

    # ------------------------------------------------------------ listening
    def on_changed(self, cb: Callable[[str], None]) -> None:
        """``cb(op)`` after every operation that may change what is shown."""
        self._listeners.append(cb)

    def _tell(self, op: str) -> None:
        for cb in list(self._listeners):
            cb(op)

    # ------------------------------------------------------------ calling
    def call(self, op: str, /, **kwargs):
        """The operation ``op`` on the session's model (its ``project_id``
        put when the operation takes one and it is not given)."""
        spec = api.OPERATIONS.get(op)
        if spec is not None and "project_id" in inspect.signature(spec.func).parameters \
                and "project_id" not in kwargs and self.project_id is not None:
            kwargs["project_id"] = self.project_id
        out = api.call(self.ws, op, **kwargs)
        if op in ("project_new", "project_open"):
            self.project_id = out["project_id"]
        elif op == "project_close":
            self.project_id = None
        if spec is not None and (spec.mutates or op in SHOWN):
            self._tell(op)
        return out

    # ------------------------------------------------------------ reading
    @property
    def handle(self):
        return None if self.project_id is None else self.ws.get(self.project_id)

    @property
    def model(self) -> md.Model | None:
        h = self.handle
        return None if h is None else h.project.model

    @property
    def path(self) -> Path | None:
        h = self.handle
        return None if h is None or h.path is None else Path(h.path)

    @property
    def unsaved(self) -> bool:
        h = self.handle
        return bool(h is not None and h.unsaved())

    def history(self) -> tuple[list[str], list[str]]:
        """(undo, redo) names, most recent last."""
        if self.project_id is None:
            return [], []
        h = api.call(self.ws, "project_history", project_id=self.project_id)
        return h["undo"], h["redo"]

    def close(self) -> None:
        """End the session: its jobs and their files go."""
        self.ws.shutdown()
