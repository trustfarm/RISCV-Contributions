# LWE → RLWE → NTT → Keccak / RV‑PQC Report V1

[KO](LWE_to_RV_PQC_Report_v1_KR.md) | [EN](LWE_to_RV_PQC_Report_v1_EN.md)
---

## 1️⃣ Overview

As quantum computers continue to evolve, classical public‑key cryptography systems such as RSA and ECC face potential vulnerabilities to quantum algorithms like Shor’s algorithm.  
To prepare for this, **Post‑Quantum Cryptography (PQC)** has emerged as the foundation for future‑proof cryptographic systems.

This report explains the mathematical and architectural connection from **LWE → RLWE → NTT → Keccak**,  
and how these components form the backbone of **RISC‑V‑based PQC (RV‑PQC)** hardware acceleration.

---

## 2️⃣ LWE (Learning With Errors)

### Basic Idea

> “Recovering a secret vector from noisy linear equations is computationally hard.”

Given a secret vector $s \in \mathbb{Z}_q^n$, we observe several noisy linear equations:

$$
b_i = \langle a_i, s \rangle + e_i \pmod{q}
$$

where  
- $a_i$ — known random vector  
- $b_i$ — known output  
- $e_i$ — small random noise  
- $s$ — secret vector to be recovered

Even though $a_i$ and $b_i$ are public, the small error term $e_i$ makes recovering $s$ computationally difficult.

### Security Foundation

LWE is provably as hard as well‑known **lattice problems** such as GapSVP and SIVP.  
These problems remain difficult even for quantum computers, which makes LWE a strong foundation for PQC.

**References:**  
- NIST PQC Project: https://csrc.nist.gov/projects/post-quantum-cryptography  
- Learning with Errors (Wikipedia): https://en.wikipedia.org/wiki/Learning_with_errors

---

## 3️⃣ RLWE (Ring Learning With Errors)

### Motivation for RLWE

Standard LWE operates on high‑dimensional vectors and large matrices, which quickly becomes computationally expensive.  
**RLWE (Ring‑LWE)** generalizes LWE to operate over polynomial rings, achieving significant efficiency gains.

### Mathematical Definition

$$
b(x) = a(x) \cdot s(x) + e(x) \pmod{(x^n + 1, q)}
$$

Here, $a(x), s(x), e(x)$ are elements of the ring $R_q = \mathbb{Z}_q[x]/(x^n + 1)$.  
Polynomial multiplication corresponds to **cyclic convolution**, which can be efficiently computed using the **NTT (Number Theoretic Transform)**.

### Circulant Matrix View

Each polynomial $a(x)$ can be represented as a **circulant matrix**, where each row is a cyclic rotation of its coefficients:

$$
A =
\begin{pmatrix}
a_0 & a_{n-1} & \cdots & a_1 \\
a_1 & a_0 & \cdots & a_2 \\
\vdots & \vdots & \ddots & \vdots \\
a_{n-1} & a_{n-2} & \cdots & a_0
\end{pmatrix}
$$

This view shows that RLWE retains the same structure as LWE — but with compact, cyclicly structured data.

### References:

