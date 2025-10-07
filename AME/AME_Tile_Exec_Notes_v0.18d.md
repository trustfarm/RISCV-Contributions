# AME Tile Execution Unified Specification (v0.18d)
**Version:** v0.18d (Unified Internal/External Spec)  
**Editor:** TrustFarm / K.T. Ahn  
**Date:** 2025-10-07  

---

## 1. Overview
This unified note consolidates previous versions (v0.18a–v0.18c) into a single, coherent AME Tile execution specification.  
It defines full ISA behavior for both **internal (bTOP=0)** and **external (bTOP=1)** tile modes, including DMA extensions, CSR separation, and runtime signaling.  

---

## 2. Tile Architecture Recap
- **Tile size:** Fixed 256 B.  
- **Geometry:**  
  - 8-bit → 16×16  
  - 16-bit → 16×8  
  - 32-bit → 16×4  
  - 64-bit → 16×2  
- **Sub-Tile Mapping:**  
  - 2×2, 1×4, 4×1, Guarded 4×4 (≤16b outputs).  
- **Note:** Diagrams with 4×4 blocks represent *sub-tiles*, not the entire tile.  

In compact SoCs, the TRF (Tile Register File) can be **logically unified** (A,B,C share same space) or **split** (A,B in TRF, C in A‑RF). Both fall under internal `bTOP=0` mode.

---

## 3. Tile Operation Summary

| bTOP | Mode | Data Location | Typical Usage |
|------|------|----------------|----------------|
| `0` | Internal Unified | TRF only | Compact, small kernels |
| `0` | Internal Separate | T‑RF + A‑RF | Output‑stationary, large tiles |
| `1` | External DMA | External memory / HBM | Streaming GEMM, LLM workloads |

---

## 4. ISA Syntax and Behavior

```asm
C = MMACC(A, B, K, M, bTR, RFmt, IFmt, bTOP)
```
- `A`, `B`: Tile operands (TRF IDs or external addresses).  
- `K`: Elements per row.  
- `M`: Rows per tile.  
- `bTR`: Transpose flag (A×B / A×Bᵀ / Aᵀ×B / Aᵀ×Bᵀ).  
- `RFmt`: Accumulator/output format.  
- `IFmt`: Input format.  
- `bTOP`: Tile Operation Mode (0b internal, 1b external).  

---

## 5. Internal Mode (bTOP=0)

### 5.1 Unified‑Internal Example
```asm
tconfig.t tmask={tA|tB|tC}, rows=16, dtype=fp16
tconfig.a amask={tC},       rows=16, dtype_acc=fp32
tzero     tC
MMACC     tC, tA, tB, K=16, M=16, bTR=00, RFmt=FP32, IFmt=FP16, bTOP=0
tst       tC, [C_base], ldc
```
- A,B,C share same TRF.  
- **No data move needed between TRF and ACC.**
- Ideal for small tiles fitting into 256 B.  

### 5.2 Separate‑Internal Example
```asm
tconfig.t tmask={tA|tB}, rows=16, dtype=bf16
tconfig.a amask={aC},    rows=16, dtype_acc=fp32
tzero     aC
MMACC     aC, tA, tB, K=16, M=16, bTR=00, RFmt=FP32, IFmt=BF16, bTOP=0
aadd      aC, aC_part2
ast       aC, [C_base], ldc
```
- **A,B in TRF, C in dedicated A‑RF.**
- Used when K×M×width > 256 B or for high precision accumulation.  

### 5.3 Behavior Summary
| Condition | TRF Usage | Note |
|------------|------------|------|
| Fits within 256 B | Unified (A,B,C) | Minimal context |
| Exceeds 256 B | Split (A,B vs C) | Dedicated ACC RF |

---

## 6. External Mode (bTOP=1)

### 6.1 External Operand Registers
| Register | Purpose | Description |
|-----------|----------|-------------|
| **Reg1** | Tile A address | External memory address |
| **Reg2** | Tile B address | External memory address |
| **Reg3** | Tile C destination | External accumulator buffer |
| **Reg4** | Extended K/M register | 16+16 bits for large loops |

