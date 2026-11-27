# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The results file, ``modelo.h5`` (spec 005, RF-1, RF-2, RF-4; D6, D7, D13;
ADR-0003). Its layout, field by field, is in docs/resultados/formato.md.

What goes in it is what the engine gave and what follows from it with
nothing chosen (D6): per stage, the displacements, the stresses, the strains
(B u), the plastic flags, the active elements, the removed nodes and those
of the axis, the reactions, the convergence history and the settings; a
copy of the mesh with the coordinates of the integration points; the
fingerprint of the model, the versions, the variant of the engine and what
decided the result (rule 12). In the ENGINE'S sign (tension positive), as
the attribute ``sign_convention`` says (D1). Nothing that depends on a
convention.

The values recovered at the nodes depend on a method, and D6 left them
out; since v0.0.15 (spec 006, T36; D6 modified by the owner on 2026-11-27)
a stage MAY carry them, in ``recovered/<kind>``, marked with the method and
its version (``recovery.METHOD``): a reader takes them only when the mark is
that of its own method, and recovers again otherwise, so a better method
is still seen on old results (D6's reason). They are written when
calculating so that the first drawing of a stage does not wait for them
(D15). Optional: a file without them is read as before.

* ``Writer``: writes to ``<path>.tmp`` and, at ``finish``, moves it over
  ``<path>`` with ``os.replace`` (D13, the pattern of OGR Slip2D's results
  writer). Stages are added as they come; a write that fails or is left
  unfinished removes the temporary file and leaves the previous ``<path>``
  as it was (RF-2). ``finish`` takes the status: ``complete``, or
  ``incomplete`` / ``cancelled`` with the stage that was not solved and why
  (D7).
* ``read``: opens a file and checks its shape at once (the format, its
  version, every attribute and every field with its size), and only then
  reads, lazily, a stage or a field alone (RF-4). A damaged file, a missing
  field or a later format raise ``ResultsError`` naming what and where;
  nothing is read half way.

h5py (BSD-3-Clause), declared by this program (D8); gzip, the compression
every HDF5 reader has, on the large fields.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np

from ..engine.analysis import StageOutcome

FORMAT = "ogr-fem2d-results"
FORMAT_VERSION = 1
COMPLETE, INCOMPLETE, CANCELLED = "complete", "incomplete", "cancelled"
STATUSES = (COMPLETE, INCOMPLETE, CANCELLED)
UNITS_STORED = "m, kN, kPa"
SIGN = "tension positive, lengthening positive (the engine's)"
#: the gzip level (T5: measured on case 005, changelog v0.0.11)
GZIP_LEVEL = 4

HEADER = ("format", "format_version", "written_by", "core", "engine_variant",
          "model_fingerprint", "analysis", "units_stored", "sign_convention", "status",
          "stopped_at", "reason", "n_stages")
MESH = ("nodes", "elements", "element_region", "element_material", "points", "point_element")
STAGE_ATTRS = ("id", "name", "solved", "steps", "tolerance", "cuts")
STAGE_FIELDS = ("displacement", "stress", "strain", "plastic", "active", "removed_nodes",
                "axis_held", "reaction_nodes", "reactions", "history")
#: the tensors whose recovered values a stage may carry (optional)
RECOVERED = ("stress", "strain")


class ResultsError(ValueError):
    """A results file that cannot be read as it is, and why."""

    def __init__(self, path, what: str):
        self.path, self.what = Path(path), what
        super().__init__(f"{Path(path).name}: {what}")


@dataclass(frozen=True)
class MeshData:
    nodes: np.ndarray             # (N, 2)
    elements: np.ndarray          # (E, 3 or 6)
    element_region: np.ndarray    # (E,)
    element_material: np.ndarray  # (E,)
    points: np.ndarray            # (P, 2), the engine's order
    point_element: np.ndarray     # (P,)


# ----------------------------------------------------------------- writing
def _big(group, name, data, level):
    data = np.asarray(data)
    if data.size == 0 or level is None:
        return group.create_dataset(name, data=data)
    return group.create_dataset(name, data=data, compression="gzip", compression_opts=level,
                                shuffle=True)


def stress_array(outcome: StageOutcome) -> np.ndarray:
    """The stresses of a stage as (P, 4), NaN at the inactive points."""
    out = np.full((len(outcome.stresses), 4), np.nan)
    for k, s in enumerate(outcome.stresses):
        if s is not None:
            out[k] = s
    return out


def node_table(values, element_material, elements):
    """``(table, at)`` of values per element node (E, n, c): one row per
    node and material, and each element node's row (-1 where NaN, an
    element not active). Refuses values that differ for one node and
    material: they would not come back the same."""
    values = np.asarray(values, dtype=float)
    elements = np.asarray(elements, dtype=np.int64)
    n_el, n_per, comps = values.shape
    live = ~np.isnan(values).all(axis=2)                              # (E, n)
    key = (np.asarray(element_material, dtype=np.int64)[:, None] * (int(elements.max()) + 1)
           + elements)
    keys, first, inverse = np.unique(key[live], return_index=True, return_inverse=True)
    table = values[live][first]
    if not np.array_equal(table[inverse], values[live], equal_nan=True):
        raise ValueError("values that differ for one node and material")
    at = np.full((n_el, n_per), -1, dtype=np.int64)
    at[live] = inverse
    return table, at


def from_node_table(table, at) -> np.ndarray:
    """The values per element node back: ``table[at]``, NaN where -1."""
    out = np.full(at.shape + (table.shape[1],), np.nan)
    live = at >= 0
    out[live] = table[at[live]]
    return out


class Writer:
    """``with Writer(path, ...) as w: w.add_stage(...); w.finish(status)``."""

    def __init__(self, path, *, written_by: str, core: str, engine_variant: str,
                 model_fingerprint: str, analysis: str, mesh: MeshData,
                 deciding: list[tuple[str, object, str]], level: int = GZIP_LEVEL):
        self.path = Path(path)
        self.tmp = self.path.with_name(self.path.name + ".tmp")
        self.level = level
        self.n = 0
        self.done = False
        self.f = h5py.File(self.tmp, "w")
        try:
            a = self.f.attrs
            a["format"], a["format_version"] = FORMAT, FORMAT_VERSION
            a["written_by"], a["core"], a["engine_variant"] = written_by, core, engine_variant
            a["model_fingerprint"], a["analysis"] = model_fingerprint, analysis
            a["units_stored"], a["sign_convention"] = UNITS_STORED, SIGN
            a["status"], a["stopped_at"], a["reason"], a["n_stages"] = INCOMPLETE, -1, "", 0
            rows = [(str(what), json.dumps(value, ensure_ascii=False), str(why))
                    for what, value, why in deciding]
            self.f.create_dataset("deciding", data=np.array(rows, dtype=h5py.string_dtype())
                                  .reshape(len(rows), 3))
            g = self.f.create_group("mesh")
            _big(g, "nodes", np.asarray(mesh.nodes, dtype=float), level)
            _big(g, "elements", np.asarray(mesh.elements, dtype=np.int64), level)
            for name in MESH[2:]:
                dtype = float if name == "points" else np.int64
                _big(g, name, np.asarray(getattr(mesh, name), dtype=dtype), level)
            self.f.create_group("stages")
        except BaseException:
            self._drop()
            raise

    def add_stage(self, stage_id: str, name: str, outcome: StageOutcome, strain) -> None:
        g = self.f["stages"].create_group(f"{self.n:04d}")
        g.attrs["id"], g.attrs["name"] = stage_id, name
        g.attrs["solved"], g.attrs["steps"] = int(outcome.solved), int(outcome.steps)
        g.attrs["tolerance"], g.attrs["cuts"] = float(outcome.tolerance), int(outcome.cuts)
        lvl = self.level
        _big(g, "displacement", np.asarray(outcome.displacement, dtype=float).reshape(-1, 2), lvl)
        _big(g, "stress", stress_array(outcome), lvl)
        _big(g, "strain", np.asarray(strain, dtype=float), lvl)
        _big(g, "plastic", np.asarray(outcome.plastic, dtype=np.uint8), lvl)
        _big(g, "active", np.asarray(outcome.active, dtype=np.uint8), lvl)
        g.create_dataset("removed_nodes", data=np.asarray(outcome.removed_nodes, dtype=np.int64))
        g.create_dataset("axis_held", data=np.asarray(outcome.axis_held, dtype=np.int64))
        nodes = sorted(outcome.reactions)
        g.create_dataset("reaction_nodes", data=np.asarray(nodes, dtype=np.int64))
        g.create_dataset("reactions", data=np.asarray([outcome.reactions[n] for n in nodes],
                                                      dtype=float).reshape(len(nodes), 2))
        g.create_dataset("history", data=np.asarray(outcome.history, dtype=float)
                         .reshape(len(outcome.history), 3))
        self.n += 1
        self.f.attrs["n_stages"] = self.n

    def add_recovered(self, kind: str, values, source, notes: dict, method: str,
                      element_material, elements) -> None:
        """The recovered values of ``kind`` of the stage last added, marked
        with the method that gave them: once per node and material (``table``,
        K x 4) and, per element node, its row (``at``, -1 for an element not
        active). A node has one value per material (recovery, D5), so the
        values per element node are ``table[at]``, the same bits. Case 005,
        measured: the file is 6.1 MB without them, 12.6 MB with them per
        element node, 8.9 MB so."""
        if kind not in RECOVERED:
            raise ValueError(f"no recovered {kind!r}; a stage may have {', '.join(RECOVERED)}")
        table, at = node_table(values, element_material, elements)
        g = self.f["stages"][f"{self.n - 1:04d}"].require_group("recovered").create_group(kind)
        g.attrs["method"], g.attrs["notes"] = method, json.dumps(notes)
        _big(g, "table", table, self.level)
        _big(g, "at", at, self.level)
        _big(g, "source", np.asarray(source, dtype=np.int8), self.level)

    def finish(self, status: str = COMPLETE, stopped_at: int | None = None,
               reason: str = "") -> Path:
        if status not in STATUSES:
            raise ValueError(f"status {status!r} is not one of {STATUSES}")
        if (status == COMPLETE) != (stopped_at is None):
            raise ValueError("a complete calculation has no stage where it stopped, and an "
                             "incomplete or cancelled one has")
        a = self.f.attrs
        a["status"], a["stopped_at"], a["reason"] = status, -1 if stopped_at is None else stopped_at, reason
        self.f.close()
        os.replace(self.tmp, self.path)
        self.done = True
        return self.path

    def _drop(self) -> None:
        try:
            self.f.close()
        except Exception:  # noqa: BLE001 - the file may be half made
            pass
        self.tmp.unlink(missing_ok=True)

    def __enter__(self):
        return self

    def __exit__(self, kind, value, tb):
        if not self.done:
            self._drop()
        return False


# ----------------------------------------------------------------- reading
@dataclass(frozen=True)
class Header:
    format_version: int
    written_by: str
    core: str
    engine_variant: str
    model_fingerprint: str
    analysis: str
    units_stored: str
    sign_convention: str
    status: str
    stopped_at: int | None
    reason: str
    n_stages: int


def _shape_problems(f, n_stages: int) -> list[str]:
    out = []
    if "deciding" not in f:
        out.append("no 'deciding'")
    if "mesh" not in f:
        return out + ["no group 'mesh'"]
    m = f["mesh"]
    for name in MESH:
        if name not in m:
            out.append(f"mesh: no '{name}'")
    if out:
        return out
    n_nodes, n_el, n_pt = m["nodes"].shape[0], m["elements"].shape[0], m["points"].shape[0]
    sizes = {"nodes": (n_nodes, 2), "element_region": (n_el,), "element_material": (n_el,),
             "points": (n_pt, 2), "point_element": (n_pt,)}
    for name, shape in sizes.items():
        if m[name].shape != shape:
            out.append(f"mesh: '{name}' has shape {m[name].shape}, not {shape}")
    if "stages" not in f:
        return out + ["no group 'stages'"]
    for k in range(n_stages):
        key = f"{k:04d}"
        if key not in f["stages"]:
            out.append(f"no stage {key}")
            continue
        g = f["stages"][key]
        out += [f"stage {key}: no attribute '{a}'" for a in STAGE_ATTRS if a not in g.attrs]
        missing = [name for name in STAGE_FIELDS if name not in g]
        out += [f"stage {key}: no '{name}'" for name in missing]
        if missing:
            continue
        want = {"displacement": (n_nodes, 2), "stress": (n_pt, 4), "plastic": (n_pt,),
                "active": (n_el,)}
        for name, shape in want.items():
            if g[name].shape != shape:
                out.append(f"stage {key}: '{name}' has shape {g[name].shape}, not {shape}")
        if g["strain"].shape[0] != n_pt or g["strain"].shape[1:] not in ((3,), (4,)):
            out.append(f"stage {key}: 'strain' has shape {g['strain'].shape}")
        n_per = m["elements"].shape[1]
        for kind in (g["recovered"] if "recovered" in g else ()):
            r = g["recovered"][kind]
            if kind not in RECOVERED or "method" not in r.attrs or "notes" not in r.attrs \
                    or any(name not in r for name in ("table", "at", "source")):
                out.append(f"stage {key}: 'recovered/{kind}' is not as written")
            elif r["at"].shape != (n_el, n_per) or r["source"].shape != (n_el, n_per) \
                    or r["table"].ndim != 2 or r["table"].shape[1] != 4:
                out.append(f"stage {key}: 'recovered/{kind}' has shape {r['table'].shape}, "
                           f"{r['at'].shape}")
    return out


class Results:
    """An opened results file: its header, and its mesh, stages and fields
    read when asked for. Every read opens and closes the file."""

    def __init__(self, path, header: Header, deciding: tuple):
        self.path, self.header, self.deciding = Path(path), header, deciding
        self._mesh: MeshData | None = None

    def _open(self):
        return h5py.File(self.path, "r")

    @property
    def n_stages(self) -> int:
        return self.header.n_stages

    def mesh(self) -> MeshData:
        if self._mesh is None:
            with self._open() as f:
                m = f["mesh"]
                self._mesh = MeshData(*(m[name][()] for name in MESH))
        return self._mesh

    def stage_info(self, k: int) -> dict:
        self._check_stage(k)
        with self._open() as f:
            a = f["stages"][f"{k:04d}"].attrs
            return {"id": str(a["id"]), "name": str(a["name"]), "solved": bool(a["solved"]),
                    "steps": int(a["steps"]), "tolerance": float(a["tolerance"]),
                    "cuts": int(a["cuts"])}

    def field(self, k: int, name: str) -> np.ndarray:
        """One field of stage ``k`` (STAGE_FIELDS), read alone."""
        self._check_stage(k)
        if name not in STAGE_FIELDS:
            raise KeyError(f"no field {name!r}; a stage has {', '.join(STAGE_FIELDS)}")
        with self._open() as f:
            return f["stages"][f"{k:04d}"][name][()]

    def recovered(self, k: int, kind: str, method: str):
        """``(values, source, notes)`` recovered when calculating, if stage
        ``k`` has them for ``kind`` by ``method``; None otherwise."""
        self._check_stage(k)
        with self._open() as f:
            g = f["stages"][f"{k:04d}"]
            if "recovered" not in g or kind not in g["recovered"]:
                return None
            r = g["recovered"][kind]
            if str(r.attrs["method"]) != method:
                return None
            at = r["at"][()]
            if at.size and int(at.max()) >= r["table"].shape[0]:
                raise ResultsError(self.path, f"stage {k:04d}: 'recovered/{kind}' points "
                                              "past its table")
            return (from_node_table(r["table"][()], at), r["source"][()],
                    json.loads(r.attrs["notes"]))

    def outcome(self, k: int) -> StageOutcome:
        """Stage ``k`` as the engine gave it (the strains apart, ``field``)."""
        info = self.stage_info(k)
        stress = self.field(k, "stress")
        active = self.field(k, "active").astype(bool)
        element = self.mesh().point_element
        stresses = [tuple(float(v) for v in s) if active[e] else None
                    for s, e in zip(stress, element)]
        nodes, forces = self.field(k, "reaction_nodes"), self.field(k, "reactions")
        return StageOutcome(
            [float(v) for v in self.field(k, "displacement").reshape(-1)], stresses,
            {int(n): (float(r[0]), float(r[1])) for n, r in zip(nodes, forces)},
            [bool(v) for v in self.field(k, "plastic")],
            tuple(int(n) for n in self.field(k, "axis_held")), info["solved"],
            [(int(i), int(j), float(r)) for i, j, r in self.field(k, "history")],
            info["steps"], info["tolerance"], info["cuts"], tuple(bool(v) for v in active),
            tuple(int(n) for n in self.field(k, "removed_nodes")))

    def _check_stage(self, k: int) -> None:
        if not 0 <= k < self.n_stages:
            raise IndexError(f"stage {k}: the file has {self.n_stages}")


def read(path) -> Results:
    """Open a results file, checking its shape first (RF-4)."""
    path = Path(path)
    if not path.exists():
        raise ResultsError(path, "there is no such file")
    try:
        f = h5py.File(path, "r")
    except OSError as err:
        raise ResultsError(path, f"not an HDF5 file, or a damaged one ({err})") from None
    with f:
        a = f.attrs
        if a.get("format") != FORMAT:
            raise ResultsError(path, f"not a results file of OGR FEM2D (format {a.get('format')!r})")
        missing = [k for k in HEADER if k not in a]
        if missing:
            raise ResultsError(path, "no attribute " + ", ".join(repr(k) for k in missing))
        version = int(a["format_version"])
        if version > FORMAT_VERSION:
            raise ResultsError(path, f"format version {version}, later than this program's "
                                     f"({FORMAT_VERSION}): written by {a['written_by']}")
        if str(a["status"]) not in STATUSES:
            raise ResultsError(path, f"status {a['status']!r} is not one of {STATUSES}")
        n = int(a["n_stages"])
        problems = _shape_problems(f, n)
        if problems:
            raise ResultsError(path, "; ".join(problems))
        stopped = int(a["stopped_at"])
        header = Header(version, str(a["written_by"]), str(a["core"]), str(a["engine_variant"]),
                        str(a["model_fingerprint"]), str(a["analysis"]), str(a["units_stored"]),
                        str(a["sign_convention"]), str(a["status"]),
                        None if stopped < 0 else stopped, str(a["reason"]), n)
        deciding = tuple((str(r[0].decode() if isinstance(r[0], bytes) else r[0]),
                          json.loads(r[1].decode() if isinstance(r[1], bytes) else r[1]),
                          str(r[2].decode() if isinstance(r[2], bytes) else r[2]))
                         for r in f["deciding"][()])
    return Results(path, header, deciding)
