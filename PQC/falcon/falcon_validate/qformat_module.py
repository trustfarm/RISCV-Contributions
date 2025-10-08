# falcon_validate/qformat_module.py
# Q-format fixed-point arithmetic utilities for Falcon validation

from __future__ import annotations

class QCtx:
    """Q-format context: manages bit-width and scaling."""
    def __init__(self, I_bits: int):
        assert 1 <= I_bits <= 63, "I_bits must be between 1 and 63"
        self.I = I_bits
        self.F = 64 - I_bits
        self.QONE = 1 << self.F
        self.QMAX = (1 << 63) - 1
        self.QMIN = -(1 << 63)

    def from_f(self, x: float) -> int:
        y = int(round(x * self.QONE))
        return min(max(y, self.QMIN), self.QMAX)

    def to_f(self, q: int) -> float:
        return float(q) / self.QONE

    def add(self, a: int, b: int) -> int:
        z = a + b
        return min(max(z, self.QMIN), self.QMAX)

    def sub(self, a: int, b: int) -> int:
        z = a - b
        return min(max(z, self.QMIN), self.QMAX)

    def mul(self, a: int, b: int) -> int:
        """Q-multiplication with rounding"""
        prod = a * b
        prod += (1 << (self.F - 1)) if prod >= 0 else -(1 << (self.F - 1))
        z = prod >> self.F
        return min(max(z, self.QMIN), self.QMAX)

    def shr_round(self, x: int, s: int) -> int:
        if s <= 0:
            y = x << (-s)
        else:
            add = 1 << (s - 1)
            y = (x + add) >> s if x >= 0 else (x - add) >> s
        return min(max(y, self.QMIN), self.QMAX)


class Qc:
    """Complex number with Q-format components"""
    def __init__(self, re: int, im: int):
        self.re = re
        self.im = im

    def __repr__(self):
        return f"Qc(re={self.re}, im={self.im})"
