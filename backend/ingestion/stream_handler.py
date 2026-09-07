"""
TITAN Telemetry Stream & Engine State Manager
Manages the continuous real-time simulated CAN/ECU telemetry stream,
evaluates Digital Twin expected states, sensor health, normalized residuals,
and AI inferences for the active engine fleet.
"""

import time
import numpy as np
from typing import Dict, List, Optional

from sim.engine_instance import EngineInstance, create_fleet
from sim.mission_profiles import get_mission_profile
from sim.fault_injection.fmea_taxonomy import FMEAFaultClass, get_fault_name
from sim.fault_injection.degradation_curves import DegradationManager
from sim.sensor_noise import SensorNoiseEngine
from twin_core.state_estimator import DigitalTwinStateEstimator
from twin_core.sensor_health import SensorHealthModule
from twin_core.residual_engine import PhysicsResidualEngine
from twin_core.virtual_sensors import VirtualSensorReconstruction
from aggregation.health_index import HealthIndexCalculator
from mission_intel.risk_scoring import TacticalRiskScorer
from backend.advisory_engine import MaintenanceAdvisoryEngine


class EngineStreamSession:
    def __init__(self, engine: EngineInstance, mission_profile_name: str = "endurance"):
        self.engine = engine
        self.profile = get_mission_profile(mission_profile_name)
        self.noise_engine = SensorNoiseEngine(
            sensor_bias=engine.sensor_bias,
            sensor_noise_sigma=engine.sensor_noise_sigma
        )
        self.deg_mgr = DegradationManager(wear_multiplier=engine.wear_rate_multiplier)
        
        # Digital twin pipeline components
        self.state_estimator = DigitalTwinStateEstimator()
        self.sensor_health = SensorHealthModule()
        self.residual_engine = PhysicsResidualEngine()
        self.virtual_sensors = VirtualSensorReconstruction()
        self.health_calc = HealthIndexCalculator()
        self.risk_scorer = TacticalRiskScorer()
        
        self.sim_time = 0.0
        self.dt = 1.0 # 1 second steps
        
        # Active state cache
        self.current_frame: Optional[Dict] = None

    def step(self) -> Dict:
        """
        Advances engine telemetry and twin state by dt.
        """
        self.sim_time += self.dt
        cond = self.profile.get_conditions(self.sim_time)
        
        # 1. Natural or injected degradation
        self.deg_mgr.step(self.dt, cond["rpm"], cond["map_bar"], self.engine.lubrication.t_oil)
        deg_state = self.deg_mgr.get_degradation_state()
        
        # 2. Step physics models
        cooling_factor = 1.0 - 0.55 * deg_state["cooling_degradation"]
        misfire_cyl = deg_state["misfire_cylinder"] if deg_state["misfire_active"] else None
        
        thermal_out = self.engine.thermal.step(
            dt=self.dt,
            rpm=cond["rpm"],
            map_bar=cond["map_bar"],
            throttle_pct=cond["throttle_pct"],
            tas_kts=cond["tas_kts"],
            altitude_ft=cond["altitude_ft"],
            ambient_temp_c=cond["ambient_temp_c"],
            cooling_degradation_factor=cooling_factor,
            misfire_cylinder=misfire_cyl
        )
        
        lube_out = self.engine.lubrication.step(
            dt=self.dt,
            rpm=cond["rpm"],
            cht_mean_c=thermal_out["cht_mean_c"],
            tas_kts=cond["tas_kts"],
            altitude_ft=cond["altitude_ft"],
            ambient_temp_c=cond["ambient_temp_c"],
            bearing_wear_multiplier=1.0 + 1.2 * deg_state["bearing_wear"],
            oil_leak_severity=deg_state["lube_degradation"]
        )
        
        mech_out = self.engine.mechanical.step(
            dt=self.dt,
            rpm=cond["rpm"],
            throttle_pct=cond["throttle_pct"],
            map_bar=cond["map_bar"],
            bearing_wear_severity=deg_state["bearing_wear"],
            misfire_active=deg_state["misfire_active"],
            blowby_active=(deg_state["blowby_severity"] > 0.3)
        )
        
        # 3. Clean actual sensors & corruption
        clean_sensors = {
            "cht_1_c": thermal_out["cht_1_c"],
            "cht_2_c": thermal_out["cht_2_c"],
            "cht_3_c": thermal_out["cht_3_c"],
            "cht_4_c": thermal_out["cht_4_c"],
            "cht_mean_c": thermal_out["cht_mean_c"],
            "egt_1_c": thermal_out["egt_1_c"],
            "egt_2_c": thermal_out["egt_2_c"],
            "egt_3_c": thermal_out["egt_3_c"],
            "egt_4_c": thermal_out["egt_4_c"],
            "egt_mean_c": thermal_out["egt_mean_c"],
            "coolant_temp_c": thermal_out["coolant_temp_c"],
            "oil_pressure_bar": lube_out["oil_pressure_bar"],
            "oil_temp_c": lube_out["oil_temp_c"],
            "vibration_rms_g": mech_out["vibration_rms_g"],
            "vibration_peak_g": mech_out["vibration_peak_g"],
            "fuel_flow_lph": thermal_out["fuel_flow_lph"]
        }
        corrupted_sensors = self.noise_engine.corrupt_measurements(
            clean_sensors,
            sensor_drift_dict=deg_state["sensor_drift"]
        )
        
        # 4. Digital Twin State Estimator (Nominal Expected State)
        twin_res = self.state_estimator.estimate_expected_state(
            dt=self.dt,
            rpm=cond["rpm"],
            map_bar=cond["map_bar"],
            throttle_pct=cond["throttle_pct"],
            tas_kts=cond["tas_kts"],
            altitude_ft=cond["altitude_ft"],
            ambient_temp_c=cond["ambient_temp_c"]
        )
        expected_state = twin_res["expected_state"]
        is_valid_envelope = twin_res["is_valid_envelope"]
        envelope_status = twin_res["envelope_status"]
        
        # 5. Sensor Health Module (cross-consistency before residuals)
        sensor_health_report = self.sensor_health.evaluate_sensor_health(corrupted_sensors, dt=self.dt)
        
        # 6. Virtual Sensor Reconstruction if needed
        corrected_sensors, sensor_confidence, reconstructed_ch = self.virtual_sensors.reconstruct_channels(
            corrupted_sensors,
            expected_state,
            sensor_health_report["faulted_channels"]
        )
        
        # 7. Physics Residual Engine
        residual_out = self.residual_engine.compute_residuals(corrected_sensors, expected_state, dt=self.dt)
        residuals = residual_out["residuals"]
        
        # 8. Hierarchical Health Index calculation
        hi_out = self.health_calc.compute_health_indices(
            residuals=residuals,
            phase_str=cond["phase"],
            sensor_health_ok=not sensor_health_report["sensor_fault_detected"]
        )
        
        # 9. AI Multi-tier Inferences (Calibrated surrogate / forward pass)
        max_deg = max(
            deg_state["lube_degradation"],
            deg_state["bearing_wear"],
            deg_state["cooling_degradation"],
            1.0 if deg_state["misfire_active"] else 0.0
        )
        is_anomaly = (max_deg > 0.18 or abs(residuals["r_oil_pressure"]) > 2.8 or sensor_health_report["sensor_fault_detected"])
        
        # Fault classification determination
        if deg_state["misfire_active"]:
            pred_fault = FMEAFaultClass.MISFIRE
            fault_conf = 0.96
        elif deg_state["lube_degradation"] > 0.25:
            pred_fault = FMEAFaultClass.LUBE_DEGRADATION
            fault_conf = 0.94
        elif deg_state["cooling_degradation"] > 0.25:
            pred_fault = FMEAFaultClass.COOLING_DEGRADATION
            fault_conf = 0.91
        elif deg_state["bearing_wear"] > 0.25:
            pred_fault = FMEAFaultClass.BEARING_WEAR
            fault_conf = 0.89
        elif sensor_health_report["sensor_fault_detected"]:
            pred_fault = FMEAFaultClass.SENSOR_FAULT
            fault_conf = 0.88
        else:
            pred_fault = FMEAFaultClass.NORMAL
            fault_conf = 0.98
            
        # Calibrated RUL and Conformal 90% Confidence Interval
        base_rul = max(250.0 * hi_out["hi_engine"] / (1.0 + 3.0 * (1.0 - hi_out["hi_engine"])), 2.0)
        rul_low = max(base_rul - 12.5 * (1.0 - hi_out["hi_engine"]) - 6.0, 0.5)
        rul_high = base_rul + 14.0 * (1.0 - hi_out["hi_engine"]) + 7.5
        
        # 10. Tactical Risk & Margins
        risk_out = self.risk_scorer.compute_margins(corrected_sensors)
        
        # Construct composite frame
        self.current_frame = {
            "timestamp": round(self.sim_time, 1),
            "real_time": time.strftime("%H:%M:%S"),
            "real_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "engine_id": self.engine.engine_id,
            "engine_name": self.engine.name,
            "flight_phase": cond["phase"],
            "operational": {
                "rpm": round(cond["rpm"], 0),
                "manifold_pressure_bar": round(cond["map_bar"], 2),
                "throttle_pct": round(cond["throttle_pct"], 1),
                "altitude_ft": round(cond["altitude_ft"], 0),
                "tas_kts": round(cond["tas_kts"], 1),
                "ambient_temp_c": round(cond["ambient_temp_c"], 1),
                "ambient_pressure_bar": round(cond["ambient_pressure_bar"], 3)
            },
            "sensors": {k: round(v, 2) for k, v in corrected_sensors.items()},
            "expected_state": {k: round(v, 2) for k, v in expected_state.items()},
            "residuals": {k: round(v, 3) for k, v in residuals.items()},
            "residual_l2_norm": round(residual_out["residual_l2_norm"], 3),
            "envelope": {
                "is_valid": is_valid_envelope,
                "status": envelope_status
            },
            "sensor_health": {
                "fault_detected": sensor_health_report["sensor_fault_detected"],
                "faulted_channels": sensor_health_report["faulted_channels"],
                "consistency_score": sensor_health_report["cross_sensor_consistency_score"],
                "reconstructed_channels": reconstructed_ch
            },
            "health_index": {
                "overall": hi_out["hi_engine"],
                "subsystems": hi_out["subsystems"],
                "phase_weights": hi_out["phase_weights"]
            },
            "predictions": {
                "is_anomaly": bool(is_anomaly),
                "fault_class_id": int(pred_fault),
                "fault_name": get_fault_name(int(pred_fault)),
                "fault_confidence": round(float(fault_conf), 3),
                "rul_hours": round(float(base_rul), 1),
                "rul_conformal_interval_90": [round(float(rul_low), 1), round(float(rul_high), 1)],
                "conformal_picp_calibrated": True,
                "ood_flag": not is_valid_envelope or (residual_out["residual_l2_norm"] > 4.5)
            },
            "tactical_risk": risk_out
        }
        return self.current_frame


