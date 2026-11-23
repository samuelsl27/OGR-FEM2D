# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Undo and redo of the edits of a model (spec 004, RF-15).

The model is a value (``model``): an edit gives a new one. A ``Document``
holds the current model, and every edit is an ``Edit`` command that keeps
the model before and the model after it, on the core's ``CommandStack``
(``ogr_core.project.commands``, which asks of the object it is given only
what the command does with it). Undoing puts the model before back; redoing,
the one after: the same objects, so the same fingerprint, bit for bit.

An edit that changes nothing leaves no step to undo.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from collections.abc import Callable

from ogr_core.project.commands import Command, CommandStack

from . import model as md


class Document:
    """The model being edited, and its history."""

    def __init__(self, model: md.Model | None = None, max_depth: int = 200):
        self.model = md.Model() if model is None else model
        self.history = CommandStack(max_depth)

    def edit(self, change: Callable[[md.Model], md.Model], description: str = "") -> bool:
        """Apply ``change`` (a function from the model to a new one) as one
        step to undo; False if it changed nothing."""
        after = change(self.model)
        if after == self.model:
            return False
        self.history.do(self, Edit(self.model, after, description))
        return True

    def undo(self) -> bool:
        return self.history.undo(self) is not None

    def redo(self) -> bool:
        return self.history.redo(self) is not None


class Edit(Command):
    """One edit: the model before and after it."""

    def __init__(self, before: md.Model, after: md.Model, description: str = ""):
        self.before, self.after = before, after
        self.description = description

    def execute(self, doc: Document) -> None:
        doc.model = self.after

    def undo(self, doc: Document) -> None:
        doc.model = self.before
