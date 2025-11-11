# √x Approximation Methods for ASIC (v0.1)

This note summarizes practical square-root (√x) implementations for ASICs, focusing on speed/area/accuracy trade-offs and signal-processing use (FFT/OFDM magnitude, normalization, PQC/NTT scaling).

---

## 1) Lookup Table (LUT) + Linear Interpolation
**Idea.** Use top bits of *x* as index; fetch a seed `y0 ≈ sqrt(x)`; refine with linear interpolation.

- **Pros:** 1–2 cycle latency, simple control, fully combinational option.
- **Cons:** ROM area vs. precision trade-off; interpolation error must be bounded.
- **Tips:** 8–12 bit index is common (256–4096 entries). Pack entries as Q-format; optional piecewise-linear with per-segment slope.

---

## 2) Newton–Raphson (NR)
**Recurrence.**
\[ y_{k+1} = \tfrac{1}{2}\left(y_k + \frac{x}{y_k}\right) \]

- **Pros:** Quadratic convergence (2–3 iters → FP16/FP32-class); good PPA with small LUT seed.
- **Cons:** Needs divide or reciprocal. Usually done as `y = x * rsqrt(x)` or use `reciprocal(y)` macro.
- **Pipeline:** seed from LUT → 2 multipliers + 1 adder (+ optional divider/rsqrt).

**Fixed-point pseudo-code (Q16.16):**
```c
// x: Q16.16 (unsigned), returns sqrt(x) in Q16.16
uint32_t y = lut_seed(x >> 24);  // 8-bit seed in Q16.16
#pragma unroll 2
for (int i = 0; i < 2; ++i) {
    y = (y + ( (uint64_t)x / y )) >> 1;
}
return y;
```

---

## 3) Goldschmidt Iteration (for rsqrt/sqrt)
Compute `g ≈ 1/sqrt(x)` with multiply-only iteration, then `sqrt(x) = x * g`.

**Form (one variant):**
\[ g_{k+1} = 0.5\, g_k\, (3 - x\, g_k^2) \]

- **Pros:** Multiplier-centric; high throughput in FP pipelines.
- **Cons:** Requires good initial seed and careful scaling to avoid overflow.

---

## 4) Bit-by-Bit (Restoring / Non-Restoring)
Digit-by-digit algorithm similar to long division; decides one result bit per cycle.

- **Pros:** Minimal area, no ROM, no multiplier/divider.
- **Cons:** Latency ≈ number of bits (e.g., 16 cycles for 16-bit). Low throughput unless heavily interleaved.
- **Use:** Small MCUs, sensor ASICs, slow paths.

---

## 5) CORDIC (Vectoring Mode) for Magnitude
Use vectoring to get `r = sqrt(x^2 + y^2)`; shares HW with trig/log blocks.

- **Pros:** Reuses a common shift-add pipeline; good when you already need CORDIC.
- **Cons:** More cycles (N≈iterations), scaling factor compensation required.

---

## 6) Method Selection Guide

| Application | Recommended | Why |
|---|---|---|
| FFT/OFDM magnitude & normalization | **NR (2 iters)** or **Goldschmidt** | <5 cycles, error < 1e-4, easy pipeline |
| Low-power, tiny area | **Bit-by-Bit** | No ROM/MUL/DIV |
| GPU/DNN FP pipeline | **Goldschmidt** | Multiplier-only, throughput |
| Integer/PQC/NTT scaling | **LUT + Linear** | Deterministic error, simple |
| Radar/Polar (√(x²+y²)) | **CORDIC vectoring** | Shares with trig, stable |

---

## 7) Hardware Notes & Q-Format Hints
- **Normalization:** Scale `x` into [0.5, 2) by exponent adjust, compute sqrt mantissa, then correct exponent (IEEE-like).
- **Seeds:** 8–10 bit LUT is typically enough for 2 NR iterations to reach ~16–20 effective bits.
- **Fixed-point:** Keep guard bits (≥2) in multipliers; round-to-nearest-even at stage boundaries.
- **Exceptions:** Clamp denormals/zero; saturate for overflow; optional sticky flags for diagnostics.
- **Throughput:** NR/Goldschmidt map well to 2–3 stage pipelines (MUL-ADD/MAC heavy).

---

## 8) Example: rsqrt + sqrt via Goldschmidt (pseudo-C)
```c
// Compute sqrt(x) using rsqrt via Goldschmidt
// x in FP-like fixed format; assumes x normalized into [0.5, 2).
float g = lut_seed_rsqrt(x);           // initial g0 ≈ 1/sqrt(x)
#pragma unroll 2
for (int i = 0; i < 2; ++i) {
    float t = 1.0f - x * g * g;        // residual
    g = g * (1.0f + 0.5f * t * (3.0f - 2.0f)); // fused form to reduce muls
}
float y = x * g;                        // sqrt(x)
return y;
```

---

## 9) Quick Reference (Pros/Cons)

| Method | Latency | Area | Accuracy | Notes |
|---|---:|---:|---:|---|
| LUT + Linear | 1–2 cyc | ROM medium | 10–14 bits (config) | Easiest fast path |
| Newton–Raphson | 2–4 cyc | MUL/DIV | 16–24 bits | Needs seed & div/rsqrt |
| Goldschmidt | 3–5 cyc | MUL-heavy | 16–24 bits | Best in FP pipelines |
| Bit-by-Bit | N cyc | Tiny | 12–16 bits | Control-simple, slow |
| CORDIC | N cyc | Medium | 12–16 bits | Multi-function reuse |

---

**Implementation tip:** For FFT magnitude `abs = sqrt(re^2 + im^2)` in FP16 input with FP32 output, accumulate in FP32, normalize `re²+im²` to [0.5,2), run **NR 2 iters**, then store **FP32** (or cast to FP16 if required by XMODE `POST.CAST_OUT`).

