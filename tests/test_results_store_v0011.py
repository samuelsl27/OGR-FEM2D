# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.11 (spec 005, T4) — the results file (RF-1, RF-2, RF-4; D6, D13).

Invariants protected:

* **there and back, bit for bit**: every stage read back is the engine's
  outcome written (displacements, stresses with None where the element is
  inactive, reactions, plastic flags, axis, history, settings, active and
  removed), and the strains and the mesh are the same bits, NaN in place;
  what decided the result comes back too;
* **one field alone**: a stage's field is read without the others;
* **the shape is checked before anything is read**: a file that is not HDF5,
  one of another program, one of a later format version, one without a field
  or with a field of the wrong size raise ResultsError naming what;
* **a write cut short leaves the previous file** (RF-2, D13): an error while
  adding a stage, or a writer left without ``finish``, removes the temporary
  file and the old file keeps its bytes;
* **the status is consistent**: complete has no stage where it stopped; an
  incomplete or cancelled one has, and says why.
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import replace
from pathlib import Path

import h5py
import numpy as np

import _models
from ogr_fem2d.engine import analysis
from ogr_fem2d.model import translate
from ogr_fem2d.results import store
from ogr_fem2d.results import strains as st


def _calculated():
    m = _models.meshed(_models.with_stages(_models.tunnel(), 2))
    m = replace(m, assignments=(m.assignments[0], replace(m.assignments[1], excavated=(False, True))))
    engine = translate.to_engine(m)
    g = st.geometry(engine.nodes, engine.elements, engine.analysis)
    outs = analysis.run(engine)
    mesh = store.MeshData(np.array(engine.nodes), np.array(engine.elements),
                          np.array(m.mesh.element_region), np.array(engine.element_material),
                          g.xy, g.element)
    return m, engine, g, outs, mesh


M, ENGINE, GEOMETRY, OUTCOMES, MESH = _calculated()


def _write(path, stages=None, status=store.COMPLETE, stopped=None, reason=""):
    with store.Writer(path, written_by="OGR FEM2D test", core="ogr-core test",
                      engine_variant="reference", model_fingerprint="abc", analysis=ENGINE.analysis,
                      mesh=MESH, deciding=translate.deciding_values(M)) as w:
        for k, out in enumerate(OUTCOMES if stages is None else stages):
            w.add_stage(str(k + 1), f"Stage {k + 1}", out, st.strains(GEOMETRY, out.displacement,
                                                                         out.active))
        w.finish(status, stopped, reason)
    return path


def _bits(a):
    return np.ascontiguousarray(a).view(np.uint8).tobytes()


class TestThereAndBack:
    def test_every_stage_is_the_engines(self):
        with tempfile.TemporaryDirectory() as d:
            r = store.read(_write(Path(d) / "m.h5"))
            assert r.n_stages == 2 and r.header.status == store.COMPLETE
            for k, out in enumerate(OUTCOMES):
                assert r.outcome(k) == out, k
                want = st.strains(GEOMETRY, out.displacement, out.active)
                assert _bits(r.field(k, "strain")) == _bits(want), k
                assert r.stage_info(k)["id"] == str(k + 1)
            mesh = r.mesh()
            for name in store.MESH:
                assert _bits(getattr(mesh, name)) == _bits(np.asarray(getattr(MESH, name),
                                                                       dtype=getattr(mesh, name).dtype))
            assert np.isnan(r.field(1, "stress")).any()          # the hole, inactive in stage 2

    def test_the_header_and_what_decided(self):
        with tempfile.TemporaryDirectory() as d:
            r = store.read(_write(Path(d) / "m.h5"))
            h = r.header
            assert (h.format_version, h.written_by, h.core, h.engine_variant, h.model_fingerprint,
                    h.stopped_at) == (1, "OGR FEM2D test", "ogr-core test", "reference", "abc", None)
            assert "tension positive" in h.sign_convention and h.units_stored == "m, kN, kPa"
            want = [(w, json.loads(json.dumps(v)), y) for w, v, y in translate.deciding_values(M)]
            assert list(r.deciding) == want

    def test_one_field_alone(self):
        with tempfile.TemporaryDirectory() as d:
            path = _write(Path(d) / "m.h5")
            with h5py.File(path, "a") as f:
                del f["stages"]["0001"]["strain"]          # another field, damaged afterwards
            # the check on opening would refuse it; a field read alone reads only itself
            r = store.Results(path, store.read(_write(Path(d) / "n.h5")).header, ())
            assert r.field(1, "displacement").shape == (len(ENGINE.nodes), 2)


