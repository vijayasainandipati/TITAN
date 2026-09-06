"""
TITAN Synthetic Data Generator
Orchestrates multi-engine physics models, mission profiles, FMEA fault injection,
and sensor noise to produce high-fidelity synthetic telemetry datasets for training,
ablation benchmarks (A->E), and leave-engine-out cross-validation.
"""

import os
import json
import argparse
import numpy as np
import pandas as pd
from typing import Dict, List, Optional

from .engine_instance import EngineInstance, create_fleet
from .mission_profiles import get_mission_profile
from .fault_injection.fmea_taxonomy import FMEAFaultClass
from .fault_injection.degradation_curves import DegradationManager
from .sensor_noise import SensorNoiseEngine


def simulate_mission(engine: EngineInstance,
                     mission_name: str = "endurance",
                     duration_hours: float = 6.0,
                     dt_seconds: float = 1.0,
                     fault_class: FMEAFaultClass = FMEAFaultClass.NORMAL,
                     fault_start_fraction: float = 0.40,
                     fault_severity: float = 0.65,
                     maintenance_event: Optional[Dict] = None,
                     seed: int = 100) -> pd.DataFrame:
    """
    Simulates a full flight mission for a specific engine instance.
    Produces both clean physics states and noisy corrupted telemetry,
    with ground truth fault labels and remaining useful life (RUL).
    """
    rng = np.random.RandomState(seed)
    profile = get_mission_profile(mission_name, duration_hours=duration_hours)
    noise_engine = SensorNoiseEngine(
        sensor_bias=engine.sensor_bias,
        sensor_noise_sigma=engine.sensor_noise_sigma
    )
    deg_mgr = DegradationManager(wear_multiplier=engine.wear_rate_multiplier)
    
    # Reset engine models to starting ambient temp
    cond0 = profile.get_conditions(0.0)
    engine.reset_state(cond0["ambient_temp_c"])
    
    total_steps = int((duration_hours * 3600.0) / dt_seconds)
    # Downsample step recording if duration is very long (e.g. sample every 5s for fast training)
    sample_interval = max(int(dt_seconds * 5), 1)
    
    records = []
    fault_injected = False
    
    for step in range(total_steps):
        t = step * dt_seconds
        frac = t / (duration_hours * 3600.0)
        cond = profile.get_conditions(t)
        
        # Check for fault injection trigger
        if not fault_injected and frac >= fault_start_fraction and fault_class != FMEAFaultClass.NORMAL:
            deg_mgr.inject_fault(fault_class, severity=fault_severity, target_cylinder=2)
            fault_injected = True
            
        # Check for maintenance event
        if maintenance_event and t >= maintenance_event.get("time_sec", 1e9):
            deg_mgr.apply_maintenance_reset(maintenance_event["type"], t)
            maintenance_event = None # Apply once
            
        # Advance degradation
        deg_mgr.step(dt_seconds, cond["rpm"], cond["map_bar"], engine.lubrication.t_oil)
        deg_state = deg_mgr.get_degradation_state()
        
        # Step thermal physics
        cooling_factor = 1.0 - 0.55 * deg_state["cooling_degradation"]
        misfire_cyl = deg_state["misfire_cylinder"] if deg_state["misfire_active"] else None
        
        thermal_out = engine.thermal.step(
            dt=dt_seconds,
            rpm=cond["rpm"],
            map_bar=cond["map_bar"],
            throttle_pct=cond["throttle_pct"],
            tas_kts=cond["tas_kts"],
            altitude_ft=cond["altitude_ft"],
            ambient_temp_c=cond["ambient_temp_c"],
            cooling_degradation_factor=cooling_factor,
            misfire_cylinder=misfire_cyl
        )
        
        # Step lubrication physics
        bearing_mult = 1.0 + 1.2 * deg_state["bearing_wear"]
        lube_out = engine.lubrication.step(
            dt=dt_seconds,
            rpm=cond["rpm"],
            cht_mean_c=thermal_out["cht_mean_c"],
            tas_kts=cond["tas_kts"],
            altitude_ft=cond["altitude_ft"],
            ambient_temp_c=cond["ambient_temp_c"],
            bearing_wear_multiplier=bearing_mult,
            oil_leak_severity=deg_state["lube_degradation"]
        )
        
        # Step mechanical physics
        mech_out = engine.mechanical.step(
            dt=dt_seconds,
            rpm=cond["rpm"],
            throttle_pct=cond["throttle_pct"],
            map_bar=cond["map_bar"],
            bearing_wear_severity=deg_state["bearing_wear"],
            misfire_active=deg_state["misfire_active"],
            blowby_active=(deg_state["blowby_severity"] > 0.3)
        )
        
        # Only record at sample interval
        if step % sample_interval == 0:
            clean_sensors = {
                "cht_1_c": thermal_out["cht_1_c"],
                "cht_2_c": thermal_out["cht_2_c"],
                "cht_3_c": thermal_out["cht_3_c"],
                "cht_4_c": thermal_out["cht_4_c"],
                "egt_1_c": thermal_out["egt_1_c"],
                "egt_2_c": thermal_out["egt_2_c"],
                "egt_3_c": thermal_out["egt_3_c"],
                "egt_4_c": thermal_out["egt_4_c"],
                "coolant_temp_c": thermal_out["coolant_temp_c"],
                "oil_pressure_bar": lube_out["oil_pressure_bar"],
                "oil_temp_c": lube_out["oil_temp_c"],
                "vibration_rms_g": mech_out["vibration_rms_g"],
                "vibration_peak_g": mech_out["vibration_peak_g"],
                "fuel_flow_lph": thermal_out["fuel_flow_lph"]
            }
            
            # Corrupt with realistic noise, biases, dropouts
            corrupted = noise_engine.corrupt_measurements(
                clean_sensors,
                sensor_drift_dict=deg_state["sensor_drift"],
                rng=rng
            )
            
            # Ground truth health and RUL calculation
            max_deg = max(
                deg_state["lube_degradation"],
                deg_state["bearing_wear"],
                deg_state["cooling_degradation"],
                1.0 if deg_state["misfire_active"] else 0.0
            )
            gt_health_index = float(np.clip(1.0 - max_deg, 0.05, 1.0))
            is_anomaly = (max_deg > 0.20 or deg_state["sensor_drift"]["drift_value"] != 0.0)
            
            # Remaining Useful Life in flight hours (estimated time to failure threshold HI < 0.35)
            if max_deg <= 0.05:
                rul_hours = 250.0 + rng.uniform(-10.0, 10.0)
            else:
                # Degradation trajectory toward critical limit
                rul_hours = max(250.0 * (1.0 - max_deg) / (1.0 + 3.0 * max_deg), 0.5)
                
            rec = {
                "timestamp": round(t, 2),
                "engine_id": engine.engine_id,
                "flight_phase": cond["phase"],
                "rpm": cond["rpm"],
                "map_bar": cond["map_bar"],
                "throttle_pct": cond["throttle_pct"],
                "altitude_ft": cond["altitude_ft"],
                "tas_kts": cond["tas_kts"],
                "ambient_temp_c": cond["ambient_temp_c"],
                "ambient_pressure_bar": cond["ambient_pressure_bar"],
                # Sensor telemetry (corrupted)
                **corrupted,
                # Ground truth labels
                "gt_is_anomaly": int(is_anomaly),
                "gt_fault_class": int(fault_class if fault_injected else FMEAFaultClass.NORMAL),
                "gt_health_index": round(gt_health_index, 4),
                "gt_rul_hours": round(float(rul_hours), 2),
                "gt_lube_deg": round(deg_state["lube_degradation"], 4),
                "gt_bearing_wear": round(deg_state["bearing_wear"], 4),
                "gt_cooling_deg": round(deg_state["cooling_degradation"], 4)
            }
            records.append(rec)
            
    return pd.DataFrame(records)


