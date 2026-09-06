"""
Unit & Integration Tests for TITAN Fleet Ground Station Subsystem
Tests agent uplink compression, fleet aggregation, cross-engine correlation,
maintenance scheduling, federated coordinator stub, and REST API endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from fleet.agent_uplink import AgentUplinkManager, CompressedHealthSummary
from fleet.fleet_aggregation import FleetAggregationEngine
from fleet.cross_engine_correlation import CrossEngineCorrelationEngine
from fleet.maintenance_scheduler import FleetMaintenanceScheduler
from fleet.federated_coordinator import FederatedCoordinatorStub


def get_sample_frame():
    return {
        "timestamp": 120.0,
        "engine_id": "ENG-MALE-01",
        "engine_name": "UAV-ALPHA",
        "flight_phase": "LOITER",
        "health_index": {
            "overall": 0.88,
            "subsystems": {
                "thermal": 0.92,
                "lubrication": 0.82,
                "mechanical": 0.94,
                "combustion": 0.85
            }
        },
        "predictions": {
            "is_anomaly": True,
            "fault_name": "LUBE_DEGRADATION",
            "fault_confidence": 0.91,
            "rul_hours": 142.5,
            "rul_conformal_interval_90": [130.0, 155.0],
            "ood_flag": False
        },
        "tactical_risk": {
            "tactical_status": "CAUTION"
        },
        "sensor_health": {
            "fault_detected": False
        },
        # Raw sensors that should be isolated on-edge:
        "sensors": {
            "cht_1_c": 135.2,
            "egt_1_c": 745.0,
            "oil_pressure_bar": 3.4
        }
    }


@pytest.fixture
def sample_frame():
    return get_sample_frame()


def test_agent_uplink_compression(sample_frame):
    uplink_mgr = AgentUplinkManager(engine_id="ENG-MALE-01")
    summary = uplink_mgr.create_uplink_payload(sample_frame)

    assert isinstance(summary, CompressedHealthSummary)
    assert summary.engine_id == "ENG-MALE-01"
    assert summary.hi_engine == 0.88
    assert summary.tactical_status == "CAUTION"
    assert summary.predicted_fault == "LUBE_DEGRADATION"
    assert summary.raw_telemetry_isolated is True
    assert len(summary.signature) > 16  # Valid HMAC hash
    assert summary.payload_size_bytes < 1200
    assert summary.bandwidth_compression_ratio > 80.0  # Demonstrates >80% bandwidth reduction


def test_fleet_aggregation():
    aggregator = FleetAggregationEngine()
    uplinks = [
        CompressedHealthSummary(
            engine_id="ENG-MALE-01", engine_name="Alpha", timestamp=10.0, flight_phase="CRUISE",
            hi_engine=0.96, hi_subsystems={"thermal": 0.98, "lubrication": 0.95, "mechanical": 0.96, "combustion": 0.97},
            predicted_fault="NORMAL", fault_confidence=0.98, fault_probabilities={},
            rul_hours=210.0, rul_conformal_interval_90=[195.0, 225.0], tactical_status="GO",
            ood_flag=False, sensor_fault_detected=False, payload_size_bytes=420,
            bandwidth_compression_ratio=93.4, signature="mock-sig-1"
        ),
        CompressedHealthSummary(
            engine_id="ENG-MALE-02", engine_name="Bravo", timestamp=10.0, flight_phase="CLIMB",
            hi_engine=0.74, hi_subsystems={"thermal": 0.70, "lubrication": 0.75, "mechanical": 0.80, "combustion": 0.72},
            predicted_fault="COOLING_DEGRADATION", fault_confidence=0.89, fault_probabilities={},
            rul_hours=65.0, rul_conformal_interval_90=[50.0, 80.0], tactical_status="CAUTION",
            ood_flag=False, sensor_fault_detected=False, payload_size_bytes=420,
            bandwidth_compression_ratio=93.4, signature="mock-sig-2"
        ),
        CompressedHealthSummary(
            engine_id="ENG-MALE-03", engine_name="Charlie", timestamp=10.0, flight_phase="LOITER",
            hi_engine=0.48, hi_subsystems={"thermal": 0.50, "lubrication": 0.45, "mechanical": 0.52, "combustion": 0.46},
            predicted_fault="LUBE_DEGRADATION", fault_confidence=0.95, fault_probabilities={},
            rul_hours=18.0, rul_conformal_interval_90=[10.0, 26.0], tactical_status="NO-GO",
            ood_flag=True, sensor_fault_detected=False, payload_size_bytes=420,
            bandwidth_compression_ratio=93.4, signature="mock-sig-3"
        )
    ]

    res = aggregator.aggregate_fleet(uplinks)
    assert res["total_uavs"] == 3
    assert res["operational_count"] == 1
    assert res["degraded_count"] == 1
    assert res["critical_count"] == 1
    assert res["lowest_rul_engine"] == "ENG-MALE-03"
    assert res["min_rul_hours"] == 18.0
    assert len(res["vulnerable_subsystems"]) == 4
    # First sorted agent in list should be the highest urgency (NO-GO asset)
    assert res["agent_summaries"][0]["engine_id"] == "ENG-MALE-03"


def test_cross_engine_correlation_systemic():
    corr_engine = CrossEngineCorrelationEngine()
    
    # 1. Nominal case
    healthy_uplinks = [
        CompressedHealthSummary(
            engine_id=f"ENG-MALE-0{i}", engine_name=f"UAV-0{i}", timestamp=20.0, flight_phase="CRUISE",
            hi_engine=0.98, hi_subsystems={"thermal": 0.98, "lubrication": 0.98, "mechanical": 0.98, "combustion": 0.98},
            predicted_fault="NORMAL", fault_confidence=0.98, fault_probabilities={},
            rul_hours=240.0, rul_conformal_interval_90=[220.0, 260.0], tactical_status="GO",
            ood_flag=False, sensor_fault_detected=False, payload_size_bytes=420,
            bandwidth_compression_ratio=93.4, signature="sig"
        ) for i in range(1, 5)
    ]
    res_healthy = corr_engine.analyze_correlations(healthy_uplinks)
    assert res_healthy["has_systemic_anomaly"] is False

    # 2. Correlated systemic fault: Fuel Contamination (injector / combustion on multiple engines)
    fuel_incident_uplinks = list(healthy_uplinks)
    for idx in [0, 2]: # ENG-MALE-01 and ENG-MALE-03
        fuel_incident_uplinks[idx] = CompressedHealthSummary(
            engine_id=fuel_incident_uplinks[idx].engine_id, engine_name="UAV", timestamp=21.0, flight_phase="CRUISE",
            hi_engine=0.68, hi_subsystems={"thermal": 0.92, "lubrication": 0.95, "mechanical": 0.90, "combustion": 0.60},
            predicted_fault="INJECTOR_CLOGGING", fault_confidence=0.93, fault_probabilities={},
            rul_hours=45.0, rul_conformal_interval_90=[35.0, 55.0], tactical_status="CAUTION",
            ood_flag=False, sensor_fault_detected=False, payload_size_bytes=420,
            bandwidth_compression_ratio=93.4, signature="sig"
        )

    res_fuel = corr_engine.analyze_correlations(fuel_incident_uplinks)
    assert res_fuel["has_systemic_anomaly"] is True
    alert = res_fuel["systemic_alert"]
    assert alert["event_type"] == "CONTAMINATED_FUEL_BATCH"
    assert "ENG-MALE-01" in alert["affected_engines"]
    assert "ENG-MALE-03" in alert["affected_engines"]
    assert alert["correlation_score"] >= 0.85


def test_fleet_maintenance_scheduler():
    scheduler = FleetMaintenanceScheduler(max_depot_bays=2)
    uplinks = [
        CompressedHealthSummary(
            engine_id="ENG-MALE-01", engine_name="Alpha", timestamp=30.0, flight_phase="CRUISE",
            hi_engine=0.98, hi_subsystems={"thermal": 0.98, "lubrication": 0.98, "mechanical": 0.98, "combustion": 0.98},
            predicted_fault="NORMAL", fault_confidence=0.98, fault_probabilities={},
            rul_hours=220.0, rul_conformal_interval_90=[200.0, 240.0], tactical_status="GO",
            ood_flag=False, sensor_fault_detected=False, payload_size_bytes=420,
            bandwidth_compression_ratio=93.4, signature="sig"
        ),
        CompressedHealthSummary(
            engine_id="ENG-MALE-02", engine_name="Bravo", timestamp=30.0, flight_phase="LOITER",
            hi_engine=0.52, hi_subsystems={"thermal": 0.85, "lubrication": 0.45, "mechanical": 0.80, "combustion": 0.85},
            predicted_fault="LUBE_DEGRADATION", fault_confidence=0.94, fault_probabilities={},
            rul_hours=24.0, rul_conformal_interval_90=[15.0, 32.0], tactical_status="NO-GO",
            ood_flag=False, sensor_fault_detected=False, payload_size_bytes=420,
            bandwidth_compression_ratio=93.4, signature="sig"
        )
    ]

    schedule_res = scheduler.generate_schedule(uplinks)
    queue = schedule_res["queue"]
    assert len(queue) == 2
    # Highest urgency first
    assert queue[0]["engine_id"] == "ENG-MALE-02"
    assert queue[0]["urgency_tier"] == "IMMEDIATE_GROUND"
    assert queue[0]["depot_bay_assigned"] is not None
    assert "Depot" in queue[0]["assigned_mission_recommendation"]

    # Healthy asset assigned to long-endurance ISR
    assert queue[1]["engine_id"] == "ENG-MALE-01"
    assert "18h Long-Endurance" in queue[1]["assigned_mission_recommendation"]


def test_federated_coordinator_stub():
    coord = FederatedCoordinatorStub()
    status = coord.get_federated_status()
    assert status["status"] == "FUTURE_SCOPE_STUB"
    assert status["data_locality_enforcement"]["raw_telemetry_leaves_uav"] is False


def test_fleet_api_endpoints():
    client = TestClient(app)
    
    # 1. GET /api/fleet/status
    res = client.get("/api/fleet/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["fleet"]["total_uavs"] == 8

    # 2. GET /api/fleet/uplinks
    res_uplinks = client.get("/api/fleet/uplinks")
    assert res_uplinks.status_code == 200
    uplinks_data = res_uplinks.json()
    assert uplinks_data["data_locality"] == "EDGE_PRESERVED_NO_RAW_STREAM"
    assert len(uplinks_data["uplinks"]) == 8

    # 3. GET /api/fleet/correlations
    res_corr = client.get("/api/fleet/correlations")
    assert res_corr.status_code == 200
    corr_data = res_corr.json()
    assert "correlation_analysis" in corr_data

    # 4. GET /api/fleet/maintenance_queue
    res_maint = client.get("/api/fleet/maintenance_queue")
    assert res_maint.status_code == 200
    maint_data = res_maint.json()
    assert len(maint_data["schedule"]["queue"]) == 8

    # 5. POST /api/fleet/simulate_systemic_event
    res_sim = client.post("/api/fleet/simulate_systemic_event", json={
        "event_type": "CONTAMINATED_FUEL_BATCH",
        "affected_engines": ["ENG-MALE-01", "ENG-MALE-04"]
    })
    assert res_sim.status_code == 200
    sim_data = res_sim.json()
    assert sim_data["status"] == "SUCCESS"

    # Verify correlation endpoint reflects systemic alert
    res_corr2 = client.get("/api/fleet/correlations")
    corr2_data = res_corr2.json()["correlation_analysis"]
    assert corr2_data["has_systemic_anomaly"] is True
    assert corr2_data["systemic_alert"]["event_type"] == "CONTAMINATED_FUEL_BATCH"

    # 6. POST /api/fleet/clear_systemic_event
    res_clear = client.post("/api/fleet/clear_systemic_event")
    assert res_clear.status_code == 200
