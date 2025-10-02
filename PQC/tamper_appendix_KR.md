# Appendix: Tamper Resistance / Anti‑Tampering (통합 정리)

---
[KO](tamper_appendix_KR.md) | [EN](tamper_appendix_EN.md) 
---

## Tamper Resistance 핵심 정리

### 1. 정의와 계층
- **Tamper resistance**: 장치 내부를 물리적·전기적으로 조작하기 어렵게 만드는 설계·공정·패키징 기법.  
- 관련 계층:
  1. Tamper resistance (난해성 증가)
  2. Tamper evidence (조작 흔적 탐지 가능)
  3. Tamper detection (실시간 탐지)
  4. Tamper response (감지 시 즉시 대응 / zeroization 등)

### 2. 공격 유형
- **Invasive (침습적)**: 칩 디패키징, 금속층 제거, 프로빙 등 (예: IC delayering, probing).  
- **Semi‑invasive (반침습적)**: 레이저/광학 펄스, 전압/클럭 펄스 주입, 국소적 결함 유발.  
- **Non‑invasive (비침습적)**: 전력/EM/열/온도/시간 등 외부에서 간접적으로 조작·누설을 유도.

참조: [NIST Physical Security Testing materials.](https://csrc.nist.gov/csrc/media/events/physical-security-testing-workshop/documents/papers/physecpaper19.pdf)

### 3. 주요 방어 기법 (요약)
- **패키지·물리적 방호**: 금속 실드, 강화 케이스, potting, conformal coating.  
- **센서 기반 탐지**: probe sensor mesh (metal mesh), light/pressure/magnetic sensors, tamper switches.  
- **전원/클럭/온도 감시**: 이상 신호 감지 시 안전 모드 전환.  
- **Self‑zeroization / secure erase**: tamper 감지 시 키 삭제 또는 메모리 무작위화.  
- **노이즈 삽입 / 전력 필터링**: 외부 측정·프로빙을 어렵게 만드는 전력선 노이즈.  
- **논리적 보조**: 연산 중복/무결성 체크, 랜덤화, 체크섬, 분산/중복 모듈로 복원성 확보.  
- **Microcode / Firmware 대응**: tamper 감지 시 microcode로 동작을 안전하게 바꾸거나 즉시 disable/zeroize.

### 4. 주요논문 및 자료요약

| 논문 / 자료                                                                            | 핵심 내용 요약                                                                               | 시사점 / 왜 참고할 가치 있는가                                           |
| ---------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| *Cryptographic Processors — A Survey* (Anderson 등)                                 | tamper-resistant 하드웨어의 역사, 공격/방어 기법 정리. 다양한 cryptoprocessor 사례 포함. ([cl.cam.ac.uk][1]) | tamper protection의 다양한 전통적 전략들과 한계점을 알 수 있음                  |
| *Tamper-resistant cryptographic hardware*                                          | 암호 하드웨어 구현 시 tamper-resistance 고려 사항, 공격 대응 방식 등을 논의                                   | 하드웨어 설계 단계에서 고려할 사항 체크리스트로 유용 ([ResearchGate][2])            |
| *Hardware-Based Methods for Electronic Device Protection* (Vidaković 등)            | anti-tampering 보호의 4단계 정의 및 다양한 하드웨어 방어 방법 정리                                          | tamper 계층별 전략 구조 설계 시 좋은 기준 ([MDPI][3])                      |
| *Founding Cryptography on Tamper-Proof Hardware Tokens* (Goyal et al.)             | 이론적으로 tamper-proof 하드웨어를 암호학적 기반 토큰으로 활용하는 방식 제안                                       | 하드웨어 토큰 기반 보안 모델 설계 시 참고할 수 있음 ([iacr.org][4])               |
| *Anti-Tamper Radio: System-Level Tamper Detection*                                 | 장치 내부 무선 전파 경로 변화를 이용해 조작 시도를 감지하는 시스템 설계                                              | 금속 케이스 내부 조작 감지용 novel 방안 제시 ([arXiv][5])                    |
| *A testing methodology for side channel resistance validation*                     | 논리 게이트 수준에서 동적 전력 누설 분석을 통해 side-channel / tamper resistance 검증 방법 제안                  | 설계 검증 시 자동화된 SCA / tamper 테스트 도입에 유용 ([Semantic Scholar][6]) |
| *A Touch of Evil: High-Assurance Cryptographic Hardware from Untrusted Components* | 여러 COTS 보안 코프로세서를 중복/분산 구성하여 hardware Trojan / backdoor 저항성 확보                         | supply-chain 공격 대응 아키텍처 설계 인사이트 제공 ([arXiv][7])              |

[1]: https://www.cl.cam.ac.uk/techreports/UCAM-CL-TR-641.pdf "Cryptographic processors - a survey"
[2]: https://www.researchgate.net/publication/312873398_Tamper-resistant_cryptographic_hardware "(PDF) Tamper-resistant cryptographic hardware"
[3]: https://www.mdpi.com/2079-9292/12/21/4507 "Hardware-Based Methods for Electronic Device Protection ..."
[4]: https://www.iacr.org/archive/tcc2010/59780306/59780306.pdf "Founding Cryptography on Tamper-Proof Hardware Tokens"
[5]: https://arxiv.org/abs/2112.09014 "Anti-Tamper Radio: System-Level Tamper Detection for Computing Systems"
[6]: https://www.semanticscholar.org/paper/A-testing-methodology-for-side-%C2%AD-channel-resistance-Goodwill-Jun/97b6be2eaeebe1e13696e928e94f66b4c93719b8 "A testing methodology for side channel resistance validation"
[7]: https://arxiv.org/abs/1709.03817 "A Touch of Evil: High-Assurance Cryptographic Hardware from Untrusted Components"

### 5. 실무 설계 권고 (RISC‑V PQC 관점)
1. 하드웨어 설계에 **probe sensor mesh** 포함: 금속층 위/아래로 센서망 배치.  
2. `pqc_ctl` CSR에 tamper 관련 플래그/이벤트 필드 추가: 예) `PQC_CTL.TAMPER_FLAG`, `PQC_CTL.ZEROIZE_TRIGGERED`.  
3. tamper 이벤트시 동작 로직: microcode 또는 secure-firmware에서 **atomic zeroize** 수행.  
4. 전력/클럭/온도 이상 감지 시 즉시 PQC extension 비활성화 및 로그 기록.  
5. secure boot + signed microcode: microcode 업데이트는 서명 확인 후 설치, 설치 전후 `pqc_mcode_hash`로 원격/로컬 감시.  
6. SCA 테스트 벤치에 tamper 시나리오 포함: 전압/클럭 글리치, 레이저, depackaging 시도 등.

### 6. 주요 참고 문헌 (full URLs)
- "Tamper Resistance — a Cautionary Note" (Ross Anderson). https://www.cl.cam.ac.uk/archive/rja14/tamper.html
- "Hardware-Based Methods for Electronic Device Protection" (Vidaković et al., MDPI). https://www.mdpi.com/2079-9292/12/21/4507
- NIST Physical Security Testing workshop paper. https://csrc.nist.gov/csrc/media/events/physical-security-testing-workshop/documents/papers/physecpaper19.pdf
- "A Touch of Evil: High‑Assurance Cryptographic Hardware from Untrusted Components". https://arxiv.org/abs/1709.03817
- "Anti‑Tamper Radio: System‑Level Tamper Detection". https://arxiv.org/abs/2112.09014


