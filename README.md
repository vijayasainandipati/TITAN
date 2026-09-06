# TITAN — Physics-Informed Digital Twin for MALE UAV Aero-Piston Engines

**Problem Statement:** 26054 / SIH 26054 / DRDO–iDEX  
**Domain:** Defence / Aerospace / UAV Propulsion — MALE UAV Aero-Piston Engine Digital Twin  
**Document Status:** v1.0 Frozen Architecture Implementation  

---

## 1. Vision & Overview

**TITAN** is an advanced physics-informed, mission-aware Digital Twin that continuously mirrors a Medium-Altitude Long-Endurance (MALE) Unmanned Aerial Vehicle (UAV) aero-piston engine (e.g., Rotax 914 / Austro Engine AE300 / DRDO TAPAS-BH-201 class 4-cylinder turbocharged powerplant).

TITAN fundamentally transforms conventional monitoring from **Sense → Threshold → Alert** into **Sense → Understand → Predict → Simulate → Recommend**:
- **Separates Sensor Faults from Engine Faults**: Evaluates sensor cross-consistency and analytical redundancy before residual computation.
- **Physics Residual Engine**: Normalizes deviations between sensor telemetry and first-principles thermal, lubrication, and mechanical ODE predictions.
- **Hierarchical Aggregation**: Collapses high-rate continuous sensor streams into cycle-level, phase-level, and mission-level health indicators.
- **Risk-Aligned Multi-Tier AI**: Employs an asymmetric loss function penalizing late fault detection, providing event-specific heads for anomaly, FMEA fault classification, and Remaining Useful Life (RUL).
- **Calibrated Uncertainty**: Delivers conformal prediction intervals (target 90% coverage / PICP) and out-of-distribution (OOD) flagging.
- **What-If Mission Intelligence & Replay**: Simulates prospective mission feasibility and replays historical sorties with early-detection delta visualization.

---

## 2. System Architecture

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

---

## 3. Directory Layout

```
TITAN/
├── docs/                        # Complete PRD, architecture, schemas & research
│   ├── PRD.md
│   ├── architecture.md
│   ├── data_model.md
│   └── research/
├── sim/                         # First-principles synthetic physics engine & FMEA
│   ├── physics_models/          # Thermal, lubrication, mechanical differential equations
│   ├── mission_profiles/        # Endurance, hot weather, high altitude, rapid response
│   ├── fault_injection/         # FMEA taxonomy, degradation kinetics, maintenance resets
│   └── generate_dataset.py      # Multi-engine multi-mission dataset generator
├── twin_core/                   # Dynamic state estimator, sensor health, residual engine
├── aggregation/                 # Cycle, phase, and mission feature aggregation & HI
├── models/                      # Ablation models A-E, risk-aligned loss, conformal intervals
├── evaluation/                  # CMAPSS pre-validation, ablation harness, metrics
├── mission_intel/               # What-if simulator, replay engine, risk scoring
├── backend/                     # FastAPI backend, CAN ingestion, advisory engine
├── dashboard/                   # 5-View Defence Dashboard (React/Vite/Tailwind)
└── tests/                       # Pytest test suite for physics, twin, and ML pipelines
```

---

## 4. Quickstart

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Node.js 18+ (tested on Node v26)

### Installation
```bash
pip install -r requirements.txt
cd dashboard && npm install && cd ..
```

### Run Tests
```bash
python -m pytest tests/ -v
```

### Launch Backend & Dashboard
```bash
# Start FastAPI backend
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Start Vite dashboard
cd dashboard && npm run dev
```

Visit the dashboard at `http://localhost:5173` to interact with:
1. **Operational View**: Tactical HUD, live engine dials, and health indices.
2. **Engineering View**: Physics twin vs actuals, normalized residual stream, and sensor health matrix.
3. **Maintenance View**: RUL countdown, calibrated 90% confidence bands, and maintenance resets.
4. **Replay View**: Historical mission scrubbing and early detection comparison.
5. **Simulator View**: Interactive what-if mission reliability sandbox.
