
# PQC ISA — 보안 & 패치 가능성 사양 (초안) v0.1 (KR)

---
[KO](PQC_ISA_security_patch_spec_v0_1_KR.md) | [EN](PQC_ISA_security_patch_spec_v0_1_EN.md) 
---

- 작성자: KyuTae Ahn (trustfarm.info@gmail.com, cpplover@trustfarm.net)  
- 라이선스: Apache-2.0, CC BY 4.0 (RISC-V/OpenRISC/OSS Security 플랫폼에 대해 MIT 추가)  
- 이력: Oct 01, 2025 — Draft v0.1

---
## 목적 (Purpose)

이 ISA 제안은 RISC-V를 **PQC(양자내성 암호) 프리미티브**와 기존 암호 코덱(AES 등)으로 확장하면서, **보안(사이드채널 저항/상수 시간)**과 **패치 가능성**을 1급 요구사항으로 삼는 설계 기준을 정의한다.  
본 문서를 기준으로 추후에 
    - 명령어(ISA) 인코딩, 
    - CSR(Control and Status Register) 목록, 
    - 마이크로코드 모델, 
    - 컴파일러/툴체인 매핑, 
    - RTL 레퍼런스, 
    - SCA(사이드채널 분석) 
    - 테스트 계획이 
만들어집니다.

---

## 1. 개요 & 동기

수학적으로 안전한 PQC 알고리즘이라도, **임베디드 SW/SSL/SoC 구현**에서는 타이밍·전력/EM·캐시 등의 **사이드채널 공격**에 대한 대응이 필요합니다.  
따라서 ISA 수준에서 다음이 필요합니다.:

- 각 명령어의 **보안 계약**(상수 시간, 메모리 접근 제약) 정의
- 펌웨어/마이크로코드 업데이트를 통한 **Fail-safe 기능을 제공하여 비활성화 또는 공격회피(완화) 대응**
- 제안이 실행·검증 가능하도록 **레퍼런스 모델(Spike/RTL/테스트)** 제공

---

## 2. Security Scope & Threat Model & Tamper Resistance (보안 범위, 위협 모델, 변조 저항성)

**범위:** Kyber, Dilithium, 기타 격자 또는 해시 기반 PQC, 필요 시 대칭 암호(AES 파이프라인) 및 이를 지원하는 프리미티브(NTT, SHA3/Keccak, RNG)를 포함합니다.

**위협 모델(요약):**
- 공격자는 타이밍, **캐시 동작**, 공유 메모리 채널을 관찰하거나 공동 배치(co‑located) 환경에서 전력/EM 측정을 할 수 있습니다.
- 공격자가 칩을 물리적으로 디캡(decapsulation)하는 행위는 본 제안의 범위 밖입니다.
- 목표: 마이크로아키텍처 사이드채널을 통해 **비밀 키나 중간값이 유출되는 것을 방지**하고, 취약점이 발견되었을 때 **안전한 즉각적 대응방안 제공**을 가능하게합니다.

