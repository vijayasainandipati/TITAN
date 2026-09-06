# Research Notes: PHM Data Challenge 2025 Lessons & Hybrid Paradigms

## 1. Context: 2025 Jet-Engine EHM Challenge
The 2025 Prognostics and Health Management (PHM) Society Data Challenge focused on Engine Health Monitoring (EHM) under multi-mission profiles, unseen operating environments, and sparse fault examples.

## 2. Winning Patterns Adopted in TITAN

### 2.1 Physics-Informed Domain Features Outperform Pure Deep Learning
- The top-performing submissions universally relied on physics residuals rather than raw telemetry input.
- Pure black-box models suffered catastrophic false alarms during altitude climbs and high-speed maneuvers where engine operating points drifted naturally.
- Feeding normalized residuals $r_i(t) = \frac{y_i(t) - \hat{y}_i(t)}{\sigma_i}$ allows neural networks to focus strictly on degradation rather than learning standard flight dynamics.

### 2.2 Decoupled Event-Specific Heads (Backbone + Specialization)
- Jointly training a monolithic model for anomaly detection, fault classification, and RUL estimation caused negative task transfer.
- Different degradation events possess distinct characteristic time scales:
  - Misfire: Millisecond to second timescale.
  - Bearing spalling: Minute to hour timescale.
  - Lubrication degradation & wear: Tens to hundreds of flight hours.
- A shared feature backbone feeding specialized, decoupled heads prevents interference between fast-transient anomalies and slow wear trajectories.

### 2.3 Hierarchical Aggregation (SAM-IPA Pattern)
- Direct end-to-end processing of continuous high-frequency streams (10–50 Hz) creates noise saturation.
- Multi-tier aggregation (Cycle level $\rightarrow$ Flight Phase level $\rightarrow$ Mission level) yields stable, learnable features that generalize cleanly across engines.
