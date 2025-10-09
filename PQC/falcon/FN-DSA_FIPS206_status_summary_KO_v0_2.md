# 🔍 FN-DSA / FIPS 206 현황 요약 & 관련 이슈 (KO, v0.2)

Date : OCT 7,2025
---

본 문서는 FN‑DSA / FIPS 206의 진행 상황과 주요 이슈(특히 FALCON의 **FP64 기반 FFT**로 인한 **side‑channel / DIEL** 문제)를 간결히 정리하고,
실용적 대안(정수기반 NTT, 정수화 DCT 접근, Q‑fixed 기반 구현)을 제시합니다.

---

## 1) FN‑DSA / FIPS 206 개요

- **FN‑DSA**: NIST PQC 표준화에서 **FALCON 기반 디지털 서명 스킴**을 지칭하는 이름.
- **FIPS 206**: FN‑DSA를 공식화하기 위한 문서 번호/명칭으로 사용. **Initial Public Draft(IPD)** 공개가 예고됨.
- 내부 발표 자료에 따르면 **초안은 거의 완성**, 공개 승인을 대기 중인 상태로 공유됨.

참고:
- NIST CSRC 발표/자료: https://csrc.nist.gov/  
- NIST PQC 공지: https://www.nist.gov/pqc  
- Encryption Consulting 개요: https://www.encryptionconsulting.com/post/fips-206-fn-dsa/  (개요/해설)  
- DigiCert PQC 관련 블로그 모음: https://www.digicert.com/blog/category/post-quantum-cryptography  

---

## 2) 왜 FALCON(FN‑DSA)은 FP64(배정밀도) FFT를 쓰는가?

FALCON은 **Fast Fourier Sampling**을 핵심으로 하는 격자(lattice) 기반 서명 스킴입니다.  
고차원 정규분포 샘플링을 효율화하기 위해 **복소수 FFT(부동소수점)** 를 사용하며, 이 경로가 **IEEE‑754 double (binary64)** 에 의존합니다.

- 논문/구현에서 명시적으로 **double precision** 사용:  
  https://falcon-sign.info/falcon-impl-20190802.pdf  
  https://falcon-sign.info/falcon.pdf  
  https://www.di.ens.fr/~prest/Publications/falcon.pdf

문제점(요약):
- 플랫폼/마이크로아키텍처 간 **라운딩/정규화 차이** → **비결정성/타이밍 변동**
- **NaN/Inf/subnormal** 등 예외 처리 → **constant‑time 준수 난이도 증가**
- 결과적으로 **Side‑channel / DIEL** 위험 노출

Cloudflare 등 커뮤니티 관측:
- FP 하드웨어가 없거나 시간결정성이 약한 환경에서 **서명 속도가 크게 저하(예: ~20배)** 가능성 언급.  
  https://blog.cloudflare.com/another-look-at-pq-signatures/

NIST CSRC 자료(발표 슬라이드 등)에서도 **“floating‑point 특수 이슈”** 를 별도 항목으로 다룸.  
https://csrc.nist.gov/Projects/post-quantum-cryptography

---

## 3) TRUSTFARM 의 대안 및 연구 방향 (요약)

### A. **정수기반 NTT로 변환 (PQC 스타일)**
- Kyber/Dilithium처럼 **mod‑q 정수 NTT**로 변환하여 FP 의존 제거.
- 장점: 결정론/constant‑time 용이, FPU 불필요, 하드웨어 단순화.
- 고려: 수학적 등가성/근사 정당화, 파라미터 재튜닝, 보안성 재검증.

### B. **영상 코덱의 정수화 DCT 방식 차용**
- 실수 DCT를 정수화/스케일링/시프트로 구현했던 접근을 FFT에 응용.
- 장점: 스케일 관리, 포화/라운딩 정책 고정, 하드웨어 친화.
- 고려: 정확도‑성능‑메모리 트레이드오프, 스케일 스케줄 표준화.

