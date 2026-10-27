// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
//! The Rust variant of the engine, module ogr_fem2d._engine (spec 001, T12;
//! ADR-0001). The Python side is ogr_fem2d/engine/compiled.py, which puts it
//! behind the common interface (ogr_fem2d/engine/interface.py).
//!
//! Three functions, all on NumPy arrays of float64 (int64 for node numbers):
//!
//! * `integrate(materials, start, strains)`: the constitutive integration of
//!   every point;
//! * `internal_forces(nodes, dndx, dndy, weight, stresses, n_dofs)`;
//! * `update(nodes, dndx, dndy, weight, materials, start, du)`: THE call per
//!   global iteration: strains, stresses, internal forces, tangents and the
//!   stiffness weight B^T D B of every point.
//!
//! A point whose stress cannot be updated (the apex with psi = 0) does not
//! raise here: the functions return its index as `failed` (-1 when all went
//! well), and the Python side raises the engine's StateUpdateError with the
//! element and point, as the other variants do.
//!
//! One thread (spec 001, "Fuera de alcance").

mod elastic;
mod mohr_coulomb;
mod t6;

use numpy::ndarray::{Array1, Array2, Array3};
use numpy::{IntoPyArray, PyArray1, PyArray2, PyArray3, PyReadonlyArray1, PyReadonlyArray2};
use pyo3::prelude::*;

use mohr_coulomb::{MohrCoulomb, Region};

/// Kind of a row of the material table (interface.MATERIAL_COLUMNS).
const ELASTIC: f64 = 0.0;

/// Stress update of one point with the material of its row: (stress,
/// plastic, tangent), or Err when the return has no solution.
fn integrate_point(row: &[f64], start: [f64; 4], strain: [f64; 3]) -> Result<([f64; 4], bool, [[f64; 3]; 3]), ()> {
    let (young, poisson) = (row[1], row[2]);
    if row[0] == ELASTIC {
        let d = elastic::stress_increment(young, poisson, strain);
        let stress = [start[0] + d[0], start[1] + d[1], start[2] + d[2], start[3] + d[3]];
        return Ok((stress, false, elastic::plane_strain_matrix(young, poisson)));
    }
    let m = MohrCoulomb { young, poisson, cohesion: row[3], phi: row[4], psi: row[5] };
    let u = mohr_coulomb::update(&m, start, strain).map_err(|_| ())?;
    Ok((u.stress, u.region != Region::Elastic, u.tangent))
}

type Integrated<'py> = (
    Bound<'py, PyArray2<f64>>,
    Bound<'py, PyArray1<bool>>,
    Bound<'py, PyArray3<f64>>,
    i64,
);

/// The constitutive integration of every point.
#[pyfunction]
fn integrate<'py>(
    py: Python<'py>,
    materials: PyReadonlyArray2<'py, f64>,
    start: PyReadonlyArray2<'py, f64>,
    strains: PyReadonlyArray2<'py, f64>,
) -> Integrated<'py> {
    let (materials, start, strains) = (materials.as_array(), start.as_array(), strains.as_array());
    let n = start.nrows();
    let mut stresses = Array2::<f64>::zeros((n, 4));
    let mut plastic = Array1::<bool>::from_elem(n, false);
    let mut tangents = Array3::<f64>::zeros((n, 3, 3));
    let mut failed = -1i64;
    for p in 0..n {
        let row = materials.row(p).to_vec();
        let s0 = [start[[p, 0]], start[[p, 1]], start[[p, 2]], start[[p, 3]]];
        let eps = [strains[[p, 0]], strains[[p, 1]], strains[[p, 2]]];
        match integrate_point(&row, s0, eps) {
            Ok((s, is_plastic, d)) => {
                for i in 0..4 {
                    stresses[[p, i]] = s[i];
                }
                plastic[p] = is_plastic;
                for i in 0..3 {
                    for j in 0..3 {
                        tangents[[p, i, j]] = d[i][j];
                    }
                }
            }
            Err(()) => {
                failed = p as i64;
                break;
            }
        }
    }
    (stresses.into_pyarray(py), plastic.into_pyarray(py), tangents.into_pyarray(py), failed)
}

