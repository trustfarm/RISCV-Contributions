# falcon_validate/sampler_module.py
# Falcon-style discrete Gaussian samplers

# --- ADD/UPDATE: imports ---
import numpy as np
import math
from time import perf_counter_ns
from .qformat_module import QCtx
from .gaussian_module import box_muller_qx
# ---------------------------

# --- ADD: Alias Table utilities ---
def build_alias_table(pmf):
    p = np.array(pmf, dtype=np.float64)
    p = p / p.sum()
    n = len(p)
    q = p * n
    prob = np.zeros(n, dtype=np.float64)
    alias = np.zeros(n, dtype=np.int32)
    small = [i for i,v in enumerate(q) if v < 1.0]
    large = [i for i,v in enumerate(q) if v >= 1.0]
    while small and large:
        s = small.pop(); l = large.pop()
        prob[s] = q[s]
        alias[s] = l
        q[l] = (q[l] + q[s]) - 1.0
        (small if q[l] < 1.0 else large).append(l)
    for i in large + small:
        prob[i] = 1.0
        alias[i] = i
    return prob, alias

def sample_discrete_alias(prob, alias, rng):
    n = len(prob)
    i = int(rng.integers(0, n))
    u = rng.random()
    return i if u < prob[i] else alias[i]
# ---------------------------------

def sample_discrete_cdt(pmf, rng):
    cdf = np.cumsum(np.array(pmf, dtype=np.float64))
    u = rng.random()
    idx = int(np.searchsorted(cdf, u, side="right"))
    return idx


def sample_discrete_knuth_yao(pmf, rng, bits=24):
    cdf = np.cumsum(np.array(pmf, dtype=np.float64))
    u = 0.0
    for i in range(bits):
        u += rng.integers(0, 2) / (2 ** (i + 1))
    idx = int(np.searchsorted(cdf, u, side="right"))
    return idx


def sample_discrete_rejection(sigma, k_max, rng):
    for _ in range(10000):
        x = rng.normal(0.0, sigma)
        k = int(round(x))
        if abs(k) > k_max:
            continue
        acc = math.exp(-(k * k - x * x) / (2 * sigma * sigma))
        if rng.random() <= acc:
            return k + k_max
    return k_max


def sample_discrete_variants(pmf_mp, sigma, k_max, n, variant, seed=0):
    rng = np.random.default_rng(seed)
    idxs = []
    pmf_f = [float(p) for p in pmf_mp]
    for _ in range(n):
        if variant == "cdt":
            idx = sample_discrete_cdt(pmf_f, rng)
        elif variant == "knuth_yao":
            idx = sample_discrete_knuth_yao(pmf_f, rng)
        else:
            idx = sample_discrete_rejection(sigma, k_max, rng)
        idxs.append(idx)
    vals = [i - k_max for i in idxs]
    return np.array(vals, dtype=np.int32)


def sample_discrete_variants_qx(pmf_mp, sigma, k_max, n, variant, q: QCtx, seed=0):
    rng = np.random.default_rng(seed)
    pmf_f = np.array([float(p) for p in pmf_mp], dtype=np.float64)
    cdf = np.cumsum(pmf_f)
    idxs = []
    for _ in range(n):
        u = float(rng.random())
        uq = q.to_f(q.from_f(u))
        if variant in ("cdt", "knuth_yao"):
            idx = int(np.searchsorted(cdf, uq, side="right"))
        else:
            u1, u2 = float(rng.random()), float(rng.random())
            z0, _ = box_muller_qx(u1, u2, q)
            k = int(round(z0 * sigma))
            k = max(-k_max, min(k, k_max))
            idx = k + k_max
        idxs.append(idx)
    vals = [i - k_max for i in idxs]
    return np.array(vals, dtype=np.int32)


# --- ADD: Ziggurat-based discrete via rounding ---
def sample_discrete_ziggurat(sigma, k_max, rng):
    z = rng.standard_normal()        # ziggurat 기반 표준정규
    k = int(round(z * sigma))
    return max(-k_max, min(k, k_max)) + k_max
# -----------------------------------------------

