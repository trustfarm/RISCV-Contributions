# Appendix: Security Attacks and Mitigation Strategies (English)

---
[KO](security_attack_appendix_KR.md) | [EN](security_attack_appendix_EN.md) 

---

This appendix summarizes **CacheBleed** and related side-channel attack papers with mitigation strategies.  
Each section provides the core idea and references (with full URLs).

---

## 1) Secret-dependent Memory Offset Removal (Software)
- Idea: Refactor implementations to avoid secret-dependent memory indices.  
  Or always access all candidate entries to eliminate address-pattern leakage.

### References
- CacheBleed (Yarom, Genkin, Heninger, 2017).  
  https://faculty.cc.gatech.edu/~genkin/cachebleed/cachebleed.pdf
- Why Stopping Cache Attacks in Software is Harder Than You Think (van Schaik et al., USENIX Security 2018).  
  https://www.usenix.org/system/files/conference/usenixsecurity18/sec18-van_schaik.pdf
- Breaking Constant-Time Cryptographic Implementations (Chen et al., USENIX Security 2024).  
  https://www.usenix.org/system/files/usenixsecurity24-chen-boru.pdf

---

## 2) Memory Access Equalization / Whole-Line Load (HW/SW hybrid)
- Load an entire cache line (via ISA or scratchpad) to eliminate intra-line offset leakage.  

### References
- PREFENDER: A Prefetching Defender against Cache Side Channels (2023).  
  https://arxiv.org/pdf/2307.06756.pdf
- Mitigating Conflict-based Cache Side-channel Attacks (Mirage, USENIX 2021).  
  https://www.usenix.org/system/files/sec21fall-saileshwar.pdf
- StackOverflow discussion: https://stackoverflow.com/questions/56385789/loading-an-entire-cache-line-at-once-to-avoid-contention-for-multiple-elements-o

---

## 3) Masking / Mathematical Transformations
- Split secrets into random shares (first-/higher-order masking).  
- Provide mask-aware ALUs/NTT(Number Theoretic Transform) primitives in hardware.

### References
- Ji et al., 2025 — Masked Kyber FPGA attack study.  
  https://link.springer.com/article/10.1007/s13389-025-00375-7
- PQClean (masked reference implementations). https://github.com/PQClean/PQClean

---

## 4) Hardware-level Mitigations
- Improve cache mapping policy and reduce bank conflicts.  
- Apply cache coloring, per-bank bandwidth regulation.

### References
- CEASER (MICRO 2018). https://fast.cc.gatech.edu/papers/MICRO_2018_2.pdf
- Mirage (USENIX 2021). https://www.usenix.org/system/files/sec21fall-saileshwar.pdf
- Per-Bank Bandwidth Regulation (RTSS 2024). https://arg.csl.cornell.edu/papers/cachebankdefense-rtss2024.pdf
- COLORIS (PACT 2014). https://www.cs.bu.edu/fac/richwest/papers/pact2014.pdf
- CATalyst (HPCA 2016). https://class.ece.iastate.edu/tyagi/cpre581/papers/HPCA16Catalyst.pdf

---

## 5) Microcode / Firmware Patching
- Insert dummy accesses, serialize patterns via microcode/firmware.  
- Patch-first model is directly useful.

### References
- Intel Side-channel Mitigation Overview.  
  https://www.intel.com/content/www/us/en/developer/articles/technical/software-security-guidance/technical-documentation/mitigation-overview-side-channel-exploits-linux.html
- PREFENDER (prefetch-based defense). https://arxiv.org/pdf/2307.06756.pdf
- RTSS 2024 Per-Bank Regulation. https://arg.csl.cornell.edu/papers/cachebankdefense-rtss2024.pdf

---

## Recommended Reading Order
1. CacheBleed original: https://faculty.cc.gatech.edu/~genkin/cachebleed/cachebleed.pdf  
2. Why Stopping Cache Attacks (van Schaik, 2018).  
3. Per-Bank Regulation, Mirage, CEASER.  
4. PREFENDER.  
5. Masking-related research (Ji et al., 2025).

---

## Recommended Practical Actions
- Step 1: Reproduce CacheBleed PoC with PQC NTT victim + probe.  
- Step 2: Add `LOAD_LINE` primitive in PQC ISA.  
- Step 3: Apply HW-level cache mapping/bank regulation.  
- Step 4: Apply masking, blinding, and microcode mitigations.

