# Research Notes: Indian Defence Standards, CEMILAC & Airworthiness Certification

## 1. Statutory Framework for Military UAV Propulsion
In Indian defence aviation (DRDO, Indian Air Force, Indian Army, Indian Navy), engine health monitoring and digital twin solutions are governed by strict airworthiness frameworks:
- **CEMILAC** (Centre for Military Airworthiness and Certification) per DDPMAS-2002 (Design, Development and Production of Military Aircraft and Airborne Stores).
- **DGAQA** (Directorate General of Aeronautical Quality Assurance) for manufacturing and operational quality acceptance.
- **DO-178B / DO-178C**: Software Considerations in Airborne Systems and Equipment Certification (Design Assurance Level DAL B/C for advisory and predictive maintenance subsystems).
- **MIL-STD-810G / JSS-55555**: Environmental test methods for defence electronics and onboard telemetry processing hardware.

## 2. Airworthiness Requirements Addressed in TITAN Architecture

| Airworthiness Mandate | TITAN Architectural Countermeasure |
|---|---|
| **No Unverified "Black Box" Decisions** | All predictions explainable back to physics residuals and thermodynamic parameters; SHAP attribution trail. |
| **Fail-Safe Operation** | TITAN acts as an *Advisory Engine* (recommends, does not override flight control/FADEC); parallel legacy threshold safety net preserved. |
| **Model Envelope Bounds** | Explicit live flagging of "OUTSIDE VALIDATED ENVELOPE" when operating beyond validated altitudes or ambient temperatures. |
| **Sensor vs Engine Fault Disambiguation** | Sensor Health module isolates sensor drift/dropout before residual generation, preventing unwarranted engine groundings. |
| **Determinism & Reproducibility** | Mission Replay engine allows bit-exact deterministic replay of telemetry and twin state for mishap investigations. |
| **Role-Based Access & Audit Logging** | Built-in audit trail stub recording maintenance recommendations, operator overrides, and reset events. |
