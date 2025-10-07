# RISC-V Memory Encryption Proposal (Draft v0.1)

[KO](RISCV_Memory_Encryption_uArch_(draft)_KO_V_0_1.md) | [EN](RISCV_Memory_Encryption_uArch_(draft)_EN_V_0_1.md)

---

## 1. Overview

This document proposes a low-latency and lightweight memory-encryption engine for RISC-V platforms.
Unlike ongoing community efforts focused on architectural-level confidential-memory frameworks (e.g., ePMP, IOPMP), this draft targets the implementation layer — the microarchitectural design of an inline encryption/decryption engine.

**Goals:**

* **Real-time (zero-stall)** `AES-CTR`-based encryption/decryption for **Secure World**
* **Mitigate side-channel attacks** (access-pattern or correlation leakage) **during Normal → Secure Engine mapping** via `FNV1A` hashing
* Define a **self-contained, low-overhead data-path independent** from architectural policies such as **PMP/ePMP/confidential regions**

---

## 2. Design Objectives

* **Zero-stall, high-throughput** AES-CTR pipeline
* **FNV1A-32** hash for side-channel mitigation at mapping stage
* Configurable **`bwordop`** mode for block-wise or scratchpad-line encryption
* **No interference** with existing PMP/ePMP security mechanisms


---

## 3. Core Design Elements

| Block                              | Key Function                                                           | Design Focus                                                |
| ---------------------------------- | ---------------------------------------------------------------------- | ----------------------------------------------------------- |
| **1. Key / Nonce Generator**       | `nonce = (addr ⊕ epoch ⊕ scramble)` with optional FNV1A entropy mixing | Address-based uniqueness without explicit key rotation cost |
| **2. AES-CTR Pipeline**            | AES128/256 CTR streaming; fully unrolled rounds → 1 block / cycle      | 128-bit alignment; near-zero latency                        |
| **3. XOR Mixer**                   | `AES keystream ⊕ plaintext` at DMA path                                | ≤ 1 cycle delay                                             |
| **4. Hash-Side-Channel Mitigator** | FNV1A32 used only for Normal-World mapping entropy                     | Not used inside Secure World                                |
| **5. Key Rotation FSM**            | Epoch-based hardware rekeying                                          | CPU-free automatic rotation                                 |

---

## 4. FNV1A Usage Policy

> **FNV1A hashing** is applied only in the *Normal World* to obfuscate address-to-engine mappings and **reduce side-channel correlation**.
It is not used for actual memory encryption within the Secure World.

- Secure World → AES-CTR only
- Normal World → FNV1A32 for seed or mapping entropy
- Secure data-path excludes any FNV1A input

---

## 5. `bwordop` Operation Modes

### `bwordop = 1` — Per-Transfer Block Encryption

```c
if (bwordop == 1) {
 if (width == 128) {
  keystream = AES128(SEED, nonce || CTR++);
  out = in ^ keystream;
 } else if (width == 256) {
  keystream = AES256(SEED, nonce || CTR++);
  out = in ^ keystream;
 }
}
```

* Used for native 128 / 256-bit bus interfaces or ultra-low-latency DMA paths.

### `bwordop = 0` — Scratchpad Line-Level Streaming

```c
for (i = 0; i < line_size; i += AES_block_bytes) {
 keystream = AES128(SEED, nonce || CTR++);
 out[i:i+15] = in[i:i+15] ^ keystream;
}
```

* Encrypts an entire scratchpad line (256–512 B) streaming per AES block
* Amortizes AES latency across the line

---

## 6. Secure vs Normal World Integration

| Domain           | Algorithm         | Purpose                     | Integration Level        |
| ---------------- | ----------------- | --------------------------- | ------------------------ |
| **Secure World** | AES-CTR (128/256) | Real-time memory encryption | Memory Controller inline |
| **Normal World** | FNV1A32           | Side-channel scrambler      | Seed / mapping helper    |

---

