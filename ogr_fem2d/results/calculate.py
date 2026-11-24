# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Calculate a model and write its results; open them, with their state (spec
005, RF-1 to RF-3; D7, D13; ADR-0003).

* ``calculate(model, model_path)``: translates the model to the engine
  (spec 004; a model that cannot be translated raises its ``ModelError``
  and writes nothing), solves it stage by stage (``analysis.stages``) and
  writes ``<root>.h5`` beside ``<root>.ogrfem2d`` as the stages come
  (``store.Writer``). Its status:

  - ``complete``: every stage solved;
  - ``incomplete``: a stage could not be solved (it did not converge, a
    point could not be updated, the restraints left the model free, a load
    fell outside its element). The stages before it are written, and the
    file says which stage stopped it and the engine's error (D7);
  - ``cancelled``: ``should_stop()``, asked between stages, said so. The
    interface (006) asks it; it does not interrupt a stage.

  An error of the input (the engine's ``InputError``) or of a program's own
  fault is not a stage that failed: it raises, and the previous ``.h5``
  stays.
* ``open_results(model_path)``: the state of the results of the model at
  ``model_path`` (RF-3): ``valid``; ``stale`` (the fingerprint of the
  results is not that of the model: it changed after the calculation);
  ``incomplete`` and ``cancelled`` (as written); ``missing`` (no ``.h5``:
  calculate); ``damaged`` (the file does not read, with why). Written by
  another version of the program or of the core is not stale, but it is
  said (``other_version``, D7). Only valid results are given as they are;
  the others, asked for explicitly (``read_anyway``), each value keeping
  the state it came with.

A ``.h5`` with no model is read with ``store.read``: nothing checks its
fingerprint then, and the reader knows it.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import ogr_core

import ogr_fem2d
from ..engine import analysis
from ..engine import interface
from ..engine.reference import solver
from ..model import fingerprint, ogr_file, translate
from ..model import model as md
from . import store
from . import strains as st

VALID, STALE, MISSING, DAMAGED = "valid", "stale", "missing", "damaged"
INCOMPLETE, CANCELLED = store.INCOMPLETE, store.CANCELLED

#: the engine's errors that stop a stage, and leave the stages before it
STAGE_FAILURES = (solver.NotConvergedError, solver.StateUpdateError,
                  analysis.InsufficientRestraintError, analysis.LoadError)


def written_by() -> str:
    return f"OGR FEM2D {ogr_fem2d.__version__}"


def core_version() -> str:
    return f"ogr-core {ogr_core.__version__}"


def results_path(model_path) -> Path:
    """``<root>.h5`` of ``<root>.ogrfem2d`` (D13)."""
    return Path(model_path).with_suffix(".h5")


@dataclass(frozen=True)
class Calculated:
    path: Path
    status: str
    stages: int                  # how many were written
    stopped_at: int | None
    reason: str


def mesh_data(m: md.Model, engine, g: st.PointGeometry) -> store.MeshData:
    return store.MeshData(np.asarray(engine.nodes, dtype=float),
                          np.asarray(engine.elements, dtype=np.int64),
                          np.asarray(m.mesh.element_region, dtype=np.int64),
                          np.asarray(engine.element_material, dtype=np.int64), g.xy, g.element)


def calculate(m: md.Model, model_path, variant: interface.Variant = solver.REFERENCE,
              should_stop: Callable[[], bool] | None = None,
              level: int = store.GZIP_LEVEL) -> Calculated:
    engine = translate.to_engine(m)
    g = st.geometry(engine.nodes, engine.elements, engine.analysis)
    path = results_path(model_path)
    status, stopped, reason, k = store.COMPLETE, None, "", 0
    with store.Writer(path, written_by=written_by(), core=core_version(),
                      engine_variant=variant.name, model_fingerprint=fingerprint.model_fingerprint(m),
                      analysis=m.analysis, mesh=mesh_data(m, engine, g),
                      deciding=translate.deciding_values(m), level=level) as w:
        try:
            for outcome in analysis.stages(engine, variant):
                stage = m.stages[k]
                w.add_stage(stage.id, stage.name, outcome,
                            st.strains(g, outcome.displacement, outcome.active))
                k += 1
                if k < len(m.stages) and should_stop is not None and should_stop():
                    status, stopped = store.CANCELLED, k
                    reason = f"stopped before stage {m.stages[k].id!r}"
                    break
        except STAGE_FAILURES as err:
            status, stopped = store.INCOMPLETE, k
            reason = f"stage {m.stages[k].id!r}: {type(err).__name__}: {err}"
        w.finish(status, stopped, reason)
    return Calculated(path, status, k, stopped, reason)


class NotValidError(ValueError):
    """Results asked for as they are when they are not valid."""


@dataclass(frozen=True)
class Opened:
    status: str
    path: Path
    message: str = ""
    other_version: str = ""          # who wrote them, when not this program's version
    _results: store.Results | None = None

    @property
    def results(self) -> store.Results:
        """The results, only when they are valid (RF-3)."""
        if self.status != VALID:
            raise NotValidError(f"{self.path.name}: the results are {self.status}"
                                + (f" ({self.message})" if self.message else ""))
        return self._results

    def read_anyway(self) -> store.Results:
        """The results of any state that can be read (stale, incomplete,
        cancelled), asked for explicitly; never for missing or damaged."""
        if self._results is None:
            raise NotValidError(f"{self.path.name}: {self.status}"
                                + (f" ({self.message})" if self.message else ""))
        return self._results


def open_results(model_path, m: md.Model | None = None) -> Opened:
    """The results of the model at ``model_path`` (read from it unless
    ``m`` is given) and their state."""
    path = results_path(model_path)
    if not path.exists():
        return Opened(MISSING, path, "no results: calculate the model")
    try:
        r = store.read(path)
    except store.ResultsError as err:
        return Opened(DAMAGED, path, err.what)
    if m is None:
        m = ogr_file.read(model_path)
    h = r.header
    other = "" if (h.written_by, h.core) == (written_by(), core_version()) else \
        f"{h.written_by}, {h.core}"
    if h.model_fingerprint != fingerprint.model_fingerprint(m):
        return Opened(STALE, path, "the model changed after the calculation", other, r)
    if h.status != store.COMPLETE:
        return Opened(h.status, path, h.reason, other, r)
    return Opened(VALID, path, "", other, r)
