# falcon_validate/fft_module.py
# Falcon-style FFT implementation (FP64, FP128 baseline, and Q-format fixed-point)

from __future__ import annotations
import math
import numpy as np
import mpmath as mp
from .qformat_module import QCtx, Qc


def bit_reverse_indices(n: int) -> np.ndarray:
    """Generate bit-reversed indices for FFT of length n"""
    bits = n.bit_length() - 1
    br = np.arange(n, dtype=np.uint32)
    br = ((br & 0x55555555) << 1) | ((br & 0xAAAAAAAA) >> 1)
    br = ((br & 0x33333333) << 2) | ((br & 0xCCCCCCCC) >> 2)
    br = ((br & 0x0F0F0F0F) << 4) | ((br & 0xF0F0F0F0) >> 4)
    br = ((br & 0x00FF00FF) << 8) | ((br & 0xFF00FF00) >> 8)
    br = (br << 16) | (br >> 16)
    br >>= (32 - bits)
    return br.astype(int)


def normalize_to_unit(q: QCtx, re: int, im: int) -> Qc:
    """Normalize Q-complex twiddle to unit magnitude"""
    rr = (re * re + im * im) / float(q.QONE * q.QONE)
    if rr <= 0.0:
        return Qc(q.QONE, 0)
    inv = 1.0 / math.sqrt(rr)
    re_f = inv * (re / float(q.QONE))
    im_f = inv * (im / float(q.QONE))
    return Qc(q.from_f(re_f), q.from_f(im_f))


def twiddles_q(n: int, q: QCtx):
    """Generate Falcon FFT twiddle factors in Q-format"""
    stages = []
    m = 1
    while (1 << m) <= n:
        M = 1 << m
        half = M >> 1
        stage = []
        for k in range(half):
            angle = -2.0 * math.pi * k / M
            c = math.cos(angle)
            s = math.sin(angle)
            z = normalize_to_unit(q, q.from_f(c), q.from_f(s))
            stage.append(z)
        stages.append(stage)
        m += 1
    return stages


def q_cadd(q: QCtx, a: Qc, b: Qc) -> Qc:
    return Qc(q.add(a.re, b.re), q.add(a.im, b.im))


def q_csub(q: QCtx, a: Qc, b: Qc) -> Qc:
    return Qc(q.sub(a.re, b.re), q.sub(a.im, b.im))


def q_cmul(q: QCtx, a: Qc, b: Qc) -> Qc:
    re = q.sub(q.mul(a.re, b.re), q.mul(a.im, b.im))
    im = q.add(q.mul(a.re, b.im), q.mul(a.im, b.re))
    return Qc(re, im)


def q_cshr_round(q: QCtx, a: Qc, s: int) -> Qc:
    return Qc(q.shr_round(a.re, s), q.shr_round(a.im, s))


def fft_q(x_list: list[Qc], q: QCtx):
    """Falcon-style radix-2 FFT in Q-format"""
    n = len(x_list)
    br = bit_reverse_indices(n)
    a = [x_list[i] for i in br]
    tw = twiddles_q(n, q)
    stages = len(tw)
    step = 1
    for stage in range(stages):
        M = step << 1
        half = step
        W = tw[stage]
        for k in range(0, n, M):
            for j in range(half):
                t = q_cmul(q, W[j], a[k + j + half])
                u = a[k + j]
                a[k + j] = q_cshr_round(q, q_cadd(q, u, t), 1)
                a[k + j + half] = q_cshr_round(q, q_csub(q, u, t), 1)
        step = M
    # rescale back
    for i in range(n):
        re = a[i].re << stages
        im = a[i].im << stages
        re = min(max(re, q.QMIN), q.QMAX)
        im = min(max(im, q.QMIN), q.QMAX)
        a[i] = Qc(re, im)
    return a, stages


def to_qc_array(x: np.ndarray, q: QCtx) -> list[Qc]:
    return [Qc(q.from_f(float(np.real(z))), q.from_f(float(np.imag(z)))) for z in x]


def to_complex128(a: list[Qc], q: QCtx) -> np.ndarray:
    return np.array([q.to_f(z.re) + 1j * q.to_f(z.im) for z in a], dtype=np.complex128)


def mp_fft(x_list, dps: int = 60):
    """High-precision mpmath FFT baseline"""
    mp.mp.dps = dps
    x = [mp.mpc(complex(z)) for z in x_list]
    n = len(x)
    bits = n.bit_length() - 1
    rev = [int('{:0{w}b}'.format(i, w=bits)[::-1], 2) for i in range(n)]
    a = [x[rev[i]] for i in range(n)]
    m = 1
    stage = 0
    while m < n:
        M = m * 2
        for k in range(0, n, M):
            for j in range(m):
                angle = -2 * mp.pi * j / M
                w = mp.e ** (mp.j * angle)
                t = w * a[k + j + m]
                u = a[k + j]
                a[k + j] = (u + t) / 2
                a[k + j + m] = (u - t) / 2
        m = M
        stage += 1
    for i in range(n):
        a[i] = a[i] * (2 ** stage)
    return a