**우선 보안 목표:**
1. 보안 민감 명령어의 *상수 시간(Constant‑time)* 동작성 확보
2. *비밀 의존적 캐시라인 내 오프셋 금지* [(CacheBleed 완화)](#appendix-a--security-attack-summary--references-cachebleed)
3. 마이크로코드/펌웨어 업데이트 및 `CSR` 기반 disable 경로를 통한 *패치 가능성(Patchability)* 보장
4. *검증 가능성(Verifiability)* — Spike 모델, RTL 스켈레톤, 테스트 벡터, SCA 하네스 제공

>  Security Threat Model 및 Tamper Threat Model 참조.
❗  자세한 내용은 👉  [Appendix Security Threat Model](security_attack_appendix_KR.md)

**Tamper Attack and Resistance Model:** 
- Tamper resistance는 공격자가 장치를 물리적·전자적으로 조작하기 어렵게 만드는 설계 및 제조적 조치를 의미합니다.
일반적으로 다음과 같은 보호 계층(layer)으로 설명됩니다: (보호 코팅, 탐지 센서, 차폐 구조 등)

❗  자세한 내용은 👉 [Appendix Tamper Threat Model](tamper_appendix_KR.md)

---

## 3. Functional ISA Logic (기능적 ISA 로직)

보안 위협과 변조 위협에 대응하기 위해 기능적 ISA 로직은 **I/O를 simplehash 기반으로 스크램블(scramble)** 하고, `register file` 혹은 `scratchpad`를 사용하여 `CRYPTOENGINE`에 안전하게 데이터를 전달하는 패턴을 채택합니다.

> ```
> C_scrmb = CRYPTOENGINE (P_scrmb, K_scrmb, IV_scrmb, b_OP, b_scrmb, b_loadonscp, BlockWidth, TotalLength)
> ```
>   - `CRYPTOENGINE`은 `PQC` 또는 `AES` 등으로 치환됩니다.  
  
**비고:** `scrmb`는 `scramble`을 의미합니다. 

투명한 scrambling 처리는 사이드채널 타이밍 공격 및 캐시(메모리) 블리드 공격을 방지합니다.  
**선택적으로 HW적으로 Cost가 거의 없고,지연(Latency)가 없는 HW Scramble 처리는 다음과 같은 예가 있습니다.**
1. RNG-IV — 스트림으로 들어오는 데이터와 XOR HW 생성된 RANDOM 값을 IV (초기벡터) 로 사용하여 Scramble 하는 방법.
2. 상수(Prime)‑기반의 간단해시 (FNV‑1a variant) 를 scramble 기능에 적용. 참조:[**FNV-1A Hash**](https://en.wikipedia.org/wiki/Fowler%E2%80%93Noll%E2%80%93Vo_hash_function#FNV-1a_hash)
   - **FNV-1a 는 이더리움의 [Ethash FNV-0](https://ethereum.org/developers/docs/consensus-mechanisms/pow/mining/mining-algorithms/ethash/#date-aggregation-function) 로 사용되었고, trustfarm (저자)의 경우 FNV-1A버전으로 수정하였습니다. [TEthashV1 : EIP-1485](https://eips.ethereum.org/EIPS/eip-1485)
3. System clock 을 기반으로 간단한 RND 를 생성하여, 이를 scramble 기능의 IV로 사용.


**필드 및 플래그(의미):**
- `b_loadonscp` (1 bit): 입력(Key, PlainText, IV)을 *scratchpad* 또는 즉시 레지스터 버퍼에 로드합니다. 스트리밍 다중 블록의 경우 파이프라인을 위한 레지스터 파일 더블 버퍼링 권장.  
- `C_scrmb` [O]: 출력 `CipherText`. `b_scrmb=1`인 경우 출력은 스크램블된 ciphertext이며, ISA(또는 마이크로코드)는 메모리에 쓰기 전에 내부적으로 디스크램블해야 합니다.  
- `P_scrmb` [I]: 입력 `PlainText`. `b_scrmb=1`이면 입력은 스크램블되어 내부에서 디스크램블해야 합니다.  
- `K_scrmb` [I]: 입력 Key. `b_scrmb=1`이면 내부에서 디스크램블해야 합니다.  
- `IV_scrmb` [I]: 입력 IV (스크램블 IV 또는 알고리즘 IV). `b_scrmb` 플래그는 IV 값은 scramble하지 않습니다.  
- `b_OP` [I] (2 bits): 연산 모드 — `00`=Decryption, `01`=Encryption, `10`=Patch/Security(완화 호출), `11`=Reserved/Disable PQC block.  
- `BlockWidth`: 블록 폭(비트) — 허용값: 128, 256, 512, 1024.  
- `TotalLength`: 전체 데이터 길이(바이트).

---

### 3.1 Functional ISA primitives (필수 빌딩블록)

PQC ISA는 *상수 시간(constant-time)* 이라는 계약을 갖고 고수준 PQC 알고리즘이 매핑될 수 있는 소수의 저수준 프리미티브를 제공해야 합니다. 

예시 프리미티브 (니모닉):

- `PQC.LOAD_LINE scratch, addr` — PQC 스크래치로 전체 캐시 라인 로드(라인 내 누수 방지)  
- `PQC.NTT.BF rd, rs1, rs2, twiddle_idx` — NTT 버터플라이(모듈러 add/sub/mul)  
- `PQC.POLY.MUL_ACC rd, rs1, rs2` — 다항식 곱·누산  
- `PQC.SHA3.XOF rd, rs1, rs2, len` — SHA3 / XOF 흡수/추출  
- `PQC.RNG_FILL dest, len` — 하드웨어 RNG로 스크래치 영역 채움(증명/증명서 포함 가능)  
- `PQC.MASK.LOAD shareptr, value` — 마스크 셰어를 마스킹 레지스터 파일에 로드  
- `PQC.MASK.OP op, dst, src1, src2` — 마스크 인식 산술 연산(마이크로코드 지원 가능)  
- `PQC.MCODE.CALL idx` — 마이크로코드 완화 루틴 호출(원자적, 보안 영역)

모든 프리미티브는 ISA 스펙으로 명시된 보안 특성(**상수 시간**, **비밀 의존적 라인내 오프셋 금지** 등)을 준수해야 합니다.

---

## 4. Mapping PQC Algorithms to Functional ISA Logic (PQC 알고리즘 ↔ ISA 매핑)

아래는 대표적인 PQC 알고리즘을 *함수형 시그니처 스타일*로 매핑한 예시입니다. 

각각 매핑은 고수준 함수 시그니처 `CRYPTOENGINE`와 내부적으로 필요한 `PQC(...)` 과 같은 내부 ISA 프리미티브와 치환될수 있습니다.


### 4.1 Kyber (KEM) — high‑level operations (Kyber 주요 동작)

Kyber 기본 연산: `KeyGen()`, `Encaps(pk) -> ct, ss`, `Decaps(sk, ct) -> ss`

**ISA 함수 시그니처 (스크램블 인지형):**
```
# Key Generation (generates public key pk_scrmb, secret key sk_scrmb)
(PUBk_scrmb, SECk_scrmb) = PQC_KYBER_KEYGEN(K_seed_scrmb, IV_scrmb, b_scrmb, b_loadonscp, Params, TotalLength)
```
- 입력: `K_seed_scrmb` (b_scrmb=1이면 스크램블된 시드), `Params` (Kyber 파라미터: k, q, n 등)  
- 출력: `PUBk_scrmb` (옵션으로 스크램블된 공개키), `SECk_scrmb` (PQC 보안 스크래치에 저장, 플랫폼이 지원하면 마스킹)  

**내부 흐름 (프리미티브 매핑):**
1. RNG / 시드 확장 — `PQC.RNG_FILL scratch_seed, seed_len`  
2. 행렬/다항 생성 — `PQC.SHA3.XOF ...`로 확장; 트위들(twiddle) 테이블은 `PQC.LOAD_LINE` 정렬 쓰기로 `pqc_scratch_base`에 기록.  
3. 다항식에 대한 NTT 도메인 변환 — `PQC.NTT.BF` 및 `PQC.POLY.MUL_ACC` 프리미티브를 파이프라인 루프에서 사용; `pqc_feat.MASKING_SUPPORTED`일 경우 마스킹 연산 보장.  
4. Pack 및 `PUBk_scrmb` 출력 — 마이크로코드 경로에서 `b_scrmb` 인코딩/디스크램블 적용 가능.


```
# Encapsulation
(ct_scrmb, ss_scrmb) = PQC_KYBER_ENCAP(PUBk_scrmb, RNG_seed_scrmb, IV_scrmb, b_scrmb, b_loadonscp, Params, TotalLength)
```

**내부 단계:**  
- 에페메랄 시드 생성: `PQC.RNG_FILL`  
- 에페메랄 키 및 메시지 유도: `PQC.SHA3.XOF`  
- 다항 연산: NTT 변환, 다항 곱 (`PQC.NTT.BF`, `PQC.POLY.MUL_ACC`)  
- 거부 샘플링(rejection sampling) / 노이즈 처리: 상수 시간 루프; 비밀 의존 인덱싱 회피 (`PQC.LOAD_LINE` 및 고정 시퀀스 접근 사용)  
- ciphertext `ct_scrmb` 패킹; `b_scrmb`=1 이면 마이크로코드가 스크램블 적용 후 저장.


```
# Decapsulation
(ss_scrmb) = PQC_KYBER_DECAP(sk_scrmb, ct_scrmb, IV_scrmb, b_scrmb, b_loadonscp, Params, TotalLength)
```

**노트 & 보안 요구사항 (Kyber):**
- NTT 프리미티브는 상수 시간이어야 한다; `PQC.NTT.BF` 및 `PQC.POLY.MUL_ACC`가 비밀 의존 메모리 오프셋을 노출하지 않도록 보장.  
- 거부 샘플링은 상수 시간으로 구현하거나 안전한 마이크로코드 경로로 옮겨야 함.  
- 마스킹: `pqc_feat.MASKING_SUPPORTED`일 경우 비밀 키 물질은 스크래치패드에 마스킹 상태로 보관.

---

## Glossary — Kyber (KEM) Abbreviations

- **pk** = **PUBk** : *Public Key*  
- **sk** = **SECK** : *Secret Key (Private Key)*  
- **ct** = **CIPHERT** : *Ciphertext*  
- **ss** = **SHRDS** : *Shared Secret*  
- **CSR** = **Control and Status Register** :
    *RISC-V 에서 control and status 정보를 저장하는 레지스터*
    - *PQC ISA 에서는, (pqc_feat, masking support, etc.) 같은 flag 를 저장하고, 마이크로코드 패치를 제어한다. *
- **Constant-Time** : *CryptoEngine 이 동작시에, secret data (keys, messages) 따른 동작시간 및 메모리 접근 타이밍이 일정하게 하여 공격을 방어할수있도록 한다.*
    - *부채널 (side-channel) 공격에 대한 방어기능으로서 필수 기능이다.*
- **Masking** : *민감한 값을 여러 개의 무작위 셰어(share)로 분할하는 대응 기법.*
    - *비밀(secret) 데이터의 누출을 방지한다.*
    - *본 PQC ISA에서는 `PQC.MASK.LOAD`, `PQC.MASK.OP`, 와 제어비트 `pqc_feat.MASKING_SUPPORTED` 를 이용하여 지원된다.*
- **Microcode Mitigation** : *`PQC.MCODE.CALL` 을 호출하여, 마이크로코드의 수정(Patch)/동작변경을 수행한다.*
    - *(Fail-Safe)설계철학에 따라, 새로운 Chip Revision 전에, 보안결함에 대해서 즉각적인 대응방안을 제공한다.*
- **Tamper Resistance** : *공격자가 장치를 물리적·전자적으로 조작하기 어렵게 만드는 설계 및 제조적 조치를 의미합니다. 일반적으로 다음과 같은 보호 계층(layer)으로 설명됩니다: (보호 코팅, 전압/온도탐지 센서, EMI차폐 구조 등)*

### Kyber 기본동작 정리

- **`KeyGen()`** → generates a keypair → returns *(PUBk, SECK)*  
- **`Encaps(PUBk)`** → encapsulates using the public key → returns *(CIPHERT, SHRDS)*  
- **`Decaps(SECK, CIPHERT)`** → decapsulates using the secret key → returns *(SHRDS)*  


### 4.2 Dilithium (CRYSTALS‑Dilithium) — signature scheme (요약)

Top level: `KeyGen(), Sign(sk, msg) -> sig, Verify(pk, msg, sig) -> ok`

**ISA 함수 시그니처: 키생성**
```
# KeyGen
(pk_scrmb, sk_scrmb) = PQC_DILITHIUM_KEYGEN(seed_scrmb, IV_scrmb, b_scrmb, b_loadonscp, Params, TotalLength)
```

**Sign: 서명**
```
# Sign
(sig_scrmb) = PQC_DILITHIUM_SIGN(sk_scrmb, msg_scrmb, IV_scrmb, b_scrmb, b_loadonscp, Params, TotalLength)
```

**Verify: 검증**
```
# Verify
(ok_flag) = PQC_DILITHIUM_VERIFY(pk_scrmb, msg_scrmb, sig_scrmb, IV_scrmb, b_scrmb, b_loadonscp, Params, TotalLength)
```

**필드 및 플래그**
-  입력:
- `pk_scrmb` : 공개키 (스크램블 가능)
- `msg_scrmb` : 메시지 (스크램블 가능)
- `sig_scrmb` : 서명 (스크램블 가능)
- `IV_scrmb`, `b_scrmb`, `b_loadonscp`, `Params`, `TotalLength`
- 출력:
  `ok_flag` (1 bit) : 검증 성공 여부 (1 = 유효, 0 = 실패)


**내부 매핑(빌딩블록):**
1. 시드 확장 → `PQC.SHA3.XOF`로 행렬 A 생성; 정렬 저장.  
2. NTT 프리미티브(`PQC.NTT.BF`, `PQC.POLY.MUL_ACC`)로 다항 곱 수행.  
3. 노름 확인 및 거부 루프: 상수 시간으로 구현되어야 하며, 마이크로코드로 직렬화하여 비밀 종속 분기를 회피.  
4. 챌린지 해시 생성(SHAKE/SHA3) → `PQC.SHA3.XOF`.  
5. 서명 패킹 및 필요 시 스크램블 적용.

**Dilithium 특이 사항:**  
- 메시지+난수를 통한 챌린지 생성은 해시 프리미티브의 메모리 접근 또한 상수 시간이어야 함.  
- 노름/거부 검사(logic)는 상수 시간으로 구현하거나 타이밍 가변을 없애도록 마이크로코드 안전 경로로 이동해야 함.

---

### 4.3 SPHINCS+ (hash‑based signature family) (요약)

Top-level signature call:

**Sign: 서명**
```
# Sign
(sig_scrmb) = PQC_SPHINCS_SIGN(sk_scrmb, msg_scrmb, IV_scrmb, b_scrmb, b_loadonscp, Params, TotalLength)
```

**Verify: 검증**
```
## Verify
(ok_flag) = PQC_SPHINCS_VERIFY(pk_scrmb, msg_scrmb, sig_scrmb, IV_scrmb, b_scrmb, b_loadonscp, Params, TotalLength)

```

**필드 및 플래그**
-  입력:
- `pk_scrmb` : 공개키 (스크램블 가능)
- `msg_scrmb` : 메시지 (스크램블 가능)
- `sig_scrmb` : 서명 (스크램블 가능)
- `IV_scrmb`, `b_scrmb`, `b_loadonscp`, `Params`, `TotalLength`
- 출력:
  `ok_flag` (1 bit) : 검증 성공 여부 (1 = 유효, 0 = 실패)



**내부 매핑:**  
- SPHINCS+는 WOTS, FORS, hypertree 등 많은 해시 연산을 사용하므로 해시 중심의 작업을 `PQC.SHA3.XOF`로 매핑.  
- 트리 탐색 및 인덱스 의존 연산은 **치명적** — 트리 순회 시 비밀 의존 메모리 오프셋을 피해야 하며, 항상 고정된 집합을 접근하거나 `PQC.LOAD_LINE`로 노드 블록을 읽거나 마스크된 인덱싱을 사용.  
- 서명 패킹 및 난수 생성은 `PQC.RNG_FILL` 사용.

**노트:** SPHINCS+는 해시 작업 비중이 높고 인덱스 연산이 많으므로 캐시 뱅크 충돌을 통한 누출을 방지해야 함.

---

### 4.4 Other primitives (기타 프리미티브)

- Lattice‑based: NTT 중심 → `PQC.NTT.BF`, `PQC.POLY.MUL_ACC`로 매핑.  
- Hash‑based: `PQC.SHA3.XOF`, `PQC.SHA3.KECCAK`로 매핑.  
- Code‑based / Multivariate: 일반적으로 테이블 인덱싱이 적음; 필요시 `PQC.POLY.*` 또는 `PQC.MASK.*`로 매핑.  
- Symmetric ciphers (AES 등): 마이크로코드 또는 하드웨어 AES 엔진과 통합; 스트리밍 모드의 경우 `b_scrmb` 처리 포함.

---

## 5. Practical ISA usage examples (실용 예시)

**예시: Kyber encapsulation (고수준 호출)**
```
# assume pk stored in secure region; we request hardware acceleration and scrambling
(ct_scrmb, ss_scrmb) = PQC_KYBER_ENCAP(pk_addr, rnd_seed_addr, iv_addr, b_OP=01, b_scrmb=1, b_loadonscp=1, BlockWidth=256, TotalLength=... )
```
디코드 시 마이크로코드는:
- `pqc_feat` 비트 검증
- `PQC.LOAD_LINE`로 pk를 스크래치패드에 로드
- 상수 시간 루프에서 NTT 프리미티브 호출
- `ct_scrmb` 생성 후, 마이크로코드가 디스크램블을 적용하고 메모리에 기록(또는 설정에 따라 소프트웨어가 적용)

---

## 6. Security & Patchability notes (요약)

- **비밀 의존적 캐시라인 내부 오프셋 금지**: 각 PQC 프리미티브의 기능적 의미론에서 필수. 구현체는 전체 라인 로드(`PQC.LOAD_LINE`)를 사용하거나 후보 오프셋 전부에 대해 일정하고 결정론적 순서로 접근해야 합니다.  
- **마이크로코드 완화**: `pqc_mcode_hash` 및 마이크로코드 오버라이드 테이블을 사용하여 하드웨어 리비전 전까지 빠른 완화(더미 접근, 직렬화)를 배포할 수 있어야 합니다.  
- **마스킹 및 블라인딩**: 비밀 저장 및 산술에는 우선순위가 높습니다; `pqc_feat.MASKING_SUPPORTED`가 설정된 경우 마스크 대응 ALU를 구현하세요.  
- **폴백(Fallback)**: 하드웨어 기능이 없거나 비활성화된 경우 알려진 SCA 보증을 가진 `libpqc_sw_fallback.a`(소프트웨어)를 사용하세요.

---

## 7. Next steps (검토 및 반복을 위한 제안)

1. Kyber, Dilithium, SPHINCS+에 대한 함수 서명 및 매핑을 검토하고 수정할 파라미터 또는 플래그를 편집하세요.  
2. 검토 후 각 기능적 시그니처를 다음으로 변환합니다:
   - 구체적 명령어 인코딩 / opcode 맵(비트 레벨)  
   - 마이크로코드 오버라이드 예제(의사코드)  
   - 고수준 PQC 함수용 Spike 모델 핸들러

---

## Appendix A — Security attack summary & references (CacheBleed)

- CacheBleed 원 논문: Yarom, Genkin, Heninger — "CacheBleed: A Timing Attack on OpenSSL Constant‑Time RSA"  
  URL: https://faculty.cc.gatech.edu/~genkin/cachebleed/cachebleed.pdf

(포이씨 패키지와 SCA 체크리스트에서 추천되는 CacheBleed 테스트 케이스: victim NTT 구현, attacker bank‑conflict probe, 측정 파라미터 등)

---