# --- ADD: ExpCut tail-aware sampler ---
def sample_discrete_expcut(sigma, k_max, rng, cut_mult=2.5):
    # 중심은 표준정규, 꼬리는 exp 제안분포로 보정
    t = int(math.ceil(cut_mult * sigma))
    for _ in range(10000):
        if rng.random() < 0.8:
            # 중심: 가우시안 근사
            z = rng.normal(0.0, sigma)
            k = int(round(z))
            if abs(k) <= t and abs(k) <= k_max:
                return k + k_max
        else:
            # 꼬리: exp 제안
            lam = 1.0 / sigma
            e = rng.exponential(1.0/lam)
            k = t + int(math.floor(e))
            if k > k_max:
                continue
            # 수락확률 (target/proposal) 비율
            ratio = math.exp(-(k*k - (t*t)) / (2*sigma*sigma)) * lam
            if rng.random() < min(1.0, ratio):
                # 부호 무작위
                k = (+k if rng.integers(0,2)==0 else -k)
                return k + k_max
    return k_max
# -------------------------------------

# --- ADD: Qx variants for new samplers ---
def sample_discrete_ziggurat_qx(sigma, k_max, rng, q: QCtx):
    z = rng.standard_normal()
    zq = q.to_f(q.from_f(z))
    k = int(round(zq * sigma))
    return max(-k_max, min(k, k_max)) + k_max

def sample_discrete_alias_qx(prob, alias, rng, q: QCtx):
    # 동일 로직 (확률 비교만 double), Qx 관여는 미미함
    return sample_discrete_alias(prob, alias, rng)

def sample_discrete_expcut_qx(sigma, k_max, rng, q: QCtx, cut_mult=2.5):
    return sample_discrete_expcut(sigma, k_max, rng, cut_mult)
# -----------------------------------------

# --- UPDATE: sample_discrete_variants(...) ---
def sample_discrete_variants(pmf_mp, sigma, k_max, n, variant, seed=0):
    rng = np.random.default_rng(seed)
    idxs = []
    pmf_f = [float(p) for p in pmf_mp]
    if variant == "alias":
        prob, alias = build_alias_table(pmf_f)
    for _ in range(n):
        if variant == "cdt":
            idx = sample_discrete_cdt(pmf_f, rng)
        elif variant == "knuth_yao":
            idx = sample_discrete_knuth_yao(pmf_f, rng)
        elif variant == "rejection":
            idx = sample_discrete_rejection(sigma, k_max, rng)
        elif variant == "ziggurat":
            idx = sample_discrete_ziggurat(sigma, k_max, rng)
        elif variant == "alias":
            idx = sample_discrete_alias(prob, alias, rng)
        elif variant == "expcut":
            idx = sample_discrete_expcut(sigma, k_max, rng)
        else:
            raise ValueError(f"Unsupported sampler: {variant}")
        idxs.append(idx)
    vals = [i - k_max for i in idxs]
    return np.array(vals, dtype=np.int32)

# --- UPDATE: sample_discrete_variants_qx(...) ---
def sample_discrete_variants_qx(pmf_mp, sigma, k_max, n, variant, q: QCtx, seed=0):
    rng = np.random.default_rng(seed)
    pmf_f = np.array([float(p) for p in pmf_mp], dtype=np.float64)
    cdf = np.cumsum(pmf_f)
    idxs = []
    if variant == "alias":
        prob, alias = build_alias_table(pmf_f)
    for _ in range(n):
        if variant == "cdt":
            u = float(rng.random()); uq = q.to_f(q.from_f(u))
            idx = int(np.searchsorted(cdf, uq, side="right"))
        elif variant == "knuth_yao":
            u = float(rng.random()); uq = q.to_f(q.from_f(u))
            idx = int(np.searchsorted(cdf, uq, side="right"))
        elif variant == "rejection":
            idx = sample_discrete_rejection(sigma, k_max, rng) + 0
        elif variant == "ziggurat":
            idx = sample_discrete_ziggurat_qx(sigma, k_max, rng, q)
        elif variant == "alias":
            idx = sample_discrete_alias_qx(prob, alias, rng, q)
        elif variant == "expcut":
            idx = sample_discrete_expcut_qx(sigma, k_max, rng, q)
        else:
            raise ValueError(f"Unsupported sampler: {variant}")
        idxs.append(idx)
    vals = [i - k_max for i in idxs]
    return np.array(vals, dtype=np.int32)
# ----------------------------------------------