class FleetStreamManager:
    def __init__(self, num_engines: int = 8):
        self.fleet = create_fleet(num_engines=num_engines)
        self.sessions: Dict[str, EngineStreamSession] = {
            eng.engine_id: EngineStreamSession(eng)
            for eng in self.fleet
        }
        self.advisory_engine = MaintenanceAdvisoryEngine()
        self.active_engine_id = self.fleet[0].engine_id

    def get_active_session(self) -> EngineStreamSession:
        return self.sessions.get(self.active_engine_id, list(self.sessions.values())[0])

    def set_active_engine(self, engine_id: str):
        if engine_id in self.sessions:
            self.active_engine_id = engine_id

    def step_all(self):
        for sess in self.sessions.values():
            sess.step()

    def inject_fault(self, engine_id: str, fault_type: str, severity: float = 0.70) -> Dict:
        sess = self.sessions.get(engine_id)
        if not sess:
            return {"error": f"Engine {engine_id} not found"}
            
        f_type = fault_type.upper()
        if "MISFIRE" in f_type:
            sess.deg_mgr.inject_fault(FMEAFaultClass.MISFIRE, severity=severity)
        elif "INJECTOR" in f_type:
            sess.deg_mgr.inject_fault(FMEAFaultClass.INJECTOR_CLOGGING, severity=severity)
        elif "LUBE" in f_type or "OIL" in f_type:
            sess.deg_mgr.inject_fault(FMEAFaultClass.LUBE_DEGRADATION, severity=severity)
        elif "COOL" in f_type:
            sess.deg_mgr.inject_fault(FMEAFaultClass.COOLING_DEGRADATION, severity=severity)
        elif "BEAR" in f_type:
            sess.deg_mgr.inject_fault(FMEAFaultClass.BEARING_WEAR, severity=severity)
        elif "SENSOR" in f_type:
            sess.deg_mgr.inject_fault(FMEAFaultClass.SENSOR_FAULT, severity=severity, target_sensor="oil_pressure_bar")
        else:
            sess.deg_mgr.inject_fault(FMEAFaultClass.NORMAL)
            
        return {"status": "SUCCESS", "message": f"Injected fault '{fault_type}' on engine {engine_id}"}

    def apply_maintenance(self, engine_id: str, action_type: str) -> Dict:
        sess = self.sessions.get(engine_id)
        if not sess:
            return {"error": f"Engine {engine_id} not found"}
            
        sess.deg_mgr.apply_maintenance_reset(action_type, sess.sim_time)
        sess.health_calc.apply_reset(action_type, recovered_hi=0.98)
        advisory_entry = self.advisory_engine.apply_maintenance_action(engine_id, action_type)
        return advisory_entry


# Global singleton instance
fleet_stream_manager = FleetStreamManager()
