# Scrambler‑TEE for RISC‑V — E‑to‑E Security (EN, refreshed)
**Keywords:** E‑To‑E Security, Overcome ARM Tz

Author: KT Ahn (with Keystone integration samples)


---

## 0) Summary
- Protect **Core→Fabric→Memory→IO** with a single **EID/world attribute** using **(e)PMP/IOPMP + Scrambler (AES‑CTR/ChaCha/XTS/AEAD)**.
- Combine with **Keystone/Sanctum** Security Monitor (M‑mode) to create/measure/apply‑policy/bind‑key for **enclaves (EID)**.
- PQC executes on **scrambled intermediates**, reducing **side‑channel** leakage.

---

## 1) Architecture (E‑to‑E)
- **Core:** (e)PMP/Smepmp, SM (world/enclave switch)  
- **Fabric:** IOPMP (apply EID/permissions to all masters CPU/DMA/accelerators)  
- **Memory:** Scrambler before L2/DDR (**Key‑Select = f(EID/world)**, per‑line tweak, key‑rolling)  
- **Attestation:** DICE chain includes **SM hash + IOPMP policy + Scrambler cfg**

---

## 2) Keystone Integration — Sample Code

### 2.1 Common top API (shared by HPC/IoT builds)
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

### 2.2 Keystone SM (M‑mode) side hooks
```c
// sm_keystone_hooks.c (M-mode, Security Monitor)
#include "soc_iopmp.h"
#include "soc_scr.h"
#include "epmp.h"
#include "hash.h"

static int apply_epmp(eid_t eid, const tee_region_t* r, int n) {
  for (int i=0;i<n;i++) epmp_program(r[i].pstart, r[i].pend, r[i].perms);
  return 0;
}
static int apply_iopmp(eid_t eid, const tee_region_t* r, int n) {
  iopmp_set_domain(eid); // default-deny, then enable EID
  for (int i=0;i<n;i++) iopmp_program_region(eid, r+i);
  return 0;
}
static int bind_scrambler(eid_t eid) {
  uint8_t kmem[32], tweak[16];
  kdf_derive_kmem_for_eid(eid, kmem, tweak); // derive from K_root & measurement
  scr_set_key(eid, kmem, tweak);
  scr_bind_domain(eid);       // Key-Select(EID)
  // optional: scr_roll_key(eid);
  return 0;
}

int sm_enclave_create(eid_t eid, const tee_region_t* r, int n) {
  // 1) measurement
  hash_ctx h; hash_init(&h);
  hash_update(&h, (void*)SM_TEXT_START, SM_TEXT_SIZE);
  for (int i=0;i<n;i++) hash_update(&h, (void*)r[i].pstart, r[i].pend - r[i].pstart);
  store_measurement(eid, &h);
  // 2) policy/key apply
  apply_epmp(eid, r, n);
  apply_iopmp(eid, r, n);
  bind_scrambler(eid);
  return 0;
}

int sm_enclave_enter(eid_t eid) {
  iopmp_activate_domain(eid);
  epmp_activate_for_eid(eid);
  scr_bind_domain(eid);
  cache_partition_apply(eid); // optional
  return 0;
}

int sm_enclave_exit(eid_t eid) {
  cache_partition_reset();
  iopmp_deactivate_domain(eid);
  epmp_reset();
  return 0;
}
```

### 2.3 Userland (Linux) — create/enter an enclave
```c
// user_enclave_demo.c (S-mode app)
#include "tee_api.h"
#include <stdio.h>

int main(void){
  tee_region_t regs[] = {
    {.pstart=0x90000000, .pend=0x90040000, .perms=0x7, .attr=0x1},
    {.pstart=0x90040000, .pend=0x90060000, .perms=0x3, .attr=0x1},
  };
  uint8_t m[48];
  tee_update_policy(regs, 2);
  tee_scrambler_select(1 /*EID*/);
  tee_measure_commit(m);
  printf("measurement[0..3]=%02x%02x%02x%02x\n", m[0],m[1],m[2],m[3]);

  tee_world_switch(TEE_WORLD_SECURE);
  // ... secure work (PQC with scrambled operands) ...
  tee_world_switch(TEE_WORLD_USER);
  return 0;
}
```

### 2.4 IoT lightweight backend (direct MMIO)
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

## 3) PQC Side‑channel Hardening
- Keep NTT/poly intermediates, twiddles, accumulators **scrambled at rest/in transit**; transient uns/scramble only in ALU windows.  
- **Key‑rolling & per‑line tweak** to reduce repetitive correlations.

---

## 4) TrustZone Comparison (summary)
| Item | ARM TrustZone | Scrambler‑TEE (RISC‑V) |
|---|---|---|
| Isolation model | Two worlds via NS‑bit | ePMP + IOPMP + **Scrambler** → **EID/world** end‑to‑end |
| Data confidentiality | External / optional | **On‑die scrambler** (CTR/ChaCha/XTS/AEAD) included |
| Integrity | Not covered | (Opt.) **AXI‑AE** MAC + DICE |
| Real‑time | Monitor overhead | **Low‑latency**, no VM |
| PQC SCA | Out of scope | **Scrambled intermediates** weaken DPA/EMA |
| Openness | Licensed | **Open** RV; simple blocks; flexible policy |

---

## 5) Roadmap (Easy → Medium → Hard)
| Phase | Timeline | Components | Outcome |
|---|---|---|---|
| Easy | 1–2 yrs | ePMP + IOPMP + Scrambler(CTR/ChaCha) + RPK; OpenSBI‑EXT/SBI‑Facade | Minimal E‑to‑E; low‑latency; beyond Tz |
| Medium | 2–4 yrs | MTE‑like tagging, AXI‑AE MAC, cache/TLB partition, partial CHERI | Integrity + SC defense + fine‑grain rights |
| Hard | 5+ yrs | Full CHERI, CoVE(Realm+VM), HW PAC/CFI, hardened core | Beyond Tz/SGX; complete E‑to‑E |
