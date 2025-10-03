# Scrambler‑TEE for RISC‑V — E‑to‑E Security (KO, refreshed)
**키워드:** E‑To‑E Security, Overcome ARM Tz

작성: KT Ahn 제안안 (Keystone 연동 샘플 포함)

---

## 0) 요약
- **(e)PMP/IOPMP + Scrambler(AES‑CTR/ChaCha/XTS/AEAD)**로 **Core→Fabric→Memory→IO** 전 구간을 일관 속성(EID/world)으로 보호.
- **Keystone/Sanctum**의 Security Monitor(SM, M‑mode)와 결합하여 **Enclave(EID)** 생성·측정·정책적용·키바인딩을 수행.
- PQC 연산은 **스크램블된 중간값**을 사용해 **측채널 노출**을 낮춤.

---

## 1) 아키텍처 (E‑to‑E)
- **Core:** (e)PMP/Smepmp, SM(world/enclave switch)  
- **Fabric:** IOPMP(모든 마스터 CPU/DMA/가속기에 EID/권한 적용)  
- **Memory:** Scrambler(L2/DDR 앞단, **Key‑Select = f(EID/world)**, per‑line tweak, key‑rolling)  
- **Attestation:** DICE 체인에 **SM 해시 + IOPMP 정책 + Scrambler 설정** 포함

---

## 2) Keystone 연동 샘플 코드

### 2.1 공통 상위 API (HPC/IoT 공용 헤더)
```c
// tee_api.h
#pragma once
#include <stdint.h>

typedef enum { TEE_WORLD_USER=0, TEE_WORLD_SECURE=1 } tee_world_t;
typedef uint32_t eid_t;
typedef struct {
  uint64_t pstart, pend;
  uint32_t perms;   // bit0:R, bit1:W, bit2:X
  uint32_t attr;    // bit0:SECURE, bit1:DMA_OK ...
} tee_region_t;

int tee_world_switch(tee_world_t next);
int tee_update_policy(const tee_region_t* r, int n); // IOPMP/(e)PMP
int tee_scrambler_select(uint32_t eid_or_world);
int tee_scrambler_roll(uint32_t eid_or_world);
int tee_measure_commit(uint8_t out_hash[48]);
```

### 2.2 Keystone SM(M‑mode) 사이드 스텁
```c
// sm_keystone_hooks.c (M-mode, Security Monitor 내부)
#include "soc_iopmp.h"
#include "soc_scr.h"
#include "epmp.h"
#include "hash.h"

static int apply_epmp(eid_t eid, const tee_region_t* r, int n) {
  for (int i=0;i<n;i++) epmp_program(r[i].pstart, r[i].pend, r[i].perms);
  return 0;
}
static int apply_iopmp(eid_t eid, const tee_region_t* r, int n) {
  iopmp_set_domain(eid); // Default-Deny 후 EID 활성
  for (int i=0;i<n;i++) iopmp_program_region(eid, r+i);
  return 0;
}
static int bind_scrambler(eid_t eid) {
  uint8_t kmem[32], tweak[16];
  kdf_derive_kmem_for_eid(eid, kmem, tweak); // K_root, measurement 기반
  scr_set_key(eid, kmem, tweak);
  scr_bind_domain(eid);       // Key-Select(EID)
  // (옵션) scr_roll_key(eid);
  return 0;
}

int sm_enclave_create(eid_t eid, const tee_region_t* r, int n) {
  // 1) 측정
  hash_ctx h; hash_init(&h);
  hash_update(&h, (void*)SM_TEXT_START, SM_TEXT_SIZE);
  for (int i=0;i<n;i++) hash_update(&h, (void*)r[i].pstart, r[i].pend - r[i].pstart);
  store_measurement(eid, &h);
  // 2) 정책/키 적용
  apply_epmp(eid, r, n);
  apply_iopmp(eid, r, n);
  bind_scrambler(eid);
  return 0;
}

int sm_enclave_enter(eid_t eid) {
  iopmp_activate_domain(eid);
  epmp_activate_for_eid(eid);
  scr_bind_domain(eid); // 보장적 Key-Select
  cache_partition_apply(eid); // (옵션) set-coloring/way-partition
  return 0;
}

int sm_enclave_exit(eid_t eid) {
  cache_partition_reset();
  iopmp_deactivate_domain(eid);
  epmp_reset();
  return 0;
}
```

