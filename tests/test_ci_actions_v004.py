# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.4 — the CI cannot fall back onto an action that asks for a retired
Node runtime.

Invariant protected: every GitHub Action in ``.github/workflows`` sits at or
above the major this project has vetted, and every action in use has a
vetted major at all. The rule is OGR Core's (``tests/test_ci_actions_v10.py``
at its tag ``v0.2.2``), with this repository's actions.

What was found. Until v0.0.4 the workflow pinned ``actions/checkout@v4``,
``actions/setup-python@v5``, ``actions/upload-artifact@v4`` and
``actions/download-artifact@v4``: all four declare ``node20`` in their own
``action.yml`` (read at each tag on 2026-11-20), and a workflow cannot
override what an action declares. OGR Core's test records node20 leaving
the runners in the autumn of 2026; the CI of v0.0.3 (2026-11-18) still went
green with these four, so the runners ran them anyway, and nothing in this
repository said that they asked for a runtime on its way out.

What this is NOT: a snapshot of what the workflow says today. Each floor
below is declared with its reason, and is edited on purpose.
"""
from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_WORKFLOWS = _ROOT / ".github" / "workflows"

#: Minimum major accepted for each action, and why.
MIN_MAJOR = {
    # The floor of the suite (OGR Core and OGR Slip2D pin v7): node24 came
    # with checkout v5 and setup-python v6, and v7 keeps the jump from being
    # due again within the year.
    "actions/checkout": 7,
    "actions/setup-python": 7,
    # The first majors whose action.yml says node24: upload-artifact v6
    # (v5 had it only as an option) and download-artifact v7 (likewise v6).
    "actions/upload-artifact": 6,
    "actions/download-artifact": 7,
    # v1 is the only major there is (2026-11-20, v1.51.0), and it declares
    # node24.
    "PyO3/maturin-action": 1,
}

#: ``uses:`` may appear as a step (``- uses: x``) or on its own line.
_USES = re.compile(r"^\s*(?:-\s*)?uses:\s*(\S+)", re.MULTILINE)


def _workflow_files() -> list[Path]:
    return sorted(_WORKFLOWS.glob("*.yml")) + sorted(_WORKFLOWS.glob("*.yaml"))


def _pins(text_of=None) -> list[tuple[str, str, str]]:
    """Every ``uses:`` in the workflows as ``(file, action, ref)``.
    ``text_of`` stands in for reading a file (a test gives made-up ones)."""
    found = []
    for path in _workflow_files():
        text = text_of(path) if text_of else path.read_text(encoding="utf-8")
        for ref in _USES.findall(text):
            action, _, version = ref.partition("@")
            found.append((path.name, action, version))
    return found


def _stale(pins) -> list:
    """The pins below their floor; a ref with no major (a SHA) counts too,
    because the floor cannot be checked against it."""
    out = []
    for name, action, version in pins:
        floor = MIN_MAJOR.get(action)
        if floor is None:
            continue
        m = re.fullmatch(r"v?(\d+)(?:\.\d+)*", version)
        if m is None or int(m.group(1)) < floor:
            out.append((name, f"{action}@{version}", f"needs v{floor}+"))
    return out


def _unvetted(pins) -> list:
    return sorted({f"{action} (in {name})" for name, action, _ in pins
                   if action not in MIN_MAJOR})


class TestActionPins:
    def test_the_scan_finds_the_pins_it_guards(self):
        # A scan that matched nothing would pass everything below.
        pins = _pins()
        assert _workflow_files(), "no workflow under .github/workflows"
        assert pins, "the `uses:` scan matched nothing: the guard is blind"
        actions = {action for _, action, _ in pins}
        assert set(MIN_MAJOR) <= actions, (sorted(MIN_MAJOR), sorted(actions))

    def test_every_action_meets_its_floor(self):
        assert _stale(_pins()) == [], _stale(_pins())

    def test_every_action_in_use_has_a_floor(self):
        assert _unvetted(_pins()) == [], _unvetted(_pins())


class TestTheGuardBites:
    """The workflow of v0.0.3, and a few made-up lines, through the same
    functions."""

    _OLD = ("      - uses: actions/checkout@v4\n"
            "      - uses: actions/setup-python@v5\n"
            "        uses: PyO3/maturin-action@v1\n"
            "      - uses: actions/upload-artifact@v4\n"
            "      - uses: actions/download-artifact@v4\n")

    def _of(self, text):
        return _pins(lambda _path: text)

    def test_the_workflow_of_v0_0_3_is_stale_in_four_actions(self):
        stale = {pin for _, pin, _ in _stale(self._of(self._OLD))}
        assert stale == {"actions/checkout@v4", "actions/setup-python@v5",
                         "actions/upload-artifact@v4",
                         "actions/download-artifact@v4"}, stale

    def test_a_sha_is_not_a_major(self):
        text = "      - uses: actions/checkout@0123456789abcdef0123456789abcdef01234567\n"
        assert len(_stale(self._of(text))) == len(_workflow_files())

    def test_an_action_without_a_floor_is_named(self):
        text = "      - uses: someone/new-action@v3\n"
        assert _unvetted(self._of(text)) == sorted(
            f"someone/new-action (in {p.name})" for p in _workflow_files())

    def test_at_the_floor_and_above_pass(self):
        text = "".join(f"      - uses: {a}@v{n}\n      - uses: {a}@v{n + 1}.0.2\n"
                       for a, n in MIN_MAJOR.items())
        assert _stale(self._of(text)) == [] and _unvetted(self._of(text)) == []
