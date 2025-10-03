
# FNV-1a 스크램블 엔진 (v2, 32비트 커널)

[KO](FNV1a_Scramble_v2_KR.md) | [EN](FNV1a_Scramble_v2_EN.md)

---

## 1. 개요

이 설계는 **32비트 FNV-1a 커널**을 사용하여 스크램블/디스크램블을 수행합니다.  
64비트 커널 대비 32비트 버전은 **하드웨어 지연(latency)을 줄이고**, 여러 개의 32비트 파이프라인 인스턴스를 배치하여 병렬 처리 효율을 극대화할 수 있습니다.  
목표는 **사실상 지연 없는(latency-less) 스크램블링**, 즉 블록당 1~2 사이클 처리입니다.

### 예시 입출력데이터포맷::

- **블록 크기**: 128 바이트  
- **총 입력 데이터**: 512 바이트 (128B × 4 블록)  
- **핵심 아이디어**:  
  - `seed32`와 `rng32`를 한 번만 섞어 `IV32` 생성  
  - `CTR32`를 `rng32`에서 초기화  
  - 각 블록마다 `hash_in = IV32 + CTR32++`, `hash_out = fnv1a32(hash_in)`  
  - 128바이트 블록 전체를 4바이트 단위로 `hash_out`과 XOR

---

## 2. C 참조 구현

```c
#include <stdint.h>
#include <stddef.h>
#include <string.h>

#define FNV1A32_OFFSET 0x811C9DC5u
#define FNV1A32_PRIME  0x01000193u

static inline uint32_t fnv1a32_u8(uint32_t h, uint8_t b) {
    h ^= (uint32_t)b;
    h *= FNV1A32_PRIME;
    return h;
}

static inline uint32_t fnv1a32_u32le(uint32_t x) {
    uint32_t h = FNV1A32_OFFSET;
    for (int i = 0; i < 4; ++i) {
        h = fnv1a32_u8(h, (uint8_t)(x & 0xFF));
        x >>= 8;
    }
    return h;
}

// 512B = 4 블록 * 128B 처리
void scramble_512B_fnv1a32(uint8_t *data, uint32_t seed32, uint32_t rng32) {
    uint32_t IV32  = seed32 ^ rng32;
    uint32_t CTR32 = rng32;

    for (int i = 0; i < 4; ++i) {
        uint32_t hash_in  = IV32 + (CTR32++);
        uint32_t hash_out = fnv1a32_u32le(hash_in);

        uint32_t *p32 = (uint32_t*)(data + (i * 128));
        for (int j = 0; j < 128/4; ++j) {
            p32[j] ^= hash_out;
        }
    }
}
```

---

## 3. Verilog 스켈레톤

```verilog
// fnv1a32_core.v
module fnv1a32_core (
    input  logic        clk,
    input  logic [31:0] x_in,
    input  logic        in_valid,
    output logic [31:0] hash_out,
    output logic        out_valid
);
    localparam logic [31:0] FNV_OFFSET = 32'h811C9DC5;
    localparam logic [31:0] FNV_PRIME  = 32'h01000193;

    function automatic [31:0] fnv_u8(input [31:0] h, input [7:0] b);
        fnv_u8 = (h ^ {24'd0,b}) * FNV_PRIME;
    endfunction

    function automatic [31:0] fnv_u32_le(input [31:0] x);
        reg [31:0] h;
        begin
            h = FNV_OFFSET;
            h = fnv_u8(h, x[7:0]);
            h = fnv_u8(h, x[15:8]);
            h = fnv_u8(h, x[23:16]);
            h = fnv_u8(h, x[31:24]);
            fnv_u32_le = h;
        end
    endfunction

    always_ff @(posedge clk) begin
        if (in_valid) begin
            hash_out  <= fnv_u32_le(x_in);
            out_valid <= 1;
        end else begin
            out_valid <= 0;
        end
    end
endmodule
```

- 128B 블록 처리 시 XOR 레인을 복제 가능:  
  - 32 레인 → 1 사이클에 128B  
  - 16 레인 → 2 사이클  
  - 8 레인  → 4 사이클

---

## 4. 참고 사항

- **효율성**: 블록당 `hash_out` 1개만 필요 → XOR 전파는 단순.  
- **보안성**: FNV-1a는 암호학적으로 안전하지 않으나, 경량 스크램블에는 충분.  
- **확장**: 더 높은 보안을 원하면 동일 구조에 AES-CTR 또는 ChaCha 대체 가능.  
- **하드웨어 구현**: fnv1a32 코어 여러 개 병렬 배치로 **사실상 지연 없는 처리** 달성.

---