def generate_multi_engine_dataset(output_dir: str = "data/synthetic",
                                  num_engines: int = 8,
                                  seed: int = 42) -> Dict[str, str]:
    """
    Generates training, validation, and leave-engine-out test datasets
    across multiple engines and fault categories.
    """
    os.makedirs(output_dir, exist_ok=True)
    fleet = create_fleet(num_engines=num_engines, seed=seed)
    
    # Save fleet metadata
    fleet_meta = [eng.to_dict() for eng in fleet]
    with open(os.path.join(output_dir, "fleet_metadata.json"), "w") as f:
        json.dump(fleet_meta, f, indent=2)
        
    print(f"[TITAN SIM] Generating multi-engine synthetic dataset across {len(fleet)} engines...")
    
    all_dfs = []
    
    fault_scenarios = [
        (FMEAFaultClass.NORMAL, "endurance", 6.0),
        (FMEAFaultClass.LUBE_DEGRADATION, "hot_weather", 5.0),
        (FMEAFaultClass.COOLING_DEGRADATION, "hot_weather", 5.0),
        (FMEAFaultClass.MISFIRE, "endurance", 4.0),
        (FMEAFaultClass.BEARING_WEAR, "rapid_response", 4.0),
        (FMEAFaultClass.COMBUSTION_BLOWBY, "high_altitude", 6.0),
        (FMEAFaultClass.SENSOR_FAULT, "endurance", 5.0),
        (FMEAFaultClass.NORMAL, "high_altitude", 6.0)
    ]
    
    for i, eng in enumerate(fleet):
        fault_cls, mission_type, dur_hrs = fault_scenarios[i % len(fault_scenarios)]
        print(f"  -> Simulating {eng.engine_id} ({eng.name}) on {mission_type} profile (Fault: {fault_cls.name})...")
        
        df_mission = simulate_mission(
            engine=eng,
            mission_name=mission_type,
            duration_hours=dur_hrs,
            dt_seconds=1.0,
            fault_class=fault_cls,
            fault_start_fraction=0.35,
            fault_severity=0.70,
            seed=seed + i * 17
        )
        
        # Save individual engine flight
        eng_file = os.path.join(output_dir, f"{eng.engine_id}_flight.csv")
        df_mission.to_csv(eng_file, index=False)
        all_dfs.append(df_mission)
        
    combined_df = pd.concat(all_dfs, ignore_index=True)
    master_file = os.path.join(output_dir, "titan_multi_engine_master.csv")
    combined_df.to_csv(master_file, index=False)
    
    print(f"[TITAN SIM] Dataset successfully generated: {len(combined_df)} telemetry rows across {len(fleet)} engines.")
    return {
        "master_file": master_file,
        "total_rows": len(combined_df),
        "num_engines": len(fleet)
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TITAN Multi-Engine Telemetry Generator")
    parser.add_argument("--out_dir", type=str, default="data/synthetic")
    parser.add_argument("--engines", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    
    generate_multi_engine_dataset(args.out_dir, args.engines, args.seed)