## 7. Performance Targets

| Metric                | Target                                 |
| --------------------- | -------------------------------------- |
| AES-CTR Throughput    | ≥ 1 block / cycle @ 1 GHz (≈ 128 Gb/s) |
| Added Latency         | ≤ 0.3 cycle avg                        |
| FNV1A Mix Overhead    | ≤ 0.2 cycle                            |
| Key Rotation Interval | ≈ 10⁶ cycles or per context switch     |
| Area Overhead         | ≤ 5 % of memory controller logic       |


---

## 8. Implementation Notes

- Pre-expanded AES key cache in SRAM
- Fully unrolled AES rounds → 1 block / cycle
- Epoch-based Key Rotation FSM
- DMA secure-bit descriptor support
- Cache eviction triggers encrypted writeback

---

## 9. Example Flow

```
CPU Load → Region Check
  ├─ Secure : nonce = Addr ⊕ Epoch
  │  keystream = AES(SEED, nonce || CTR++)
  │  data = enc_data ^ keystream
  └─ Normal : fnv_hash = FNV1A32(addr || domain)
    seed' = seed ⊕ fnv_hash
    pass to engine
```

---

## 10. Conclusion

> 
> This proposal focuses on **the engine-level implementation** rather than policy or ISA-level frameworks.
It aims to **minimize side-channel exposure** between Secure and Normal domains while **achieving real-time, hardware-inline memory encryption**.

---

## Appendix A — Key Design Challenges

- Encryption granularity and metadata organization
- Integrity checking (MAC/Merkle tree) overhead
- Caching metadata without latency penalty
- Multi-core consistency and DMA/I/O integration
- Key management and root of trust protection
- Dynamic secure region management

---

##  Appendix B — Related RISC-V Proposals and Systems

| Proposal / System         | Summary                                                                                                                                                                                                       | Strengths                                          | Limitations                          |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- | ------------------------------------ |
| **Keystone + ePMP + MEE** | Adds Memory Encryption Engine to controller; ePMP tracks secure regions ([CARRV 2024](https://carrv.github.io/2024/papers/CARRV_2024_paper_7.pdf))                                                            | Integrated with monitor; per-region integrity tree | TileLink extension; DMA complexity   |
| **SPEAR-V**               | Tag-based enclave isolation ([TUGraz](https://tugraz.elsevierpure.com/ws/portalfiles/portal/58764488/spearv.pdf))                                                                                             | Low overhead; shared memory support                | Scaling and metadata complexity      |
| **SERVAS**                | Lightweight TEE for embedded RISC-V ([ResearchGate](https://www.researchgate.net/publication/364559448_Lightweight_RISC-V_Trusted_Execution_Environment_with_Hardware-based_Encryption_and_Memory_Isolation)) | Power-efficient; simple domain split               | DMA coherency issues                 |
| **ACE**                   | Formally verified confidential computing ([arXiv](https://arxiv.org/html/2505.12995v1))                                                                                                                       | IOPMP/PMP integration; formal proof                | Limited metadata; dynamic complexity |
| **Dep-TEE**               | Efficient enclave-to-enclave communication ([HPU Lab](https://luhang-hpu.github.io/files/DepTEE-ASPDAC2025.pdf))                                                                                              | Performance/scalability                            | Depends on underlying engine         |
| **Morpheus II**           | Pointer/code encryption and MAC protection ([UTexas](https://www.spark.ece.utexas.edu/pubs/HOST-21-morpheus.pdf))                                                                                             | Runtime integrity                                  | Not full memory encryption           |


---

## Appendix C — Design Lessons and Future Work
  - Metadata caching and compression
  - DMA encryption protocol standardization
  - Multi-core synchronization for secure coherency
  - Formal verification for hardware security
  - Integration of PQC and masking techniques

---

*This draft supplements ongoing RISC-V confidential memory architecture discussions by providing a practical, implementation-oriented approach to low-latency memory encryption.*
