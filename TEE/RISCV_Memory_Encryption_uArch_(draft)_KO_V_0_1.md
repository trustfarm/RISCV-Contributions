# RISC-V 메모리 암호화 아키텍처 제안서 (Draft v0.1)

[KO](RISCV_Memory_Encryption_uArch_(draft)_KO_V_0_1.md) | [EN](RISCV_Memory_Encryption_uArch_(draft)_EN_V_0_1.md)

---
## 1. 개요

본 문서는 현재 RISC‑V 커뮤니티에서 논의 중인 **아키텍처 레벨의 보안 메모리(Confidential Memory) 프레임워크**와는 별도로, 실제 하드웨어 수준에서 동작하는 **저지연 (low‑latency)** 및 **경량 (lightweight) 메모리 암호화 엔진** 구조를 제안한다.

**본 제안의 핵심 목표는 다음과 같다:**

* **Secure World** 영역의 메모리를 AES‑CTR 기반으로 실시간(무지연) 암호화 및 복호화
* **Normal World**에서 암호 데이터나 키를 Encryption Engine으로 매핑할 때 발생할 수 있는 **사이드채널 공격 (특히 접근 패턴 및 상관 분석)** 완화
* **ePMP, IOPMP, Confidential Region** 등의 아키텍처 정책과는 독립적으로 동작하며, **저오버헤드 암호화 파이프라인** 을 하드웨어 레벨에서 정의

---

## 2. 설계 목표

* **Zero‑stall / 고처리량(high‑throughput)** AES‑CTR 암복호화 파이프라인
* **FNV1A32** 해시를 활용한 Normal → Secure 매핑 시 사이드채널 리스크 감소
* **`bwordop`** 모드를 통해 블록 단위 또는 라인 단위 암호화 선택 가능
* 기존 PMP/ePMP 정책과의 충돌 없이 독립적으로 동작

---

## 3. 핵심 설계 요소

| 블록                          | 주요 기능                                                                | 설계 중점                    |
| --------------------------- | -------------------------------------------------------------------- | ------------------------ |
| **1. Key 및 Nonce 생성기**      | Nonce = (physical addr ⊕ epoch ⊕ scramble) <br> FNV1A32 scrambler 적용 | 키 교체 비용 없이 주소 기반 비중복성 보장 |
| **2. AES‑CTR 파이프라인**        | AES128/256 CTR 스트리밍 <br> Unrolled rounds → 1 block / cycle 처리        | 128b 라인 정렬, 지연 0 수준 달성   |
| **3. XOR 믹서**               | AES keystream ⊕ plain data <br> DMA path 실시간 XOR                     | XOR 지연 ≤ 1 cycle         |
| **4. Hash‑SideChannel 완화기** | Normal World 매핑 시 FNV1A32 mix 적용                                     | Secure World 내 에서는 사용 안함 |
| **5. Key 회전 FSM**           | Epoch 단위 자동 키 교체 및 갱신                                                | CPU 개입 불필요 (하드웨어 FSM 제어) |

---

## 4. FNV1A 해시 사용 정의

>  **FNV1A의 목적:** Normal World 상태에서 암호 데이터나 키를 Encryption Engine에 매핑할 때 접근 패턴 또는 데이터 상관성에 의한 사이드채널 공격을 완화하기 위함이다. 해당 해시는 Secure World 내 메모리 암호화에는 사용되지 않는다.

* Secure World → AES‑CTR 암호화만 적용
* Normal World → FNV1A32 는 seed 또는 매핑용 보조 해시로만 사용
* Secure path 내에서는 FNV1A 입력 배제

---

## 5. `bwordop` 운용 모드

### `bwordop = 1` (전송 블록 단위 암호화)

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

* 버스 native 폭(128/256b)에 적합, 초저지연 환경 용도

### `bwordop = 0` (Scratchpad 라인 스트리밍 암호화)

```c
for (i = 0; i < line_size; i += AES_block_bytes) {
 keystream = AES128(SEED, nonce || CTR++);
 out[i:i+15] = in[i:i+15] ^ keystream;
}
```

* Scratchpad 라인 (256 ~ 512 B) 단위 스트리밍 암호화
  - AES 지연을 라인 단위 로 분산하여 처리량 최대화

---

## 6. Secure / Normal World 통합

| 구분                 | 알고리즘                | 목적                    | 적용 계층                      |
| ------------------ | ------------------- | --------------------- | -------------------------- |
|  **Secure World**  |  AES‑CTR (128/256)  |  실시간 메모리 암호화          |  Memory Controller Inline  |
|  **Normal World**  |  FNV1A32            |  사이드채널 완화용 Scrambler  |  엔진 매핑 및 Seed Mixing       |

---

