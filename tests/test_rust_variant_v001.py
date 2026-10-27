# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.0.1 (spec 001, T12) — the Rust variant (rust/, module ogr_fem2d._engine,
behind ogr_fem2d/engine/compiled.py) computes what the Python reference
computes: criterion 1 of ADR-0001, agreement to a relative tolerance of the
order of 1e-10 at a material point and on a mesh.

The checks are those of the NumPy variant (tests/test_numpy_variant_v001.py),
run on this one: a seeded cloud over every region of the return, states on
the yield surface where only the tolerance decides, the refusal of the apex
with psi = 0 at the same point, and the excavation of the 21 m ring with
psi = 0 and 15 degrees. When the test was written the agreement was 7e-16 in
the stresses and 5e-16 in the tangents at a point, and 1e-14 on the mesh:
Rust follows the reference's order of operations.

And one more invariant: **the compiled module is not older than its
sources**. A stale build would be compared instead of the code in rust/src;
when it fails, rebuild with

    .venv/Scripts/python -m maturin develop --release --skip-install
"""
from __future__ import annotations

from pathlib import Path

import test_numpy_variant_v001 as checks
from ogr_fem2d.engine.compiled import RUST

_ROOT = Path(__file__).resolve().parents[1]


class TestRustVariant:
    def test_the_module_is_built_from_the_current_sources(self):
        import ogr_fem2d._engine as engine
        built = Path(engine.__file__).stat().st_mtime
        sources = [*(_ROOT / "rust" / "src").glob("*.rs"),
                   _ROOT / "rust" / "Cargo.toml"]
        stale = [s.name for s in sources if s.stat().st_mtime > built]
        assert not stale, f"ogr_fem2d._engine is older than {stale}: rebuild it"

    def test_a_cloud_over_every_region(self):
        checks.check_a_cloud_over_every_region(RUST)

    def test_states_on_the_surface(self):
        checks.check_states_on_the_surface(RUST)

    def test_the_apex_with_psi_zero_is_refused_at_the_same_point(self):
        checks.check_the_apex_with_psi_zero_is_refused_at_the_same_point(RUST)

    def test_the_ring_gives_the_same_stage(self):
        checks.check_the_ring_gives_the_same_stage(RUST)
