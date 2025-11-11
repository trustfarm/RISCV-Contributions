# XAME/VNS – TMODE Inline Descriptor Extension (Addendum v0.20a)

**Goal:** Keep the **baseline MMACC ABI** intact while allowing an **optional TileMode (TMODE) descriptor**
to ride along the callsite for domain‑specific behavior (FFT/NTT/OFDM/MIMO) and kernel binding.

---

## 1) Updated Signature (backward‑compatible)

```text
// Baseline (unchanged)
C = MMACC(A, B, K, M, bTR, RFmt, IFmt, bTOP [, bias_k])

// Optional TMODE inline (this addendum)
C = MMACC(A, B, K, M, bTR, RFmt, IFmt, bTOP [, bias_k, TMODE])
```

**Rules**
- If `TMODE == NULL` (or omitted) → **baseline behavior** (no change).
- If `TMODE != NULL` → the micro‑scheduler **loads** a TileMode descriptor and applies it as **context**.
- The opcode/encoding of MMACC does **not** change; the optional parameter is **planner/ABI‑level** metadata.
- Any field already present in `K/M/bTR/RFmt/IFmt/bTOP` **takes precedence** over the same concept in TMODE.

---

## 2) TMODE Storage Model

Two equivalent forms are supported:

1. **Pointer Form (addr)** — recommended with `bTOP=1` (external DMA path):  
   - `TMODE` holds a 64‑bit address to a memory‑resident descriptor.
2. **Handle Form (index)** — recommended with `bTOP=0` (internal A‑RF path):  
   - `TMODE` holds a small integer handle; hardware reads the descriptor from an **on‑chip TMODE SRAM**.

> Discoverability via `VNS_CAPS`: bit `TMODE_EXT=1` indicates support for this addendum.

---

## 3) TMODE Binary Layout (memory‑resident descriptor)

All fields are **little‑endian**. The structure is versioned and self‑describing.

```c
// 64‑byte minimum, 64‑byte aligned (cacheline friendly)
struct VNS_TMODE_v1 {
  uint32_t magic;      // 'TMOD' = 0x544D4F44
  uint16_t version;    // 0x0001
  uint16_t length;     // total bytes of this TMODE blob (>= 64)
  uint32_t flags;      // global flags (see below)

  // Core selectors
  uint8_t  mode_id;    // 0:NONE 1:FFT 2:NTT 3:OFDM 4:MIMO 5:CUSTOM
  uint8_t  plan_id;    // links to VNS_PLAN slot
  uint8_t  domain;     // bitset {FFT,NTT,OFDM,MIMO}
  uint8_t  cplx_fmt;   // {RE_HI_IM_LO, INTERLEAVED, SoA}

  uint8_t  scale_pol;  // {NONE, BLOCK_FLOAT, FINEGRAIN_SA_SW}
  uint8_t  norm_mode;  // {NONE, IFFT_1/N, IFFT_1/sqrtN, NTT_INV_MOD_Q}
  uint8_t  tw_src;     // {LUT_PLAN, CORDIC, CONST_1}
  uint8_t  modq_en;    // 0/1 (enable modular arithmetic, NTT)

  uint16_t stride_sel; // selects stride/transpose template
  uint16_t bind_off;   // byte offset to binding table (0=none)

  uint32_t reserved0;  // future use

  // Optional per‑stage hints (first 8 stages inline; more via plan)
  struct {
    uint8_t radix;     // {2,4,8}
    uint8_t scale;     // stage shift bits (block‑float)
    uint8_t tw_sel;    // twiddle segment index
    uint8_t flags;     // stage flags (BITREV_LAST, TRANSPOSE, …)
  } stage_hint[8];

  uint32_t crc32;      // CRC over [magic..end‑of‑binding]
  uint32_t reserved1;

  // Followed by optional Binding Table (variable length, 16‑byte aligned)
  // Each entry maps KSEL → KERN.
};
```

