⚠ **내부자료 (출처 추가 확인 필요)**
⚠ **Internal Document (Source verification required before external use)**

---

# Automotive Safety System — Full Internal Guide
**TFMotors Official Internal Training Doc**  
*(For all staff — engineers, executives, and newcomers; ~30 minutes to digest)*

---

## 1) Primary Safety (Tier‑1, Hard Real‑Time Domain)
→ Failure in any of these = **Immediate rolling coffin** (existential company risk)

### HRT Limits (TFMotors 1/5‑Tightened Targets)

| System | ASIL | Core Sensors | Core Actuators | 1/5 Safety Threshold (Scrappage‑level) | References (Official) |
|---|---:|---|---|---|---|
| **ABS (Anti‑lock Braking System)** | D | Wheel‑speed sensors (≈1 kHz) | Hydraulic Modulator (HCU) | **ECU runnable ≤ 0.2 ms / End‑to‑End ≤ 1 ms** | NHTSA Consumer Alert “Kia & Hyundai: Park Outside” (2023‑09‑27); Reuters report (US mass recall over fire risk). |
| **ESC (Electronic Stability Control)** | D | Yaw‑rate + lateral‑G + steering angle | Individual wheel braking + engine torque reduction | **E2E ≤ 1 ms** | NHTSA Recalls **24V‑653** (Ram 1500), **24V‑415** (Durango): ABS SW fault may disable ESC. |
| **AEB (Autonomous Emergency Braking)** | D | Front radar + camera fusion | Brakes + Pretensioner | **Actuation ≤ 0.2 ms / E2E ≤ 1 ms** | Euro NCAP **Kia EV9**: VRU (pedestrian/cyclist/motorcyclist) score **76%**; “adequate” in some scenarios (no public ms figure). |
| **EPS (Electric Power Steering)** | D | Dual torque/angle sensors | 3‑phase BLDC motor | **Sensor→Torque ≤ 6 ms** | **BMW iX** cruise‑control SW error recall (NHTSA 23V‑409) impacting steering safety context. |
| **Steer‑by‑Wire (planned)** | D | Triple angle sensors | Dual motor + clutch | **Cmd→Wheel angle ≤ 4 ms** | No quantitative ms rule in current Euro NCAP protocols (roadmap direction only). |
| **Airbag SRS** | D | Central accelerometer + pressure sensors | Airbag modules + igniters | **Crash→Deploy ≤ 4 ms** | NHTSA **21V‑472** (GM): SDM calibration may affect deployment timing/level. |
| **HVIL (High‑Voltage Interlock)** | D | Connector interlocks | HV contactors (≈800 V) | **Crash→Cutoff ≤ 20 ms** | **Porsche Taycan**: battery short‑circuit risk → fire hazard (Reuters; The Verge). |

> **Note**: Official recalls/reports specify **failure cause, risk, remedy**, but typically **do not publish exact control delays (ms)**. We cite verified **risk categories**, not numeric delays.

---

## 2) Secondary Safety (Tier‑2, Soft RT Assist)
→ Failure **won’t kill people**, but raises insurance/quality risk

| System | ASIL | Notes |
|---|---:|---|
| **FCW (Forward Collision Warning)** | B | Alerts only — driver or Tier‑1 ECU performs control. |
| **LDW/LKA (Lane Departure Warn/Keep)** | B | Assistive; driver override possible. |
| **ACC (Adaptive Cruise Control)** | B | Must remain isolated from Tier‑1 brake/steer HRT domain. |
| **BSM (Blind‑Spot Monitor)** | QM | Indicator‑based; false/missed alerts → minor risk. |

---

## 3) Tertiary / Convenience (Non‑RT)
→ Failure is **non‑fatal**, but hurts brand trust and UX

| System | ASIL | Fact‑checked Notes |
|---|---:|---|
| **FSD / Highway Pilot (Level 2+)** | QM | Current systems require **hands‑on & driver supervision** by law/regulation. |
| **Remote / Auto Parking** | QM | Low‑speed collision risk; insurable damage only. |
| **OTA Update** | QM | Update failures may temporarily disable non‑HRT modules; **HRT domain must be physically/logically isolated**. |

---

