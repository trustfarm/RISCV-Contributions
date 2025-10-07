# PQC Kyber / Dilithium ASIC/FPGA Design Reference Materials

> 목적: Kyber/Dilithium 하드웨어 구현(ASIC/FPGA) 설계를 위한 “도면 중심” 레퍼런스 10편의 핵심 요약과 대표 도면 위치(페이지) 안내.

---

## 1) A Compact and High-Performance Hardware Architecture for CRYSTALS-Dilithium (TCHES 2022)
- 포인트: 서명 전 과정을 커버하는 고성능 Dilithium 하드웨어 아키텍처. 공유/재사용 가능한 NTT/폴리연산 파이프라이닝이 핵심.  
- 성능-면적 균형 및 메모리/BRAM 구성, butterfly/NTT 배선 갈등 해결이 설계 포인트.  
- ASIC/FPGA 양쪽을 염두에 둔 연산 재배치와 모듈 경량화 기법 제시.  
- 도면: 256-point FFT/NTT 구조, 시스템 블록, BRAM 배열, decompose·mod-q 블록 등.  
- 대표도면 위치: Fig.1(256-pt FFT, P5-6), Fig.2(System arch, P6), Fig.6(BRAM array, P9-10), Fig.7(NTT block graph, P11-12), Fig.11–14(Decompose/Mod-q, P15–18).  
**링크:** https://tches.iacr.org/index.php/TCHES/article/view/9297/8863

---

## 2) KiD: Unified NTT for Kyber & Dilithium on FPGA (arXiv 2311.04581)
- 포인트: Kyber/Dilithium 겸용 “통합 NTT” 프레임워크(라딕스-2 BFU 수 가변).  
- 충돌 없는 메모리 매핑으로 완전 파이프라인 운영, Artix-7/Zynq/US+ 검증.  
- BFU 재구성으로 Kyber(12-bit)·Dilithium(23-bit) 계수 폭 차이 흡수.  
- 설계 3종(2/4/8 BFU for Kyber ↔ 1/2/4 BFU for Dilithium)과 ADP 비교.  
- 대표도면 위치: Fig.1 Cooley-Tukey & Gentleman-Sande butterfly(페이지 P1).  
**링크:** https://arxiv.org/abs/2311.04581

---

## 3) KyberMat: Matrix-Vector Poly Mult. Co-Design for Kyber (arXiv 2310.04618)
- 포인트: Polyphase+NTT 기반의 **행렬-벡터 다항 곱셈**을 FIR/서브구조 공유로 최적화.  
- 트랜스포즈/오리지널 구조 모두에 서브구조 공유를 도입해 mod-mul/adder 횟수 절감.  
- 임의 병렬도(4/8 등)를 아키텍처 파라미터화 → 지연↓, 처리율↑.  
- FPGA 결과와 복잡도 테이블 제시(연산량 20–30%대 절감 예시).  
- 대표도면 위치: Fig.3(a–d) 데이터플로(서브구조 공유, P4), Fig.5 4-parallel transposed 구조(사례, P5), Table III 복잡도 비교(P6).  
**링크:** https://arxiv.org/abs/2310.04618

---

## 4) Flexible Shared Accelerator for Kyber & Dilithium with SCA Protection (NIST PQC’22)
- 포인트: Kyber/Dilithium **겸용 가변 성능(경량/중간/고성능)** 아키텍처.  
- 런타임 보안레벨 선택, Kyber 마스킹(1차 DPA 대응) 구현/TVLA 결과 포함.  
- 단일/결합 아키텍처 비교에서 **자원 대비 지연** 우수성 제시.  
- 실무 관점에서 사이드채널 고려한 하드웨어 통합 설계 레퍼런스.  
- 대표도면 위치: 성능 폴라차트 Figs.6–10(P10–14), TVLA Figs.12–13(P15).  
**링크:** https://csrc.nist.gov/csrc/media/Events/2022/fourth-pqc-standardization-conference/documents/papers/a-flexible-shared-hardware-accelerator-pqc2022.pdf

---

## 5) High-Performance Hardware Implementation of Lattice-Based Digital Signatures (NIST PQC’22)
- 포인트: 공개 코드 기반 고성능 Dilithium 구현 및 병목(샘플링/NTT/리젝션) 해소 전략.  
- 2×2 butterfly로 **두 레이어 동시 처리**→ 메모리 접근 감소, 서명 파이프라인 분리.  
- Keccak 다중 코어로 샘플링 숨기기, 스케줄링 최적화 예시 풍부.  
- FALCON verify 비교까지 포함, 설계 trade-off 파악에 유용.  
- 대표도면 위치: NTT butterfly/아키텍처(페이지 10–12), 서명 스케줄(12–13), 결과/자원(24).  
**링크:** https://csrc.nist.gov/csrc/media/Events/2022/fourth-pqc-standardization-conference/documents/papers/high-performance-hardware-implementations-pqc2022.pdf

---

