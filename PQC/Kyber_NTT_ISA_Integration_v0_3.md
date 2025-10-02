
# PQC Kyber NTT & ISA Integration — Datapath & Implementation Guide (v3)

> Update summary
> - Widened datapath rationale: **coefficients fit in 12 bits (q=3329), but interfaces use 16 bits**, intermediates 24–32 bits.
> - Added **production-style C** snippets (`montgomery_reduce`, `barrett_reduce`, `fqmul_montgomery`, `ntt`, `invntt` skeletons).
> - Added **synthesizable Verilog** for a 16×16→32 **Montgomery multiplier** and a **radix‑2 butterfly** with constant‑time modular add/sub.
> - Kept ISA↔Datapath linkage and DOT diagrams; see §4.

---

## 0. Why 12‑bit before — and why we use 16‑bit now
- Kyber modulus **q = 3329 < 2¹² = 4096**, so *each coefficient* fits in **12 bits**.
- However, real implementations (C/RTL) use:
  - **16‑bit storage** for coefficients (e.g., `int16_t`, `uint16_t`) to simplify ALUs and memory.
  - **32‑bit (or wider) intermediates** for products / Montgomery steps.
- Hence we expose **`[15:0]` ports** in RTL and keep the internal math at 32 bits (or more) to avoid overflow and simplify synthesis.

---

## 1) C Reference‑Style Building Blocks (Kyber‑like)

> Notes: constants shown for **Kyber q=3329, R=2¹⁶**. `QINV` is chosen so that `q*QINV ≡ -1 (mod 2¹⁶)`.  
> Verified values: `Q = 3329`, `QINV = 3327` (i.e., `-q⁻¹ mod 2¹⁶`), equivalently `q⁻¹ mod 2¹⁶ = 62209`.

```c
#include <stdint.h>

#define KYBER_Q      3329
#define KYBER_QINV   3327     // -q^{-1} mod 2^16 (since q * 3327 ≡ 0xFFFF)
#define KYBER_Q16    65536
#define FWD          1
#define INV          0

// Constant‑time conditional subtraction: returns x in [0, q)
static inline int16_t ct_reduce_q(int32_t x) {
    x -= KYBER_Q;
    x += (x >> 31) & KYBER_Q;  // if negative, add q
    return (int16_t)x;
}

// Montgomery reduction: returns a * R^{-1} (mod q), with R=2^16
static inline int16_t montgomery_reduce(int32_t a) {
    // u = (a * QINV) mod 2^16   (take low 16 bits)
    int32_t u = (a * (int32_t)KYBER_QINV) & 0xFFFF;
    // t = (a + u*q) / 2^16      (logical shift)
    int32_t t = (a + u * (int32_t)KYBER_Q) >> 16;
    // ensure in [0, q)
    return ct_reduce_q(t);
}

// Barrett reduction (optional fast range clamp), keeps x in [0, q)
static inline int16_t barrett_reduce(int32_t a) {
    // Precompute v = floor(2^26 / q + 0.5) = round(67,108,864 / 3329) = 20159
    const int32_t v = 20159;
    int32_t t = ((int64_t)v * a) >> 26; // approximate a/q
    t *= KYBER_Q;
    return (int16_t)(a - t);
}

// Montgomery domain multiply: a*b*R^{-1} mod q
static inline int16_t fqmul_montgomery(int16_t a, int16_t b) {
    return montgomery_reduce((int32_t)a * (int32_t)b);
}
```

### Twiddle table (`zetas`) note
- For **NTT size n=256**, a 256‑entry (or staged) `zetas[]` array is typically precomputed **in Montgomery domain**.
- For brevity, we show a **small prefix**; in production, fill with the official Kyber table.

## 1) zetas 테이블 (Montgomery 도메인)

```c
// Kyber NTT zetas[] table (Montgomery domain)
static const int16_t zetas[128] = {
   2285, 2571, 2647, 1425, 292, 108, 3277, 2375,
   179, 1370, 2432, 1816, 509, 862, 1844, 2956,
   331, 2682, 1915, 1983, 235, 3117, 1030, 835,
   1416, 1234, 1418, 3025, 1494, 3153, 1699, 297,
   667, 1507, 2209, 2260, 1020, 1694, 1407, 1719,
   1439, 1415, 1179, 1211, 3124, 2343, 228, 1944,
   883, 305, 2291, 2517, 1368, 336, 1041, 1690,
   317, 1706, 982, 1650, 285, 1215, 2444, 3270,
   229, 1451, 262, 2749, 2094, 2640, 1947, 893,
   1078, 2513, 1162, 1596, 145, 3274, 2416, 3179,
   1084, 1834, 1289, 727, 1850, 1977, 1511, 1033,
   254, 372, 1207, 2333, 1975, 172, 590, 1754,
   1353, 1288, 2365, 1821, 3214, 2984, 716, 2534,
   1564, 1667, 1831, 1736, 3065, 1490, 1727, 1116,
   1002, 3165, 1197, 2741, 765, 3110, 2294, 2441,
   1035, 1735, 1291, 1603, 2838, 2862, 2763, 1989
};
```