- LWE -> RLWE Concept Paper Analysis and NIST approach to mitigation of RLWE weakness
    - [**Appendix A - Lyubashevsky et al., “On Ideal Lattices and Ring-LWE”**](#-appendixa-onideallatticesandringlwe2012)
- CRYSTALS‑Kyber Project (https://pq-crystals.org/kyber/)

---

## 4️⃣ NTT (Number Theoretic Transform)

### FFT vs NTT

While FFT operates in the complex number domain, the **NTT** performs an analogous transformation in the finite integer domain modulo $q$.

### Definition

$$
A_k = \sum_{j=0}^{n-1} a_j \cdot \omega^{jk} \pmod{q}, \quad k=0,\dots,n-1
$$

Inverse transform:

$$
a_j = n^{-1} \sum_{k=0}^{n-1} A_k \cdot \omega^{-jk} \pmod{q}
$$

Here, $\omega$ is a primitive $n$‑th root of unity modulo $q$.  
Using NTT, polynomial multiplication becomes simple pointwise multiplication followed by an inverse transform — an $O(n \log n)$ process.

### Hardware Characteristics

- The NTT size $n=256$ is **fixed** at design time.  
- Parallelism parameters control performance:  
  - $P$: number of butterflies processed per cycle  
  - $W$: number of coefficient multiplications per cycle

#### 🔹 Summary - NTT Size (n) of PQC algorithm

| Algorithm                 | Type             | Uses NTT?    | Polynomial Degree ($n$) | Modulus ($q$) | Notes                                                                                                                                                                                          |
| ------------------------- | ---------------- | ------------ | ----------------------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Kyber**                 | KEM (encryption) | ✅ Yes        | **256**                 | 3329          | Uses **integer NTT** (FNTT + INTT) with radix-2 butterflies; optimized for small $q$ and modular reduction. The reference for most PQC hardware accelerators.                                  |
| **Dilithium**             | Signature        | ✅ Yes        | **256**                 | 8380417       | Uses **same NTT core as Kyber**, but higher modulus allows larger dynamic range for signature noise; operates on **vectors of 256-point polynomials** (e.g., 4–6× 256).                        |
| **Saber**                 | KEM              | ⚠️ Partial   | 256                     | $2^{13}$      | Performs polynomial multiplication via **Toom-Cook and schoolbook methods**, not a true NTT; implemented over power-of-two modulus for efficient bit-shifts instead of modular roots of unity. |
| **NTRU**                  | KEM              | ⚙️ FFT-like  | 701                     | 2048 or 4096  | Uses **cyclic convolution mod $(x^{701}−1)$**; FFT-style transform applied in some optimized variants; relies on coefficient wrapping instead of modular roots.                                |
| **Falcon**                | Signature        | ⚙️ FFT-based | 512 / 1024              | 12289         | Uses **floating-point FFT** (not integer NTT); achieves extremely compact signatures but requires precise rounding and floating-point hardware.                                                |
| **FrodoKEM**              | KEM              | ❌ No         | —                       | 2¹⁵           | Based on **standard LWE matrix multiplication**; no transform or cyclic structure; computationally heavy but conceptually simple and secure.                                                   |
| **BIKE / HQC / McEliece** | Code-based       | ❌ No         | —                       | —             | Use **error-correcting code algebra (binary/GF(2))**; involve bitwise XOR, permutation, and decoding rather than polynomial or NTT arithmetic.                                                 |



| Parameter | Range | Description |
|------------|--------|-------------|
| $P$ | 1–16 | Butterfly parallelism |
| $W$ | 1–32 | Pointwise multiplication width |

Example latencies (for $n=256$):  
- $P=4$ → $C_{NTT} \approx 256$ clocks  
- $P=8$ → $C_{NTT} \approx 128$ clocks  
- $P=16$ → $C_{NTT} \approx 64$ clocks  

Total polynomial multiplication (NTT + pointwise + iNTT):  
≈ 512–768 clocks ($P=4$), ≈ 288–384 clocks ($P=8$).

**References:**  
- https://www.nayuki.io/page/number-theoretic-transform-integer-dft  
- https://github.com/pq-crystals/kyber

---

## 5️⃣ Keccak / SHA‑3 / SHAKE

### From Keccak to SHA‑3

Keccak won the NIST SHA‑3 competition (2012) and was standardized as **FIPS PUB 202** in 2015.  
Full specification: https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.202.pdf

| Variant | Output | Usage |
|----------|---------|-------|
| SHA3‑224/256/384/512 | Fixed length | Hashing |
| SHAKE128 / SHAKE256 | Extendable‑output (XOF) | Used in PQC (seed expansion, KDF, etc.) |

### Role in PQC

- **Seed expansion:** derive matrix A, secrets s, errors e.  
- **Key derivation (KDF):** generate shared secrets.  
- **Message binding:** in signatures and encapsulations.

### Hardware Design Perspective

The Keccak‑f[1600] permutation operates on a 1600‑bit state for 24 rounds of bitwise logic.  

| Mode | Description | Pros / Cons |
|------|--------------|-------------|
| Full Unroll | All 24 rounds in parallel | Fast / large area |
| Partial Unroll | 4–6 rounds / cycle | Balanced |
| Iterative | 1 round / cycle | Compact / slower |

In RV‑PQC, Keccak is typically streamed as an XOF source feeding the NTT pipeline; its **unroll factor u** must match the NTT consumption rate.

**References:**  
- https://keccak.team/keccak.html  
- https://csrc.nist.gov/projects/post-quantum-cryptography/finalists

---

## 6️⃣ RV‑PQC Hardware Co‑Design

### NTT ↔ Keccak Bandwidth Matching

- NTT processes one polynomial roughly every 128–256 clocks.  
- Keccak must stream XOF output at a matching rate.  
- Choose unroll factor $u$ to equalize dataflow.

### Streaming Architecture

- Use **AXI‑Stream / DMA** interfaces between Keccak and NTT.  
- Squeeze output directly into NTT input FIFO.  
- Avoid CPU polling; maintain sustained throughput.

### Security Features

- Constant‑time arithmetic  
- Masking (first‑order or higher)  
- State scrubbing and deterministic noise

### Reference Implementations

- IEEE 10839700: https://ieeexplore.ieee.org/document/10839700 — parallel Keccak/NTT co‑processing (P≈8, W≈8).  
- DBpia: https://www.dbpia.co.kr/journal/articleDetail?nodeId=NODE12331348 — embedded NTT accelerators (P = 4–8).

---
### Implication of PQC Accel Example Paper based 

- "A Pipelined Hardware Design of FNTT and INTT of CRYSTALS-Kyber PQC Algorithm" 
- See details in -->  [Appendix MDPI Analysis](#-appendixb-mdpi2025paperanalysis)

> **Main Implication**
> - ####  Keccak unroll level $u$ estimates
> 
> | Scenario | NTT Clock (C_NTT) | Keccak BW req | recommend unroll level $u$ (24 rounds base) |
> |-----------|-------------------|----------------------|----------------------|
> | Small Footprint (P=1) | ≈ 1000 clocks | Low ( x MB/s ) | $u ≈ 0.1$ (1 round/10 cycles) |
> | Balanced (P=8) | ≈ 256 clocks | Mid ( xxx MB/s) | $u ≈ 0.3 ∼ 0.5$ (1 round/2–3 cycles) |
> | High Perf (P=16) | ≈ 128 clocks | High (> 1 GB/s) | $u ≈ 0.6 ∼ 1.0$ (1 round/1–1.5 cycles) |
> - In MDPI Paper P=1 ,  Keccak XOF bandwidth requirements lower.  
> - To RV-PQC , NTT will implemented more faster,  Keccak unroll $u >≈ 0.4$.

---

## 7️⃣ Conclusion

The progression **LWE → RLWE → NTT → Keccak** forms the mathematical and architectural core of modern PQC hardware.  
RV‑PQC platforms build on this chain, synchronizing NTT throughput with Keccak unrolling to achieve optimal performance.  
For embedded FPGA‑class systems, $P=W=4–8$ is practical; for ASICs, $P=W=8–16$ is feasible.

---

# 📘 Appendix A — On Ideal Lattices and Ring‑LWE (2012)

> Lyubashevsky, Peikert & Regev, *On Ideal Lattices and Ring‑LWE*, IACR ePrint 2012/230 — https://eprint.iacr.org/2012/230.pdf

### Summary

This foundational paper introduced **Ring‑LWE**, extending LWE into the polynomial ring domain for better efficiency, and proved its hardness by reduction from **ideal lattice** problems.

### Key Contributions

1. **Ideal Lattice Definition** — lattices with multiplicative structure.  
2. **RLWE Problem Definition** — uses $R_q = \mathbb{Z}_q[x]/(f(x))$.  
3. **Security Reduction** — RLWE ↔ worst‑case Ideal‑SIVP.  
4. **Parameter Constraints** — $n$, $q$, and noise $\sigma$ requirements.

### RLWE Equation

$$
b(x) = a(x)\,s(x) + e(x) \pmod{q, f(x)}
$$

Each term is a polynomial; $e(x)$ follows a discrete Gaussian.  
Multiplication occurs modulo $f(x)$ and $q$.

### Advantages

- Compact storage, efficient convolution using NTT.  
- Security derived from hard lattice problems.

---

## Limitations & Risks

| Type | Description | NIST PQC Mitigation |
|------|--------------|--------------------|
| **Ideal lattice structure** | extra symmetry → possible subring/automorphism attacks | Cyclotomic $f(x)=x^n+1$ only |
| **Parameter sensitivity** | small $n,q,σ$ reduce security | Verified Kyber/Dilithium params |
| **Search vs Decisional gap** | hardness may differ | Module‑LWE extension used |
| **Noise bias** | RNG bias → key leakage | CBD or SHAKE noise generation |
| **Side‑channel** | timing/power leakage | constant‑time NTT & mod ops |
| **Decryption failure** | large noise → key leak | Kyber failure rate < 2⁻⁸⁰ |

### Conclusion

Modern NIST PQC algorithms (Kyber, Dilithium) mitigate all theoretical RLWE weaknesses via cyclotomic rings, module extensions, and constant‑time noise‑safe implementations.

---

# 📘 Appendix B — MDPI 2025 Paper Analysis

> Rashid et al., *A Pipelined Hardware Design of FNTT and INTT for CRYSTALS‑Kyber PQC*, *Information*, 2025, 16(1), 17 — https://www.mdpi.com/2078-2489/16/1/17

### Overview

The paper proposes a **unified pipelined architecture** for forward/inverse NTT (FNTT/INTT) in the Kyber PQC algorithm.  
It uses a single **Unified Butterfly Unit (U‑BTF)** shared by both transforms.

### Design Highlights

| Feature | Description |
|----------|--------------|
| Architecture | Single U‑BTF shared FNTT/INTT |
| Pipeline | 6 stages deep |
| Parallelism | P ≈ 1 (fully serial) |
| Frequency | 290 MHz (Virtex‑7), 256 MHz (Virtex‑6) |
| Latency | FNTT 898 cycles, INTT 1028 cycles |
| Total Process | ≈ 1410 cycles including I/O |
| Resources | 312–398 slices, no DSPs used |
| Memory | 2× dual‑port BRAM + 1 twiddle ROM |

### Observations

- Single U‑BTF saves area but increases latency.  
- Deep pipeline → high frequency, low parallelism.  
- Efficiency measured by throughput/area (FoM +62 % vs prior work).

### Adjusted P/W Guidelines

| Design Type | P Range | W Range | Strategy | Typical Latency (256‑pt) |
|--------------|---------|---------|-----------|--------------------------|
| Low‑area FPGA | 1–2 | 1–2 | Deep pipeline | ≈ 900–1500 clocks |
| Balanced SoC | 4–8 | 4–8 | Moderate pipeline | ≈ 250–500 clocks |
| High‑performance ASIC | 8–16 | 8–16 | Wide parallelism | ≈ 100–250 clocks |

### Keccak Unroll Prediction (u)

| Scenario | NTT Latency | XOF Bandwidth Need | Recommended $u$ (24 rounds) |
|-----------|-------------|--------------------|-----------------------------|
| Low‑area (P=1) | 1000 clocks | Low (few MB/s) | $u≈0.1$ (1 round/10 cycles) |
| Balanced (P=8) | 256 clocks | Medium (100s MB/s) | $u≈0.3–0.5$ (1 round/2–3 cycles) |
| High‑perf (P=16) | 128 clocks | > 1 GB/s | $u≈0.6–1.0$ (≈1 round/cycle) |

### Implications

| Aspect | MDPI Design | RV‑PQC Implication |
|--------|--------------|--------------------|
| Butterfly Parallelism | P = 1 | Increase to P≥8 for Keccak matching |
| Pipeline Depth | 6 stages | Shallower (≤ 2) adequate when parallelized |
| Keccak Integration | Low throughput → CPU driven | Streamed XOF with unroll 4–6 |
| Memory | Ping‑pong BRAM | Multi‑bank + DMA prefetch |
| Design Goal | Area efficiency | Throughput + synchronization balance |

### Conclusion

The MDPI 2025 architecture illustrates the *low‑area, deeply‑pipelined* approach (P=1).  
RV‑PQC systems should scale up to P≥8 and unroll factor u≥0.4 to synchronize Keccak and NTT pipelines efficiently.