### C. **Q‑fixed(예: AME Q32.32) 기반 구현**
- RISCV AME 스펙의 `Q32.32 (signed 64b, 32정수+32소수)`로 **복소 FFT/샘플러를 고정소수점화** 방식을 채용 `Qx.y` 에서 Q.x 를 어느 수준으로 할지는 Falcon 주요연산 부분을 simulation 해야 함. 
> [RISCV AME 스펙 Proposal-DataFormat 바로가기](../../AME/AME_MAC_Dataformat_profile_spec_v0.18e.md#4-formattype-fmt-codes-8-bit)

- 산술 규칙(핵심): `64×64→128b 곱셈값` 확보 후 **>> 32**(라운딩) 정규화, 포화 가산/감산, 스테이지별 스케일(>>1), 라운딩 정책 고정.
- 트위들 ROM은 대규모가 되지 않도록 **TWGEN(quarter‑wave LUT, per‑stage base×pow, CORDIC/DDS, 폴리근사)** 로 대체/경량화.

---
### 3-1) 적정 Qx.y  - OCT 8,2025
  - **Q18.46** - 이 Gaussian 우선 관점에서 현재 최적 Approach 임.
>
> 분포 정확도: Q16~Q22 구간에서는 동일 수준 (MSE, KS 차이 없음).
> 
>  - 정밀도 영향은 사실상 **sampler/σ**가 결정, 
>  - `Q` 비트폭은 포화 영역.
>
>  - 속도/자원: `Q18.46 ~ Q20.44` 구간이 가장 효율적.
>  - 그중 평균 속도는 Q18.46가 최적(≈8.5 μs/sample).
>  - `Q21~Q22`는 분포 이득 없이 비용만 증가.

- **추천**
> Gaussian 품질(정확도)을 최우선으로 봤을 때 Q18.46이 정확도 손실 없이 가장 빠른 균형점.
>
> 더 작은/큰 Q로 가도 분포 정확도 이득은 거의 없으니, sampler 선택(CDT/ExpCut/Ziggurat 등) 과 σ 세팅이 품질을 좌우.

[Falcon Validate Python code](#8-falcon-qxy-simulation-and-analysis)

---

## 4) 구현 관점 비교 (요약)

| 항목 | 기존 FALCON(FP64 FFT) | 제안 방향(정수 NTT / Q‑FFT) |
|---|---|---|
| 연산 도메인 | 부동소수점 복소 FFT | 정수 모듈러 NTT 또는 Q‑fixed FFT |
| 하드웨어 경로 | FPU 필요 | 정수 ALU/MUL/SHIFT, 128b 누산기 |
| 결정론/타이밍 | 어려움 (예외/라운딩) | 용이 (정해진 라운딩·포화·스케일) |
| SC/DIEL | 취약 | 개선(분기 제거·고정 시간) |
| 트위들 | 대규모 ROM 필요 | TWGEN으로 ROM 경량화 |
| 생태계 적합성 | 고정밀 FP 전제 | SoC/TEE/경량 코어 친화 |

---

## 5) 참고 구현·연구 사례 (링크)

- **Thomas Pornin** — “Falcon only uses the ‘binary64’ type” (double)  
  https://falcon-sign.info/falcon-impl-20190802.pdf
- **Falcon 논문/설명**  
  https://falcon-sign.info/falcon.pdf  
  https://www.di.ens.fr/~prest/Publications/falcon.pdf
- **Design of a Lightweight FFT for FALCON (ACM DL, 2024)**  
  https://dl.acm.org/doi/10.1145/3649476.3660370
- **Area and Power Efficient FFT/IFFT Processor for FALCON (arXiv)**  
  https://arxiv.org/abs/2401.10591
- **Internship: Fixed‑point implementation of Falcon / FN‑DSA (tprest)**  
  https://tprest.github.io/internships-2025/internship-2025-falcon.pdf
- **Cloudflare — Another look at PQ signatures**  
  https://blog.cloudflare.com/another-look-at-pq-signatures/

---

## 6) 권고안

> **결론:** FALCON(FN‑DSA)의 FP64 기반 FFT 경로는 구현 난이도와 SC/DIEL 리스크를 내포합니다.  
> 이에 대한 실용적 대안으로 (A) **정수기반 NTT 변환**, (B) **정수화 DCT 접근**, (C) **Q‑fixed(예: Qx.y) 기반 FFT/샘플러**가 타당합니다.  
> 특히 본 제안에서는 **Qx.y**를 사용하여 **FP64 결과에 근접한 수치 특성을 확보**하면서, **결정론/타이밍 일관성**을 갖추는 경로를 우선 검토합니다.  
> (현 단계: **draft idea**. RISC‑V 구현 bring‑up 이후 **NIST 재검증** 경로 협의 필요.)

---

## 7) 부록 — TWGEN 구현 메모(Q‑fixed)

- **Quarter‑wave LUT + Symmetry**: 0~π/2 LUT(소용량)만 저장, 사분면 부호/스왑으로 전역 생성.
- **Per‑stage base twiddle × on‑the‑fly power**: `W_s`만 저장하고 `W ← W·W_s`로 생성, 간헐 정규화.
- **CORDIC/DDS**: phase accumulator + 회전 연산으로 sin/cos 생성, 소형 LUT만 필요.
- **폴리근사/미니맥스 + Quarter‑wave**: 계수만 저장, 마지막 1회 정규화로 |W|≈1 유지.
- **공통 규칙**: `64×64→128b` 곱셈값, **>> 32 라운딩**, 포화 가산/감산, 스테이지별 >>1 스케일, 라운딩/스케일 정책 고정.

---

## 8) Falcon Qx.y Simulation and Analysis

`./falcon_validate/` 디렉토리에 python code 가 있음.
 - 사용예제
```bash
python -m falcon_validate.main --sweep  --I_list 16,17,18,19,20,21,22  --N_list 256,512,1024,2048  --sigma_list 1.4  --mp_dps_list 40 --sampler_list cdt,knuth_yao,rejection,ziggurat,alias,expcut
```
```
  * --sweep  : 입력 파라이미터들을 순차적으로 조합해서 sweep 수행한다.
  * --I_list 16,18  : Q16.48,Q18.46 의 FixedPoint FP 를 조합한다.
  * --N_list        : FFT N의 크기값을 지정한다.
  * --sigma_list 1.2,1.4  : sigma 범위 (1.0 ~ 2.0) 사이값을 지정한다.
  * --mp_dps_list 33 : FP128 비트의 레퍼런스 값을 랜덤생성하여 값을 계산할때 사용한다. (40 : FP256 비트크기)
  * --sampler_list : FFT 는 기본 포함되어있고, Gaussian 분포를 생성하는 알려진 알고리즘들 (cdt,knuth_yao,rejection,ziggurat,alias,expcut) 등에 대해서 연산테스트를 수행한다.
```

### 출처(요약)
- NIST CSRC PQC: https://csrc.nist.gov/Projects/post-quantum-cryptography  
- NIST PQC 프로그램: https://www.nist.gov/pqc  
- DigiCert PQC 블로그: https://www.digicert.com/blog/category/post-quantum-cryptography  
- Encryption Consulting(FIPS 206 개요): https://www.encryptionconsulting.com/post/fips-206-fn-dsa/  
- Falcon 자료: https://falcon-sign.info/ , https://www.di.ens.fr/~prest/Publications/falcon.pdf  
- Cloudflare 블로그: https://blog.cloudflare.com/another-look-at-pq-signatures/