/// int B^T sigma dA, assembled.
#[pyfunction]
fn internal_forces<'py>(
    py: Python<'py>,
    nodes: PyReadonlyArray2<'py, i64>,
    dndx: PyReadonlyArray2<'py, f64>,
    dndy: PyReadonlyArray2<'py, f64>,
    weight: PyReadonlyArray1<'py, f64>,
    stresses: PyReadonlyArray2<'py, f64>,
    n_dofs: usize,
) -> Bound<'py, PyArray1<f64>> {
    let (nodes, dndx, dndy, weight, stresses) =
        (nodes.as_array(), dndx.as_array(), dndy.as_array(), weight.as_array(), stresses.as_array());
    let mut f = vec![0.0; n_dofs];
    for p in 0..nodes.nrows() {
        let s = [stresses[[p, 0]], stresses[[p, 1]], stresses[[p, 2]], stresses[[p, 3]]];
        t6::add_internal_forces(
            &nodes.row(p).to_vec(),
            &dndx.row(p).to_vec(),
            &dndy.row(p).to_vec(),
            weight[p],
            s,
            &mut f,
        );
    }
    Array1::from(f).into_pyarray(py)
}

type Updated<'py> = (
    Bound<'py, PyArray2<f64>>,
    Bound<'py, PyArray1<f64>>,
    Bound<'py, PyArray1<bool>>,
    Bound<'py, PyArray3<f64>>,
    Bound<'py, PyArray2<f64>>,
    i64,
);

/// THE call per global iteration (ADR-0001).
#[pyfunction]
#[allow(clippy::too_many_arguments)]
fn update<'py>(
    py: Python<'py>,
    nodes: PyReadonlyArray2<'py, i64>,
    dndx: PyReadonlyArray2<'py, f64>,
    dndy: PyReadonlyArray2<'py, f64>,
    weight: PyReadonlyArray1<'py, f64>,
    materials: PyReadonlyArray2<'py, f64>,
    start: PyReadonlyArray2<'py, f64>,
    du: PyReadonlyArray1<'py, f64>,
) -> Updated<'py> {
    let (nodes, dndx, dndy, weight) = (nodes.as_array(), dndx.as_array(), dndy.as_array(), weight.as_array());
    let (materials, start, du) = (materials.as_array(), start.as_array(), du.as_array());
    let du = du.to_vec();
    let n = nodes.nrows();
    let mut stresses = Array2::<f64>::zeros((n, 4));
    let mut f = vec![0.0; du.len()];
    let mut plastic = Array1::<bool>::from_elem(n, false);
    let mut tangents = Array3::<f64>::zeros((n, 3, 3));
    let mut stiffness = Array2::<f64>::zeros((n, 144));
    let mut failed = -1i64;
    let mut k = [0.0; 144];
    for p in 0..n {
        let (pn, px, py_) = (nodes.row(p).to_vec(), dndx.row(p).to_vec(), dndy.row(p).to_vec());
        let eps = t6::strain(&pn, &px, &py_, &du);
        let s0 = [start[[p, 0]], start[[p, 1]], start[[p, 2]], start[[p, 3]]];
        let (s, is_plastic, d) = match integrate_point(&materials.row(p).to_vec(), s0, eps) {
            Ok(result) => result,
            Err(()) => {
                failed = p as i64;
                break;
            }
        };
        for i in 0..4 {
            stresses[[p, i]] = s[i];
        }
        plastic[p] = is_plastic;
        for i in 0..3 {
            for j in 0..3 {
                tangents[[p, i, j]] = d[i][j];
            }
        }
        t6::add_internal_forces(&pn, &px, &py_, weight[p], s, &mut f);
        t6::point_stiffness(&px, &py_, weight[p], &d, &mut k);
        for i in 0..144 {
            stiffness[[p, i]] = k[i];
        }
    }
    (
        stresses.into_pyarray(py),
        Array1::from(f).into_pyarray(py),
        plastic.into_pyarray(py),
        tangents.into_pyarray(py),
        stiffness.into_pyarray(py),
        failed,
    )
}

#[pymodule]
fn _engine(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(integrate, m)?)?;
    m.add_function(wrap_pyfunction!(internal_forces, m)?)?;
    m.add_function(wrap_pyfunction!(update, m)?)?;
    Ok(())
}
