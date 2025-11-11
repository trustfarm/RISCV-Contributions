# XAME/VNS – TMODE Inline Descriptor Extension (Addendum v0.20d, EN)

**Key change in v0.20d:** The baseline **signature remains untouched** and *does not* carry FFT/NTT stage/radix specifics.  
All operation semantics (e.g., FFT_BFLY, stage, radix, bitrev/transpose) are **encoded inside the TMODE descriptor’s OP table**.

---

## 1) Baseline Signature (unchanged)
```text
C = MMACC(A, B, K, M, bTR, RFmt, IFmt, bTOP [, bias_k, TMODE])
```
- `K, M, bTR, RFmt, IFmt, bTOP` are immutable at runtime and **do not encode FFT/NTT specifics**.
- `TMODE` carries the **domain program** (list of OP entries) that the dispatcher interprets to select/bind kernels.

---

## 2) TMODE OP Program (descriptor‑driven execution)
A TMODE descriptor contains an **OP table** (a small program). Each OP entry fully describes what to execute:
- logical **operation class** (`KSEL`: BFLY_R2/R4/R8, MODMUL, CGIVENS, etc.)
- **stage/radix/twiddle selector**, **bit‑reverse**, **stride/transpose template**, **conj/norm flags**, etc.
- optional **binding hint** (map `KSEL → KERN`) or a reference to `VNS_PLAN`/`VNS_BIND`.

At runtime, **each MMACC invocation consumes the *next OP*** from the TMODE program counter (TM‑PC).  
The baseline fields remain constant; the **current OP** fully determines which microkernel is activated.

---

## 3) Correct Execution Example — OFDM 4096‑pt (radix‑4)
```text
TM = &tmode_fft4096;      // 64B-aligned VNS_TMODE_v1 with OP table for 12 stages
VNS_TMODE_RESET(TM);      // reset TM-PC to the first OP

for i in 0..TM.ops_len-1 {
  C = MMACC(A, B,
            K=IDENTITY,                // baseline neutral (unchanged)
            M=0,                       // baseline neutral (unchanged)
            bTR=0,                     // baseline neutral (unchanged)
            RFmt={dtype=FP16},         // baseline format
            IFmt={dtype=FP16},         // baseline format
            bTOP={SCALE_SHIFT=1},      // baseline pipeline mode
            TMODE=TM);                 // dispatcher fetches OP[i] from TMODE

  // Dispatcher uses OP[i] to resolve:
  //   KSEL = OP[i].ksel (e.g., BFLY_R4)
  //   KERN = binding(KSEL, dtype) → e.g., BFLY_R4_PIPE
  //   Address transform (bitrev/stride/transpose) per OP[i] template
}
```
> No FFT details appear in `K/M/bTR`; they live **only** in TMODE.OP entries.

---

## 4) TMODE OP Entry (illustrative layout)
```c
struct VNS_TMODE_OP {
  uint8_t  ksel;       // e.g., BFLY_R4, CMUL_CONJ, MODMUL, CGIVENS
  uint8_t  stage;      // stage index (FFT/NTT); 0xFF if not used
  uint8_t  radix;      // {2,4,8} for FFT; 0 if not used
  uint8_t  flags;      // {BITREV_LAST, TRANSPOSE_XY, CONJ, NORM_1/N, ...}

  uint16_t stride_tpl; // stride/transpose template id
  uint16_t bind_idx;   // optional local binding index (→ KERN)

  uint32_t tw_sel;     // twiddle segment / modulus selector
  uint32_t aux;        // extra metadata (e.g., modulus q handle, axis id)
};
```
- OP entries are consumed in order (`TM‑PC` auto‑increments).  
- `VNS_TMODE_RESET(TM)` resets the `TM‑PC` to the first OP.

---

## 5) Binding & Fallback (unchanged priority)
1. `TMODE.bind[]` (if present)  
2. `VNS_PLAN[plan_id].bind[]` (per stage/axis)  
3. global `VNS_BIND[]` (CSR)  
4. fallback `IDENTITY` (baseline GEMM/MMACC)

---

## 6) Engineering Interpretation (recap)
- `MMACC` is a **single logical instruction** for **AI Matrix (AI‑MAC)**.  
- Hardware may wire one or more multiplier/operator kernels behind a **switch/MUX**.  
- `TMODE` provides the **program** (OP table) that tells the dispatcher **which kernel to engage each call**.  
- If hardware cannot support the requested OP (no kernel / no switch), it **throws a binding fault**.

*(End of Addendum v0.20d EN)*
