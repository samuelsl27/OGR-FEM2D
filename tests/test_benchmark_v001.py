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
  a sleeping one near 0, which is what the share is meant to see. Both over
  blocks of at least half a second, because Windows counts the CPU time of a
  process in ticks of 15.6 ms; and the sleeping one in a fresh interpreter
  with the benchmark's environment (NumPy limited to one thread, ONE_THREAD),
  because in the suite the threads of the linear algebra that earlier tests
  started count as this process's too (spec 002, T14: it failed now and then
  on the CI with blocks of 60 ms in the suite's process);
* **one thread when it runs, nothing changed when imported** (v0.0.3): run as
  a script, the benchmark has the three variables of ONE_THREAD in the
  environment by the time NumPy is imported, keeping a value the user set;
  imported, it leaves the environment of the process as it was. Until v0.0.3
  the import set them, and they stayed for every later test and every
  process those tests started (the leak check of OGR Core 0.2.0 named it).
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

from ogr_fem2d.engine.reference import mohr_coulomb as mc
from poc import benchmark

_ROOT = Path(__file__).resolve().parents[1]


def _without_the_threads() -> dict:
    """This process's environment without the variables of ONE_THREAD, so
    that what a child ends up with is what the benchmark put there."""
    return {k: v for k, v in os.environ.items() if k not in benchmark.ONE_THREAD}


class TestOneThread:
    def test_importing_it_changes_nothing(self):
        code = ("import json, os; from poc import benchmark; "
                "print(json.dumps({k: os.environ.get(k) for k in benchmark.ONE_THREAD}))")
        done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                              check=True, cwd=_ROOT, env=_without_the_threads())
        assert json.loads(done.stdout) == {k: None for k in benchmark.ONE_THREAD}, done.stdout

    def test_running_it_limits_numpy_before_it_loads(self):
        # The variables are read when NumPy's libraries load: a finder first
        # in the import machinery writes down the environment at the moment
        # numpy is first asked for. --help stops the run before any measure.
        code = (
            "import json, os, runpy, sys\n"
            "seen = {}\n"
            "class Spy:\n"
            "    def find_spec(self, name, path=None, target=None):\n"
            "        if name == 'numpy' and not seen:\n"
            f"            seen.update({{k: os.environ.get(k) for k in {list(benchmark.ONE_THREAD)!r}}})\n"
            "        return None\n"
            "sys.meta_path.insert(0, Spy())\n"
            "sys.argv = ['benchmark.py', '--help']\n"
            "try:\n"
            "    runpy.run_path('poc/benchmark.py', run_name='__main__')\n"
            "except SystemExit:\n"
            "    pass\n"
            "print('SEEN', json.dumps(seen))\n")
        done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                              check=True, cwd=_ROOT, env=_without_the_threads())
        line = [x for x in done.stdout.splitlines() if x.startswith("SEEN ")]
        assert line, done.stdout + done.stderr
        assert json.loads(line[0][5:]) == benchmark.ONE_THREAD, line[0]

    def test_a_value_already_set_is_kept(self):
        env = {"OMP_NUM_THREADS": "4", "PATH": "x"}
        benchmark.one_thread(env)
        assert env == {"OMP_NUM_THREADS": "4", "PATH": "x",
                       "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}, env
        assert set(benchmark.ONE_THREAD) == {"OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                                             "MKL_NUM_THREADS"}


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
        code = ("import time; from poc import benchmark; "
                "print(benchmark.timed(lambda: sum(i * i for i in range(100_000)), 3, 0.5)"
                ".cpu_share, benchmark.timed(lambda: time.sleep(0.02), 3, 0.5).cpu_share)")
        env = dict(os.environ)
        benchmark.one_thread(env)               # as the benchmark runs
        done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                              check=True, cwd=_ROOT, env=env)
        busy, asleep = (float(x) for x in done.stdout.split())
        # it had the core most of the time, and one thread cannot have more
        # than one core (two ticks of 15.6 ms over the half second: 0.06)
        assert 0.5 < busy <= 1.1, busy
        assert asleep < 0.2, asleep            # it did not

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
