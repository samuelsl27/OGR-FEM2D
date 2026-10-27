// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
//! Perfectly plastic Mohr-Coulomb in plane strain: the twin of
//! ogr_fem2d/engine/reference/mohr_coulomb.py, function by function and with
//! the same names, so that the two can be read side by side (spec 001, T16).
//!
//! Source: de Souza Neto, E. A., Perić, D. and Owen, D. R. J. (2008).
//! *Computational Methods for Plasticity*, Wiley, §8.2, pp. 295-324:
//!
//! * yield function of the main plane, sigma_1 >= sigma_2 >= sigma_3, tension
//!   positive (p. 297): Phi = s1 - s3 + (s1 + s3) sin(phi) - 2 c cos(phi);
//! * non-associative flow vectors with the dilatancy psi (Eqs. 8.54-8.59):
//!   N1 main plane, N6 right edge, N2 left edge;
//! * principal stress update, Eq. (8.68);
//! * the selection of Box 8.4: main plane, then the edge chosen by
//!   (1 - sin psi) s1 - 2 s2 + (1 + sin psi) s3 >= 0 -> right (SUMC, line
//!   97), then the apex, Eq. (8.81), refused with psi = 0 (p. 300);
//! * perfect plasticity: every return in closed form (Remark 8.1);
//! * the consistent tangent, §8.2.4 and Appendix A.3 (CTMC, DGISO2): the
//!   derivatives P of the updated principal stresses with respect to the
//!   trial ones, constant in each region, and the rotation term of the
//!   in-plane pair.
//!
//! Each return is built from Eq. (8.68) and the flow vectors, not copied
//! from the boxes (the text of Box 8.6 has dgamma_b where Eq. (8.78) has
//! dgamma_a for sigma_1 at the left edge).

/// Relative tolerance of the yield check and of the sextant check: about a
/// thousand ulps of the stress scale (the reference's TOLERANCE).
pub const TOLERANCE: f64 = 1e-12;

/// Material: E, nu, cohesion c, friction phi and dilatancy psi (radians).
#[derive(Clone, Copy, Debug)]
pub struct MohrCoulomb {
    pub young: f64,
    pub poisson: f64,
    pub cohesion: f64,
    pub phi: f64,
    pub psi: f64,
}

/// The region a return lands in.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Region {
    Elastic,
    Plane,
    RightEdge,
    LeftEdge,
    Apex,
}

/// The return to the apex with psi = 0 has no solution (p. 300).
#[derive(Debug)]
pub struct ReturnMappingError;

/// Result of one stress update at one integration point.
pub struct Update {
    pub stress: [f64; 4],
    pub region: Region,
    /// d sigma / d eps on (xx, yy, xy), consistent with this update.
    pub tangent: [[f64; 3]; 3],
}

impl MohrCoulomb {
    pub fn shear_modulus(&self) -> f64 {
        self.young / (2.0 * (1.0 + self.poisson))
    }

    pub fn bulk_modulus(&self) -> f64 {
        self.young / (3.0 * (1.0 - 2.0 * self.poisson))
    }
}

/// In-plane principal stresses (larger, smaller) and the angle theta of the
/// larger one from the x axis.
pub fn principal_in_plane(s_xx: f64, s_yy: f64, t_xy: f64) -> (f64, f64, f64) {
    let centre = 0.5 * (s_xx + s_yy);
    let radius = (0.5 * (s_xx - s_yy)).hypot(t_xy);
    let theta = 0.5 * (2.0 * t_xy).atan2(s_xx - s_yy);
    (centre + radius, centre - radius, theta)
}

/// Phi of the main plane for sigma_1 >= sigma_3 (p. 297).
pub fn yield_function(m: &MohrCoulomb, s1: f64, s3: f64) -> f64 {
    s1 - s3 + (s1 + s3) * m.phi.sin() - 2.0 * m.cohesion * m.phi.cos()
}

