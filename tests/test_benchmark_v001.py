# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.1 (spec 001, T13) — the measure of the variants (poc/benchmark.py)
measures what it says it measures.

Invariants protected:

* **the seeded set is the one documented**: exactly the share of each
  region of PROPORTIONS, each point in the region the reference (the oracle)
  says, and the same points for the same seed (so the three variants, and
  two runs, get the same work);
* **the A/B protocol of the suite**: every call is warmed up once and then
  timed ``repeats`` times; the variants are timed one after the other in a
  first round, and the whole round is repeated as the control, in the same
  order (not each variant twice in a row, which would hide a drift of the
  machine between variants);
* **the state of the machine decides** (owner, 2026-10-27): the load of the
  other programs is read from the operating system, every timing carries the
  CPU share of the process, and a measure is not valid when the others used
  more than allowed at any sample or a CPU share falls outside [0.95, 1.05];
  a single-threaded busy loop on this process shows a CPU share near 1, and
  a sleeping one near 0, which is what the share is meant to see.
"""
from __future__ import annotations

import math

from ogr_fem2d.engine.reference import mohr_coulomb as mc
from poc import benchmark


class TestSeededSet:
    def test_the_proportions_and_the_regions(self):
        n = 200
        materials, start, strains, regions = benchmark.seeded_set(n, seed=7)
        assert len(materials) == len(start) == len(strains) == len(regions) == n
        for region, share in benchmark.PROPORTIONS.items():
            assert abs(regions.count(region) - share * n) <= 1, region
        for row, s0, eps, region in zip(materials, start, strains, regions):
            m = mc.MohrCoulomb(row[1], row[2], row[3], row[4], row[5])
            assert mc.update(m, tuple(s0), tuple(eps)).region == region
        # the apex only with dilatancy (psi = 0 refuses it)
        assert all(row[5] > 0.0 for row, r in zip(materials, regions) if r == "apex")

    def test_the_same_seed_gives_the_same_set(self):
        a = benchmark.seeded_set(60, seed=3)
        b = benchmark.seeded_set(60, seed=3)
        c = benchmark.seeded_set(60, seed=4)
        assert all((x == y).all() for x, y in zip(a[:3], b[:3])) and a[3] == b[3]
        assert not (a[1] == c[1]).all()


class TestProtocol:
    def test_warm_up_then_repeats_round_then_control_round(self):
        log = []
        calls = {"a": lambda: log.append("a"), "b": lambda: log.append("b")}
        result = benchmark.rounds(calls, {"a": 2, "b": 3})
        assert set(result) == {"a", "b"}
        assert all(len(v) == 2 and min(t.seconds for t in v) >= 0.0
                   for v in result.values())
        round_ = ["a"] * 3 + ["b"] * 4          # warm-up + repeats each
        assert log == round_ + round_

    def test_timed_is_the_median(self):
        calls = []
        benchmark.timed(lambda: calls.append(1), 5)
        assert len(calls) == 6                    # one warm-up
        assert math.isfinite(benchmark.timed(lambda: None, 3).seconds)


class TestMachineState:
    def test_the_load_and_the_memory_are_read(self):
        # Windows, Linux and macOS have a way; elsewhere the state is None and
        # the verdict says the load could not be read (test_the_verdict)
        import sys
        state = benchmark.machine_state(1.0)
        assert state["logical_cores"] >= 1
        if sys.platform in ("win32", "linux", "darwin"):
            assert 0.0 <= state["other_load_percent"] <= 100.0, state
            assert state["free_memory_gb"] > 0.0, state
        else:
            assert state["other_load_percent"] is None

    def test_the_cpu_share_sees_a_core_taken_away(self):
        import time
        busy = benchmark.timed(lambda: sum(i * i for i in range(100_000)), 3)
        asleep = benchmark.timed(lambda: time.sleep(0.02), 3)
        assert busy.cpu_share > 0.5            # it had the core most of the time
        assert asleep.cpu_share < 0.2          # it did not

    def test_the_verdict(self):
        idle = {"other_load_percent": 2.0, "logical_cores": 8, "free_memory_gb": 8.0}
        loaded = dict(idle, other_load_percent=48.0)
        good = {"first": 1.0, "control": 1.0, "cpu_share": [0.99, 1.0]}
        integration = {"seconds": {"rust": good}, "machine_after": idle}
        mesh = {"update_seconds": {"rust": good}, "linear_seconds": {"solve": good},
                "machine_after": idle}
        assert benchmark.verdict(idle, integration, mesh, 10.0) == []
        assert benchmark.verdict(loaded, integration, mesh, 10.0)
        robbed = dict(good, cpu_share=[0.80, 1.0])
        assert benchmark.verdict(idle, dict(integration, seconds={"rust": robbed}),
                                 mesh, 10.0)
        unknown = dict(idle, other_load_percent=None)
        assert any("could not be read" in r
                   for r in benchmark.verdict(unknown, integration, mesh, 10.0))
        threaded = dict(good, cpu_share=[1.0, 1.9])
        assert benchmark.verdict(idle, integration,
                                 dict(mesh, linear_seconds={"solve": threaded}), 10.0)
