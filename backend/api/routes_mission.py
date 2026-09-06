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
    mission_profile: str = "endurance"
    duration_hours: float = 12.0
    ambient_temp_offset_c: float = 0.0
    altitude_ceiling_ft: float = 18000.0
    inject_fault: Optional[str] = None
    fault_severity: float = 0.0


@router.post("/what_if")
def run_what_if_simulation(req: WhatIfRequest):
    """
    Executes a pre-mission what-if simulation forward in time.
    """
    sess = fleet_stream_manager.sessions.get(req.engine_id or fleet_stream_manager.active_engine_id)
    cur_hi = sess.health_calc.hi_engine if sess else 0.95
    sub_hi = sess.health_calc.hi_subsystems if sess else None
    
    result = simulator.run_simulation(
        current_hi=cur_hi,
        current_subsystems=sub_hi,
        mission_profile_name=req.mission_profile,
        planned_duration_hours=req.duration_hours,
        ambient_temp_offset_c=req.ambient_temp_offset_c,
        altitude_ceiling_ft=req.altitude_ceiling_ft,
        inject_fault=req.inject_fault,
        fault_severity=req.fault_severity
    )
    return result


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