### 2.3 유저 공간(리눅스)에서 Enclave 생성/진입
```c
// user_enclave_demo.c (S-mode 유저 앱)
#include "tee_api.h"
#include <stdio.h>

int main(void){
  tee_region_t regs[] = {
    {.pstart=0x90000000, .pend=0x90040000, .perms=0x7, .attr=0x1}, // SECURE code/data
    {.pstart=0x90040000, .pend=0x90060000, .perms=0x3, .attr=0x1}, // SECURE rw
  };
  uint8_t m[48];
  tee_update_policy(regs, 2);
  tee_scrambler_select(1 /*EID*/);
  tee_measure_commit(m);
  printf("enclave measurement[0..3]=%02x%02x%02x%02x\n", m[0],m[1],m[2],m[3]);

  tee_world_switch(TEE_WORLD_SECURE);
  // ... secure 작업 수행 (PQC with scrambled operands) ...
  tee_world_switch(TEE_WORLD_USER);
  return 0;
}
```

### 2.4 IoT 경량 백엔드(직접 MMIO) 예시
```c
// tee_backend_facade.c
#include "soc_regs.h"
int tee_update_policy(const tee_region_t* r, int n){
  for(int i=0;i<n;i++){ iopmp_program_region(1 /*EID*/, r+i); }
  epmp_sync_from_regions(r,n);
  return 0;
}
int tee_scrambler_select(uint32_t eid){ scr_bind_domain(eid); return 0; }
```

---

## 3) PQC 측채널 하드닝 포인트
- NTT/폴리 곱셈 중간값, 트위들, 어큐뮬레이터를 **항상 스크램블 상태**로 유지(메모리/버스).  
- ALU 창 내부에서만 순간적 복호/연산 후 재스크램블.  
- **키 롤링/라인 트윅**으로 반복 상관성 감소.

---

## 4) TrustZone 대비 비교 (요약)
| 항목 | ARM TrustZone | Scrambler‑TEE (RISC‑V) |
|---|---|---|
| 격리 모델 | NS‑bit 기반 이원 세계 | ePMP + IOPMP + **Scrambler**로 **EID/world** end‑to‑end |
| 데이터 기밀성 | 외부/선택 사항 | **온다이 스크램블러**(CTR/ChaCha/XTS/AEAD) 포함 |
| 무결성 | NS‑bit로는 부족 | (옵션) **AXI‑AE** MAC + DICE |
| 실시간성 | 모니터 오버헤드 | **저지연**, VM 불필요 |
| PQC SCA | 범위 밖 | **스크램블 중간값**으로 DPA/EMA 약화 |
| 개방성 | 라이선스 종속 | **오픈** RV, 단순 블록, 유연 정책 |

---

## 5) 로드맵 (Easy → Medium → Hard)
| 단계 | 기간 | 구성요소 | 효과 |
|---|---|---|---|
| Easy | 1–2년 | ePMP + IOPMP + Scrambler(CTR/ChaCha) + RPK; OpenSBI‑EXT/SBI‑Facade | 최소 E‑to‑E, 저지연, Tz 대비 상위 |
| Medium | 2–4년 | MTE‑유사 태깅, AXI‑AE MAC, 캐시/TLB 파티션, 부분 CHERI | 무결성+SC 방어+미세권한 |
| Hard | 5년~ | Full CHERI, CoVE(Realm+VM), HW PAC/CFI, 하든드 코어 | Tz/SGX 초월, 완전 E‑to‑E |
