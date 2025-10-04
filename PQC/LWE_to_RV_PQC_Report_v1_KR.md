# LWE → RLWE → NTT → Keccak / RV‑PQC 설계 리포트 V1


[KO](LWE_to_RV_PQC_Report_v1_KR.md) | [EN](LWE_to_RV_PQC_Report_v1_EN.md)
---

## 1️⃣ 개요

양자 컴퓨터가 발전하면서 기존 공개키 암호(RSA, ECC 등)는 양자 알고리즘(Shor 등)에 의해 깨질 가능성이 커졌습니다.  
이를 대비하기 위해 등장한 것이 **양자 내성 암호(Post-Quantum Cryptography, PQC)** 입니다.

이 리포트는 PQC에서 가장 핵심적인 수학적 구조인 **LWE → RLWE → NTT → Keccak(SHA-3)** 의 연계를 설명하고,  
이를 기반으로 한 **RISC-V PQC(RV-PQC)** 하드웨어 설계 흐름을 다룹니다.

---

## 2️⃣ LWE (Learning With Errors)

### 기본 아이디어

> "작은 잡음(noise)이 포함된 선형 방정식에서 비밀을 추정하는 것은 어렵다."

비밀 벡터 $s \in \mathbb{Z}_q^n$ 에 대해, 여러 선형 방정식이 주어집니다.

$$
b_i = \langle a_i, s \rangle + e_i \pmod{q}
$$

여기서
- $a_i$: 공개된 난수 벡터
- $b_i$: 결과값 (공개)
- $e_i$: 작은 오차 (Noise)
- $s$: 비밀 벡터 (찾고자 하는 값)

**공격자는** $(a_i, b_i)$ 쌍들만 보고 $s$를 알아내야 합니다.  
하지만 작은 오차 $e_i$ 때문에 정확히 맞추기 어려워집니다.

### 난이도의 근거

LWE는 **격자(Lattice) 문제**로 환원됩니다.  
즉, 격자에서 짧은 벡터를 찾는 문제(GapSVP, SIVP)가 효율적으로 풀리지 않는 한, LWE도 어렵습니다.  
따라서 LWE는 양자 컴퓨터에서도 안전한 기반으로 평가받습니다.

### 참고

- NIST PQC 개요: https://csrc.nist.gov/projects/post-quantum-cryptography  
- LWE 설명: https://en.wikipedia.org/wiki/Learning_with_errors

---

## 3️⃣ RLWE (Ring Learning With Errors)

### 왜 LWE를 확장하는가?

LWE는 벡터와 행렬을 사용합니다.  
하지만 고차원에서는 계산량이 너무 커지므로, **다항식(polynomial)**으로 표현하는 방식이 등장합니다.  
이것이 **RLWE(Ring LWE)** 입니다.

### 수학적 구조

$$
b(x) = a(x) \cdot s(x) + e(x) \pmod{(x^n + 1, q)}
$$

여기서 $a(x), s(x), e(x)$ 는 모두 $R_q = \mathbb{Z}_q[x]/(x^n + 1)$ 에 속합니다.

행렬 곱 대신 다항식 곱으로 바뀌며,  
이 곱은 **순환 합성곱(cyclic convolution)**으로 계산됩니다.

### 순환 행렬 관점

다항식 $a(x)$는 순환 행렬(Circulant matrix)으로 표현할 수 있습니다.

$$
A =
\begin{pmatrix}
a_0 & a_{n-1} & \cdots & a_1 \\
a_1 & a_0 & \cdots & a_2 \\
\vdots & \vdots & \ddots & \vdots \\
a_{n-1} & a_{n-2} & \cdots & a_0
\end{pmatrix}
$$

즉, RLWE의 다항식 곱셈은 LWE의 행렬-벡터 곱과 구조적으로 동일합니다.

### 참고

