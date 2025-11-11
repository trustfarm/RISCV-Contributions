# XAME/VNS – TMODE 인라인 디스크립터 확장 (부록 v0.20d, KO)

**v0.20d 핵심 변경:** 기본 **시그니처는 그대로** 두고, FFT/NTT 단계/라딕스 등 모든 실행 의미는  
**TMODE 디스크립터의 OP 테이블 안에만 존재**하도록 정리했습니다.

---

## 1) 기본 시그니처 (변경 없음)
```text
C = MMACC(A, B, K, M, bTR, RFmt, IFmt, bTOP [, bias_k, TMODE])
```
- `K, M, bTR, RFmt, IFmt, bTOP`은 실행 시점에 불변이며 **FFT/NTT 세부 정보를 담지 않습니다**.  
- 실행 의미는 전부 **TMODE의 OP 실행동작**이 제공합니다.

---

## 2) TMODE OP 프로그램 (디스크립터 기반 실행)
TMODE에는 **OP (Operations) 테이블**(세부 수행동작기술)이 들어 있으며, OP는 실제적으로 어떤 작업을 수행해야 하는지 설명합니다.
- 논리 **연산 클래스**(`KSEL`: BFLY_R2/R4/R8, MODMUL, CGIVENS 등)
- **stage/radix/twiddle 선택**, **bit‑reverse**, **stride/transpose 템플릿**, **conj/norm 플래그** 등
- 선택적으로 `KSEL → KERN` 바인딩 힌트 또는 `VNS_PLAN`/`VNS_BIND` 참조

런타임에서는 **MMACC 호출시 TMODE에 포함된 OP를 수행**합니다.  
베이스라인 필드는 항상 동일하며, **TMODE, TMODE.OP** 를 통해서 어떤 마이크로커널이 활성화될지를  결정합니다.

---

## 3) 올바른 실행 예 — OFDM 4096‑pt (radix‑4)
```text
TM = &tmode_fft4096;   // OP 테이블(12 스테이지)을 가진 64B 정렬 TMODE
VNS_TMODE_RESET(TM);   // TM‑PC 초기화

for i in 0..TM.ops_len-1 {
  C = MMACC(A, B,
            K=IDENTITY,              // 베이스라인 중립값(불변)
            M=0,                     // 베이스라인 중립값(불변)
            bTR=0,                   // 베이스라인 중립값(불변)
            RFmt={dtype=FP16},       // 베이스라인 포맷
            IFmt={dtype=FP16},       // 베이스라인 포맷
            bTOP={SCALE_SHIFT=1},    // 베이스라인 파이프라인 모드
            TMODE=TM);               // 디스패처가 TM.OP[i]를 해석

  // 디스패처는 OP[i]로부터 다음을 결정:
  //   KSEL = OP[i].ksel (예: BFLY_R4)
  //   KERN = binding(KSEL, dtype) → 예: BFLY_R4_PIPE
  //   주소 변환(bitrev/stride/transpose) 템플릿 적용
}
```
> `K/M/bTR`에는 **FFT 세부사항이 전혀 나타나지 않습니다**. 모든 정보는 TMODE.OP에만 존재합니다.

---

## 4) TMODE OP 항목 형식 (예시)
```c
struct VNS_TMODE_OP {
  uint8_t  ksel;       // BFLY_R4, CMUL_CONJ, MODMUL, CGIVENS 등
  uint8_t  stage;      // FFT/NTT 단계 인덱스 (미사용 시 0xFF)
  uint8_t  radix;      // FFT {2,4,8}; 미사용 시 0
  uint8_t  flags;      // {BITREV_LAST, TRANSPOSE_XY, CONJ, NORM_1/N, ...}

  uint16_t stride_tpl; // stride/transpose 템플릿 ID
  uint16_t bind_idx;   // 선택적 로컬 바인딩 인덱스 (→ KERN)

  uint32_t tw_sel;     // twiddle 세그먼트 / 모듈러스 선택자
  uint32_t aux;        // 보조 메타데이터 (예: modulus q 핸들, 축 ID)
};
```
- OP는 순서대로 소비되며(`TM‑PC` 자동 증가), `VNS_TMODE_RESET(TM)`으로 처음부터 다시 실행할 수 있습니다.

---

## 5) 바인딩 및 폴백 (우선순위 동일)
1. `TMODE.bind[]` (디스크립터 내부)
2. `VNS_PLAN[plan_id].bind[]` (stage/axis 별)
3. 글로벌 `VNS_BIND[]` (CSR)
4. 폴백 `IDENTITY` (기본 GEMM/MMACC)

---

## 6) 엔지니어링 해설 (요약)
- `MMACC`는 **AI Matrix (AI‑MAC)** 을 위한 **하나의 논리 명령어**입니다.  
- 하드웨어는 스위치/MUX 뒤에 하나 또는 여러 개의 커널을 배선(wiring)할 수 있습니다.  
- `TMODE`는 **OP 프로그램**(테이블)로 각 호출에서 **어떤 커널을 선택할지**를 알려줍니다.  
- 하드웨어에 해당 커널/스위칭이 없으면 **바인딩 fault**를 보고해야 합니다.

*(End of Addendum v0.20d KO)*
