# XAME/VNS Optional TileMode & Kernel Binding (v0.20)
**Scope:** Keep **baseline `bTOP` semantics unchanged**. Add an **optional TileMode** layer that defines
FFT/NTT/OFDM/MIMO tile behaviors, and a **selective multiplication–kernel binding** mechanism.

---
## 1. Design Goals
- **No change to baseline**: `C = MMACC(A, B, K, M, bTR, RFmt, IFmt, bTOP [, bias_k])` remains intact.
- **Optional extension only**: TileMode is an orthogonal descriptor consumed by the micro-scheduler.
- **Pluggable kernels**: A symbolic kernel class (KSEL) is **bound** to a concrete **mul/acc microkernel** at runtime via CSR/Plan.
- **Deterministic fallback**: If no binding exists, MMACC executes baseline GEMM/CMAC (identity behavior).

- **extend to baseline support TMODE descriptors**:  descriptors stored in additional address
`C = MMACC(A, B, K, M, bTR, RFmt, IFmt, bTOP [, bias_k, TMODE])` 
---
## 2. TileMode Descriptor (TMODE)
A compact descriptor that declares **how a tile participates** in a domain-specific pipeline.

```
TMODE {
  mode_id    : u8   // 0: NONE, 1: FFT, 2: NTT, 3: OFDM, 4: MIMO, 5: CUSTOM
  plan_id    : u8   // link to VNS_PLAN slot (stage/radix/stride tables)
  domain     : bits // {FFT, NTT, OFDM, MIMO}
  cplx_fmt   : bits // {RE_HI_IM_LO, INTERLEAVED, SoA}
  scale_pol  : bits // {NONE, BLOCK_FLOAT, FINEGRAIN_SA_SW}
  norm_mode  : bits // {NONE, IFFT_1/N, IFFT_1/sqrtN, NTT_INV_MOD_Q}
  tw_src     : bits // {LUT_PLAN, CORDIC, CONST_1}
  modq_en    : bit  // enable modular arithmetic (NTT)
  stride_sel : bits // stride/transpose template index (used with bTR)
}
```

> **Note:** TMODE does not alter `bTOP`. It supplies **context** to the dispatcher and address generators.

---
## 3. Kernel Class (KSEL) & Binding
We introduce **logical kernel classes** (KSEL). Each KSEL can be **bound** to a concrete microkernel implementation
(**KERN**) depending on type/precision/platform.

### 3.1 Kernel Classes (KSEL)
| KSEL Symbol | Meaning | Typical Usage |
|-------------|---------|---------------|
| `KSEL.CMUL` | Complex multiply (no twiddle) | Generic CMAC |
| `KSEL.CMUL_CONJ` | Complex mul with conjugate(B) | FFT twiddle / OFDM |
| `KSEL.TWIDMUL` | Twiddle multiply only | Pre/post butterfly |
| `KSEL.BFLY_R2` | Radix-2 butterfly fused kernel | FFT/NTT R2 |
| `KSEL.BFLY_R4` | Radix-4 butterfly fused kernel | FFT/NTT R4 |
| `KSEL.BFLY_R8` | Radix-8 butterfly fused kernel | FFT R8 |
| `KSEL.MODMUL` | Modular multiply (Barrett/Mont) | NTT |
| `KSEL.MODMAC` | Modular MAC (mul+add mod q) | NTT |
| `KSEL.CGIVENS` | Complex Givens rotation | MIMO QR/SVD |
| `KSEL.CGEMM_SM` | Small complex GEMM (2/4/8) | MIMO batch |
| `KSEL.IDENTITY` | Baseline GEMM/MMACC | Fallback |

### 3.2 Concrete Microkernels (KERN)
| KERN ID | Numeric Profile | Notes |
|---------|------------------|-------|
| `KERN.CMUL_FP16` | FP16/BF16 | vectorized complex mul |
| `KERN.CMUL_INT16_SAT` | INT16 (saturate) | block-float friendly |
| `KERN.CMUL_CONJ_FP16` | FP16 | conj(B) fused |
| `KERN.BFLY_R4_PIPE` | FP16/INT16 | 1-bfly/clk pipeline |
| `KERN.BFLY_R2_MODQ` | INT16 mod q | NTT R2 fused |
| `KERN.MODMUL_MONT16` | INT16 mod q (Montgomery) | q, R params from CSR |
| `KERN.MODMAC_BARRETT16` | INT16 mod q (Barrett) | stage-local constants |
| `KERN.CGIVENS_FP32` | FP32 | accuracy-critical stage |
| `KERN.CGEMM_SM4_FP16` | FP16 small-mat | unrolled 4×4 |
| `KERN.IDENTITY` | any | baseline |

### 3.3 Binding Mechanism
Two levels are supported:

1) **Global CSR Binding (static)**  
```
VNS_BIND[n] = { ksel : KSEL, kern : KERN_ID, dtype: RFmt/IFmt.dtypes, flags }
```
2) **Plan-local Binding (per stage/axis)**  
Embedded in `VNS_PLAN[plan_id].stage[s].bind[]`

**Dispatch Rule:**  
When executing `MMACC(...)` the dispatcher sees `(TMODE, K/M/RFmt/IFmt)` → resolves **KSEL** (from `K` or template) →
looks up binding table → installs **KERN** for the micro-scheduler. If no match → `KERN.IDENTITY`.

