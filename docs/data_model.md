# TITAN Data Model & Telemetry Specification

## 1. Raw Telemetry Schema (`TelemetryFrame`)

Each frame represents the high-frequency telemetry ingested from the engine ECU and external avionics bus:

```json
{
  "timestamp": 12450.5,
  "engine_id": "ENG-MALE-01",
  "flight_id": "FLIGHT-2026-0906-01",
  "flight_phase": "CRUISE",
  "operational_conditions": {
    "rpm": 4850.0,
    "manifold_pressure_bar": 1.15,
    "throttle_pct": 78.5,
    "altitude_ft": 18500.0,
    "true_airspeed_kts": 105.0,
    "ambient_temp_c": -18.2,
    "ambient_pressure_bar": 0.505
  },
  "sensors": {
    "cht_1_c": 118.5,
    "cht_2_c": 119.2,
    "cht_3_c": 120.1,
    "cht_4_c": 118.9,
    "egt_1_c": 745.0,
    "egt_2_c": 752.0,
    "egt_3_c": 748.0,
    "egt_4_c": 750.0,
    "oil_pressure_bar": 3.82,
    "oil_temp_c": 88.4,
    "coolant_temp_c": 82.1,
    "vibration_rms_g": 1.42,
    "vibration_peak_g": 2.85,
    "fuel_flow_lph": 24.6
  }
}
```

## 2. Digital Twin Expected State Schema (`TwinState`)

```json
{
  "timestamp": 12450.5,
  "engine_id": "ENG-MALE-01",
  "expected": {
    "cht_mean_c": 118.2,
    "egt_mean_c": 748.5,
    "oil_pressure_bar": 3.90,
    "oil_temp_c": 87.8,
    "coolant_temp_c": 81.5,
    "vibration_rms_g": 1.38,
    "fuel_flow_lph": 24.3
  },
  "envelope_status": "VALID_ENVELOPE",
  "confidence": 0.96
}
```

## 3. Residual Vector Schema (`ResidualFrame`)

```json
{
  "timestamp": 12450.5,
  "residuals": {
    "r_cht_mean": 0.12,
    "r_egt_mean": 0.05,
    "r_oil_pressure": -0.45,
    "r_oil_temp": 0.32,
    "r_coolant_temp": 0.28,
    "r_vibration_rms": 0.15
  },
  "sensor_health": {
    "cht_sensor_ok": true,
    "egt_sensor_ok": true,
    "oil_press_sensor_ok": true,
    "oil_temp_sensor_ok": true,
    "vibration_sensor_ok": true,
    "status": "ALL_HEALTHY"
  }
}
```

## 4. Health & Advisory Schema (`EngineHealthStatus`)

```json
{
  "timestamp": 12450.5,
  "engine_id": "ENG-MALE-01",
  "health_index": {
    "engine_overall": 0.912,
    "subsystems": {
      "thermal": 0.940,
      "lubrication": 0.885,
      "mechanical": 0.930,
      "combustion": 0.960
    },
    "phase_weights": {
      "thermal": 0.30,
      "lubrication": 0.35,
      "mechanical": 0.20,
      "combustion": 0.15
    }
  },
  "predictions": {
    "anomaly_detected": false,
    "anomaly_score": 0.18,
    "fault_class": "NORMAL",
    "fault_confidence": 0.92,
    "rul_flight_hours": 142.5,
    "rul_confidence_interval_90": [128.0, 157.0],
    "picp_calibrated": true,
    "ood_flag": false
  },
  "mission_risk": {
    "status": "GO",
    "risk_index": 0.12,
    "limiting_factor": "NONE"
  }
}
```
