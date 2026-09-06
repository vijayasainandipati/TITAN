"""
TITAN Edge Agent Uplink Module
Serializes autonomous UAV engine twin state into a compressed, cryptographically
signed health-summary payload for transmission to Fleet Ground Station.
Enforces edge telemetry isolation: raw continuous sensor streams never leave the UAV.
"""

import hmac
import hashlib
import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict


# Secret key for military telemetry authentication (mocked for development)
DATALINK_SECRET_KEY = b"DRDO-TITAN-MIL-SPEC-AUTHENTICATED-DATALINK-KEY-2026"


@dataclass
class CompressedHealthSummary:
    engine_id: str
    engine_name: str
    timestamp: float
    flight_phase: str
    hi_engine: float
    hi_subsystems: Dict[str, float]
    predicted_fault: str
    fault_confidence: float
    fault_probabilities: Dict[str, float]
    rul_hours: float
    rul_conformal_interval_90: List[float]
    tactical_status: str
    ood_flag: bool
    sensor_fault_detected: bool
    payload_size_bytes: int
    bandwidth_compression_ratio: float
    signature: str
    raw_telemetry_isolated: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AgentUplinkManager:
    """
    Runs on the edge UAV compute module. Extracts health summaries from
    the local Digital Twin state and produces signed, bandwidth-efficient payloads.
    """
    def __init__(self, engine_id: str, secret_key: bytes = DATALINK_SECRET_KEY):
        self.engine_id = engine_id
        self.secret_key = secret_key

    def create_uplink_payload(self, frame: Dict[str, Any]) -> CompressedHealthSummary:
        """
        Compresses full engine telemetry frame into a lightweight health summary.
        Raw sensor arrays (temperatures, vibrations, high-frequency signals) are
        intentionally dropped to protect military data privacy and save tactical bandwidth.
        """
        engine_id = frame.get("engine_id", self.engine_id)
        engine_name = frame.get("engine_name", "UAV Powerplant")
        timestamp = frame.get("timestamp", time.time())
        flight_phase = frame.get("flight_phase", "CRUISE")
        
        hi_dict = frame.get("health_index", {})
        hi_engine = float(hi_dict.get("overall", 1.0))
        hi_subsystems = hi_dict.get("subsystems", {
            "thermal": 1.0,
            "lubrication": 1.0,
            "mechanical": 1.0,
            "combustion": 1.0
        })
        
        predictions = frame.get("predictions", {})
        pred_fault = predictions.get("fault_name", "NORMAL")
        fault_conf = float(predictions.get("fault_confidence", 0.95))
        rul_hours = float(predictions.get("rul_hours", 200.0))
        rul_interval = predictions.get("rul_conformal_interval_90", [rul_hours - 10.0, rul_hours + 10.0])
        ood_flag = bool(predictions.get("ood_flag", False))
        
        # Build fault probability distribution
        fault_probs = {
            "NORMAL": 0.05,
            "MISFIRE": 0.01,
            "INJECTOR_CLOGGING": 0.01,
            "LUBE_DEGRADATION": 0.01,
            "COOLING_DEGRADATION": 0.01,
            "BEARING_WEAR": 0.01,
            "SENSOR_FAULT": 0.01
        }
        if pred_fault in fault_probs:
            for k in fault_probs:
                fault_probs[k] = round((1.0 - fault_conf) / (len(fault_probs) - 1), 4)
            fault_probs[pred_fault] = round(fault_conf, 4)
        else:
            fault_probs["NORMAL"] = round(fault_conf, 4)

        tactical_risk = frame.get("tactical_risk", {})
        tactical_status = tactical_risk.get("tactical_status", "GO")
        
        sensor_health = frame.get("sensor_health", {})
        sensor_fault = bool(sensor_health.get("fault_detected", False))
        
        # Calculate bandwidth metrics
        # Raw 100Hz 16-channel 32-bit float telemetry is ~6.4 KB/s = 6400 bytes per second
        raw_telemetry_bytes = 6400
        
        summary_core = {
            "engine_id": engine_id,
            "timestamp": timestamp,
            "flight_phase": flight_phase,
            "hi_engine": round(hi_engine, 3),
            "hi_subsystems": {k: round(v, 3) for k, v in hi_subsystems.items()},
            "predicted_fault": pred_fault,
            "fault_confidence": round(fault_conf, 3),
            "fault_probabilities": fault_probs,
            "rul_hours": round(rul_hours, 1),
            "rul_conformal_interval_90": [round(x, 1) for x in rul_interval],
            "tactical_status": tactical_status,
            "ood_flag": ood_flag,
            "sensor_fault_detected": sensor_fault
        }
        
        # Serialize to calculate packet size
        serialized_json = json.dumps(summary_core, separators=(",", ":"))
        payload_bytes = len(serialized_json.encode("utf-8"))
        compression_ratio = round((raw_telemetry_bytes - payload_bytes) / raw_telemetry_bytes * 100.0, 1)
        
        # Generate HMAC-SHA256 signature for message authentication
        sig_digest = hmac.new(
            self.secret_key,
            serialized_json.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()[:32] # 128-bit truncated military hash

        return CompressedHealthSummary(
            engine_id=engine_id,
            engine_name=engine_name,
            timestamp=timestamp,
            flight_phase=flight_phase,
            hi_engine=round(hi_engine, 3),
            hi_subsystems={k: round(v, 3) for k, v in hi_subsystems.items()},
            predicted_fault=pred_fault,
            fault_confidence=round(fault_conf, 3),
            fault_probabilities=fault_probs,
            rul_hours=round(rul_hours, 1),
            rul_conformal_interval_90=[round(x, 1) for x in rul_interval],
            tactical_status=tactical_status,
            ood_flag=ood_flag,
            sensor_fault_detected=sensor_fault,
            payload_size_bytes=payload_bytes,
            bandwidth_compression_ratio=compression_ratio,
            signature=sig_digest,
            raw_telemetry_isolated=True
        )
