"""
TITAN API — Mission Intelligence & Replay Endpoints
"""

import os
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Dict, List, Optional
import pandas as pd

from mission_intel.simulator import WhatIfMissionSimulator
from mission_intel.replay import MissionReplayEngine
from backend.ingestion.stream_handler import fleet_stream_manager

router = APIRouter(prefix="/api/mission", tags=["mission"])
simulator = WhatIfMissionSimulator()
replay_engine = MissionReplayEngine(data_dir="data/synthetic")


class WhatIfRequest(BaseModel):
    engine_id: Optional[str] = "ENG-MALE-01"
    snapshot_id: Optional[str] = None
    mission_profile: str = "endurance"
    duration_hours: float = 12.0
    ambient_temp_offset_c: float = 0.0
    altitude_ceiling_ft: float = 18000.0
    inject_fault: Optional[str] = None
    fault_severity: float = 0.0


# Twin state snapshot cache for reproducible Monte Carlo projections (PRD Section I.5)
twin_snapshots: Dict[str, Dict] = {}


@router.post("/what_if")
def run_what_if_simulation(req: WhatIfRequest):
    """
    Executes a pre-mission what-if simulation forward in time using the engine's
    actual Digital Twin state (health, residuals, degradation trajectory).
    Uses deterministic seeding per PRD Section I.5.
    If snapshot_id is specified and cached, uses the exact frozen twin state for bit-exact reproducibility.
    """
    engine_id = req.engine_id or fleet_stream_manager.active_engine_id or "ENG-MALE-01"
    sess = fleet_stream_manager.sessions.get(engine_id)

    # Check if this snapshot is already captured and frozen
    if req.snapshot_id and req.snapshot_id in twin_snapshots:
        snap = twin_snapshots[req.snapshot_id]
        cur_hi = snap["cur_hi"]
        sub_hi = snap["sub_hi"]
        cur_residuals = snap["cur_residuals"]
        cur_deg_state = snap["cur_deg_state"]
        wear_mult = snap["wear_mult"]
        snapshot_timestamp = snap["snapshot_timestamp"]
        snapshot_id = req.snapshot_id
    else:
        # Capture a fresh snapshot from the active engine session
        cur_hi = sess.health_calc.hi_engine if sess else 0.95
        sub_hi = dict(sess.health_calc.hi_subsystems) if sess and sess.health_calc.hi_subsystems else None
        cur_frame = sess.current_frame if sess else None
        cur_residuals = dict(cur_frame["residuals"]) if cur_frame and "residuals" in cur_frame else None
        cur_deg_state = dict(sess.deg_mgr.get_degradation_state()) if sess else None
        wear_mult = sess.engine.wear_rate_multiplier if sess else 1.0

        # Calculate twin state snapshot timestamp for operator traceability
        sim_time_sec = cur_frame.get("timestamp", 0.0) if cur_frame else (sess.sim_time if sess else 0.0)
        hours = int(sim_time_sec // 3600)
        minutes = int((sim_time_sec % 3600) // 60)
        seconds = int(sim_time_sec % 60)
        snapshot_timestamp = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # Deterministic snapshot ID based on engine and exact current degradation state
        snapshot_id = req.snapshot_id or f"{engine_id}-T{int(sim_time_sec)}-HI{round(cur_hi, 3)}"

        # Freeze snapshot in cache
        twin_snapshots[snapshot_id] = {
            "cur_hi": cur_hi,
            "sub_hi": sub_hi,
            "cur_residuals": cur_residuals,
            "cur_deg_state": cur_deg_state,
            "wear_mult": wear_mult,
            "snapshot_timestamp": snapshot_timestamp,
            "sim_time_sec": sim_time_sec
        }
        if len(twin_snapshots) > 100:
            oldest_key = next(iter(twin_snapshots))
            twin_snapshots.pop(oldest_key, None)

    result = simulator.run_simulation(
        current_hi=cur_hi,
        current_subsystems=sub_hi,
        current_residuals=cur_residuals,
        current_deg_state=cur_deg_state,
        wear_multiplier=wear_mult,
        engine_id=engine_id,
        twin_snapshot_id=snapshot_id,
        twin_snapshot_timestamp=snapshot_timestamp,
        mission_profile_name=req.mission_profile,
        planned_duration_hours=req.duration_hours,
        ambient_temp_offset_c=req.ambient_temp_offset_c,
        altitude_ceiling_ft=req.altitude_ceiling_ft,
        inject_fault=req.inject_fault,
        fault_severity=req.fault_severity
    )
    return {
        **result,
        "projected_health_index": result.get("projected_final_hi", cur_hi),
        "projected_rul_hours": result.get("projected_post_mission_rul_hours", 150.0),
        "tactical_clearance": {
            "recommendation": result.get("status", "GO"),
            "rationale": result.get("recommendation", "Engine cleared for scheduled profile."),
            "firing_rule": result.get("firing_rule", "NOMINAL_CLEARANCE")
        }
    }


@router.get("/replay/catalog")
def get_replay_catalog():
    """
    Returns list of recorded flight missions available for scrubbing replay.
    """
    catalog = [
        {
            "mission_id": "ENG-MALE-02",
            "name": "Maritime Patrol Sortie #102 (Incipient Lubrication Leak)",
            "airframe": "TAPAS-BH-201 Unit #02",
            "profile": "Hot Weather Desert",
            "duration_hours": 5.0,
            "fault_type": "LUBE_DEGRADATION",
            "severity": "CRITICAL",
            "early_detection_gain": "42 mins gained"
        },
        {
            "mission_id": "ENG-MALE-04",
            "name": "Cylinder #2 Ignition Misfire Event",
            "airframe": "Rustom-II Unit #04",
            "profile": "Endurance ISR",
            "duration_hours": 4.0,
            "fault_type": "MISFIRE",
            "severity": "HIGH",
            "early_detection_gain": "18 mins gained"
        },
        {
            "mission_id": "ENG-MALE-05",
            "name": "High-Ceiling FL240 Thermal Stress Run",
            "airframe": "Airframe #05",
            "profile": "High Altitude",
            "duration_hours": 6.0,
            "fault_type": "COOLING_DEGRADATION",
            "severity": "HIGH",
            "early_detection_gain": "35 mins gained"
        },
        {
            "mission_id": "ENG-MALE-01",
            "name": "Nominal 18-Hour Endurance Baseline",
            "airframe": "TAPAS-BH-201 Unit #01",
            "profile": "Endurance ISR",
            "duration_hours": 6.0,
            "fault_type": "NORMAL",
            "severity": "NOMINAL",
            "early_detection_gain": "Zero false alarms"
        }
    ]
    return {"catalog": catalog}


@router.get("/replay/timeline")
def get_replay_timeline(mission_id: str = "ENG-MALE-02"):
    """
    Returns full timeline series and early detection delta for a replay mission.
    """
    df = replay_engine.load_mission(mission_id)
    if df is None or df.empty:
        # Generate on the fly if needed
        from sim.generate_dataset import simulate_mission
        from sim.fault_injection.fmea_taxonomy import FMEAFaultClass
        eng = fleet_stream_manager.sessions.get(mission_id, fleet_stream_manager.get_active_session()).engine
        df = simulate_mission(
            engine=eng,
            mission_name="hot_weather",
            duration_hours=4.0,
            fault_class=FMEAFaultClass.LUBE_DEGRADATION,
            fault_start_fraction=0.35,
            fault_severity=0.65
        )
        replay_engine.cached_missions[mission_id] = df
        
    delta_report = replay_engine.compute_detection_delta(df)
    
    # Downsample points for fast UI rendering (e.g. 100 points)
    n = len(df)
    step = max(n // 100, 1)
    sub_df = df.iloc[::step]
    
    series_points = []
    for _, row in sub_df.iterrows():
        series_points.append({
            "timestamp": round(row["timestamp"], 1),
            "time_min": round(row["timestamp"] / 60.0, 1),
            "flight_phase": row["flight_phase"],
            "rpm": round(row["rpm"], 0),
            "cht_mean_c": round((row["cht_1_c"] + row["cht_2_c"] + row["cht_3_c"] + row["cht_4_c"]) / 4.0, 1),
            "oil_pressure_bar": round(row["oil_pressure_bar"], 2),
            "oil_temp_c": round(row["oil_temp_c"], 1),
            "vibration_rms_g": round(row["vibration_rms_g"], 2),
            "health_index": round(row["gt_health_index"], 3),
            "rul_hours": round(row["gt_rul_hours"], 1),
            "is_anomaly": bool(row["gt_is_anomaly"])
        })
        
    return {
        "mission_id": mission_id,
        "early_detection_delta": delta_report,
        "timeline_series": series_points
    }