## 7. 성능 목표

| 항목                   | 목표 수치                                  |
| -------------------- | -------------------------------------- |
|  AES‑CTR Throughput  |  ≥ 1 block / cycle @ 1 GHz (128 Gb/s)  |
|  추가 메모리 지연           |  ≤ 0.3 cycle                           |
|  FNV1A mix 오버헤드      |  ≤ 0.2 cycle                           |
|  Key 회전 주기           |  약 10⁶ cycles 또는 context switch 기준     |
|  면적 오버헤드             |  ≤ 5 % (Memory Controller 기준)          |

---

## 8. 구현 권장 사항

* AES Key 사전 전개 (Cache 저장) 및 Unrolled Round 구현
  - Epoch 기반 Key 자동 회전 FSM 도입
  - DMA Secure‑bit Descriptor 통합 암복호화 지원
  - Cache Evict 시 자동 Encrypt Writeback 경로 적용

---

## 9. 동작 흐름 예시

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

## 10. 결론

본 제안은 RISC‑V 아키텍처 수준의 보안 프레임워크 논의와는 독립적으로, **실제 하드웨어 암복호화 엔진의 저지연·경량화 구현 방안** 을 제시한다. 

이 문서는 정책적 수준이 아닌 **엔진 레벨 구현(Implementation Layer)** 을 초점으로 두며, Secure/Normal 간 사이드채널 노출을 최소화하고 실시간 암호화를 지원하는 구체적 마이크로아키텍처를 제안한다.

---

##  부록 A — 핵심 설계 요소 및 기술 도전과제


    - 암호화 단위(Granularity) 및 Metadata 관리
    - 무결성 검증용 MAC/Merkle Tree 관리 구조
    - 캐시 메타데이터 오버헤드 최소화 및 성능 저하 방지
    - 다중 코어 일관성 및 DMA/I/O 연동
    - Key 관리 및 Root of Trust 보호 메커니즘
    - 확장성 및 동적 보안 영역 관리

---

##  부록 B — 관련 연구 및 RISC‑V 메모리 암호화 제안

|  제안 / 시스템                   |  핵심 내용                                                                                                                                                                                      |  강점                        |  한계                         |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- | --------------------------- |
|  **Keystone + ePMP + MEE**  |  메모리 컨트롤러에 암호화 엔진 추가, ePMP 로 보호 영역 추적 ([CARRV 2024](https://carrv.github.io/2024/papers/CARRV_2024_paper_7.pdf))                                                                            |  보안 모니터 통합, 영역별 무결성 트리 지원  |  TileLink 확장 필요, DMA 처리 복잡  |
|  **SPEAR‑V**                |  태깅 및 격리 기반 Enclave 보호 ([TUGraz](https://tugraz.elsevierpure.com/ws/portalfiles/portal/58764488/spearv.pdf))                                                                                |  저오버헤드, 공유 메모리 지원          |  확장성 및 메타데이터 복잡성            |
|  **SERVAS**                 |  임베디드 환경용 경량 TEE ([ResearchGate](https://www.researchgate.net/publication/364559448_Lightweight_RISC-V_Trusted_Execution_Environment_with_Hardware-based_Encryption_and_Memory_Isolation))  |  저전력 설계 적합                 |  DMA 일관성 보장 어려움             |
|  **ACE**                    |  형식 검증 기반 Confidential Computing ([arXiv](https://arxiv.org/html/2505.12995v1))                                                                                                             |  PMP/IOPMP 통합, 형식 검증 지원    |  메타데이터 제약 및 구성 복잡           |
|  **Dep‑TEE**                |  Enclave 간 통신 효율화 ([HPU Lab](https://luhang-hpu.github.io/files/DepTEE-ASPDAC2025.pdf))                                                                                                     |  성능 향상 및 확장성               |  기저 암호엔진 의존성 높음             |
|  **Morpheus II**            |  코드 포인터 암호화 및 MAC 기반 제어 흐름 보호 ([UTexas](https://www.spark.ece.utexas.edu/pubs/HOST-21-morpheus.pdf))                                                                                        |  실행 무결성 보장                 |  전체 메모리 암호화 범위 아님           |

---

##  부록 C — 설계 교훈 및 향후 연구 방향
    - 메타데이터 오버헤드 감소 및 캐싱 전략
    - DMA 암호화 버스 프로토콜 확립
    - 다중 코어 간 동기화 및 보안 일관성 유지
    - 형식 검증(formal verification) 기반 보안성 평가
    - PQC 및 마스킹 기법 통합 탐색

---

*본 문서는 RISC‑V 메모리 암호화 분야의 기초 아키텍처 논의를 보완하며, 구현 중심의 실용적 방안을 제시하기 위한 초안이다.*