**Descriptor Flags (`flags`)**
- `BIT_PREFETCH` (hardware prefetch TMODE before execution)
- `BIT_LOCKED` (descriptor is immutable until job completion)
- `BIT_SECURE` (access requires privileged domain / PMP entry)

**Alignment & Size**
- 64‑byte **aligned**, minimum 64 bytes. Additional sections (binding table) extend `length`.

---

## 4) Kernel Class (KSEL) → Microkernel (KERN) Binding

Binding entries may live:
- **inside** the TMODE blob (`bind_off` points to the table), or
- **externally** in `VNS_BIND[]` (global CSR table), or
- in the **per‑stage** area of `VNS_PLAN[plan_id]`.

**Binding Entry (16 bytes)**
```c
struct VNS_BIND_ENTRY {
  uint16_t ksel;   // e.g., BFLY_R4, CMUL_CONJ, MODMUL, CGIVENS, ...
  uint16_t kern;   // e.g., BFLY_R4_PIPE, CMUL_CONJ_FP16, MODMUL_MONT16, ...
  uint16_t dtype;  // FP16, INT16, BF16, ...
  uint16_t flags;  // vendor / accuracy / energy hints
  uint32_t aux0;   // optional: q, R, tw_base segment, etc.
  uint32_t aux1;   // optional
};
```

**Dispatch Order**
1. If TMODE contains a binding table → use it.  
2. Else if `VNS_PLAN[plan_id]` has per‑stage bindings → use those.  
3. Else consult global `VNS_BIND[]`.  
4. Else fallback to **baseline** kernel (`KERN.IDENTITY`).

---

## 5) Execution Semantics (no ISA change)

```text
// Example: OFDM 4096‑pt (radix‑4)
TM = &tmode_fft4096;     // 64B‑aligned VNS_TMODE_v1
for s in 0..11 {
  C = MMACC(A, B, K=FFT_BFLY, M={stage:s, radix:4},
            bTR={bitrev if last},
            RFmt={dtype=FP16}, IFmt={dtype=FP16}, bTOP={SCALE_SHIFT=1},
            TMODE=TM);
}
```

- The hardware **may prefetch** `TMODE` (set `BIT_PREFETCH`).  
- If `crc32` fails or access is denied (PMP), the engine raises a **TMODE_FAULT** in `VNS_STATUS`.  
- TMODE fields are **advisory**; explicit fields in `K/M/bTR/RFmt/IFmt/bTOP` override them.

---

## 6) Security & Robustness

- **Bounds & PMP:** Pointer form must pass PMP/IOPMP checks; length validated against upper bound.
- **CRC/Hash:** `crc32` provides quick integrity; vendors may add a 128‑bit MAC as a vendor extension.
- **Privilege:** `BIT_SECURE` requires privileged callsite or pre‑approved handle registration.
- **DoS Avoidance:** Maximum `length` and binding count limited by `VNS_CAPS` (e.g., 2KB per TMODE).

---

## 7) Latency & Prefetch

- TMODE should be **resident** in L2/SRAM or prefetchable region.  
- Recommended to write TMODE into the **plan cache** (`VNS_PLAN[plan_id]`) for multi‑stage re‑use.  
- With `BIT_PREFETCH`, the dispatcher fetches TMODE on **kernel queueing**, not on the first cycle.

---

## 8) Compatibility Notes

- **Binary compatibility:** MMACC opcode unchanged; the 9th/10th argument is a planner ABI convention.  
- **Tooling:** Assemblers may expose `, TMODE=&sym` syntax; compilers pass the pointer/handle via sideband registers.  
- **Fallback:** Platforms lacking TMODE support ignore the parameter (treated as `NULL`).

---

## 9) Mini Reference: KSEL Catalog

- `CMUL`, `CMUL_CONJ`, `TWIDMUL`  
- `BFLY_R2`, `BFLY_R4`, `BFLY_R8`  
- `MODMUL`, `MODMAC`  
- `CGIVENS`, `CGEMM_SM(2/4/8)`  
- `IDENTITY` (baseline GEMM/MMACC)

---

*(End of Addendum v0.20a)*
