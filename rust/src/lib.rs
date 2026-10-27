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
//! The inputs are read as C-contiguous slices and the outputs written into
//! vectors allocated once: nothing is allocated per point (the review before
//! the measure, spec 001, T13). A non-contiguous input raises ValueError.
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

/// The data of a C-contiguous array as a slice (the Python side,
/// compiled.py, makes them contiguous).
fn data<'a, T: numpy::Element, D: numpy::ndarray::Dimension>(
    a: &'a numpy::ndarray::ArrayView<'a, T, D>,
    name: &str,
) -> PyResult<&'a [T]> {
    a.as_slice()
        .ok_or_else(|| pyo3::exceptions::PyValueError::new_err(format!("{name} is not C-contiguous")))
}

fn stress_at(start: &[f64], p: usize) -> [f64; 4] {
    [start[4 * p], start[4 * p + 1], start[4 * p + 2], start[4 * p + 3]]
}

/// Writes the stress, the tangent and the flag of point p into the outputs.
fn store(p: usize, s: [f64; 4], d: &[[f64; 3]; 3], is_plastic: bool,
         stresses: &mut [f64], tangents: &mut [f64], plastic: &mut [bool]) {
    stresses[4 * p..4 * p + 4].copy_from_slice(&s);
    for i in 0..3 {
        tangents[9 * p + 3 * i..9 * p + 3 * i + 3].copy_from_slice(&d[i]);
    }
    plastic[p] = is_plastic;
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
) -> PyResult<Integrated<'py>> {
    let (materials, start, strains) = (materials.as_array(), start.as_array(), strains.as_array());
    let n = start.nrows();
    let (m, s0, eps) = (data(&materials, "materials")?, data(&start, "start")?, data(&strains, "strains")?);
    let mut stresses = vec![0.0; 4 * n];
    let mut tangents = vec![0.0; 9 * n];
    let mut plastic = vec![false; n];
    let mut failed = -1i64;
    for p in 0..n {
        let strain = [eps[3 * p], eps[3 * p + 1], eps[3 * p + 2]];
        match integrate_point(&m[6 * p..6 * p + 6], stress_at(s0, p), strain) {
            Ok((s, is_plastic, d)) => store(p, s, &d, is_plastic, &mut stresses, &mut tangents, &mut plastic),
            Err(()) => {
                failed = p as i64;
                break;
            }
        }
    }
    Ok((
        Array2::from_shape_vec((n, 4), stresses).unwrap().into_pyarray(py),
        Array1::from(plastic).into_pyarray(py),
        Array3::from_shape_vec((n, 3, 3), tangents).unwrap().into_pyarray(py),
        failed,
    ))
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
) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let (nodes, dndx, dndy, weight, stresses) =
        (nodes.as_array(), dndx.as_array(), dndy.as_array(), weight.as_array(), stresses.as_array());
    let (nd, dx, dy, w, s) = (data(&nodes, "nodes")?, data(&dndx, "dndx")?, data(&dndy, "dndy")?,
                              data(&weight, "weight")?, data(&stresses, "stresses")?);
    let mut f = vec![0.0; n_dofs];
    for p in 0..w.len() {
        let r = 6 * p..6 * p + 6;
        t6::add_internal_forces(&nd[r.clone()], &dx[r.clone()], &dy[r], w[p], stress_at(s, p), &mut f);
    }
    Ok(Array1::from(f).into_pyarray(py))
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
) -> PyResult<Updated<'py>> {
    let (nodes, dndx, dndy, weight) = (nodes.as_array(), dndx.as_array(), dndy.as_array(), weight.as_array());
    let (materials, start, du) = (materials.as_array(), start.as_array(), du.as_array());
    let (nd, dx, dy, w) = (data(&nodes, "nodes")?, data(&dndx, "dndx")?, data(&dndy, "dndy")?, data(&weight, "weight")?);
    let (m, s0, du) = (data(&materials, "materials")?, data(&start, "start")?, data(&du, "du")?);
    let n = w.len();
    let mut stresses = vec![0.0; 4 * n];
    let mut tangents = vec![0.0; 9 * n];
    let mut plastic = vec![false; n];
    let mut stiffness = vec![0.0; 144 * n];
    let mut f = vec![0.0; du.len()];
    let mut failed = -1i64;
    for p in 0..n {
        let r = 6 * p..6 * p + 6;
        let (pn, px, py_) = (&nd[r.clone()], &dx[r.clone()], &dy[r]);
        let eps = t6::strain(pn, px, py_, du);
        let (s, is_plastic, d) = match integrate_point(&m[6 * p..6 * p + 6], stress_at(s0, p), eps) {
            Ok(result) => result,
            Err(()) => {
                failed = p as i64;
                break;
            }
        };
        store(p, s, &d, is_plastic, &mut stresses, &mut tangents, &mut plastic);
        t6::add_internal_forces(pn, px, py_, w[p], s, &mut f);
        t6::point_stiffness(px, py_, w[p], &d, &mut stiffness[144 * p..144 * p + 144]);
    }
    Ok((
        Array2::from_shape_vec((n, 4), stresses).unwrap().into_pyarray(py),
        Array1::from(f).into_pyarray(py),
        Array1::from(plastic).into_pyarray(py),
        Array3::from_shape_vec((n, 3, 3), tangents).unwrap().into_pyarray(py),
        Array2::from_shape_vec((n, 144), stiffness).unwrap().into_pyarray(py),
        failed,
    ))
}

#[pymodule]
fn _engine(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(integrate, m)?)?;
    m.add_function(wrap_pyfunction!(internal_forces, m)?)?;
    m.add_function(wrap_pyfunction!(update, m)?)?;
    Ok(())
}