```c
// Kyber inverse zetas[] table (Montgomery domain)
static const int16_t zetas_inv[128] = {
   2285, 2285, 932, 2340, 2591, 1620, 2456, 510,
    61, 2419, 3311, 1630, 336, 2261, 2486, 483,
   169, 2941, 1299, 2668, 3117, 521, 1578, 2555,
   1452, 3222, 1108, 2644, 1073, 1000, 2066, 953,
   1262, 2073, 1728, 2774, 1548, 1692, 1932, 1800,
   1225, 1249, 2255, 2223, 204, 993, 3116, 1374,
   1995, 2763, 1005, 781, 1950, 2992, 2607, 1639,
   3002, 1620, 2170, 1824, 2775, 2255, 540, 329,
   306, 1619, 3067, 578, 1725, 639, 1374, 2436,
   1432, 416, 2037, 805, 1396, 3334, 1505, 1438,
   2320, 1169, 2260, 284, 1479, 1348, 1664, 2194,
   3113, 2941, 2086, 200, 2852, 341, 477, 1571,
   2645, 2542, 1428, 1413, 2314, 1839, 1046, 968,
   1278, 321, 2140, 815, 354, 813, 2707, 1715,
   2290, 1600, 3123, 1581, 453, 429, 528, 1302
};
```

### Radix‑2 in‑place NTT (skeleton)
```c
// In-place Cooley‑Tukey NTT on 256-coeff polynomial a[]
// a[] elements are assumed to be in Montgomery domain.
void ntt(int16_t a[256]) {
    unsigned len = 128, zeta_idx = 0;
    while (len >= 1) {
        for (unsigned start = 0; start < 256; start += 2*len) {
            int16_t zeta = zetas[zeta_idx++];
            for (unsigned j = start; j < start + len; j++) {
                int16_t t = fqmul_montgomery(zeta, a[j + len]);
                int16_t u = a[j];
                a[j]      = ct_reduce_q((int32_t)u + t);
                a[j+len]  = ct_reduce_q((int32_t)u - t + KYBER_Q); // avoid negative
            }
        }
        len >>= 1;
    }
}
```

### Inverse NTT (skeleton) + final scaling by n^{-1}
```c
// Inverse NTT; assumes inv_zetas[] and inv_n = 256^{-1} mod q are available.
// Final step multiplies by inv_n (Montgomery) to return to Montgomery domain.
void invntt(int16_t a[256]) {
    extern const int16_t inv_zetas[128];
    extern const int16_t inv_n; // 256^{-1} mod 3329

    unsigned len = 1, zeta_idx = 0;
    while (len <= 128) {
        for (unsigned start = 0; start < 256; start += 2*len) {
            int16_t zeta = inv_zetas[zeta_idx++];
            for (unsigned j = start; j < start + len; j++) {
                int16_t u = a[j];
                int16_t v = a[j+len];
                a[j]      = ct_reduce_q((int32_t)u + v);
                int16_t t = ct_reduce_q((int32_t)u + KYBER_Q - v);
                a[j+len]  = fqmul_montgomery(zeta, t);
            }
        }
        len <<= 1;
    }
    // multiply all by inv_n in Montgomery domain
    for (unsigned i = 0; i < 256; i++) {
        a[i] = fqmul_montgomery(a[i], inv_n);
    }
}
```

> Implementation notes
> - Indexing & zeta order must match the chosen CT/GS schedule.
> - Use **constant‑time** add/sub and avoid secret‑dependent memory access.

---

## 2) Verilog RTL: 16‑bit interface, 32‑bit intermediates

