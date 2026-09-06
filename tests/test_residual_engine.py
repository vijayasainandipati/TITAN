"""
Unit Tests for Digital Twin Core, Sensor Health, Residuals, and Envelope Validation
"""

import pytest
import numpy as np
from twin_core.sensor_health import SensorHealthModule
from twin_core.residual_engine import PhysicsResidualEngine
from twin_core.state_estimator import DigitalTwinStateEstimator
from twin_core.virtual_sensors import VirtualSensorReconstruction


def test_sensor_health_range_and_cross_consistency():
    module = SensorHealthModule()
    
    # 1. Nominal balanced readings
    nominal_sensors = {
        "cht_1_c": 118.0, "cht_2_c": 119.0, "cht_3_c": 117.5, "cht_4_c": 118.5,
        "egt_1_c": 740.0, "egt_2_c": 745.0, "egt_3_c": 742.0, "egt_4_c": 744.0,
        "coolant_temp_c": 82.0, "oil_pressure_bar": 3.9, "oil_temp_c": 88.0,
        "vibration_rms_g": 1.35
    }
    rep_nom = module.evaluate_sensor_health(nominal_sensors)
    assert not rep_nom["sensor_fault_detected"]
    assert rep_nom["cross_sensor_consistency_score"] == 1.0
    
    # 2. Inject isolated thermocouple drift on CHT 3 (spread > 22 C without EGT shift)
    corrupted = dict(nominal_sensors)
    corrupted["cht_3_c"] = 155.0 # +37 C drift
    rep_corrupt = module.evaluate_sensor_health(corrupted)
    assert rep_corrupt["sensor_fault_detected"]
    assert "cht_3_c" in rep_corrupt["faulted_channels"]


def test_residual_engine_normalization():
    engine = PhysicsResidualEngine()
    
    actual = {
        "cht_mean_c": 118.0,
        "egt_mean_c": 745.0,
        "coolant_temp_c": 82.0,
        "oil_pressure_bar": 2.2, # 1.7 bar drop
        "oil_temp_c": 98.0,       # 10 C rise
        "vibration_rms_g": 1.35
    }
    expected = {
        "cht_mean_c": 118.0,
        "egt_mean_c": 745.0,
        "coolant_temp_c": 82.0,
        "oil_pressure_bar": 3.9,
        "oil_temp_c": 88.0,
        "vibration_rms_g": 1.35
    }
    
    res = engine.compute_residuals(actual, expected)
    residuals = res["residuals"]
    
    # Nominal channels should be zero
    assert abs(residuals["r_cht_mean"]) < 0.1
    # Oil pressure drop should be large negative normalized residual
    assert residuals["r_oil_pressure"] < -5.0
    # Oil temp rise should be positive
    assert residuals["r_oil_temp"] > 3.0


def test_envelope_validation():
    estimator = DigitalTwinStateEstimator(max_altitude_ft=24000.0)
    
    # Within envelope
    valid, msg = estimator.check_envelope(altitude_ft=18000.0, ambient_temp_c=10.0, rpm=5000.0)
    assert valid
    assert msg == "VALID_ENVELOPE"
    
    # Exceed ceiling
    valid_alt, msg_alt = estimator.check_envelope(altitude_ft=28000.0, ambient_temp_c=-20.0, rpm=5000.0)
    assert not valid_alt
    assert "OUTSIDE VALIDATED ENVELOPE" in msg_alt


def test_virtual_sensor_reconstruction():
    reconstructor = VirtualSensorReconstruction()
    
    raw = {
        "cht_1_c": 118.0,
        "cht_2_c": 119.0,
        "cht_3_c": 0.0, # Dropped channel
        "cht_4_c": 118.0,
        "oil_pressure_bar": 0.0 # Dropped pressure transducer
    }
    expected = {
        "cht_mean_c": 118.5,
        "oil_pressure_bar": 4.1
    }
    
    corrected, conf, reconstructed = reconstructor.reconstruct_channels(
        raw, expected, faulted_channels=["cht_3_c", "oil_pressure_bar"]
    )
    
    assert "cht_3_c" in reconstructed
    assert "oil_pressure_bar" in reconstructed
    assert 117.0 < corrected["cht_3_c"] < 120.0
    assert corrected["oil_pressure_bar"] == 4.1
    assert conf < 1.0 # Confidence penalization applied