## 6) Implementing CRYSTALS-Dilithium Signature Scheme on FPGAs (ACM ARES 2021)
- 포인트: **최초의 VHDL 기반 Dilithium FPGA** 구현 보고(키생성/서명/검증).  
- 서명/검증 초당 처리량 수만 TPS급으로 실험치 제시.  
- 모듈화된 다항연산/해시 블록 설계 및 자원-성능 트레이드오프.  
- 이후 다수 연구의 비교 기준점(베이스라인) 역할.  
- (ACM 유료, 초록/메타데이터 공개)  
**링크:** https://dl.acm.org/doi/10.1145/3465481.3465756

---

## 7) Hardware Acceleration for High-Volume Operations of Kyber & Dilithium (ACM/T-RETS 2024)
- 포인트: **대량 처리(batch) 가속**에 특화된 HLS 기반 Kyber/Dilithium HW/SW 코디자인.  
- 데이터 이동 병목을 **배치-처리 파이프라인**으로 완화, 소프트웨어 대비 **3–9×** 가속.  
- ML-KEM/ML-DSA로의 이행 시 성능 추세 보존 가능성 논의.  
- 자원-성능 비교 및 에너지/스루풋 평가 포함.  
- 실제 서비스형 시나리오에서의 최적 배치 크기 추정도 제시.  
**링크:** (학술DB/출판사 링크 참조)

---

## 8) Compact & Low-Latency FPGA-Based NTT Architecture for CRYSTALS-Kyber (MDPI *Information* 2024)
- 포인트: **경량 NTT(순/역 지원) 하이브리드 설계**로 Artix-7에서 최고 417 MHz 달성.  
- 다단 파이프라인 BFU + 효율적 계수 접근 패턴으로 **저지연/저자원** 구현.  
- 541 LUT, 680 FF, BRAM×4 등 **소형 자원** 구성 제시.  
- IoT급 단말 타깃 경량화에 초점.  
**링크:** https://www.mdpi.com/2078-2489/15/7/400

---

## 9) A Pipelined Hardware Design of FNTT & INTT of CRYSTALS-Kyber (MDPI *Information* 2025)
- 포인트: **6-stage 파이프라인 U-BTF**(CT/GS 통합)로 FNTT/INTT를 단일 버터플라이로 처리.  
- Virtex-6/7 실측: FNTT 898cy / INTT 1028cy(U-BTF 기준), 전체 NTT 설계 1410/1540cy.  
- BRAM ping-pong, Barrett-based mod-q 단일화로 자원 절감.  
- FoM(throughput/slices)로 기존 대비 ~62% 개선 사례 제시.  
**링크:** https://www.mdpi.com/2078-2489/16/1/17

---

## 10) FPGA Energy Consumption of Post-Quantum Cryptography (NIST PQC’22)
- 포인트: FPGA에서 PQC(포함: Kyber/Dilithium) **에너지 소비**를 비교 분석.  
- 실제 측정 vs Vivado 추정 비교로 **추정치 신뢰도**도 논의.  
- 구현군별(고속/경량) 에너지 특성 파악에 좋은 베이스라인.  
- NIST PQC 2022 수락 논문 목록에도 등재.  
**링크:** https://csrc.nist.gov/csrc/media/Events/2022/fourth-pqc-standardization-conference/documents/papers/fpga-energy-consumption-of-pqc-pqc2022.pdf

---

## Figure 캡처 + 페이지 표

| # | 논문 | 대표 도면(캡션 요지) | 페이지/위치 |
|---|---|---|---|
| 1 | TCHES’22 Dilithium | Fig.1 256-pt FFT/NTT, Fig.2 시스템, Fig.6 BRAM, Fig.7 NTT 그래프, Fig.11–14 Decompose/Mod-q | P5–6, P6, P9–10, P11–12, P15–18 |
| 2 | KiD (arXiv 2311) | Fig.1 CT/GS butterfly(통합 NTT 배경) | P1 |
| 3 | KyberMat (arXiv 2310) | Fig.3(a–d) 데이터플로(서브구조 공유), Fig.5 4-parallel transposed | P4–5 |
| 4 | NIST Flexible Shared Accel (2022) | Figs.6–10 성능 폴라차트, Figs.12–13 TVLA 테스트 | P10–15 |
| 5 | High-Perf. Lattice Sigs (슬라이드) | NTT 2×2 butterfly/아키텍처, 서명 스케줄 | P10–13, P24 |
| 6 | FPGA Energy Consumption (2022) | Table I RTL 구현 요약, 에너지 그래프 | P0–1, (중후반 그래프들) |
| 7 | MDPI Info 2025 FNTT/INTT | Figure 1 전체 아키텍처, Figure 2 U-BTF 6-stage, Table 2–3 성능 | P6, P7–8, P10–11 |
| 8 | DATE’21 Kyber 폴리멀트 | 유니파이드 BFU/레이어 병합 블록도 | (초중반 도면 섹션) |
| 9 | PQShield NTT (2024) | NTT 파이프라인/메모리 토폴로지 개략 | (중반 도식) |
|10 | RNS-based Kyber Multiplier (2024) | RNS 모듈/테이블 분해, 단/이중 BFU 흐름 | (초중반 도면) |

---

### 주의
- 일부 논문은 유료 접근(ACM 등)일 수 있습니다. 도면/페이지 표시는 공개본 또는 저자 슬라이드 기준으로 기입했으며, 최종 페이지는 출판사 버전에 따라 차이가 있을 수 있습니다.