/// 2G [N_dev]_j + K tr N for a flow vector given by its principal values:
/// the term of Eq. (8.68) that multiplies dgamma.
fn stress_change(m: &MohrCoulomb, flow: [f64; 3]) -> [f64; 3] {
    let (g, k) = (m.shear_modulus(), m.bulk_modulus());
    let trace = flow[0] + flow[1] + flow[2];
    let mut out = [0.0; 3];
    for j in 0..3 {
        out[j] = 2.0 * g * (flow[j] - trace / 3.0) + k * trace;
    }
    out
}

/// The flow vectors N1, N6 and N2 by their principal values.
fn flows(m: &MohrCoulomb) -> ([f64; 3], [f64; 3], [f64; 3]) {
    let sp = m.psi.sin();
    (
        [1.0 + sp, 0.0, -(1.0 - sp)],  // N1, main plane
        [1.0 + sp, -(1.0 - sp), 0.0],  // N6, right edge
        [0.0, 1.0 + sp, -(1.0 - sp)],  // N2, left edge
    )
}

fn in_order(s: [f64; 3]) -> bool {
    let largest = s[0].abs().max(s[1].abs()).max(s[2].abs());
    let delta = TOLERANCE * largest.max(1.0);
    s[0] + delta >= s[1] && s[1] + delta >= s[2]
}

fn dot(u: [f64; 3], v: [f64; 3]) -> f64 {
    u[0] * v[0] + u[1] * v[1] + u[2] * v[2]
}

/// Return mapping of principal trial stresses ordered s1 >= s2 >= s3, Box
/// 8.4, steps (iii) and (iv): the updated principal stresses and the region.
pub fn return_principal(
    m: &MohrCoulomb,
    trial: [f64; 3],
) -> Result<([f64; 3], Region), ReturnMappingError> {
    let [s1, s2, s3] = trial;
    let largest = trial[0].abs().max(trial[1].abs()).max(trial[2].abs());
    let scale = m.cohesion.abs().max(largest).max(1.0);
    let phi_trial = yield_function(m, s1, s3);
    if phi_trial <= TOLERANCE * scale {
        return Ok((trial, Region::Elastic));
    }

    let sf = m.phi.sin();
    let two_c_cos = 2.0 * m.cohesion * m.phi.cos();
    let (n1, n6, n2) = flows(m);
    let d1 = stress_change(m, n1);

    // (iv.a) main plane: Phi(trial) - a dgamma = 0, a = Eq. (8.72)
    let a = (d1[0] - d1[2]) + (d1[0] + d1[2]) * sf;
    let dg = phi_trial / a;
    let plane = [trial[0] - dg * d1[0], trial[1] - dg * d1[1], trial[2] - dg * d1[2]];
    if in_order(plane) {
        return Ok((plane, Region::Plane));
    }

    // (iv.c) edge: SUMC, p. 311, line 97
    let sp = m.psi.sin();
    let right = (1.0 - sp) * s1 - 2.0 * s2 + (1.0 + sp) * s3 >= 0.0;
    let (db, phi_b, row_a, row_b);
    if right {
        db = stress_change(m, n6);
        // Phi_b of the plane on the right: sigma_1 - sigma_2 form
        phi_b = s1 - s2 + (s1 + s2) * sf - two_c_cos;
        row_a = ((d1[0] - d1[2]) + (d1[0] + d1[2]) * sf, (db[0] - db[2]) + (db[0] + db[2]) * sf);
        row_b = ((d1[0] - d1[1]) + (d1[0] + d1[1]) * sf, (db[0] - db[1]) + (db[0] + db[1]) * sf);
    } else {
        db = stress_change(m, n2);
        // Phi_b of the plane on the left: sigma_2 - sigma_3 form
        phi_b = s2 - s3 + (s2 + s3) * sf - two_c_cos;
        row_a = ((d1[0] - d1[2]) + (d1[0] + d1[2]) * sf, (db[0] - db[2]) + (db[0] + db[2]) * sf);
        row_b = ((d1[1] - d1[2]) + (d1[1] + d1[2]) * sf, (db[1] - db[2]) + (db[1] + db[2]) * sf);
    }
    // Two linear equations: Phi_k(trial) - row_k . (dgamma_a, dgamma_b) = 0
    let det = row_a.0 * row_b.1 - row_a.1 * row_b.0;
    let dga = (phi_trial * row_b.1 - row_a.1 * phi_b) / det;
    let dgb = (row_a.0 * phi_b - row_b.0 * phi_trial) / det;
    let mut edge = [0.0; 3];
    for j in 0..3 {
        edge[j] = trial[j] - dga * d1[j] - dgb * db[j];
    }
    if in_order(edge) {
        return Ok((edge, if right { Region::RightEdge } else { Region::LeftEdge }));
    }

    // (iv.e) apex
    if m.psi.sin() == 0.0 || m.phi.sin() == 0.0 {
        return Err(ReturnMappingError);
    }
    let p = m.cohesion / m.phi.tan(); // Eq. (8.81)
    Ok(([p, p, p], Region::Apex))
}

