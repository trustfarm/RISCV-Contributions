# XAME/VNS – TMODE Inline Descriptor Extension (Addendum v0.20b)

**Scope:** Keep the **baseline MMACC fields immutable at execution time** (`K, M, bTR, RFmt, IFmt, bTOP`).
`TMODE` is an **orthogonal, optional** descriptor that *interprets* the call logically and **binds** a concrete
microkernel for `MMACC` without changing any baseline semantics or encodings.

---

## 5) Execution Semantics (no ISA change, baseline fields read‑only)

**Baseline remains the source of truth.** The hardware must not mutate or reinterpret `K, M, bTR, RFmt, IFmt, bTOP`.
`TMODE` only supplies *context* to a binding step that selects which multiplication/operation kernel is **wired** under
the same `MMACC` descriptor.

### 5.1 TMODE‑driven Logical Interpretation
At dispatch time, the micro‑scheduler evaluates:
```
INPUTS  :  (K, M, bTR, RFmt, IFmt, bTOP)  // read‑only baseline
CONTEXT :  TMODE                          // optional, may be NULL
TABLES  :  { TMODE.bind[ ], VNS_PLAN[pid].bind[ ], VNS_BIND[ ] }
OUTPUT  :  KERN := ResolveKernel(KSEL, dtype, flags)
```

- A **KSEL** (logical kernel class) is derived from `(K, M)` or explicitly from `TMODE.domain/ops` table.
- The **binding tables** map `KSEL → KERN` (concrete microkernel implementation).
- If no binding exists, the dispatcher uses **IDENTITY** (baseline GEMM/MMACC) and proceeds.

> **Custom hardware** may physically implement **one** microkernel and **switch** modes (e.g., `conj`, `modq`)
via control bits. `MMACC` remains a single logical operation; `TMODE` does *not* alter inputs—only which kernel is engaged.

### 5.2 OP Table inside TMODE
`TMODE` may carry a compact OP table describing the recognizable operations/modes for the domain.
This table does **not** override `K/M/bTR/bTOP`; it *classifies* the call for kernel selection.

Example OP entries (illustrative):
| op_id | domain | ksel         | when (guard)                         |
|------:|--------|--------------|--------------------------------------|
| 0x01  | FFT    | BFLY_R4      | K=FFT_BFLY ∧ M.radix=4               |
| 0x02  | FFT    | CMUL_CONJ    | K=FFT_TWID ∧ bTOP.CONJ=1             |
| 0x10  | NTT    | BFLY_R2      | K=NTT_BFLY ∧ M.radix=2 ∧ TM.modq=1   |
| 0x20  | MIMO   | CGEMM_SM     | K=CGEMM_SM ∧ M.size∈{2,4,8}          |
| 0x21  | MIMO   | CGIVENS      | K=GIVENS                              |

> Guards may also reference `RFmt/IFmt.dtype`, `VNS_MODQ`, or `plan_id`.

---

### 5.3 Revised Example (OFDM 4096‑pt, radix‑4)

```text
// Inputs are baseline and immutable at runtime
TM = &tmode_fft4096;  // 64B‑aligned VNS_TMODE_v1, contains OP table + bindings
for s in 0..11 {
  C = MMACC(A, B,
            K=FFT_BFLY,                 // baseline: not changed by TMODE
            M={stage:s, radix:4},       // baseline
            bTR={bitrev if last},       // baseline
            RFmt={dtype=FP16},          // baseline
            IFmt={dtype=FP16},          // baseline
            bTOP={SCALE_SHIFT=1},       // baseline
            TMODE=TM);                  // optional context

  // Dispatch resolves: KSEL=BFLY_R4 (from K/M) → KERN=BFLY_R4_PIPE (from TMODE.bind or PLAN/BIND tables)
}
```

**Key properties**
- `MMACC` behaves identically to baseline if `TMODE=NULL` or no matching binding is found.
- `TMODE` provides a **logical explanation** and **binding decision** only.
- Hardware can be simple: a single fused kernel with mode switches controlled by the resolved `KERN` profile.

---

## Appendix A — Binding Resolution Priority

1. `TMODE.bind[]` (if present)  
2. `VNS_PLAN[plan_id].bind[]` (per‑stage/axis)  
3. Global `VNS_BIND[]` (CSR table)  
4. Fallback `IDENTITY` (baseline GEMM/MMACC)

## Appendix B — Minimal HW/SW Contract
- HW: provide a **KSEL decoder** (from `K/M`) and a **KERN switch** fabric.  
- SW: populate `TMODE`/PLAN/BIND tables; guarantee immutability of baseline fields at callsite.

*(End of v0.20b)*
