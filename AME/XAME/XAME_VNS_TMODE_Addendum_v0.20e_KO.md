# XAME/VNS – XMODE 인라인 디스크립터 확장 (부록 v0.20e, KO)

**핵심:** 베이스라인 시그니처는 유지되고, FFT/NTT/OFDM/MIMO 등의 연산은 **실제 수행 동작은 XMODE 디스크립터안에 확장연산방식의 OPS(options arguments) 를 활용해 수행됩니다.**

**OPS(options arguments)** XMODE가 지시하는 **마이크로커널/커스텀 HW 로직의 동작 옵션**을 표현합니다.

---

## 1) 기본 시그니처 (XAME XMODE descriptor추가)
```text
C = MMACC(A, B, K, M, bTR, RFmt, IFmt, bTOP [, bias_k, XMODE])
```
- `K, M, bTR, RFmt, IFmt, bTOP`은 실행 시점에 **불변**이며 **FFT/NTT 세부 정보를 담지 않습니다**.  
- **실행 의미는 전부 XMODE의 OPS(options arguments)**에서 Custom 매트릭스 커널의 동작이 결정됩니다.
  
---

## 2) 엔지니어링 해설 (요약)
- `MMACC`는 **AI Matrix(AI‑MAC)** 을 수행하는 **하나의 논리 명령어**입니다.
- 이를 기준으로 ISA 는 쉽게 설정되고, 확장및 변경될수 있습니다.
- 주요 연산 하드웨어는 커널이라고 부르고, 하나 이상의 커널을 **MUX/switch** 뒤에 배선할 수 있습니다.
- **XMODE.OP**는 각 호출에서 MMACC 코어가 “어떤 커널을 어떤 모드로 돌릴지”를 지정합니다.
- 하드웨어에 해당 커널/스위칭이 없으면 SW Runtime 에는 **바인딩 fault**를 return하게 됩니다.

- 즉, HW 적으로는 입력되는 dataformat / 출력 dataformat / 누적 값 처리방식에 대한 로직이 존재하고,
- 다양한 입출력 포맷과 누적 값 처리를 위해서 별도의 Custom hw logic 이 존재합니다.
- MMACC 에서는 이를 MUX/Switch 하게 됩니다.
- 일반적으로 익숙한 Plug-and-Play 의 HW 구성방식과 비교하여 이해하면 됩니다.
  - ex> fp8 -> fp32 연산용 MAC HW
  -     int16 -> FFT 연산용 MAC HW

## 3) XMODE OPS inline (디스크립터 기반 실행)
XMODE는 **OP(Operations) 테이블**을 보유합니다. 각 OP는 *무엇을 어떻게 수행해야 하는지*를 기술합니다.
- 논리 **연산 클래스**(`KSEL`: `BFLY_R2/R4/R8`, `MODMUL`, `CGIVENS`, …)
- **stage/radix/twiddle 선택**, **bit‑reverse**, **stride/transpose 템플릿**, **conj/norm 플래그** 등
- 선택적으로 `KSEL → KERN` 바인딩 힌트(혹은 `VNS_PLAN`/`VNS_BIND` 참조)

> OP는 XMODE가 지시하는 **마이크로커널(또는 커스텀 HW 로직)의 동작 방식**을 지정하는 *운영 단위*입니다.  
> 즉, OP는 “어떤 커널을 어떤 모드/매개변수로 돌릴지”를 설명하며, CPU ISA 명령어와 혼동하면 안 됩니다.

런타임에서는 **MMACC 호출 시 XMODE에 포함된 OP가 즉시 해석/수행**됩니다.  
베이스라인 필드는 항상 동일하며, **XMODE 및 XMODE.OP**가 어떤 **마이크로커널(KERN)**이 활성화될지 결정합니다.

---

## 3) 올바른 실행 예 — OFDM 4096‑pt (radix‑4)
```text
TM = &XMODE_fft4096;   // OP 테이블(12단계)을 가진 64B 정렬 XMODE
VNS_XMODE_RESET(TM);   // TM‑PC 초기화

while (VNS_TMODE_HAS_NEXT(TM)) {
  C = MMACC(A, B, K , M , bTR ,        
            RFmt={dtype=FP16}, IFmt={dtype=FP16}, bTOP, // 베이스라인: 중립값(불변)
            TMODE=TM);                      // TM.OP를 해석·수행
}
```
- 디스패처는 현재 OP로부터 **KSEL**(KERNEL선택) 하고, 바인딩 테이블을 통해 **KERN**(구체 마이크로커널)을 선택합니다.  
- 주소 변환(비트리버설/스트라이드/트랜스포즈)과 보정(conj/norm)도 **OP 템플릿**에서 지정됩니다.

---

## 4) OP 항목 형식 (예시)
```c
struct VNS_TMODE_OP {
  uint8_t  ksel;       // 논리 커널: BFLY_R4, CMUL_CONJ, MODMUL, CGIVENS 등
  uint8_t  stage;      // FFT/NTT 단계 (미사용 시 0xFF)
  uint8_t  radix;      // FFT radix {2,4,8}; 미사용 0
  uint8_t  flags;      // {BITREV_LAST, TRANSPOSE_XY, CONJ, NORM_1/N, ...}
  uint16_t stride_tpl; // stride/transpose 템플릿 ID
  uint16_t bind_idx;   // 로컬 바인딩 인덱스 (→ KERN), 0이면 외부참조
  uint32_t tw_sel;     // twiddle segment / modulus selector
  uint32_t aux;        // 보조 메타데이터 (modulus q 핸들, 축 ID 등)
};
```
- OP 에 지정된 Kernel 수행용 파라미터를 의미하고, `VNS_TMODE_RESET`으로 재시작할 수 있습니다.

---

## 5) 바인딩 및 폴백 (우선순위 동일)
1. `TMODE.bind[]` (디스크립터 내부)
2. `VNS_PLAN[plan_id].bind[]` (stage/axis 단위)
3. 글로벌 `VNS_BIND[]` (CSR)
4. 폴백 `IDENTITY` (기본 GEMM/MMACC)

---

## 6) 엔지니어링 해설 (요약)
- `MMACC`는 **AI Matrix(AI‑MAC)** 을 수행하는 **하나의 논리 명령어**입니다.
- 하드웨어는 하나 이상의 커널을 **MUX/switch** 뒤에 배선할 수 있습니다.
- **TMODE.OP**는 각 호출에서 “어떤 커널을 어떤 모드로 돌릴지”를 지정합니다.
- 하드웨어에 해당 커널/스위칭이 없으면 **바인딩 fault**를 보고해야 합니다.

*(End of Addendum v0.20e KO)*
