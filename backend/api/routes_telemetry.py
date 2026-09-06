"""
TITAN API — Telemetry & Live Twin State Endpoints
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Dict, List, Optional

from backend.ingestion.stream_handler import fleet_stream_manager

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])


class FaultInjectionRequest(BaseModel):
    engine_id: str
    fault_type: str
    severity: float = 0.70


class SelectEngineRequest(BaseModel):
    engine_id: str


@router.get("/live")
def get_live_telemetry(engine_id: Optional[str] = None):
    """
    Returns the latest live telemetry frame, digital twin state,
    normalized residuals, and AI predictions.
    """
    if engine_id:
        fleet_stream_manager.set_active_engine(engine_id)
        
    sess = fleet_stream_manager.get_active_session()
    frame = sess.step()
    return frame


@router.get("/fleet")
def get_fleet_status():
    """
    Returns the status summary of all engines in the MALE UAV fleet.
    """
    fleet_data = []
    for eng in fleet_stream_manager.fleet:
        sess = fleet_stream_manager.sessions[eng.engine_id]
        if sess.current_frame is None:
            sess.step()
        frame = sess.current_frame
        fleet_data.append({
            "engine_id": eng.engine_id,
            "name": eng.name,
            "flight_phase": frame["flight_phase"],
            "rpm": frame["operational"]["rpm"],
            "health_index": frame["health_index"]["overall"],
            "tactical_status": frame["tactical_risk"]["tactical_status"],
            "anomaly_detected": frame["predictions"]["is_anomaly"],
            "fault_name": frame["predictions"]["fault_name"],
            "is_active": (eng.engine_id == fleet_stream_manager.active_engine_id)
        })
    return {"fleet": fleet_data, "active_engine_id": fleet_stream_manager.active_engine_id}


@router.post("/select_engine")
def select_active_engine(req: SelectEngineRequest):
    fleet_stream_manager.set_active_engine(req.engine_id)
    return {"status": "SUCCESS", "active_engine_id": req.engine_id}


@router.post("/inject_fault")
def inject_fault(req: FaultInjectionRequest):
    res = fleet_stream_manager.inject_fault(
        engine_id=req.engine_id,
        fault_type=req.fault_type,
        severity=req.severity
    )
    return res