/// P[i][j] = d sigma_i / d sigma_trial_j for the return of `region`, in the
/// sorted order (Eqs. 8.93-8.94 with H = 0; the edges; Remark 8.3).
pub fn principal_derivatives(m: &MohrCoulomb, region: Region) -> [[f64; 3]; 3] {
    let identity = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]];
    let zero = [[0.0; 3]; 3];
    let sf = m.phi.sin();
    let (n1, n6, n2) = flows(m);
    let d1 = stress_change(m, n1);
    let ga = [1.0 + sf, 0.0, -(1.0 - sf)]; // gradient of the main plane
    match region {
        Region::Elastic => identity,
        Region::Apex => zero,
        Region::Plane => {
            let a = dot(ga, d1); // = Eq. (8.72)
            let mut p = identity;
            for i in 0..3 {
                for j in 0..3 {
                    p[i][j] -= d1[i] * ga[j] / a;
                }
            }
            p
        }
        Region::RightEdge | Region::LeftEdge => {
            let (db, gb) = if region == Region::RightEdge {
                (stress_change(m, n6), [1.0 + sf, -(1.0 - sf), 0.0]) // sigma_1 - sigma_2
            } else {
                (stress_change(m, n2), [0.0, 1.0 + sf, -(1.0 - sf)]) // sigma_2 - sigma_3
            };
            let r = [[dot(ga, d1), dot(ga, db)], [dot(gb, d1), dot(gb, db)]];
            let det = r[0][0] * r[1][1] - r[0][1] * r[1][0];
            let inv = [[r[1][1] / det, -r[0][1] / det], [-r[1][0] / det, r[0][0] / det]];
            let mut p = identity;
            for i in 0..3 {
                for j in 0..3 {
                    // d dgamma_a / d trial_j and d dgamma_b / d trial_j
                    let dga = inv[0][0] * ga[j] + inv[0][1] * gb[j];
                    let dgb = inv[1][0] * ga[j] + inv[1][1] * gb[j];
                    p[i][j] -= d1[i] * dga + db[i] * dgb;
                }
            }
            p
        }
    }
}

