"""
TITAN API — Maintenance Advisory & Health Reset Endpoints
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List, Optional

from backend.ingestion.stream_handler import fleet_stream_manager

router = APIRouter(prefix="/api/advisory", tags=["advisory"])


class MaintenanceActionRequest(BaseModel):
    engine_id: str
    action_type: str # e.g. "Oil Service", "Spark Plug Replacement", "Radiator Flush", "Top-End Overhaul"
    technician: Optional[str] = "Flight Line Technician (DRDO UAV Base)"


@router.get("/active")
def get_active_advisories():
    """
    Returns active prescriptive maintenance advisories for current engine state.
    """
    sess = fleet_stream_manager.get_active_session()
    if sess.current_frame is None:
        sess.step()
    frame = sess.current_frame
    
    advisory = fleet_stream_manager.advisory_engine.generate_advisory(
        engine_id=sess.engine.engine_id,
        fault_class=frame["predictions"]["fault_class_id"],
        confidence=frame["predictions"]["fault_confidence"],
        rul_hours=frame["predictions"]["rul_hours"],
        residuals=frame["residuals"],
        subsystems_hi=frame["health_index"]["subsystems"],
        is_valid_envelope=frame["envelope"]["is_valid"]
    )
    
    # Also attach explainability narrative
    from models.titan_full.explainability import PhysicalExplainabilityEngine
    exp_engine = PhysicalExplainabilityEngine()
    attr = exp_engine.compute_residual_attribution(frame["residuals"], frame["predictions"]["fault_class_id"])
    narrative = exp_engine.generate_narrative(
        predicted_fault_class=frame["predictions"]["fault_class_id"],
        fault_confidence=frame["predictions"]["fault_confidence"],
        attributions=attr,
        envelope_valid=frame["envelope"]["is_valid"],
        flight_phase=frame["flight_phase"]
    )
    
    return {
        "engine_id": sess.engine.engine_id,
        "advisory": advisory,
        "residual_attributions": attr,
        "physical_evidence_narrative": narrative
    }


@router.get("/history")
def get_maintenance_history():
    """
    Returns past completed maintenance interventions and reset logs.
    """
    return {"history": fleet_stream_manager.advisory_engine.get_maintenance_history()}


@router.post("/apply_reset")
def apply_maintenance_action(req: MaintenanceActionRequest):
    """
    Executes a maintenance reset, restoring relevant health index back to nominal.
    """
    entry = fleet_stream_manager.apply_maintenance(
        engine_id=req.engine_id,
        action_type=req.action_type
    )
    return {"status": "SUCCESS", "message": f"Applied {req.action_type} on {req.engine_id}", "entry": entry}
