"""
TITAN Fleet Ground Station API Routes
Exposes REST endpoints for swarm aggregation, cross-engine correlation,
maintenance scheduling, and compressed agent uplinks.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from backend.ingestion.stream_handler import fleet_stream_manager
from fleet.agent_uplink import AgentUplinkManager, CompressedHealthSummary
from fleet.fleet_aggregation import FleetAggregationEngine
from fleet.cross_engine_correlation import CrossEngineCorrelationEngine
from fleet.maintenance_scheduler import FleetMaintenanceScheduler
from fleet.federated_coordinator import FederatedCoordinatorStub

fleet_router = APIRouter(prefix="/api/fleet", tags=["Fleet Ground Station"])

# Global engine singletons for Fleet Ground Station layer
aggregation_engine = FleetAggregationEngine()
correlation_engine = CrossEngineCorrelationEngine()
scheduler_engine = FleetMaintenanceScheduler(max_depot_bays=2)
federated_stub = FederatedCoordinatorStub()


def _collect_current_uplinks() -> List[CompressedHealthSummary]:
    """
    Steps or retrieves the current frame from every engine in the fleet,
    and runs the local AgentUplinkManager to simulate transmission of compressed health summaries.
    """
    uplinks: List[CompressedHealthSummary] = []
    for eng_id, session in fleet_stream_manager.sessions.items():
        if session.current_frame is None:
            session.step()
        frame = session.current_frame
        uplink_mgr = AgentUplinkManager(engine_id=eng_id)
        uplink = uplink_mgr.create_uplink_payload(frame)
        uplinks.append(uplink)
    return uplinks


@fleet_router.get("/status")
def get_fleet_status():
    """
    Returns high-level swarm health map, readiness percentages, and asset status.
    """
    uplinks = _collect_current_uplinks()
    aggregation = aggregation_engine.aggregate_fleet(uplinks)
    return {
        "status": "SUCCESS",
        "timestamp": uplinks[0].timestamp if uplinks else 0.0,
        "fleet": aggregation
    }


@fleet_router.get("/uplinks")
def get_fleet_uplinks():
    """
    Returns latest compressed health summary packets received from each UAV agent.
    Raw telemetry is isolated on-edge.
    """
    uplinks = _collect_current_uplinks()
    return {
        "status": "SUCCESS",
        "count": len(uplinks),
        "data_locality": "EDGE_PRESERVED_NO_RAW_STREAM",
        "uplinks": [u.to_dict() for u in uplinks]
    }


@fleet_router.get("/correlations")
def get_fleet_correlations():
    """
    Runs multi-engine correlation analysis to identify systemic multi-aircraft failures.
    """
    uplinks = _collect_current_uplinks()
    results = correlation_engine.analyze_correlations(uplinks)
    return {
        "status": "SUCCESS",
        "correlation_analysis": results
    }


@fleet_router.get("/maintenance_queue")
def get_fleet_maintenance_queue():
    """
    Returns optimized fleet-wide maintenance priority queue and sortie assignments.
    """
    uplinks = _collect_current_uplinks()
    schedule = scheduler_engine.generate_schedule(uplinks)
    return {
        "status": "SUCCESS",
        "schedule": schedule
    }


@fleet_router.get("/federated_status")
def get_federated_status():
    """
    Returns the edge-privacy federated learning protocol status (Future Scope).
    """
    return federated_stub.get_federated_status()


class SystemicEventRequest(BaseModel):
    event_type: str = "CONTAMINATED_FUEL_BATCH"
    affected_engines: Optional[List[str]] = None


@fleet_router.post("/simulate_systemic_event")
def simulate_systemic_event(req: SystemicEventRequest):
    """
    Injects a multi-engine systemic anomaly (e.g. Contaminated Fuel or Bearing Defect)
    across multiple UAV agents to demonstrate real-time cross-engine correlation.
    """
    affected = req.affected_engines or ["ENG-MALE-01", "ENG-MALE-03", "ENG-MALE-06"]
    
    # Inject actual physical faults on affected engines
    for eng_id in affected:
        if req.event_type == "CONTAMINATED_FUEL_BATCH":
            fleet_stream_manager.inject_fault(eng_id, "INJECTOR_CLOGGING", severity=0.75)
        elif req.event_type == "MANUFACTURING_LOT_DEFECT":
            fleet_stream_manager.inject_fault(eng_id, "BEARING_WEAR", severity=0.70)
        elif req.event_type == "ENVIRONMENTAL_DUST_INGESTION":
            fleet_stream_manager.inject_fault(eng_id, "COOLING_DEGRADATION", severity=0.65)

    correlation_engine.trigger_simulated_systemic_event(req.event_type, affected)
    return {
        "status": "SUCCESS",
        "message": f"Simulated systemic event '{req.event_type}' injected across {len(affected)} engines.",
        "affected_engines": affected
    }


@fleet_router.post("/clear_systemic_event")
def clear_systemic_event():
    """
    Clears active simulated systemic event and restores nominal conditions.
    """
    correlation_engine.clear_simulated_event()
    return {
        "status": "SUCCESS",
        "message": "Systemic correlation event cleared."
    }
