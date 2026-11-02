// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
//! What a triangle of k nodes (k = 3 or 6, one kind per model; spec 002, T4)
//! needs per integration point, from the derivatives of its shape functions:
//! the twin of IntegrationPoint.strain, internal_forces, point_stiffness and
//! _axisymmetric_point_stiffness of ogr_fem2d/engine/reference/solver.py,
//! with the same order of operations.
//!
//! The B matrix (Zienkiewicz and Taylor 2000, Eqs. 2.2-2.4): row eps_x has
//! dN_a/dx under u_a, row eps_y has dN_a/dy under v_a, row gamma_xy has both.
//! In axisymmetry (spec 002, T5; Eqs. 5.5-5.6) x is the radius, y the axis,
//! and B has one more row, eps_theta = u / r, with N_a / r under u_a: the
//! points then bring `n_over_r`, and their weight already includes 2 pi r.

/// B u at one point, with u two values per node. In plane strain
/// (eps_x, eps_y, gamma_xy, 0), of which the first three count; in
/// axisymmetry (eps_r, eps_z, eps_theta, gamma_rz).
pub fn strain(nodes: &[i64], dndx: &[f64], dndy: &[f64], n_over_r: Option<&[f64]>, du: &[f64]) -> [f64; 4] {
    let (mut ex, mut ey, mut gxy) = (0.0, 0.0, 0.0);
    for a in 0..nodes.len() {
        let n = nodes[a] as usize;
        let (ux, uy) = (du[2 * n], du[2 * n + 1]);
        ex += dndx[a] * ux;
        ey += dndy[a] * uy;
        gxy += dndy[a] * ux + dndx[a] * uy;
    }
    match n_over_r {
        None => [ex, ey, gxy, 0.0],
        Some(nr) => {
            let mut et = 0.0;
            for a in 0..nodes.len() {
                et += nr[a] * du[2 * nodes[a] as usize];
            }
            [ex, ey, et, gxy]
        }
    }
}

/// Adds weight B^T sigma of one point into `f` (Eq. 4.65). sigma_zz does no
/// work in plane strain; in axisymmetry it is the hoop stress and adds
/// N_a / r sigma_theta to the radial force of node a (Eq. 5.6).
pub fn add_internal_forces(
    nodes: &[i64],
    dndx: &[f64],
    dndy: &[f64],
    n_over_r: Option<&[f64]>,
    weight: f64,
    stress: [f64; 4],
    f: &mut [f64],
) {
    let (s_xx, s_yy, s_zz, t_xy) = (stress[0], stress[1], stress[2], stress[3]);
    for a in 0..nodes.len() {
        let n = nodes[a] as usize;
        // the two rows of B^T for node n: (dx, 0, dy) and (0, dy, dx)
        f[2 * n] += weight * (dndx[a] * s_xx + dndy[a] * t_xy);
        f[2 * n + 1] += weight * (dndy[a] * s_yy + dndx[a] * t_xy);
    }
    if let Some(nr) = n_over_r {
        for a in 0..nodes.len() {
            f[2 * nodes[a] as usize] += weight * nr[a] * s_zz;
        }
    }
}

/// weight B^T D B of one point in plane strain (Eq. 4.80), 2k x 2k
/// row-major in the dofs (u1, v1, ..., uk, vk): block (a, b) is
/// B_a^T D B_b. D is (eps_x, eps_y, gamma_xy): its first three rows and
/// columns.
pub fn point_stiffness(dndx: &[f64], dndy: &[f64], weight: f64, d: &[[f64; 4]; 4], k: &mut [f64]) {
    let m = 2 * dndx.len();
    for a in 0..dndx.len() {
        let (ax, ay) = (dndx[a], dndy[a]);
        // B_a^T rows: u_a -> (ax, 0, ay), v_a -> (0, ay, ax)
        let rows = [(2 * a, [ax, 0.0, ay]), (2 * a + 1, [0.0, ay, ax])];
        for (ra, c) in rows {
            for b in 0..dndx.len() {
                let (bx, by) = (dndx[b], dndy[b]);
                // D B_b, the columns for u_b and v_b
                let dbu = [d[0][0] * bx + d[0][2] * by, d[1][0] * bx + d[1][2] * by, d[2][0] * bx + d[2][2] * by];
                let dbv = [d[0][1] * by + d[0][2] * bx, d[1][1] * by + d[1][2] * bx, d[2][1] * by + d[2][2] * bx];
                k[m * ra + 2 * b] = weight * (c[0] * dbu[0] + c[1] * dbu[1] + c[2] * dbu[2]);
                k[m * ra + 2 * b + 1] = weight * (c[0] * dbv[0] + c[1] * dbv[1] + c[2] * dbv[2]);
            }
        }
    }
}

/// weight B^T D B of one point in axisymmetry, D 4 x 4 on (eps_r, eps_z,
/// eps_theta, gamma_rz): the column of B for u_a is (dN_a/dr, 0, N_a/r,
/// dN_a/dz) and for v_a (0, dN_a/dz, 0, dN_a/dr) (Eq. 5.6). Same layout as
/// point_stiffness.
pub fn axisymmetric_point_stiffness(
    dndx: &[f64],
    dndy: &[f64],
    n_over_r: &[f64],
    weight: f64,
    d: &[[f64; 4]; 4],
    k: &mut [f64],
) {
    let m = 2 * dndx.len();
    let column = |i: usize| -> [f64; 4] {
        let a = i / 2;
        if i % 2 == 0 {
            [dndx[a], 0.0, n_over_r[a], dndy[a]]
        } else {
            [0.0, dndy[a], 0.0, dndx[a]]
        }
    };
    for i in 0..m {
        let bi = column(i);
        for j in 0..m {
            let bj = column(j);
            let mut dbj = [0.0; 4];
            for r in 0..4 {
                for c in 0..4 {
                    dbj[r] += d[r][c] * bj[c];
                }
            }
            let mut s = 0.0;
            for r in 0..4 {
                s += bi[r] * dbj[r];
            }
            k[m * i + j] = weight * s;
        }
    }
}
