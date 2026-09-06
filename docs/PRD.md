# TITAN — Physics-Informed Digital Twin for MALE UAV Aero-Piston Engines
## Final PRD / MVP Specification, Implementation Architecture, Project Structure & Methodology

**Problem Statement:** 26054 / SIH 26054 / DRDO–iDEX  
**Domain:** Defence / Aerospace / UAV Propulsion — MALE UAV Aero-Piston Engine Digital Twin  
**Document Status:** Frozen for build — v1.0  

**TITAN** is the finalized product and architecture name (supersedes earlier "AeroTwin AI" working title).

---

# PART A — PRODUCT DEFINITION

## A.1 Vision

> A physics-informed, mission-aware Digital Twin that continuously mirrors a MALE-UAV piston engine, separates sensor faults from engine faults, detects developing abnormalities before thresholds are crossed, predicts faults and degradation, estimates Remaining Useful Life with calibrated confidence, and evaluates mission-level reliability — with every prediction explainable back to physical evidence.

Transforms conventional monitoring from **Sense → Threshold → Alert** into **Sense → Understand → Predict → Simulate → Recommend**.

## A.2 Problem Grounding (Research Gaps)

| Gap | Why it matters here |
|---|---|
| Reactive, threshold-based monitoring | Long-endurance ISR cannot afford late detection |
| No RUL/degradation tracking for piston engines | Existing PHM research (CMAPSS, DRDO TDF) targets gas turbines, not piston |
| No mission-wise what-if simulation | Operators need pre-mission reliability answers, not just post-flight logs |
| Physics+AI hybrid work is turbine-focused | Piston thermodynamics, vibration, lubrication behavior differ materially |
| Real fault-labeled data is scarce | True industry-wide (confirmed by DRDO TDF context, CMAPSS documentation, and PHM Society Data Challenge patterns independently) — justifies synthetic-first strategy |
| Cloud-heavy / black-box DTs don't fit defence | Need lightweight, offline-capable, explainable, edge-deployable design |
| No mission-context-aware health weighting | Same residual means different risk in climb vs. loiter |

## A.3 Positioning

Complementary niche to DRDO's TDF gas-turbine HUMS effort and IAF–IIT Bombay Su-30 MKI health-index work — both gas-turbine-focused. Piston-engine MALE UAV propulsion is an underserved segment. Architecture choices (hybrid physics+data, uncertainty quantification, explainability, event-specific models) track directly with themes recurring across NASA CMAPSS benchmark research and PHM Society Data Challenges (2025 jet-engine EHM challenge in particular), rather than being ad hoc.

---

# PART B — MVP SCOPE

## B.1 MVP MUST include

1. Multi-engine synthetic telemetry simulator (physics-grounded, multiple simulated engine instances — see B.3)
2. Real-time telemetry stream (simulated CAN/ECU feed)
3. Digital Twin state (virtual engine mirror)
4. Physics-based expected-state model (thermal, lubrication, mechanical)
5. Sensor Health module (cross-sensor consistency, independent of engine health)
6. Physics residual engine
7. Hierarchical aggregation (sensor → phase → mission → engine)
8. Anomaly detection head
9. Fault classification head
10. Health Index (subsystem + engine-level, mission-phase-weighted)
11. RUL estimation head with calibrated confidence interval
12. Recovery/reset modeling after maintenance events
13. Mission simulation & what-if engine
14. Mission replay
15. Explainable dashboard (5 views: Operational, Engineering, Maintenance, Replay, Simulator)
16. Ablation study results (A→E, see Part E) as MVP evidence, not just a working demo

## B.2 Explicitly OUT of MVP scope (Future Work)

- Real ECU/FADEC/CAN bus hardware integration
- Real engine test-rig data
- Hardware-in-the-loop testing
- Full defence-grade security stack (represented architecturally only — see Part F)
- Federated fleet learning
- Edge hardware deployment (architecture supports it; MVP runs on a single local/cloud instance)
- Formal CEMILAC/DGAQA certification submission

## B.3 Multi-Engine Synthetic Data Requirement

To support the leave-engine-out generalization test in Part E, the synthetic generator must produce **multiple distinct simulated engine instances** — not just multiple missions of one engine. Vary per instance:
- Manufacturing-tolerance-style parameter jitter (±X% on thermal/mechanical constants)
- Baseline wear-rate multiplier
- Sensor noise/bias profile per instance

---

# PART C — TITAN ARCHITECTURE

## C.1 Pipeline

