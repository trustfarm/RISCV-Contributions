# falcon_validate/gaussian_module.py
# Continuous and discrete Gaussian generation and metrics

from __future__ import annotations
import numpy as np
import math
import mpmath as mp
from .qformat_module import QCtx


def box_muller_from_uniforms_np(u1, u2):
    r = np.sqrt(-2.0 * np.log(u1))
    theta = 2.0 * np.pi * u2
    z0 = r * np.cos(theta)
    z1 = r * np.sin(theta)
    return z0, z1


def box_muller_from_uniforms_mp(u1_list, u2_list, dps=60):
    mp.mp.dps = dps
    out = []
    for u1, u2 in zip(u1_list, u2_list):
        u1m = mp.mpf(str(u1))
        if u1m == 0:
            u1m = mp.mpf("1e-60")
        u2m = mp.mpf(str(u2))
        r = mp.sqrt(-2 * mp.log(u1m))
        theta = 2 * mp.pi * u2m
        z0 = r * mp.cos(theta)
        z1 = r * mp.sin(theta)
        out.append((float(z0), float(z1)))
    return out


def box_muller_qx(u1: float, u2: float, q: QCtx):
    """Box-Muller transform with staged Q-format rounding"""
    ln_u1 = math.log(max(u1, 1e-300))
    val = -2.0 * ln_u1
    qv = q.from_f(val)
    r = math.sqrt(max(q.to_f(qv), 0.0))
    rq = q.to_f(q.from_f(r))
    theta = 2.0 * math.pi * u2
    tq = q.to_f(q.from_f(theta))
    c = math.cos(tq)
    s = math.sin(tq)
    cq = q.to_f(q.from_f(c))
    sq = q.to_f(q.from_f(s))
    return rq * cq, rq * sq


def discrete_gaussian_pmf_mp(k_max, sigma, mp_dps=60):
    mp.mp.dps = mp_dps
    two = mp.mpf(2)
    s2 = mp.mpf(sigma) ** 2
    vals = [mp.e ** (-mp.mpf(k * k) / (two * s2)) for k in range(-k_max, k_max + 1)]
    Z = mp.fsum(vals)
    pmf = [v / Z for v in vals]
    return pmf


def discrete_gaussian_pmf_float(k_max, sigma):
    ks = np.arange(-k_max, k_max + 1, dtype=np.float64)
    vals = np.exp(-(ks ** 2) / (2.0 * (sigma ** 2)))
    Z = np.sum(vals)
    return (vals / Z).tolist()


def pmf_to_cdf(pmf):
    s = 0.0
    out = []
    for p in pmf:
        s += p
        out.append(s)
    out[-1] = 1.0
    return out


def ks_distance_discrete(cdf_p, cdf_q):
    return float(np.max(np.abs(np.array(cdf_p) - np.array(cdf_q))))


def wasserstein1_discrete(pmf_p, pmf_q):
    cdf_p = np.cumsum(pmf_p)
    cdf_q = np.cumsum(pmf_q)
    return float(np.sum(np.abs(cdf_p - cdf_q)))