### 6.2 Example (DMA / PIO Mode)
```asm
li  t1, 0x80000000    ; A
li  t2, 0x90000000    ; B
li  t3, 0xA0000000    ; C
MMACC.T.ext (t3), (t1), (t2), K=128, M=128, bTOP=1
```
- Hardware fetches A/B, performs MAC, writes C via DMA/PIO.  
- Supports asynchronous overlapping execution.  

### 6.3 PTX‑Style Async Flow
```asm
MMACC.async (Reg3), (Reg1), (Reg2), K=128, M=64, bTOP=1
sync.wait_group 0
```
Equivalent to CUDA PTX `wait_group.sync`.  

---

## 7. CSR Architecture

### 7.1 Internal Mode (bTOP=0)
```text
CSR.mx.status (0x7C3)
----------------------------------
[0] busy          Hardware executing async op
[1] signal        Operation complete
[7:2] tile_count  Processed tiles (TRF context)
[15:8] km_progress  K×M loop progress
[31:16] error/stall/status flags
```
Used for internal tile pipelines.

---

### 7.2 External Mode (bTOP=1)
To separate DMA progress tracking, external tile operations use dedicated indexed CSRs.

| CSR Name | Addr | Width | Description |
|-----------|-------|--------|--------------|
| **CSR.mx.status_ext** | `0x7C4` | 32 | DMA/PIO status (busy/signal/error) |
| **CSR.ext_tile_sel** | `0x7C5` | 8 | External tile group selector (0–15) |
| **CSR.ext_tile_count[n]** | `0x7C6 + n` | 16 | Tile count for group *n* |
| **CSR.ext_tile_addr[n]** | `0x7D0 + n` | 64 | Base address for group *n* |

#### Behavior
- `CSR.ext_tile_sel` = current DMA group index (linked to Reg3).  
- Each group maintains independent counter + base address.  
- SoC may implement up to 16 DMA contexts.

#### Example
```asm
csrw ext_tile_sel, 0x03
csrw ext_tile_addr3, 0xA0000000
MMACC.T.ext (t3), (t1), (t2), K=128, M=128, bTOP=1
poll_ext:
  csrr t0, mx.status_ext
  andi t1, t0, 0x1
  bnez t1, poll_ext
  csrr t2, ext_tile_count3
```

#### C Example
```c
uint8_t group = read_csr(CSR_EXT_TILE_SEL);
uint16_t tiles = read_csr(CSR_EXT_TILE_COUNT_BASE + group);
uint64_t addr  = read_csr64(CSR_EXT_TILE_ADDR_BASE + group);
printf("Group %d: Tiles=%u @Addr=0x%llx\n", group, tiles, addr);
```

---

## 8. Unified CSR Summary

| Mode | CSR Used | Domain | Key Fields | Context |
|------|-----------|---------|-------------|----------|
| bTOP=0 | `mx.status` | Internal TRF | busy, signal, tile_count, km_progress | per‑thread context |
| bTOP=1 | `mx.status_ext`, `ext_tile_*` | DMA/PIO | ext_tile_count[n], ext_tile_addr[n] | per‑DMA group |

---

## 9. Runtime Flow (External DMA)

```
1. Select tile group index (CSR.ext_tile_sel = n)
2. Bind Reg3 → CSR.ext_tile_addr[n]
3. Configure K,M and issue MMACC.T.ext
4. DMA fetches A,B → compute → store C
5. CSR.ext_tile_count[n] increments
6. CSR.mx.status_ext updates {busy=0, signal=1}
7. Runtime polls or ISR handles callback
```

---

## 10. Notes for SoC Integration
- DMA controller should signal completion to both `status_ext` and `ext_tile_count[n]`.  
- Implementers may extend `ext_tile_count[n]` to 32‑bit for large loops.  
- `ext_tile_sel` may alias with DMA channel ID.  
- Future AME revisions may add unified async queue semantics.

---

## 11. Revision History

| Version | Summary | Date |
|----------|----------|------|
| v0.18a | Defined internal modes (`bTOP=0`) | 2025‑10‑05 |
| v0.18b | Added DMA async & wait_group | 2025‑10‑06 |
| v0.18c | Split external CSR structure | 2025‑10‑07 |
| **v0.18d** | Unified full spec (internal + external + CSR hierarchy) | **2025‑10‑07** |

---

***All comments welcome — even rough ones, just throw them in.***