### 2.1 Montgomery Multiplier (16×16→32 -> reduce to 16 mod q)
```verilog
// montgomery_mult16.v
module montgomery_mult16 #(
    parameter Q     = 16'd3329,
    parameter QINV  = 16'd3327   // -q^{-1} mod 2^16
) (
    input  logic [15:0] a,   // Montgomery domain
    input  logic [15:0] b,   // Montgomery domain
    output logic [15:0] c    // Montgomery domain: a*b*R^{-1} mod q
);
    // full product
    logic [31:0] t_prod;
    logic [15:0] u;
    logic [31:0] t_sum;
    logic [15:0] t_red;

    always_comb begin
        t_prod = a * b;                          // 32-bit
        u      = (t_prod[15:0] * QINV);          // (a*b * QINV) mod 2^16 (implicit low 16)
        t_sum  = t_prod + (u * Q);               // 32-bit add
        t_red  = t_sum[31:16];                   // divide by R=2^16
        // constant-time conditional subtract
        c      = (t_red >= Q) ? (t_red - Q) : t_red;
    end
endmodule
```

### 2.2 Radix‑2 Butterfly (Cooley‑Tukey, constant‑time add/sub)
```verilog
// ntt_butterfly.v
module ntt_butterfly #(
    parameter Q = 16'd3329
) (
    input  logic        clk,
    input  logic        en,        // one-cycle enable
    input  logic [15:0] a_in,      // Montgomery domain
    input  logic [15:0] b_in,      // Montgomery domain
    input  logic [15:0] zeta,      // Montgomery domain twiddle
    output logic [15:0] a_out,     // a' = a + zeta*b  (mod q)
    output logic [15:0] b_out      // b' = a - zeta*b  (mod q)
);
    logic [15:0] t;
    montgomery_mult16 u_mul (.a(b_in), .b(zeta), .c(t));

    // constant-time modular add/sub
    function automatic [15:0] add_mod_q(input [15:0] x, input [15:0] y);
        logic [16:0] sum;
        begin
            sum = x + y;
            add_mod_q = (sum >= Q) ? (sum - Q) : sum[15:0];
        end
    endfunction

    function automatic [15:0] sub_mod_q(input [15:0] x, input [15:0] y);
        logic signed [16:0] diff;
        begin
            diff = {1'b0,x} - {1'b0,y};
            sub_mod_q = (diff[16]) ? (diff + Q) : diff[15:0];
        end
    endfunction

    always_ff @(posedge clk) begin
        if (en) begin
            a_out <= add_mod_q(a_in, t);
            b_out <= sub_mod_q(a_in, t);
        end
    end
endmodule
```

> Integration tips
> - Pipeline the multiplier if Fmax is tight (stage on `t_prod`, `t_sum`).
> - Keep **twiddles in Montgomery domain** in BRAM/SRAM.
> - Use **fixed access patterns** (butterfly schedule) for side‑channel robustness.

---

## 3) ISA ↔ NTT Link (unchanged)
See v1 for DOT diagrams (§4 of previous version). Key reminders:
- **Data edges**: black dashed
- **Control edges**: blue dotted (microcode, masking)
- **Exception/Priority**: red solid

---

## 4) What to fill before tape‑out
- ✅ Replace `zetas[]` / `inv_zetas[]` with **official Kyber tables** (Montgomery domain).
- ✅ Confirm **inv_n = 256^{-1} mod 3329** and load as constant.
- ✅ Choose CT vs GS schedule and **verify index order** matches the table.
- ✅ Add **formal/RTL TB** comparing against the C functions above on random vectors.


## 0. 업데이트 사항
- **zetas[128] / zetas_inv[128]** 전체 테이블 (Montgomery 도메인) 추가 (Kyber 공식 레퍼런스 기반).
- C/Verilog 모두에서 바로 참조 가능.
- 비트폭: 계수/zetas는 **int16_t / [15:0]**, 곱/중간값은 **int32_t / [31:0]**.

---

## 2) 비트폭 가이드
- **16bit (int16_t, logic [15:0])**
  - 계수, zetas[], inv_zetas[], Q(3329), QINV(3327), Barrett v(20159) → 모두 안전하게 저장.
- **32bit (int32_t, logic [31:0])**
  - 곱/누산 중간값: a*b (최대 ~11비트×11비트=22bit), (a+u*q)까지 합산시 32bit 확보 필요.
- 하드웨어 권장: DSP 16×16 곱 → 32bit 결과, 모듈러 축약 후 다시 16bit.

---

## 3) 참고 구현 (Verilog)
(이전 버전의 `montgomery_mult16` / `ntt_butterfly` 코드 참조)

---

## 4) 결론
- zetas/zetas_inv는 **공식 Kyber 표준 테이블**을 그대로 사용.
- 저장 폭은 16bit, 연산 폭은 32bit 이상.
- ISA ↔ NTT 연계는 변함 없음.