/// Assemble d sigma / d eps on (xx, yy, xy) from the principal derivatives:
/// Appendix A, Box A.3 and Eqs. (A.28)-(A.33), for the in-plane pair (hi, lo)
/// at sorted positions `h` and `l`.
fn tangent(
    m: &MohrCoulomb,
    h: usize,
    l: usize,
    trial: [f64; 3],
    returned: [f64; 3],
    region: Region,
    theta: f64,
) -> [[f64; 3]; 3] {
    let (g, k) = (m.shear_modulus(), m.bulk_modulus());
    let lam = k - 2.0 * g / 3.0;
    let p = principal_derivatives(m, region);
    let de = |i: usize, j: usize| lam + if i == j { 2.0 * g } else { 0.0 };
    // (P De)[i][j], j in-plane
    let c = |i: usize, j: usize| (0..3).map(|q| p[i][q] * de(q, j)).sum::<f64>();
    let (c_hh, c_hl, c_lh, c_ll) = (c(h, h), c(h, l), c(l, h), c(l, l));
    let gap = trial[h] - trial[l];
    let shear = if gap.abs() > TOLERANCE * trial[h].abs().max(trial[l].abs()).max(1.0) {
        g * (returned[h] - returned[l]) / gap // (A.28)
    } else {
        g * (p[h][h] - p[h][l]) // (A.30)
    };
    let (cs, sn) = (theta.cos(), theta.sin());
    let a = [
        [cs * cs, sn * sn, -2.0 * sn * cs],
        [sn * sn, cs * cs, 2.0 * sn * cs],
        [sn * cs, -sn * cs, cs * cs - sn * sn],
    ];
    let cp = [[c_hh, c_hl, 0.0], [c_lh, c_ll, 0.0], [0.0, 0.0, shear]];
    // D = A C A^T
    let mut ac = [[0.0; 3]; 3];
    for i in 0..3 {
        for j in 0..3 {
            ac[i][j] = (0..3).map(|q| a[i][q] * cp[q][j]).sum();
        }
    }
    let mut d = [[0.0; 3]; 3];
    for i in 0..3 {
        for j in 0..3 {
            d[i][j] = (0..3).map(|q| ac[i][q] * a[j][q]).sum();
        }
    }
    d
}

/// Box 8.4: elastic predictor, spectral decomposition, return, assembly,
/// and the consistent tangent of this update. `stress` is (sigma_xx,
/// sigma_yy, sigma_zz, tau_xy) at the start of the increment and
/// `strain_increment` (d_eps_xx, d_eps_yy, d_gamma_xy), with d_eps_zz = 0.
pub fn update(
    m: &MohrCoulomb,
    stress: [f64; 4],
    strain_increment: [f64; 3],
) -> Result<Update, ReturnMappingError> {
    let d = crate::elastic::stress_increment(m.young, m.poisson, strain_increment);
    let (t_xx, t_yy, t_zz, t_xy) = (stress[0] + d[0], stress[1] + d[1], stress[2] + d[2], stress[3] + d[3]);
    // (ii) spectral decomposition: two in-plane principal stresses and zz,
    // named 0 = hi, 1 = lo, 2 = zz, sorted descending (stable, as Python's)
    let (p_hi, p_lo, theta) = principal_in_plane(t_xx, t_yy, t_xy);
    let named = [p_hi, p_lo, t_zz];
    let mut order = [0usize, 1, 2];
    order.sort_by(|&a, &b| named[b].partial_cmp(&named[a]).unwrap());
    let trial = [named[order[0]], named[order[1]], named[order[2]]];
    let (returned, region) = return_principal(m, trial)?;
    let h = order.iter().position(|&n| n == 0).unwrap();
    let l = order.iter().position(|&n| n == 1).unwrap();
    let tangent = tangent(m, h, l, trial, returned, region, theta);
    if region == Region::Elastic {
        return Ok(Update { stress: [t_xx, t_yy, t_zz, t_xy], region, tangent });
    }
    // (v) assembly: sigma = sum sigma_i e_i x e_i, same directions
    let mut new = [0.0; 3];
    for (k, &n) in order.iter().enumerate() {
        new[n] = returned[k];
    }
    let (c, s) = (theta.cos(), theta.sin());
    let (hi, lo) = (new[0], new[1]);
    Ok(Update {
        stress: [hi * c * c + lo * s * s, hi * s * s + lo * c * c, new[2], (hi - lo) * s * c],
        region,
        tangent,
    })
}