class TestTheShape:
    def _refused(self, path, words):
        try:
            store.read(path)
        except store.ResultsError as err:
            for w in words:
                assert w in str(err), (str(err), w)
        else:
            raise AssertionError("read")

    def test_not_hdf5_and_another_program(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "x.h5"
            bad.write_bytes(b"not a results file")
            self._refused(bad, ["x.h5", "HDF5"])
            with h5py.File(Path(d) / "y.h5", "w") as f:
                f.attrs["format"] = "something-else"
            self._refused(Path(d) / "y.h5", ["something-else"])
            self._refused(Path(d) / "none.h5", ["no such file"])

    def test_a_later_version_and_a_missing_field(self):
        with tempfile.TemporaryDirectory() as d:
            path = _write(Path(d) / "m.h5")
            with h5py.File(path, "a") as f:
                f.attrs["format_version"] = 2
            self._refused(path, ["format version 2", "later"])
            path = _write(Path(d) / "n.h5")
            with h5py.File(path, "a") as f:
                del f["stages"]["0001"]["reactions"]
            self._refused(path, ["stage 0001", "'reactions'"])

    def test_a_field_of_the_wrong_size(self):
        with tempfile.TemporaryDirectory() as d:
            path = _write(Path(d) / "m.h5")
            with h5py.File(path, "a") as f:
                del f["stages"]["0000"]["active"]
                f["stages"]["0000"].create_dataset("active", data=np.zeros(3, dtype=np.uint8))
            self._refused(path, ["stage 0000", "'active'", "shape"])


class TestACutWrite:
    def test_an_error_leaves_the_previous_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "m.h5"
            path.write_bytes(b"the previous results")
            try:
                with store.Writer(path, written_by="t", core="c", engine_variant="v",
                                  model_fingerprint="f", analysis="plane_strain", mesh=MESH,
                                  deciding=[]) as w:
                    w.add_stage("1", "", OUTCOMES[0], object())       # not a strain
            except Exception:  # noqa: BLE001 - whatever h5py says
                pass
            assert path.read_bytes() == b"the previous results"
            assert not (Path(d) / "m.h5.tmp").exists()

    def test_a_writer_left_unfinished(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "m.h5"
            path.write_bytes(b"old")
            with store.Writer(path, written_by="t", core="c", engine_variant="v",
                              model_fingerprint="f", analysis="plane_strain", mesh=MESH,
                              deciding=[]) as w:
                w.add_stage("1", "", OUTCOMES[0], st.strains(GEOMETRY, OUTCOMES[0].displacement))
            assert path.read_bytes() == b"old" and not (Path(d) / "m.h5.tmp").exists()


class TestTheStatus:
    def test_incomplete_says_where_and_why(self):
        with tempfile.TemporaryDirectory() as d:
            r = store.read(_write(Path(d) / "m.h5", OUTCOMES[:1], store.INCOMPLETE, 1, "not converged"))
            assert (r.header.status, r.header.stopped_at, r.header.reason, r.n_stages) == \
                (store.INCOMPLETE, 1, "not converged", 1)

    def test_inconsistent_statuses_are_refused(self):
        with tempfile.TemporaryDirectory() as d:
            for status, stopped in ((store.COMPLETE, 0), (store.CANCELLED, None), ("done", None)):
                try:
                    _write(Path(d) / "m.h5", OUTCOMES[:1], status, stopped)
                except ValueError:
                    pass
                else:
                    raise AssertionError((status, stopped))
                assert not (Path(d) / "m.h5.tmp").exists()
