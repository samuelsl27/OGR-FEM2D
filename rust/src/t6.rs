// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
//! What the six-node triangle needs per integration point, from the
//! derivatives of its shape functions: the twin of IntegrationPoint.strain,
//! internal_forces and point_stiffness of
//! ogr_fem2d/engine/reference/solver.py.
//!
//! The B matrix (Zienkiewicz and Taylor 2000, Eqs. 2.2-2.4): row eps_x has
//! dN_a/dx under u_a, row eps_y has dN_a/dy under v_a, row gamma_xy has both.

/// (eps_x, eps_y, gamma_xy) = B u at one point.
pub fn strain(nodes: &[i64], dndx: &[f64], dndy: &[f64], du: &[f64]) -> [f64; 3] {
    let (mut ex, mut ey, mut gxy) = (0.0, 0.0, 0.0);
    for a in 0..6 {
        let n = nodes[a] as usize;
        let (ux, uy) = (du[2 * n], du[2 * n + 1]);
        ex += dndx[a] * ux;
        ey += dndy[a] * uy;
        gxy += dndy[a] * ux + dndx[a] * uy;
    }
    [ex, ey, gxy]
}

/// Adds weight B^T sigma of one point into `f` (Eq. 4.65).
pub fn add_internal_forces(
    nodes: &[i64],
    dndx: &[f64],
    dndy: &[f64],
    weight: f64,
    stress: [f64; 4],
    f: &mut [f64],
) {
    let (s_xx, s_yy, t_xy) = (stress[0], stress[1], stress[3]);
    for a in 0..6 {
        let n = nodes[a] as usize;
        // the two rows of B^T for node n: (dx, 0, dy) and (0, dy, dx)
        f[2 * n] += weight * (dndx[a] * s_xx + dndy[a] * t_xy);
        f[2 * n + 1] += weight * (dndy[a] * s_yy + dndx[a] * t_xy);
    }
}

/// weight B^T D B of one point (Eq. 4.80), 12 x 12 row-major in the dofs
/// (u1, v1, ..., u6, v6): block (a, b) is B_a^T D B_b.
pub fn point_stiffness(dndx: &[f64], dndy: &[f64], weight: f64, d: &[[f64; 3]; 3], k: &mut [f64]) {
    for a in 0..6 {
        let (ax, ay) = (dndx[a], dndy[a]);
        // B_a^T rows: u_a -> (ax, 0, ay), v_a -> (0, ay, ax)
        let rows = [(2 * a, [ax, 0.0, ay]), (2 * a + 1, [0.0, ay, ax])];
        for (ra, c) in rows {
            for b in 0..6 {
                let (bx, by) = (dndx[b], dndy[b]);
                // D B_b, the columns for u_b and v_b
                let dbu = [d[0][0] * bx + d[0][2] * by, d[1][0] * bx + d[1][2] * by, d[2][0] * bx + d[2][2] * by];
                let dbv = [d[0][1] * by + d[0][2] * bx, d[1][1] * by + d[1][2] * bx, d[2][1] * by + d[2][2] * bx];
                k[12 * ra + 2 * b] = weight * (c[0] * dbu[0] + c[1] * dbu[1] + c[2] * dbu[2]);
                k[12 * ra + 2 * b + 1] = weight * (c[0] * dbv[0] + c[1] * dbv[1] + c[2] * dbv[2]);
            }
        }
    }
}