## 4) Verified Recalls & Incidents (Delay Not Disclosed; Models Masked)
— **Compliance‑safe table** with masked models and official sources only

| No. | Model (Masked) | Delay | Issue Summary | Official Source |
|---:|---|---|---|---|
| 1 | 20XX **H*** Crossover | N/A | ABS module leak → electrical short → **fire risk** (“Park Outside” recall) | NHTSA Consumer Alert (2023‑09‑27); Reuters |
| 2 | 2019–2024 **R\*\*** 1500 | N/A | ABS SW fault may **disable ESC** (≈1.2M units) | NHTSA Recalls **24V‑653** & **24V‑415** |
| 3 | 2022–2024 **B\*\*** iX | N/A | Cruise‑control SW error → steering‑safety impact | Car and Driver; NHTSA **23V‑409** |
| 4 | 20XX **B****/*** T***** | N/A | Airbag **SDM calibration** may affect timing/level | NHTSA **21V‑472** |
| 5 | 2021–2024 **P****** T***** | N/A | HV battery **short‑circuit** risk → fire hazard | Reuters; The Verge |

> **Legal note**: We avoid publishing ms‑level delays for incidents, as these are generally not disclosed. Only **verified defect types and official recall facts** are listed.

---

## 6) One‑Line Summary Variants

| Use | EN Message |
|---|---|
| **Internal awareness** | “If primary safety misses the 1/5 threshold, the car becomes a rolling coffin.” |
| **Executive briefing** | “Miss 1/5 and you own a 1.5‑ton coffin, a bomb, and a $1.5B recall bill.” |
| **Public/official** | “The 1/5 threshold in Primary Safety is not optional — it’s survival.” |


## 🚨 Conclusion:
  - The vehicle itself may be **destroyed**, but the **occupant’s life must never be sacrificed**.
The **HRT** specification is **a line of survival**, prioritized above convenience features or smart functionality.

---

## Appendix A — Historical Warning Case (Toyota Recall Crisis, 2009–2011)

- **Issue**: “Unintended acceleration” → ~**9 million** vehicles recalled worldwide.  
- **Causes**: Pedal‑stick/floor‑mat interference; ECU concerns investigated.  
- **Outcomes**:  
  - **US$ 1.2B** settlement (2014, US DOJ).  
  - Sales slump and brand trust damage; temporary production suspension.  
  - Share price drop (≈20% at troughs cited across reports).  
- **Meaning**: Even the largest OEM can face **existential risk** from a Tier‑1 safety failure — threatening **survival, jobs, and national industrial trust**.

**Timeline**
| Year | Event | Impact |
|---|---|---|
| **2009‑09** | First high‑profile US crash reported | National media spotlight |
| **2010‑02** | ~9M vehicles recalled | Production pause; dealer inspections |
| **2014‑03** | US DOJ settlement **$1.2B** | Criminal charges avoided; brand hit |
| **2015–2017** | Gradual market‑share recovery | Large‑scale reinvestment in quality & safety |

**Sources**: Wikipedia “2009–2011 Toyota vehicle recalls”; ABC News (2014, $1.2B settlement); Investopedia (recall impact on companies).

---

## References
- NHTSA Consumer Alert (2023‑09‑27): “Kia and Hyundai — Park Outside.”  
- Reuters (2023‑09‑27): “Kia, Hyundai recall 3.37M US vehicles over fire risks.”  
- NHTSA Recalls 24V‑653 / 24V‑415 (ABS SW → ESC disable risk).  
- Car and Driver (2023): “BMW iX Cruise Control Recall.” + NHTSA 23V‑409.  
- NHTSA 21V‑472 (GM Airbag SDM Calibration Error).  
- Reuters / The Verge (2024‑10‑08): Porsche Taycan Battery Short Circuit Risk.  
- Euro NCAP (2024): Kia EV9 — Pedestrian/VRU score 76%.  
- Wikipedia: 2009–2011 Toyota Vehicle Recalls; ABC News (2014 $1.2B settlement); Investopedia on recall impact.

---

© 2025 TFMotors Safety‑Critical Systems Division 
 - Contact: trustfarm.info@gmail.com  

(Internal training & verification use only. **Source re‑verification required prior to any external references.**)
