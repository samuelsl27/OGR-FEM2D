# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.15 (spec 006, T34; D8) — the agent bridge: Tools > Agent Bridge (MCP)
serves the window's model to the MCP server, on the core's protocol.

Invariants protected:

* **an agent's edit is the window's**: it is drawn there (the window's
  model, its title) and is one step of its history, undone with Edit >
  Undo;
* **the MCP server goes to the window** when one has its bridge on (the
  core's ``WindowRouter``, as ``build_server`` makes it), and to its own
  models otherwise; ``--attach`` without a window says what to open;
* **with a calculation running, an edit answers Busy**; a question
  (``job_list``, ``project_summary``) is answered;
* a wrong token is refused; turning the bridge off, or closing the window,
  withdraws its announcement.

The client runs in a thread of its own while the window's event loop
answers it, as the MCP server does from its own process.
"""
from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from ogr_core.api import Busy, NotConfigured, OgrApiError  # noqa: E402
from ogr_core.api.bridge import BridgeClient, WindowRouter, live_bridges  # noqa: E402

import _results  # noqa: E402
from _settings import recent_kept  # noqa: E402
from ogr_fem2d import api  # noqa: E402
from ogr_fem2d.api.bridge import CONFIG  # noqa: E402
from ogr_fem2d.gui.main_window import MainWindow  # noqa: E402
from ogr_fem2d.model import ogr_file  # noqa: E402

APP = QApplication.instance() or QApplication([])


def _off_thread(fn):
    """``fn()`` in a thread while the window's loop goes on; its result, or
    what it raised."""
    out = {}

    def run():
        try:
            out["value"] = fn()
        except BaseException as err:          # noqa: BLE001 - handed back
            out["error"] = err
    t = threading.Thread(target=run, daemon=True)
    loop, timer = QEventLoop(), QTimer()
    timer.timeout.connect(lambda: None if t.is_alive() else loop.quit())
    t.start()
    timer.start(10)
    loop.exec()
    timer.stop()
    t.join(5)
    if "error" in out:
        raise out["error"]
    return out["value"]


class _Bridged:
    def __init__(self, path=None):
        self.path = path

    def __enter__(self):
        self._recent = recent_kept()
        self._recent.__enter__()
        self.w = MainWindow()
        if self.path is None:
            self.w.act_new()
        else:
            self.w.open_path(str(self.path))
        self.w._actions["agent_bridge"].trigger()
        assert self.w.agent_bridge.running
        b = self.w.agent_bridge
        self.port, self.token = b.port, b.token
        return self

    def client(self, token=None):
        return BridgeClient(CONFIG, self.port, token or self.token)

    def __exit__(self, *exc):
        self.w.confirm_discard = lambda: True
        self.w.confirm_stop_calculation = lambda: True
        self.w.close()
        self._recent.__exit__(*exc)


class TestTheWindowsModel:
    def test_an_agents_edit_is_drawn_and_undone_in_the_window(self):
        with _Bridged() as b:
            def agent():
                c = b.client()
                try:
                    c.call("project_settings", title="Del agente")
                    return c.call("project_summary")
                finally:
                    c.close()
            summary = _off_thread(agent)
            assert summary["name"] == "Del agente"
            assert b.w.session.model.summary.title == "Del agente"
            assert b.w.windowTitle().startswith("Del agente")
            assert b.w.actions_by_key["undo"].text().startswith("Undo: ")
            b.w.act_undo()
            assert b.w.session.model.summary.title != "Del agente"

    def test_the_mcp_server_goes_to_the_window(self):
        import json
        import anyio
        from mcp import Client
        from ogr_core.testing.leaks import root_logging_kept
        from ogr_fem2d.mcp.server import build_server

        def tool(srv, name, args):
            async def go():
                async with Client(srv) as c:
                    return await c.call_tool(name, args)
            with root_logging_kept():
                got = anyio.run(go)
            assert not got.is_error, got.content[0].text
            return json.loads(got.content[0].text)
        own = api.workspace()
        try:
            with _Bridged() as b:
                with root_logging_kept():
                    srv = build_server(own)
                got = _off_thread(lambda: tool(srv, "project_list", {}))
                assert [p["project_id"] for p in got["projects"]] == [b.w.session.project_id]
                _off_thread(lambda: tool(srv, "project_settings", {"title": "Por MCP"}))
                assert b.w.session.model.summary.title == "Por MCP"
                assert not own.projects                         # none of the server's own
                srv._fem_router.close()
            # without a window: the server's own models, or, attached only, what to open
            with root_logging_kept():
                srv = build_server(own)
                only = build_server(own, only_window=True)._fem_router
            assert tool(srv, "project_new", {})["project_id"] in own.projects
            try:
                only.call("project_list")
            except NotConfigured as err:
                assert "Agent Bridge (MCP)" in str(err) + str(getattr(err, "hint", ""))
            else:
                raise AssertionError("worked without a window")
        finally:
            own.shutdown()


class TestBusy:
    def test_an_edit_while_calculating(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "modelo.ogrfem2d"
            ogr_file.write(_results.excavated_tunnel(3), path)
            with _Bridged(path) as b:
                assert b.w.compute() is None

                def agent():
                    c = b.client()
                    try:
                        try:
                            c.call("project_settings", title="durante")
                        except Busy as err:
                            refused = err
                        else:
                            refused = None
                        asked = c.call("project_summary")
                        return refused, c.call("job_list")["jobs"], asked
                    finally:
                        c.close()
                refused, jobs, asked = _off_thread(agent)
                assert asked["project_id"] == b.w.session.project_id     # a question: answered
                assert refused is not None and "calculation is running" in str(refused)
                assert "job_get" in str(refused.hint)
                assert jobs and jobs[0]["state"] in ("running", "queued", "done")
                assert b.w.session.model.summary.title != "durante"
                b.w.compute_window.wait()


class TestTheDoor:
    def test_a_wrong_token_and_turning_it_off(self):
        with _Bridged() as b:
            try:
                _off_thread(lambda: b.client("no es el suyo"))
            except OgrApiError as err:
                assert "E_UNAUTHORIZED" in str(err.to_dict())
            else:
                raise AssertionError("a wrong token was let in")
            import socket

            def knock():
                with socket.create_connection(("127.0.0.1", b.port), 5) as s:
                    s.settimeout(5)
                    s.sendall(b'{"hello": "ogr-fem2d-bridge/1", "token": "no"}\n')
                    f = s.makefile("rb")
                    first = f.readline()
                    return first, f.readline()                    # then the door shuts
            first, then = _off_thread(knock)
            assert b'"ok": false' in first and then == b""
            assert [x["pid"] for x in live_bridges(CONFIG)] == [os.getpid()]
            assert b.w.act_agent_bridge(False).startswith("Agent bridge off")
            assert live_bridges(CONFIG) == [] and not b.w.agent_bridge.running
            b.w.act_agent_bridge(True)
            assert b.w.agent_bridge.discovery.exists()
            disc = b.w.agent_bridge.discovery
        assert not disc.exists()                           # the window closed
