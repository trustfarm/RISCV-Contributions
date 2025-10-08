# falcon_validate/metrics_module.py
# Error metrics and evaluation utilities

from __future__ import annotations
import numpy as np

# --- REPLACE: mse(...) to handle complex safely ---
def mse(a, b):
    a = np.asarray(a); b = np.asarray(b)
    diff = a - b
    if np.iscomplexobj(diff):
        return float(np.mean(np.abs(diff) ** 2))
    return float(np.mean(diff ** 2))
# --------------------------------------------------

# --- ADD: histogram KS utility (empirical) ---
def ks_from_hist(hist_a, hist_b):
    a = np.cumsum(np.asarray(hist_a, dtype=np.float64))
    b = np.cumsum(np.asarray(hist_b, dtype=np.float64))
    a /= a[-1] if a[-1] != 0 else 1.0
    b /= b[-1] if b[-1] != 0 else 1.0
    return float(np.max(np.abs(a - b)))
# ---------------------------------------------

# AFTER (정상화: ref = b)
def relative_L2(a, ref):
    a = np.asarray(a); ref = np.asarray(ref)
    num = np.linalg.norm(a - ref)
    den = np.linalg.norm(ref)
    return float(num / den if den != 0 else float("inf"))

def compute_fft_errors(fp64, fp128, qx):
    return {
        "fft64_mse": mse(fp64, fp128),
        "fft64_relL2": relative_L2(fp64, fp128),
        "fftq_mse": mse(qx, fp128),
        "fftq_relL2": relative_L2(qx, fp128),
    }

# --- UPDATE: compute_hist_errors(...) to return KS too ---
def compute_hist_errors(mp_pmf, f_pmf, q_pmf, hist_fp64, hist_qx):
    return {
        "disc_pmf_l2_fp64": float(np.sum((np.array(mp_pmf) - np.array(f_pmf)) ** 2)),
        "disc_hist_mse_fp64": float(np.mean(hist_fp64 ** 2)),
        "disc_hist_mse_qx": float(np.mean(hist_qx ** 2)),
        "disc_hist_ks_qx": ks_from_hist(hist_fp64, hist_qx),
    }
# ---------------------------------------------------------

def compute_continuous_errors(fp64, fp128, qx):
    return {
        "cont64_mse": mse(fp64, fp128),
        "contqx_mse": mse(qx, fp128),
    }