```
                 UAV ENGINE
                     │
                     ▼
              Raw Telemetry
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
    Sensor Health          Physics Twin
   (cross-sensor            (thermal /
    consistency,          lubrication /
    drift/dropout          mechanical
    detection)              models →
          │              expected state)
          │                     │
          └──────────┬──────────┘
                     ▼
              Residual Engine
           r_i(t) = (y_i - ŷ_i)/(σ_i+ε)
                     │
                     ▼
        Hierarchical Aggregation
        ┌──────────┼───────────┐
        ▼          ▼           ▼
      Sensor     Mission     Engine
      Features   Phase       State
      (cycle-    (IDLE/CLIMB/
       level)     CRUISE/...)
        └──────────┼───────────┘
                   ▼
             Health Indicators
         HI_i(t) = f(r_i, ṙ_i, op. condition)
         HI_engine(t) = Σ w_i·HI_i(t)
         (w_i = mission-phase-dependent)
                   │
          ┌────────┼─────────┬───────────┐
          ▼        ▼         ▼           ▼
       Anomaly   Fault    Degradation   Virtual
       (head)   (head)      (head)      Sensors
                              │        (missing-
                              ▼         channel
                             RUL       reconstruction,
                        (+ confidence   confidence
                         interval /      reduction)
                         OOD flag)
                              │
                 ┌────────────┘
                 ▼
           Mission Risk
        (What-if simulator,
         mission replay)
                 │
                 ▼
        Maintenance Advisory
      (recommend, not authorize;
       recovery/reset logic tied
       to maintenance events)
                 │
                 ▼
          Explainable Dashboard
     (residual contribution + SHAP +
      temporal evidence + physical
      consistency flags)
```

## C.2 Key design decisions locked in this revision

| Decision | Rationale |
|---|---|
| Sensor Health separated from Physics Twin **before** residual computation | Lets the system distinguish "sensor is lying" from "engine is degrading" structurally, not post-hoc |
| Event-specific heads (anomaly / fault / degradation / RUL) on a shared aggregated-feature backbone | Matches PHM NA 2025 winning pattern: different subsystems/events have different time scales; a single shared model underperforms |
| Physics residuals as the primary AI input feature, not raw telemetry | Validated by PHM NA 2025 top-3 solutions, all physics/domain-feature-driven, outperforming pure black-box models |
| Recovery/reset modeling tied to maintenance events | Without it, degradation curves are wrongly monotonic; maintenance actions must visibly reset relevant HI_i |
| Physical consistency constraints (residual bounds, trajectory monotonicity between maintenance events) | Enforce plausibility; flag out-of-envelope operation explicitly rather than emit a confident-but-wrong number |
| Confidence/OOD layer as a named, implemented component (not a label) | See C.3 — required for judge-defensible uncertainty claims |
| Hierarchical aggregation (sensor → phase → mission → engine) before sequence modeling | Converts noisy continuous streams into stable, learnable cycle/segment-level features (SAM-IPA-1 pattern) |

## C.3 Confidence / OOD Method (confirmed)

MVP uses **ensemble variance** across the ablation models (cheapest to implement, already trained as part of Part E) as the confidence signal. **Conformal prediction** is the stretch goal, to obtain a calibrated, provable coverage guarantee on RUL intervals (reportable via PICP — see Part E metrics). Mahalanobis distance on the residual feature space is the fallback for OOD flagging if ensembling proves too slow for real-time use.

## C.4 Physical-consistency violation handling (confirmed)

On residual-bound or monotonicity violation, TITAN **flags live as "outside validated envelope"** rather than silently clipping — surfaced on the Engineering dashboard view as a distinct state from a normal fault alert, since it means the *physics model* may be inadequate for current conditions (e.g., extreme altitude/temperature), not necessarily that the *engine* has faulted.

---

# PART D — METHODOLOGY & COMPARISON

## E.0 Phase 0 — Pre-validation on CMAPSS

Before building the piston-engine simulator, validate candidate sequence architectures on **NASA CMAPSS FD001** (turbofan RUL benchmark) to de-risk architecture choice independent of your own synthetic data.
- Metrics: RMSE, NASA asymmetric score
- Explicit disclaimer: turbofan physics ≠ piston thermodynamics — this validates *methodology*, not piston-engine performance

## E.1 Core Ablation Study (mandatory)

| Variant | Configuration |
|---|---|
| A | GRU on raw telemetry |
| B | CNN-GRU + engineered features |
| C | CNN-GRU + physics residuals |
| D | CNN-GRU + physics residuals + mission context |
| E | Full TITAN: aggregation + event-specific heads + confidence/OOD layer |

**Metrics reported for every variant:**
- Anomaly recall
- Fault macro-F1
- Health-index MAE
- RUL MAE
- Late-detection rate (asymmetric — critical per risk-aligned loss framing)
- False-positive rate
- Performance on unseen operating conditions (leave-engine-out split, per B.3)
- **PICP** (Prediction Interval Coverage Probability) — calibration quality of RUL confidence intervals, applicable to variant E

**Research question:** Does physics-residual and mission-context fusion improve generalization, early fault detection, and RUL estimation of aero-piston engine PHM under limited failure data?

**Success criterion:** C/D/E outperforming A/B on the above metrics is the evidence for the central hypothesis — this is what makes the physics-informed claim defensible rather than asserted.

## E.2 Generalization Test

Leave-engine-out cross-validation using the multi-engine synthetic dataset (B.3) — train on N-1 simulated engine instances, test on the held-out instance, repeated across instances.
