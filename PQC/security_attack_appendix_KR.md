# Appendix: 보안 공격 및 완화 전략 정리

---
[KO](security_attack_appendix_KR.md) | [EN](security_attack_appendix_EN.md) 

---

본 부록은 업로드된 문서에서 다룬 **CacheBleed** 및 관련 사이드채널 공격 논문·자료들을 정리한 것입니다.  
각 섹션은 대응 전략별로 핵심 아이디어와 참고 문헌을 포함합니다.

---

## 1) 비밀 의존 메모리 오프셋 제거 (소프트웨어)
- 핵심 아이디어: 메모리 인덱스(오프셋)를 비밀 값에 의존하지 않게 구현.  
  또는 모든 후보 주소를 항상 접근하여 주소 패턴 누설 제거.

### 참고 문헌
- CacheBleed (Yarom, Genkin, Heninger, 2017) — scatter-gather 불충분성 증명.  
  https://faculty.cc.gatech.edu/~genkin/cachebleed/cachebleed.pdf
- Why Stopping Cache Attacks in Software is Harder Than You Think (van Schaik et al., USENIX Security 2018).  
  https://www.usenix.org/system/files/conference/usenixsecurity18/sec18-van_schaik.pdf
- Breaking Constant-Time Cryptographic Implementations (Chen et al., USENIX Security 2024).  
  https://www.usenix.org/system/files/usenixsecurity24-chen-boru.pdf

---

## 2) 메모리 액세스 균일화 / Whole-Line Load (HW/SW 혼합)
- 캐시 라인 전체를 읽어와 intra-line 오프셋 차이를 제거.  
- Scratchpad 또는 전용 ISA 명령어(PQC.LOAD_LINE) 활용.

### 참고 문헌
- PREFENDER: A Prefetching Defender against Cache Side Channels (2023).  
  https://arxiv.org/pdf/2307.06756.pdf
- Mitigating Conflict-based Cache Side-channel Attacks (Mirage, USENIX 2021).  
  https://www.usenix.org/system/files/sec21fall-saileshwar.pdf
- StackOverflow 토론: https://stackoverflow.com/questions/56385789/loading-an-entire-cache-line-at-once-to-avoid-contention-for-multiple-elements-o

---

## 3) 마스킹 / 수학적 변환
- 비밀 데이터를 랜덤 셰어로 분할(1차/고차 마스킹).  
- ALU/NTT(Number Theoretic Transform)  연산에 mask-aware 연산 제공.

### 참고 문헌
- Ji et al., 2025 — Masked Kyber FPGA 공격 사례.  
  https://link.springer.com/article/10.1007/s13389-025-00375-7
- PQClean: https://github.com/PQClean/PQClean

---

## 4) 하드웨어 차원 완화
- 캐시 매핑 정책 개선, bank conflict 완화.  
- Cache coloring, per-bank bandwidth regulation 적용.

### 참고 문헌
- CEASER (MICRO 2018). https://fast.cc.gatech.edu/papers/MICRO_2018_2.pdf
- Mirage (USENIX 2021). https://www.usenix.org/system/files/sec21fall-saileshwar.pdf
- Per-Bank Bandwidth Regulation (RTSS 2024). https://arg.csl.cornell.edu/papers/cachebankdefense-rtss2024.pdf
- COLORIS (PACT 2014). https://www.cs.bu.edu/fac/richwest/papers/pact2014.pdf
- CATalyst (HPCA 2016). https://class.ece.iastate.edu/tyagi/cpre581/papers/HPCA16Catalyst.pdf

---

## 5) Microcode / Firmware 패치
- 마이크로코드로 dummy access 추가, 직렬화 등을 통한 완화.  
- Patch-first 모델로 즉시 대응 가능.

### 참고 문헌
- Intel Side-channel Mitigation Overview:  
  https://www.intel.com/content/www/us/en/developer/articles/technical/software-security-guidance/technical-documentation/mitigation-overview-side-channel-exploits-linux.html
- PREFENDER (prefetch 기반 완화): https://arxiv.org/pdf/2307.06756.pdf
- RTSS 2024 Per-Bank Regulation: https://arg.csl.cornell.edu/papers/cachebankdefense-rtss2024.pdf

---

## 권장 읽기 순서
1. CacheBleed (원문): https://faculty.cc.gatech.edu/~genkin/cachebleed/cachebleed.pdf
2. Why Stopping Cache Attacks... (van Schaik, 2018).  
3. Per-Bank Bandwidth Regulation, Mirage, CEASER.  
4. PREFENDER.  
5. 마스킹 관련 최신 연구(Ji et al., 2025).

---

## 권장 실무 액션
- 단계 1: CacheBleed PoC 구현 및 검증.  
- 단계 2: PQC ISA에 `LOAD_LINE` 포함.  
- 단계 3: HW 캐시 매핑·bank regulation 적용.  
- 단계 4: 마스킹·블라인딩·Microcode 완화 병행.



[def]: security