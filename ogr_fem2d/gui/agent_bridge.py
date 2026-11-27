# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The window's side of the agent bridge (spec 006, T34; D8): Tools > Agent
Bridge (MCP) serves the window's model to the program's MCP server, on the
core's protocol (``ogr_core.api.bridge``, ``api/bridge.CONFIG``).

* A ``QTcpServer`` on 127.0.0.1, in the window's event loop; each
  connection is a ``BridgeSession`` of the core (its handshake with the
  token, its dispatch), fed the lines the socket reads. The port and the
  token are announced in a file the user alone reads, removed when the
  bridge stops or the window closes.
* **Every call is the window's**: it goes through the window's session, as
  a menu's does, so an agent's edit is drawn at once and is one step of the
  window's history, undone with Edit > Undo.
* **With a calculation running, an edit is refused with ``Busy``**: the
  results being written are of the model as it was when the calculation
  started, and an agent that went on editing would leave them stale
  without knowing it. A question (a read, ``job_get``, ``job_cancel``)
  is answered.
* The greeting's working folder becomes the window's when it has none, so
  a relative path means the same in the window as in the MCP server.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import secrets
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject
from PySide6.QtNetwork import QHostAddress, QTcpServer

from ogr_core.api import Busy
from ogr_core.api.bridge import BridgeSession, remove_discovery, write_discovery

import ogr_fem2d
from .. import api
from ..api.bridge import CONFIG
from ..api.messages import say

#: what an agent may still do while a calculation runs: ask, follow it, stop it
WHILE_CALCULATING = ("job_get", "job_cancel", "job_list")


class AgentBridge(QObject):
    """The bridge of one window (see the module's notes)."""

    def __init__(self, window, parent=None):
        super().__init__(parent or window)
        self.window = window
        self.token = secrets.token_urlsafe(24)
        self.server: Optional[QTcpServer] = None
        self.discovery: Optional[Path] = None
        self._sessions: dict = {}

    @property
    def running(self) -> bool:
        return self.server is not None

    @property
    def port(self) -> int:
        return int(self.server.serverPort()) if self.server is not None else 0

    def start(self) -> int:
        """Listen and announce; the port."""
        if self.server is not None:
            return self.port
        server = QTcpServer(self)
        if not server.listen(QHostAddress(QHostAddress.SpecialAddress.LocalHost), 0):
            raise OSError(server.errorString())
        server.newConnection.connect(self._connected)
        self.server = server
        self.discovery = write_discovery(CONFIG, self.port, self.token,
                                         self.window.windowTitle(), ogr_fem2d.__version__)
        return self.port

    def stop(self) -> None:
        if self.discovery is not None:
            remove_discovery(CONFIG, self.discovery)
            self.discovery = None
        for sock in list(self._sessions):
            sock.disconnectFromHost()
        self._sessions.clear()
        if self.server is not None:
            self.server.close()
            self.server.deleteLater()
            self.server = None

    # ------------------------------------------------------------ connections
    def _connected(self) -> None:
        while self.server is not None and self.server.hasPendingConnections():
            sock = self.server.nextPendingConnection()
            self._sessions[sock] = (BridgeSession(
                CONFIG, self.token, self.call, window=self.window.windowTitle,
                version=ogr_fem2d.__version__, on_hello=self._hello), bytearray())
            sock.readyRead.connect(lambda s=sock: self._read(s))
            sock.disconnected.connect(lambda s=sock: self._gone(s))

    def _read(self, sock) -> None:
        session, buf = self._sessions.get(sock, (None, None))
        if session is None:
            return
        buf += bytes(sock.readAll())
        while b"\n" in buf:
            k = buf.index(b"\n")
            line = bytes(buf[:k + 1])
            del buf[:k + 1]
            sock.write(session.answer_line(line))
            sock.flush()
            if not session.authed:
                sock.disconnectFromHost()
                return

    def _gone(self, sock) -> None:
        self._sessions.pop(sock, None)
        sock.deleteLater()

    def _hello(self, message: dict) -> None:
        folder = message.get("workdir")
        ws = self.window.session.ws
        if folder and getattr(ws, "workdir", None) is None and Path(folder).is_dir():
            ws.workdir = Path(folder)

    # ------------------------------------------------------------ the calls
    def call(self, op: str, /, **kwargs):
        """An operation on the window's session (see the module's notes)."""
        spec = api.OPERATIONS.get(op)
        changes = spec is not None and (spec.mutates or op == "analysis_run")
        if changes and op not in WHILE_CALCULATING:
            running = self.window.running_jobs()
            if running:
                raise Busy(say("fem.bridge.busy", op=op, job=running[0]),
                           hint=say("fem.bridge.busy.hint", job=running[0]))
        return self.window.session.call(op, **kwargs)
