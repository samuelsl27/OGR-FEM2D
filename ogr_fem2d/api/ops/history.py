# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Undo and redo, as an operation (spec 006, T11; RF-8): the steps of the
model's handle, whoever made them (the interface, the command line or an
agent), as OGR Slip2D's ``project_history``.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Optional

from ogr_core.api import Busy, InvalidArgument, unknown
from ogr_core.api.coerce import coerce_value
from ogr_core.api.messages import say as core_say
from ogr_core.project.commands import step_description

from ..messages import say
from ..registry import OPERATIONS

ACTIONS = ("list", "undo", "redo")


@OPERATIONS.operation("project_history", toolset="history", mutates=True)
def project_history(ws, project_id: Optional[str] = None, action: str = "list",
                    steps: int = 1) -> dict:
    """List, undo or redo edits."""
    if action not in ACTIONS:
        raise unknown(say("fem.history.action"), action, list(ACTIONS))
    steps = coerce_value(steps, int, "steps")
    if not 1 <= steps <= 200:
        raise InvalidArgument(say("fem.history.steps"))
    handle = ws.get(project_id)
    if action != "list" and ws.host is not None:
        why = ws.host.busy()
        if why:
            raise Busy(why, hint=core_say("api.retry.window"))
    done = []
    with ws.reading(handle.id, f"history {action}") as held:
        for _ in range(steps if action != "list" else 0):
            cmd = handle.stack.undo(held) if action == "undo" else handle.stack.redo(held)
            if cmd is None:
                break
            done.append(step_description(cmd))
        undo, redo = handle.stack.history()
    return {"project_id": handle.id, "action": action, "done": done,
            "undo": undo[-10:], "redo": redo[-10:]}
