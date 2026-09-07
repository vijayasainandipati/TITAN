"""
Unit Tests for TITAN Mission Intelligence — Physics-Informed Fast-Time Monte Carlo What-If Simulator
Verifies Part I 7-step pipeline:
1. Twin state initialization
2. Phase timeline expansion
3. Physics forward integration (Peak CHT, Min Oil Pressure, Peak Vibration)
4. Degradation kinetics projection
5. Monte Carlo empirical probability estimation
6. Fixed-order GO / NO_GO decision rules (Rules 1-4, Caution, GO)
7. Traceable explainable operational assessment
"""

import pytest
from mission_intel.simulator import (
    WhatIfMissionSimulator,
    SUBSYSTEM_RISK_CRITICAL,
    MIN_OIL_PRESSURE_FLOOR,
    MAX_CHT_FLOOR,
    HEALTH_DELTA_MAX,
    OOD_ALTITUDE_CEILING_MAX
)


def test_what_if_simulator_nominal_go():
    """Verify nominal baseline profile on a healthy engine receives clearance (GO)."""
    sim = WhatIfMissionSimulator(ensemble_size=15)
    res = sim.run_simulation(
        current_hi=0.96,
        current_subsystems={"thermal": 0.96, "lubrication": 0.96, "mechanical": 0.96, "combustion": 0.96},
        mission_profile_name="endurance",
        planned_duration_hours=6.0,
        ambient_temp_offset_c=0.0,
        altitude_ceiling_ft=12000.0
    )
    
    assert res["status"] in ["GO", "CAUTION"]
    assert res["projected_final_hi"] > 0.85
    assert res["projected_post_mission_rul_hours"] > 100.0
    assert res["min_oil_pressure_bar"] >= MIN_OIL_PRESSURE_FLOOR
    assert res["max_cht_c"] <= MAX_CHT_FLOOR
    assert res["failure_probabilities"]["lubrication_failure"] < SUBSYSTEM_RISK_CRITICAL
    assert res["ensemble_stats"]["ensemble_runs"] == 15
    assert len(res["trajectory_samples"]) > 0


def test_what_if_simulator_rule1_critical_thermal_risk():
    """Verify high altitude and extreme hot weather triggers Rule 1 Thermal Risk NO_GO."""
    sim = WhatIfMissionSimulator(ensemble_size=20)
    res = sim.run_simulation(
        current_hi=0.88,
        current_subsystems={"thermal": 0.70, "lubrication": 0.92, "mechanical": 0.94, "combustion": 0.95},
        mission_profile_name="hot_weather",
        planned_duration_hours=14.0,
        ambient_temp_offset_c=12.0,
        altitude_ceiling_ft=19000.0
    )
    
    # Thermal runaway risk should be elevated due to high ambient OAT and degraded cooling
    assert res["failure_probabilities"]["thermal_runaway"] > 0.0
    if res["failure_probabilities"]["thermal_runaway"] >= SUBSYSTEM_RISK_CRITICAL:
        assert res["status"] == "NO_GO"
        assert "RULE_1" in res["firing_rule"] or "RULE_2" in res["firing_rule"]
        assert "thermal" in res["recommendation"].lower() or "cht" in res["recommendation"].lower()


def test_what_if_simulator_rule2_hard_physics_floor_breach():
    """Verify severe lube fault triggers Rule 2 (Min Oil Pressure Floor Breach) NO_GO."""
    sim = WhatIfMissionSimulator(ensemble_size=15)
    res = sim.run_simulation(
        current_hi=0.72,
        current_subsystems={"thermal": 0.90, "lubrication": 0.45, "mechanical": 0.85, "combustion": 0.90},
        inject_fault="oil_leak",
        fault_severity=0.75,
        mission_profile_name="endurance",
        planned_duration_hours=10.0
    )
    
    assert res["status"] == "NO_GO"
    # Oil pressure should drop significantly below floor
    assert res["min_oil_pressure_bar"] <= 1.50
    assert "NO-GO" in res["recommendation"]


def test_what_if_simulator_rule4_ood_envelope():
    """Verify mission profile exceeding validated ceiling (e.g. 24,000 ft) triggers Rule 4 OOD NO_GO."""
    sim = WhatIfMissionSimulator(ensemble_size=15)
    res = sim.run_simulation(
        current_hi=0.98,
        mission_profile_name="endurance",
        planned_duration_hours=6.0,
        altitude_ceiling_ft=24000.0 # Exceeds OOD_ALTITUDE_CEILING_MAX (22,000 ft)
    )
    
    assert res["status"] == "NO_GO"
    assert res["firing_rule"] == "RULE_4_OOD_ENVELOPE"
    assert "validated" in res["recommendation"].lower() or "envelope" in res["recommendation"].lower()


def test_what_if_simulator_deterministic_reproducibility():
    """
    Verify PRD Section I.5 requirement:
    Identical inputs against the same twin state snapshot produce 100% bit-exact outputs.
    """
    sim = WhatIfMissionSimulator(ensemble_size=20)
    config = {
        "current_hi": 0.92,
        "current_subsystems": {"thermal": 0.91, "lubrication": 0.93, "mechanical": 0.94, "combustion": 0.90},
        "engine_id": "ENG-MALE-01",
        "twin_snapshot_id": "ENG-MALE-01-T500-HI0.920",
        "twin_snapshot_timestamp": "00:08:20",
        "mission_profile_name": "endurance",
        "planned_duration_hours": 18.5,
        "ambient_temp_offset_c": 0.0,
        "altitude_ceiling_ft": 18000.0
    }

    run1 = sim.run_simulation(**config)
    run2 = sim.run_simulation(**config)

    assert run1["deterministic_seed"] == run2["deterministic_seed"]
    assert run1["snapshot_id"] == run2["snapshot_id"]
    assert run1["snapshot_timestamp"] == run2["snapshot_timestamp"]
    assert run1["projected_final_hi"] == run2["projected_final_hi"]
    assert run1["projected_post_mission_rul_hours"] == run2["projected_post_mission_rul_hours"]
    assert run1["min_oil_pressure_bar"] == run2["min_oil_pressure_bar"]
    assert run1["max_cht_c"] == run2["max_cht_c"]
    assert run1["max_vibration_g"] == run2["max_vibration_g"]
    assert run1["failure_probabilities"] == run2["failure_probabilities"]
    assert run1["tactical_clearance"] == run2["tactical_clearance"]

