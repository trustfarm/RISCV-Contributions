# XAME/VNS – TMODE Inline Descriptor Extension (Addendum v0.20e, EN)

**Essence:** The baseline signature is preserved; FFT/NTT/OFDM/MIMO execution semantics live **only** in the TMODE’s **OP (Operations) table**.  
Here, **OP is *not* a CPU opcode**. It is an *operation item* that specifies **how the microkernel / custom hardware logic should run** under TMODE control.

---

## 1) Baseline Signature (unchanged)
```text
C = MMACC(A, B, K, M, bTR, RFmt, IFmt, bTOP [, bias_k, TMODE])
```
- `K, M, bTR, RFmt, IFmt, bTOP` are **immutable** at runtime and **do not carry FFT/NTT details**.  
- All execution semantics come from **TMODE’s OP execution**.

---

## 2) TMODE OP Program (descriptor‑driven execution)
TMODE contains an **OP (Operations) table**. Each OP fully describes *what to run and how*:
- Logical **kernel class** (`KSEL`: `BFLY_R2/R4/R8`, `MODMUL`, `CGIVENS`, …)
- **stage/radix/twiddle selection**, **bit‑reverse**, **stride/transpose template**, **conj/norm flags**, etc.
- Optional binding hint `KSEL → KERN` (or reference to `VNS_PLAN` / `VNS_BIND`).

> ⚠️ **Note:** **OP is not a CPU opcode.**  
> It specifies the **behavior of the microkernel (or custom HW logic)** that TMODE orchestrates.  
> In other words, OP describes **which kernel to run and in what mode/parameters**, not a new ISA instruction.

At runtime, **each MMACC call executes the OP embedded in TMODE**.  
Baseline fields stay constant; **TMODE and TMODE.OP** determine which **microkernel (KERN)** is engaged.

---

## 3) Correct Execution Example — OFDM 4096‑pt (radix‑4)
```text
TM = &tmode_fft4096;   // 64B-aligned TMODE with a 12-stage OP table
VNS_TMODE_RESET(TM);   // reset TM‑PC

while (VNS_TMODE_HAS_NEXT(TM)) {
  C = MMACC(A, B,
            K=IDENTITY, M=0, bTR=0,         // baseline: neutral, unchanged
            RFmt={dtype=FP16}, IFmt={dtype=FP16}, bTOP={SCALE_SHIFT=1},
            TMODE=TM);                      // dispatcher interprets TM.OP[TM‑PC]
}
```
- The dispatcher derives **KSEL** from the current OP and selects **KERN** via binding tables.  
- Address transforms (bit‑reverse/stride/transpose) and conj/norm come from the **OP template**.

---

## 4) OP Entry Layout (illustrative)
```c
struct VNS_TMODE_OP {
  uint8_t  ksel;       // logical kernel: BFLY_R4, CMUL_CONJ, MODMUL, CGIVENS, ...
  uint8_t  stage;      // FFT/NTT stage index (0xFF if unused)
  uint8_t  radix;      // FFT radix {2,4,8}; 0 if unused
  uint8_t  flags;      // {BITREV_LAST, TRANSPOSE_XY, CONJ, NORM_1/N, ...}
  uint16_t stride_tpl; // stride/transpose template id
  uint16_t bind_idx;   // local binding index (→ KERN), 0 = external
  uint32_t tw_sel;     // twiddle segment / modulus selector
  uint32_t aux;        // auxiliary metadata (e.g., modulus q handle, axis id)
};
```
- OPs are consumed in order (TM‑PC auto‑increments). `VNS_TMODE_RESET` restarts from the first OP.

---

## 5) Binding & Fallback (same priority)
1. `TMODE.bind[]` (in-descriptor)  
2. `VNS_PLAN[plan_id].bind[]` (per stage/axis)  
3. Global `VNS_BIND[]` (CSR)  
4. Fallback `IDENTITY` (baseline GEMM/MMACC)

---

## 6) Engineering Recap
- `MMACC` is a **single logical instruction** that performs **AI Matrix (AI‑MAC)**.  
- Hardware may wire one/more kernels behind a **MUX/switch**.  
- **TMODE.OP** tells which kernel to run and how to parameterize it.  
- If hardware lacks the requested kernel/switching, a **binding fault** must be raised.

*(End of Addendum v0.20e EN)*