---
## 4. Execution Model (unchanged API)

```text
C = MMACC(A, B, K, M, bTR, RFmt, IFmt, bTOP [, bias_k])
// optional context:
TMODE = VNS_TILEMODE.load(mode_id=FFT, plan_id=0, scale_pol=BLOCK_FLOAT, cplx_fmt=SoA)
```

**Key points**
- `K/M/bTR` keep their original meaning (baseline spec).  
- TMODE provides **domain hints**; binding selects concrete microkernels.  
- `bTOP` remains baseline (acc path, pipeline mode).

---
## 5. Worked Examples

### 5.1 OFDM 4096-pt (radix-4, 12 stages)
```text
// TileMode
VNS_TILEMODE <- {mode_id=FFT, plan_id=0, cplx_fmt=SoA, scale_pol=BLOCK_FLOAT, norm_mode=IFFT_1/N}

// Binding (global or plan-local)
VNS_BIND[0] <- { KSEL.BFLY_R4,  KERN.BFLY_R4_PIPE,  FP16 }
VNS_BIND[1] <- { KSEL.CMUL_CONJ, KERN.CMUL_CONJ_FP16, FP16 }

// Execution
for s in 0..11:
  C = MMACC(A,B, K=FFT_BFLY, M={stage:s, radix:4}, bTR={bitrev if last},
            RFmt={dtype=FP16}, IFmt={dtype=FP16}, bTOP={SCALE_SHIFT=1})
// Twiddle pre/post if required:
_ = MMACC(A,B, K=FFT_TWID, M={stage:s}, RFmt=..., IFmt=...)
```

### 5.2 4‑D Radar 256×128×128×128
```text
VNS_TILEMODE <- {mode_id=FFT, plan_id=1, cplx_fmt=SoA, scale_pol=BLOCK_FLOAT}
VNS_BIND[0]  <- { KSEL.BFLY_R4, KERN.BFLY_R4_PIPE, INT16 }
VNS_BIND[1]  <- { KSEL.CMUL,    KERN.CMUL_INT16_SAT, INT16 }

// axes: Range(256), Doppler(128), Az(128), El(128)
for axis in axes:
  for s in axis.stages:
    C = MMACC(A,B, K=FFT_BFLY, M={stage:s, radix:4},
              bTR={stride/transpose template},
              RFmt={dtype=INT16,saturate=1}, IFmt={dtype=INT16}, bTOP={SCALE_SHIFT=1})
```

### 5.3 PQC NTT (shared butterfly, mod q)
```text
VNS_TILEMODE <- {mode_id=NTT, plan_id=2, cplx_fmt=SoA, scale_pol=BLOCK_FLOAT, modq_en=1}
VNS_BIND[0]  <- { KSEL.BFLY_R2,      KERN.BFLY_R2_MODQ,       INT16 }
VNS_BIND[1]  <- { KSEL.MODMUL,       KERN.MODMUL_MONT16,      INT16 }
VNS_BIND[2]  <- { KSEL.MODMAC,       KERN.MODMAC_BARRETT16,   INT16 }

for s in 0..(log2N-1):
  C = MMACC(A,B, K=NTT_BFLY, M={stage:s, radix:2},
            bTR={BITREV if last}, RFmt={dtype=INT16}, IFmt={dtype=INT16}, bTOP={SCALE_SHIFT=1})
```

### 5.4 MIMO 4×4 SVD/QR
```text
VNS_TILEMODE <- {mode_id=MIMO, plan_id=3, cplx_fmt=RE_HI_IM_LO, scale_pol=FINEGRAIN_SA_SW}
VNS_BIND[0]  <- { KSEL.CGIVENS,  KERN.CGIVENS_FP32,  FP32 }
VNS_BIND[1]  <- { KSEL.CGEMM_SM, KERN.CGEMM_SM4_FP16, FP16 }

_ = MMACC(A,B, K=GIVENS,   M={pivot:(i,j)}, RFmt={FP32}, IFmt={FP32}, bTOP=0)
C = MMACC(A,B, K=CGEMM_SM, M={size:4},      RFmt={FP16}, IFmt={FP16}, bTOP=0)
```

---
## 6. CSR Summary
| CSR | Purpose |
|-----|---------|
| `VNS_TILEMODE` | Load/store TMODE (optional context) |
| `VNS_BIND[n]` | KSEL→KERN binding entries |
| `VNS_PLAN[id]` | stage/radix/stride/twiddle descriptors |
| `VNS_SCALE` | per-stage shift bits (block-float) |
| `VNS_CPLX_FMT` | complex packing / endianness |
| `VNS_LAYOUT` | SoA↔AoS swizzle control |
| `VNS_STATUS` | progress / saturation flags |
| `VNS_MODQ` | enable modular arithmetic (NTT) |

---
## 7. Compatibility Notes
- **Binary/ISA**: No change to baseline `MMACC` encoding or `bTOP` control.
- **Compiler**: TileMode + Binding tables are **planner metadata** that guide microkernel selection.
- **Platform**: Vendors may ship platform‑optimized KERN sets without fragmenting the ISA.

---
*(End of Document)*
