## Tamper Resistance — Overview & Recommendations

---
[KO](tamper_appendix_KR.md) | [EN](tamper_appendix_EN.md) 
---

### 1. Definition & Layers

- **Tamper resistance** refers to design and manufacturing measures that increase the difficulty for an adversary to physically or electronically manipulate a device. Commonly described layers:
  1. Tamper resistance
  2. Tamper evidence
  3. Tamper detection
  4. Tamper response (e.g., zeroization)

### 2. Attack Categories
- **Invasive**: physical removal of package and direct probing (delayering, FIB probing).  
- **Semi‑invasive**: fault injection via laser, EM pulses, voltage/clocks affecting circuits without opening packaging fully.  
- **Non‑invasive**: side‑channel/fault attacks from outside (power glitches, EM pulses, thermal, etc.).

Reference: [NIST physical security testing materials.](https://csrc.nist.gov/csrc/media/events/physical-security-testing-workshop/documents/papers/physecpaper19.pdf)

### 3. Defensive Techniques (summary)
- **Package-level protections**: metal shields, potting, conformal coatings.  
- **Sensor-based detection**: metal mesh/probe sensors, light/pressure sensors, tamper switches.  
- **Voltage/clock/temperature monitors**: trigger safe-mode when anomalies detected.  
- **Automatic zeroization / secure erase**: wipe keys on detection.  
- **Noise injection / power filtering**: make probing or fine-grained measurements harder.  
- **Logical aids**: redundancy, randomized execution, integrity checks, threshold/distributed modules.  
- **Microcode/FW response**: switch to safe microcode path or disable functionality on detection.

### 4. Prefable Papers and Summarize

| Paper / Document                                                                            | Abstract                                                                               | Implication / Why It is Considerable                                           |
| ------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| *Cryptographic Processors — A Survey* (Anderson et al.)                                     | Summarizes the history of tamper-resistant hardware, attack/defense techniques, and includes various cryptoprocessor case studies. ([cl.cam.ac.uk][1]) | Helps understand diverse traditional strategies of tamper protection and their limitations |
| *Tamper-resistant cryptographic hardware*                                                   | Discusses considerations of tamper-resistance and attack countermeasures in cryptographic hardware implementation. | Useful as a checklist of considerations at the hardware design stage ([ResearchGate][2]) |
| *Hardware-Based Methods for Electronic Device Protection* (Vidaković et al.)                | Defines a four-level model of anti-tampering protection and summarizes diverse hardware defense methods. | Provides a solid baseline when designing strategy structures per tamper-resistance level ([MDPI][3]) |
| *Founding Cryptography on Tamper-Proof Hardware Tokens* (Goyal et al.)                      | Proposes a theoretical model of using tamper-proof hardware tokens as a foundation for cryptographic systems. | Useful reference for designing hardware token-based security models ([iacr.org][4]) |
| *Anti-Tamper Radio: System-Level Tamper Detection*                                          | Designs a system that detects tampering attempts by exploiting changes in internal RF propagation paths. | Provides a novel approach for detecting tampering inside metal cases ([arXiv][5]) |
| *A testing methodology for side channel resistance validation*                              | Proposes a method to validate side-channel/tamper resistance through dynamic power leakage analysis at the logic gate level. | Valuable for introducing automated SCA/tamper testing during design validation ([Semantic Scholar][6]) |
| *A Touch of Evil: High-Assurance Cryptographic Hardware from Untrusted Components*          | Builds resilience against hardware Trojans/backdoors by composing multiple COTS security coprocessors redundantly/distributed. | Provides architectural insights for defending against supply-chain attacks ([arXiv][7]) |

[1]: https://www.cl.cam.ac.uk/techreports/UCAM-CL-TR-641.pdf "Cryptographic processors - a survey"
[2]: https://www.researchgate.net/publication/312873398_Tamper-resistant_cryptographic_hardware "(PDF) Tamper-resistant cryptographic hardware"
[3]: https://www.mdpi.com/2079-9292/12/21/4507 "Hardware-Based Methods for Electronic Device Protection ..."
[4]: https://www.iacr.org/archive/tcc2010/59780306/59780306.pdf "Founding Cryptography on Tamper-Proof Hardware Tokens"
[5]: https://arxiv.org/abs/2112.09014 "Anti-Tamper Radio: System-Level Tamper Detection for Computing Systems"
[6]: https://www.semanticscholar.org/paper/A-testing-methodology-for-side-%C2%AD-channel-resistance-Goodwill-Jun/97b6be2eaeebe1e13696e928e94f66b4c93719b8 "A testing methodology for side channel resistance validation"
[7]: https://arxiv.org/abs/1709.03817 "A Touch of Evil: High-Assurance Cryptographic Hardware from Untrusted Components"

### 5. Practical Recommendations for RISC‑V PQC
1. Integrate **probe sensor mesh** into package/PCB layout; connect to secure monitor domain.  
2. Extend `pqc_ctl` CSR set with tamper event flags: e.g., `PQC_CTL.TAMPER_ALERT`, `PQC_CTL.ZEROIZE_REQ`.  
3. Provide atomic zeroize routines callable from microcode and secure firmware; ensure that zeroize path clears scratchpad, masked shares, microcode staging area.  
4. Monitor supply and clock rails with high‑resolution ADCs and fast comparators to detect glitch attempts.  
5. Enforce signed microcode updates and include `pqc_mcode_hash` in remote attestation.  
6. Incorporate tamper scenarios into SCA/FA test plans (glitching, laser, depackaging).

### 6. Key References (full URLs)
- "Tamper Resistance — a Cautionary Note" (Ross Anderson). https://www.cl.cam.ac.uk/archive/rja14/tamper.html  
- "Hardware-Based Methods for Electronic Device Protection" (Vidaković et al., MDPI). https://www.mdpi.com/2079-9292/12/21/4507  
- NIST Physical Security Testing workshop paper. https://csrc.nist.gov/csrc/media/events/physical-security-testing-workshop/documents/papers/physecpaper19.pdf
- "A Touch of Evil: High-Assurance Cryptographic Hardware from Untrusted Components". https://arxiv.org/abs/1709.03817
- "Anti‑Tamper Radio: System‑Level Tamper Detection". https://arxiv.org/abs/2112.09014

---

*Document generated for PQC‑on‑RISC‑V design review. If you want, I can:*
- add a one‑page visual checklist for PCB/packaging teams, or
- generate CSR spec snippets (bitfields) for tamper flags, or
- integrate this appendix into the main ISA MD file.