- LWE -> RLWE 개념최조제안 논문 분석 및 NIST 의 취약점 대응내용
    - [**Appendix A - Lyubashevsky et al., “On Ideal Lattices and Ring-LWE”**](#-appendix-a-on-ideal-lattices-and-ring-lwe-lyubashevsky-peikert-regev-2012) 
- CRYSTALS-Kyber 프로젝트 (https://pq-crystals.org/kyber/)

---

## 4️⃣ NTT (Number Theoretic Transform)

### FFT와 NTT의 차이

FFT는 실수/복소수 공간에서의 변환입니다.  
NTT는 **정수(mod q)** 공간에서 동일한 아이디어를 적용한 변환입니다.

### NTT 정의

$$
A_k = \sum_{j=0}^{n-1} a_j \cdot \omega^{jk} \pmod{q}, \quad k=0,\dots,n-1
$$

역변환(iNTT)은 다음과 같습니다.

$$
a_j = n^{-1} \sum_{k=0}^{n-1} A_k \cdot \omega^{-jk} \pmod{q}
$$

$\omega$는 $n$차 원시근(primitive n-th root of unity)입니다.

### 주요 특징

- 다항식 곱을 **NTT → 점별곱 → iNTT** 로 효율적으로 계산 ($O(n \log n)$)
- **고정 크기**: NTT의 크기 $n=256$ 은 설계 시 결정됨 (입력에 따라 변하지 않음)
- 하드웨어 구현 시 병렬도($P$), 곱 병렬도($W$) 등 주요 파라미터 존재

#### 🔹 주요 PQC 알고리즘의 NTT 크기 (n) 요약

| Algorithm                 | Type             | Uses NTT?    | Polynomial Degree ($n$) | Modulus ($q$) | Notes                                                                                                                                                                                          |
| ------------------------- | ---------------- | ------------ | ----------------------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Kyber**                 | KEM (encryption) | ✅ Yes        | **256**                 | 3329          | Uses **integer NTT** (FNTT + INTT) with radix-2 butterflies; optimized for small $q$ and modular reduction. The reference for most PQC hardware accelerators.                                  |
| **Dilithium**             | Signature        | ✅ Yes        | **256**                 | 8380417       | Uses **same NTT core as Kyber**, but higher modulus allows larger dynamic range for signature noise; operates on **vectors of 256-point polynomials** (e.g., 4–6× 256).                        |
| **Saber**                 | KEM              | ⚠️ Partial   | 256                     | $2^{13}$      | Performs polynomial multiplication via **Toom-Cook and schoolbook methods**, not a true NTT; implemented over power-of-two modulus for efficient bit-shifts instead of modular roots of unity. |
| **NTRU**                  | KEM              | ⚙️ FFT-like  | 701                     | 2048 or 4096  | Uses **cyclic convolution mod $(x^{701}−1)$**; FFT-style transform applied in some optimized variants; relies on coefficient wrapping instead of modular roots.                                |
| **Falcon**                | Signature        | ⚙️ FFT-based | 512 / 1024              | 12289         | Uses **floating-point FFT** (not integer NTT); achieves extremely compact signatures but requires precise rounding and floating-point hardware.                                                |
| **FrodoKEM**              | KEM              | ❌ No         | —                       | 2¹⁵           | Based on **standard LWE matrix multiplication**; no transform or cyclic structure; computationally heavy but conceptually simple and secure.                                                   |
| **BIKE / HQC / McEliece** | Code-based       | ❌ No         | —                       | —             | Use **error-correcting code algebra (binary/GF(2))**; involve bitwise XOR, permutation, and decoding rather than polynomial or NTT arithmetic.                                                 |



### 병렬도 모델

| 구분 | 범위 | 설명 |
|------|------|------|
| $P$ (버터플라이 병렬도) | 1 ~ 16 | 한 번에 처리하는 버터플라이 연산 수 |
| $W$ (점별곱 병렬도) | 1 ~ 32 | 한 번에 처리하는 계수 곱 개수 |

예시:  
- $n=256, P=4$ → $C_{NTT} \approx 256$ clocks  
- $P=8$ → $C_{NTT} \approx 128$ clocks  
- $P=16$ → $C_{NTT} \approx 64$ clocks  

다항식 곱(=NTT + iNTT + pointwise)은 약 **512~768 clocks** (P=4), **288~384 clocks** (P=8)

### 참고

- Number Theoretic Transform 설명: https://www.nayuki.io/page/number-theoretic-transform-integer-dft  
- Kyber GitHub: https://github.com/pq-crystals/kyber

---

## 5️⃣ Keccak / SHA-3 / SHAKE

### SHA-3의 표준화

Keccak은 NIST의 SHA-3 공모전에서 2012년 우승하여, 2015년 **FIPS PUB 202**로 공식 표준화되었습니다.  
문서: https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.202.pdf

SHA-3 표준군에는 다음이 포함됩니다.

| 이름 | 출력 길이 | 용도 |
|------|------------|------|
| SHA3-224/256/384/512 | 고정 출력 해시 | 일반 해시 |
| SHAKE128 / SHAKE256 | 가변 출력 XOF | PQC 시드 확장, KDF 등 |

### PQC에서의 역할

- **시드 확장(Seed Expansion)**: 작은 난수(seed)에서 거대한 행렬/잡음 다항식 생성  
- **KDF(Key Derivation)**: 공유 비밀로부터 키 생성  
- **메시지 해시**: 서명 검증 시 바인딩

### 하드웨어 고려사항

Keccak-f[1600]은 1600비트 상태를 24라운드 반복하는 비트단위 퍼뮤테이션입니다.

- **Full Unroll**: 24라운드 전부 병렬 → 빠르지만 면적 큼  
- **Partial Unroll**: 일부 병렬 (예: 4~6라운드) → 균형적  
- **Iterative**: 1라운드씩 순차 처리 → 면적 최소, 속도 느림

RV-PQC에서는 Keccak을 XOF로 스트리밍하며,  
NTT의 소비율에 맞춰 **언롤 정도(unroll factor $u$)** 를 설계합니다.

### 참고

- Keccak 공식 사이트: https://keccak.team/keccak.html  
- NIST PQC 결과: https://csrc.nist.gov/projects/post-quantum-cryptography/finalists

---

## 6️⃣ RV-PQC 하드웨어 설계 연계

### (1) NTT ↔ Keccak 대역폭 정합

- NTT는 다항식 1개를 약 128~256 clocks에 소비  
- Keccak은 XOF로 데이터를 지속 공급해야 함  
- Keccak 언롤 정도 $u$를 NTT 소비율에 맞춰 조정

### (2) DMA / FIFO / 스트리밍 구조

- Keccak → NTT 사이를 **AXI-Stream** 또는 **DMA 기반 버퍼**로 연결  
- Keccak의 SQUEEZE 출력이 NTT 입력 FIFO로 바로 들어가도록 설계  
- IRQ/드라이버 개입 없이 지속 스트리밍 유지

### (3) 보안 옵션

- **Constant-time** 연산  
- **Masking (1st-order 이상)**  
- **중간 상태 스크럽(scrub)**

### (4) 실측 논문 예시

- IEEE 10839700: https://ieeexplore.ieee.org/document/10839700  
  → Keccak/NTT 병렬 처리 최적화, P≈8, W≈8 수준
- DBpia 논문: https://www.dbpia.co.kr/journal/articleDetail?nodeId=NODE12331348  
  → 임베디드 지향 NTT 가속기, P=4~8 범위

---
### (5) PQC 가속기 공개논문 기반 주요 Implication

- "A Pipelined Hardware Design of FNTT and INTT of CRYSTALS-Kyber PQC Algorithm" 
- 자세한 분석내용은 [Appendix 참고](#-appendix-b-mdpi-2025-논문-기반-분석-예시분석--implication)

> **주요 Implication**
> - ####  Keccak 언롤 정도 $u$ 예측
> 
> | 시나리오 | NTT 클록 (C_NTT) | Keccak 대역폭 요구 | 권장 언롤 $u$ (24 라운드 기준) |
> |-----------|-------------------|----------------------|----------------------|
> | 저면적형 (P=1) | ≈ 1000 clocks | 저 (수 MB/s 수준) | $u ≈ 0.1$ (1 round/10 cycles) |
> | 균형형 (P=8) | ≈ 256 clocks | 중 (수 백 MB/s) | $u ≈ 0.3 ∼ 0.5$ (1 round/2–3 cycles) |
> | 고성능형 (P=16) | ≈ 128 clocks | 높음 (> 1 GB/s) | $u ≈ 0.6 ∼ 1.0$ (1 round/1–1.5 cycles) |
> - MDPI 논문의 경우 P=1이므로 Keccak XOF bandwidth 요구가 낮음.  
> - RV-PQC에서는 NTT가 훨씬 빠르므로 Keccak 언롤 팩터 $u ≈ 0.4$ 이상 필요.

---
## 7️⃣ 결론

- **LWE → RLWE → NTT → Keccak** 흐름은 PQC 하드웨어의 핵심 구조다.  
- LWE는 수학적 난이도, RLWE는 효율적 구조, NTT는 속도, Keccak은 난수/시드 확장 역할을 맡는다.  
- RV-PQC 설계자는 **NTT 파이프라인의 클록당 처리율에 맞춰 Keccak의 언롤 정도를 조정**해야 한다.  
- 일반적으로 $P=W=8$ 수준이 균형적이며, ASIC 환경에서는 $P=W=16$까지 확장 가능하다.

---
## 8️⃣ 요약 및 향후 방향

- **핵심 흐름**: LWE → RLWE → NTT → Keccak 구조는 PQC 하드웨어 설계의 표준적 경로입니다.
- **설계 포인트**: NTT의 병렬도(P, W)와 Keccak의 언롤 팩터(u)를 맞추는 것이 RV-PQC의 성능/자원 균형에 중요합니다.
- **실제 구현**: 임베디드/저면적 환경에서는 P=1~2, 고성능/ASIC 환경에서는 P=W=8~16이 권장됩니다.
- **메모리/스트리밍**: DMA, AXI-Stream, 멀티뱅크 구조를 활용해 NTT와 Keccak 사이의 데이터 흐름을 최적화해야 합니다.
- **보안 고려**: Constant-time, Masking, 중간 상태 스크럽 등 하드웨어 보안 옵션을 반드시 적용해야 합니다.
- **향후 과제**: PQC 알고리즘별 NTT/Keccak 파라미터 최적화, 실측 기반 throughput/area trade-off 분석, 차세대 RV-PQC 아키텍처 연구가 필요합니다.

---

### 📚 주요 참고자료

- NIST PQC 프로젝트: https://csrc.nist.gov/projects/post-quantum-cryptography  
- FIPS 202 (SHA-3 표준): https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.202.pdf  
- Kyber 공식 사이트: https://pq-crystals.org/kyber/  
- Keccak 공식 페이지: https://keccak.team/  
- Lyubashevsky et al., "On Ideal Lattices and Ring-LWE": https://eprint.iacr.org/2012/230.pdf  
- Number Theoretic Transform 소개: https://www.nayuki.io/page/number-theoretic-transform-integer-dft  
- IEEE 10839700 논문: https://ieeexplore.ieee.org/document/10839700  
- DBpia 논문: https://www.dbpia.co.kr/journal/articleDetail?nodeId=NODE12331348

---

# 📘 Appendix A. On Ideal Lattices and Ring-LWE (Lyubashevsky, Peikert, Regev, 2012)

> **논문:** [On Ideal Lattices and Ring‑LWE](https://eprint.iacr.org/2012/230.pdf)  
> **저자:** Vadim Lyubashevsky, Chris Peikert, Oded Regev  
> **출판:** IACR ePrint Archive, 2012/230  
> **목적:** LWE 문제를 다항식 링 위로 확장한 *Ring-LWE* 문제를 제안하고, 그 보안성을 *Ideal Lattice* 문제와 연결시킴.

---

## A.1 논문 개요

이 논문은 **LWE(Learning With Errors)** 문제의 효율성을 높이기 위해,  
벡터와 행렬이 아닌 **다항식(polynomial)** 과 **다항식의 링(Ring)** 을 사용하는 *Ring‑LWE (RLWE)* 문제를 제안합니다.  
또한, 이 RLWE의 보안성이 **이상 격자(Ideal Lattice)** 의 최악 경우 문제(worst-case problem)와 등가임을 보입니다.

### 📗 주요 기여
1. **Ideal Lattice 개념 도입**  
   - LWE의 격자에 곱셈 구조를 부여한 “이상 격자” 정의.
2. **Ring-LWE 문제 제안**  
   - 효율성을 위해 다항식 기반 구조 사용.  
   $$ b(x) = a(x)·s(x) + e(x) \pmod{q, f(x)} $$
1. **보안 환원 증명 (Security Reduction)**  
   - RLWE의 보안성을 Ideal-SIVP 등의 격자 문제로 환원.
2. **파라미터 조건 명시**  
   - 차수 $n$, 모듈러스 $q$, 오차 분포 폭 $\sigma$ 의 선택 조건.

---

## A.2 Ideal Lattice와 Ring-LWE 구조

### (1) Ideal Lattice 정의
- 격자(Lattice)에 “곱셈” 연산이 추가된 구조로, $R = \mathbb{Z}[x]/(f(x))$  형태.
- Ring-LWE의 격자는 $R_q = \mathbb{Z}_q[x]/(f(x))$ 로 표현됨.
- 이 격자는 다항식의 계수를 통해 곱셈이 가능 → 효율적 연산 구조 제공.

### (2) Ring-LWE 문제 정의
$$
\text{Given } (a_i(x), b_i(x)=a_i(x)·s(x)+e_i(x)) \text{ over } R_q, \text{ find } s(x)
$$

- $a_i(x)$, $b_i(x)$, $s(x)$, $e_i(x)$ 모두 $R_q$ 상의 다항식.
- 오차항 $e(x)$ 는 가우시안 분포를 따름.
- 연산은 모듈러 $q$ 와 다항식 $f(x)$ 에 대해 수행.

---

## A.3 RLWE의 효율성 및 수학적 근거

- LWE보다 **메모리 효율**이 높고, **곱셈이 순환 합성곱(cyclic convolution)** 으로 처리 가능.  
  → NTT(Number Theoretic Transform)로 병렬화 용이.  
- 보안성은 여전히 **격자 문제 기반**으로 유지됨.
- 즉, RLWE는 구조를 추가하면서도 안전성은 LWE 수준으로 보장한다는 점이 핵심.

---

## A.4 RLWE의 한계와 약점

RLWE는 강력하지만, 구조화된 격자(ideal lattice)를 사용하기 때문에 잠재적인 위험요소를 내포합니다.

### (a) Ideal Lattice의 구조적 위험
- 일반 LWE보다 **구조적 대칭성(symmetry)** 이 많음.  
  → 일부 공격(Subring, Automorphism attack) 가능성.
- 특정 $f(x)$ 선택 시 약한 구조 발생 가능.

🟢 **NIST 대응:**  
Kyber, Dilithium 등은 $f(x)=x^n+1$ 형태의 **Cyclotomic polynomial**만 사용.  
이 형태는 수학적으로 가장 안전하며, 알려진 구조적 공격 없음.

---

### (b) 파라미터 민감성
- 보안성은 세 변수 $(n, q, \sigma)$ 에 의존.  
- 작은 $n$이나 작은 오차폭은 공격자에게 유리.

🟢 **NIST 대응:**  
Kyber (n=256, q=3329), Dilithium (n=256, q=8380417) 등은  
128/192/256-bit 보안 수준을 보장하는 조합으로 검증 완료.

---

### (c) Decisional vs Search RLWE 간 난이도 불일치
- 일부 링 구조에서 두 문제(Search / Decision)가 동일 난이도가 아닐 수 있음.

🟢 **NIST 대응:**  
Kyber는 **Module-LWE (MLWE)** 구조를 채택하여 일반성을 복원함.  
즉, RLWE를 작은 다항식 벡터 공간 형태로 확장해 구조적 편향을 완화.

---

### (d) 오차 생성 분포의 편향
- RNG나 샘플러 편향 시 비밀키 유출 가능.

🟢 **NIST 대응:**  
Kyber/Saber는 **centered binomial distribution (CBD)**,  
Dilithium은 **SHAKE 기반 deterministic noise generator** 사용.

---

### (e) Side-channel 취약성
- NTT나 modular reduction 중 데이터 의존 분기가 생기면 정보 누출.

🟢 **NIST 대응:**  
모든 공식 구현(PQClean, libOQS 등)은 **constant-time NTT**와 **데이터 독립 연산**을 사용.

---

### (f) 복호 오류(Decryption Failure) 공격
- 오차 분포가 크면 복호 실패 확률 증가 → 통계적 키 누출 가능.

🟢 **NIST 대응:**  
Kyber의 실패 확률은 2⁻⁸⁰ 이하로 제어됨.  
실패 확률은 통계적으로 무시 가능 수준.

---

## A.5 요약표

| 약점 유형 | 설명 | NIST PQC 완화 방법 |
|------------|------|------------------|
| Ideal lattice 구조 | 대칭성 공격 가능성 | Cyclotomic ring만 사용 |
| 파라미터 취약성 | 작은 n, q, σ 선택 시 위험 | Kyber/Dilithium 파라미터 검증 완료 |
| Decisional RLWE | Search RLWE와 난이도 차이 | Module-LWE 확장 |
| 오차 분포 편향 | RNG 편향 → 키 노출 | CBD/SHAKE 기반 노이즈 생성 |
| Side-channel | 데이터 의존 연산 위험 | constant-time 구현 필수 |
| Decryption failure | 오류 통계 → 키 누출 | Kyber는 실패확률 2⁻⁸⁰ 이하 |

---

## A.6 결론

- **Lyubashevsky–Peikert–Regev (2012)** 의 논문은 RLWE 개념의 기반이 된 근본 논문입니다.  
- RLWE는 구조적 효율성을 얻으면서도 격자 기반 보안성을 유지하지만, 구조로 인한 잠재적 약점이 존재했습니다.  
- NIST PQC 표준(특히 Kyber, Dilithium)은 이러한 위험을 완전히 고려하여 **Cyclotomic Ring**, **CBD 노이즈**, **Module-LWE 확장** 등으로 모두 커버했습니다.  

결과적으로, **오늘날의 NIST 표준 PQC는 RLWE의 모든 이론적·실제적 약점을 완화한 안전한 형태**로 발전했습니다.

---
**참조:**  
- https://eprint.iacr.org/2012/230.pdf  
- https://pq-crystals.org/kyber/  
- https://pq-crystals.org/dilithium/  
- https://csrc.nist.gov/projects/post-quantum-cryptography  

---

## 📘 Appendix B. MDPI 2025 논문 기반 분석 (예시분석 + Implication)

> **논문**: A Pipelined Hardware Design of FNTT and INTT of CRYSTALS-Kyber PQC Algorithm  
> **저자**: Muhammad Rashid et al.  
> **저널**: *Information*, 2025, 16(1), 17  
> **DOI**: https://doi.org/10.3390/info16010017  
> **원문**: https://www.mdpi.com/2078-2489/16/1/17  

---

### B.1 설계 요약

| 항목 | 내용 |
|------|------|
| **타깃 알고리즘** | CRYSTALS-Kyber |
| **변환 유형** | FNTT + INTT |
| **구조적 특징** | 단일 Unified Butterfly Unit (U-BTF) 기반, FNTT/INTT 통합 |
| **파이프라인 깊이** | 내부 6단계 pipeline |
| **병렬도** | 단일 버터플라이 (즉, P ≈ 1) |
| **동작 주파수** | Virtex-7 FPGA: 290 MHz / Virtex-6 FPGA: 256 MHz |
| **지연** | FNTT: 898 cycles / INTT: 1028 cycles |
| **전체 처리** | 약 1410 cycles (로드 + 변환 + 출력 포함) |
| **자원 사용량** | Virtex-7: 312 slices / Virtex-6: 398 slices |
| **BRAM/ROM 구조** | 2 × dual-port BRAM + 1 × twiddle ROM |
| **FoM (throughput / area)** | 기존 대비 +62 % 개선 보고 |

---

### B.2 주요 관찰 (Observations)

1. **통합 U-BTF 구조**  
   - FNTT와 INTT를 동일한 하드웨어 모듈로 처리 → 자원 절감 극대화.  
   - 단일 버터플라이 및 멀티플렉서 전환 구조 → 면적 ↓, 클록수 ↑.

2. **파이프라인 중심 구조**  
   - 병렬도보다는 파이프라인 딥닝으로 throughput 확보.  
   - 6-stage pipeline으로 critical path 단축 → 290 MHz 동작 확보.

3. **지연 특성**  
   - 내부 변환만 ≈ 900–1000 cycles → P=1 수준의 설계.  
   - 우리가 제시한 P=8 모델(128 clocks/폴리)보다 약 7–8배 지연.

4. **자원 활용**  
   - DSP 없이 논리 + BRAM 만으로 구현 → 면적 효율형 설계.  
   - 소형 FPGA 타깃에서 Kyber NTT 가속에 적합.

---

### B.3 P · W 수치 유효 범위 재조정

| 설계 타입 | 병렬도 P 범위 | 곱병렬도 W 범위 | 주 전략 | 예상 지연 (256-pt 기준) |
|------------|----------------|----------------|---------|----------------|
| **저면적 (임베디드 / FPGA 소형)** | 1 ~ 2 | 1 ~ 2 | 단일 U-BTF, 깊은 pipeline | ≈ 900–1500 clocks |
| **균형형 (중형 FPGA / SoC)** | 4 ~ 8 | 4 ~ 8 | 다중 버터플라이 + 얕은 pipeline | ≈ 250–500 clocks |
| **고성능 (ASIC / 가속기)** | 8 ~ 16 | 8 ~ 16 | 광폭 병렬 + inter-stage pipeline | ≈ 100–250 clocks |

➡ MDPI 논문 구조는 **P ≈ 1, W ≈ 1** 형태로, 깊은 파이프라인 중심.  
➡ RV-PQC에서는 NTT 스루풋을 Keccak 공급률과 맞추기 위해 **P ≥ 8** 이상 권장.

---

### B.4 Keccak 언롤 정도 $u$ 예측

| 시나리오 | NTT 클록 (C_NTT) | Keccak 대역폭 요구 | 권장 언롤 $u$ (24 라운드 기준) |
|-----------|-------------------|----------------------|----------------------|
| 저면적형 (P=1) | ≈ 1000 clocks | 저 (수 MB/s 수준) | $u ≈ 0.1$ (1 round/10 cycles) |
| 균형형 (P=8) | ≈ 256 clocks | 중 (수 백 MB/s) | $u ≈ 0.3 ∼ 0.5$ (1 round/2–3 cycles) |
| 고성능형 (P=16) | ≈ 128 clocks | 높음 (> 1 GB/s) | $u ≈ 0.6 ∼ 1.0$ (1 round/1–1.5 cycles) |

- MDPI 논문의 경우 P=1이므로 Keccak XOF bandwidth 요구가 낮음.  
- RV-PQC에서는 NTT가 훨씬 빠르므로 Keccak 언롤 팩터 $u ≈ 0.4$ 이상 필요.

---

### B.5 Implication 요약

| 항목 | MDPI 논문 접근 | RV-PQC 설계 함의 |
|------|----------------|----------------|
| 버터플라이 병렬도 | P=1 (U-BTF 단일) | P=8 이상으로 스루풋 확보 필요 |
| 파이프라인 전략 | 깊은 파이프 (6-stage) | 병렬도 확대로 파이프라인 깊이 감소 가능 |
| Keccak 정합 | 낮은 throughput → CPU 호출형 적합 | 스트리밍 정합 위해 XOF unroll 4~6 필요 |
| 메모리 구조 | Ping-pong BRAM 2개 | 멀티뱅크 + DMA prefetch 필수 |
| 자원/성능 목표 | 면적 효율 중심 | Keccak/NTT 동기 처리율 중심 |

---

### B.6 결론

MDPI 2025 논문은 “단일 U-BTF + 깊은 파이프라인” 기반의 **저면적 FPGA 중심 NTT 설계**입니다.  
RV-PQC와 같은 고성능 환경에서는 다음과 같은 확장이 필요합니다:

- **버터플라이 병렬도 P ≥ 8**  
- **Keccak 언롤 팩터 $u ≥ 0.4$**  
- **DMA 스트리밍 및 멀티뱅크 메모리 설계**

이 두 변수를 맞춰야 **NTT ↔ Keccak 파이프라인 정합**이 안정적으로 달성됩니다.

---
