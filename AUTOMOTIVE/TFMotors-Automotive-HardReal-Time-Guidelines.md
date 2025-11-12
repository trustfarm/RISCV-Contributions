# TFMotors Automotive Hard Real-Time (HRT) 가이드라인  
**버전**: 1.0 | **발행일**: 2025-11-12 | **승인**: 안전총괄이사  
**적용 범위**: 모든 1차 안전기능 (Primary Safety-Critical Systems)  
> **이 스펙을 만족하지 못하면 차량은 즉시 폐차/리콜 대상입니다.**

## 1. 1차 안전기능 1/5 강화 마지노선 (폐차급 기준)

| 시스템 | ASIL | 기존 마지노선 | **1/5 강화 마지노선 (폐차급)** | HRT 성격 및 폐차 사유 |
|--------|------|----------------|--------------------------------|-----------------------|
| 브레이킹 시스템 (ABS/ESC/AEB 액추에이션) | D | <50 ms / <200 ms | **≤10 ms** (ECU runnable)<br>**≤40 ms** (End-to-End) | 10 ms 초과 → 고속사고 필연 |
| 스티어링 시스템 (EPS, Steer-by-Wire) | D | <30 ms | **≤6 ms** (센서→타이어 각도) | 6 ms 지연 → 100 km/h 기준 1.6 m 이탈 → 즉사 |
| 엔진/파워트레인 제어 | D | <10 ms | **≤2 ms** (연료 분사/스로틀) | 2 ms 지연 → 순간 가속/제동 불능 |
| 에어백 배포 시스템 | D | <20 ms | **≤4 ms** (Crash→Deploy) | 4 ms 늦음 → 사망률 90 %↑ |
| 긴급 차선 유지 (ELK) | D | <50 ms | **≤10 ms** (센서→조향 토크) | 10 ms 늦음 → 120 km/h 기준 3.3 m 이탈 |
| 고전압 배터리 안전 차단 | D | <100 ms | **≤20 ms** (충돌→HV 차단) | 20 ms 늦음 → 배터리 화재/전소 |

## 2. 강화 스펙 달성 필수 조건 (미준수 시 인증 불가)

| 항목 | 요구사항 | 비고 |
|------|----------|------|
| OS | AUTOSAR Classic **SC4 + OSEC4** | SC1~3 절대 금지 |
| MCU | Lockstep Core, **≥2000 DMIPS** (TC397/TC49x 권장) | 단일 코어 금지 |
| 네트워크 | **TSN Ethernet 1000BASE-T1** 또는 **FlexRay 10 Mbps** | CAN-FD 사용 시 즉시 불합격 |
| WCET 분석 | RapiTime + aiT로 **100 % 커버리지** | 80 % 이상 시 불합격 |
| 런타임 모니터링 | SafeTI 또는 RTA-HVR **상시 데드라인 감시** | 위반 1회 → 즉시 Safe State + 리콜 |

## 3. 한 줄 요약
> **“1차 안전기능이 1/5 마지노선을 못 맞추면, 그 차는 도로 위 이동형 관(棺)이다.”**

---

###  **English Version (EN)**

# TFMotors Automotive Hard Real-Time (HRT) Guidelines  
**Version**: 1.0 | **Issued**: 2025-11-12 | **Approved by**: Chief Safety Officer  
**Scope**: All Primary Safety-Critical Systems  
> **Failure to meet this spec = Immediate vehicle scrapping/recall**

## 1. Primary Safety Functions – 1/5 Tightened Deadline (Scrappage-Level)

| System | ASIL | Original Deadline | **1/5 Tightened Deadline (Scrappage)** | HRT Nature & Scrappage Reason |
|--------|------|-------------------|---------------------------------------|-------------------------------|
| Braking System (ABS/ESC/AEB actuation) | D | <50 ms / <200 ms | **≤10 ms** (ECU runnable)<br>**≤40 ms** (End-to-End) | >10 ms → inevitable high-speed crash |
| Steering System (EPS, Steer-by-Wire) | D | <30 ms | **≤6 ms** (sensor→tire angle) | 6 ms delay → 1.6 m lane departure at 100 km/h → fatality |
| Engine/Powertrain Control | D | <10 ms | **≤2 ms** (fuel injection/throttle) | 2 ms delay → instantaneous loss of acceleration/braking |
| Airbag Deployment | D | <20 ms | **≤4 ms** (crash→deploy) | 4 ms late → mortality ↑90 % |
| Emergency Lane Keeping (ELK) | D | <50 ms | **≤10 ms** (sensor→steering torque) | 10 ms late → 3.3 m departure at 120 km/h |
| HV Battery Safety Cut-off | D | <100 ms | **≤20 ms** (crash→HV contactor open) | 20 ms late → battery fire/total loss |

## 2. Mandatory Requirements for Compliance (Non-compliance = Certification Failure)

| Item | Requirement | Note |
|------|-------------|------|
| OS | AUTOSAR Classic **SC4 + OSEC4** | SC1~3 strictly prohibited |
| MCU | Lockstep Core, **≥2000 DMIPS** (TC397/TC49x recommended) | Single-core forbidden |
| Network | **TSN Ethernet 1000BASE-T1** or **FlexRay 10 Mbps** | CAN-FD = instant rejection |
| WCET Analysis | 100 % coverage with RapiTime + aiT | <80 % = fail |
| Runtime Monitoring | SafeTI or RTA-HVR **continuous deadline watchdog** | 1 violation → immediate Safe State + recall |

## 3. One-Line Summary
> **“If primary safety misses the 1/5 deadline, the vehicle is no longer a car—it’s a rolling coffin.”**

---
**TFMotors Div.**  
Safety-Critical Systems Division  
Contact: trustfarm.info@gmail.com