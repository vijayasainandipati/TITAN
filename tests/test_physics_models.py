"""
Unit Tests for TITAN Physics Models (Thermal, Lubrication, Mechanical)
"""

import pytest
import numpy as np
from sim.physics_models.thermal import ThermalPhysicsModel
from sim.physics_models.lubrication import LubricationPhysicsModel
from sim.physics_models.mechanical import MechanicalPhysicsModel


def test_thermal_physics_energy_balance():
    model = ThermalPhysicsModel(param_jitter=1.0)
    model.reset(ambient_temp_c=25.0)
    
    # Run 60 seconds at cruise power
    for _ in range(60):
        out = model.step(
            dt=1.0,
            rpm=4800.0,
            map_bar=1.05,
            throttle_pct=72.0,
            tas_kts=95.0,
            altitude_ft=5000.0,
            ambient_temp_c=25.0
        )
        
    # Thermodynamic hierarchy: Combustion head > Coolant > Ambient
    assert out["cht_mean_c"] > out["coolant_temp_c"]
    assert out["coolant_temp_c"] > 25.0
    assert out["egt_mean_c"] > 500.0
    assert 15.0 < out["fuel_flow_lph"] < 35.0


def test_thermal_misfire_response():
    model = ThermalPhysicsModel(param_jitter=1.0)
    model.reset(ambient_temp_c=20.0)
    
    # Run nominal
    for _ in range(30):
        model.step(1.0, 4800.0, 1.05, 70.0, 90.0, 5000.0, 20.0)
        
    # Inject misfire on cylinder 2
    for _ in range(10):
        out = model.step(1.0, 4800.0, 1.05, 70.0, 90.0, 5000.0, 20.0, misfire_cylinder=2)
        
    # Cylinder 2 EGT should collapse relative to other cylinders
    assert out["egt_2_c"] < out["egt_1_c"] - 100.0


def test_lubrication_viscosity_and_pressure():
    model = LubricationPhysicsModel(param_jitter=1.0)
    model.reset(ambient_temp_c=20.0)
    
    # Viscosity should decrease monotonically with temperature
    v_cold = model.compute_viscosity_cst(20.0)
    v_warm = model.compute_viscosity_cst(60.0)
    v_hot = model.compute_viscosity_cst(100.0)
    assert v_cold > v_warm > v_hot
    
    # Run at idle vs cruise
    out_idle = model.step(1.0, 1800.0, 85.0, 10.0, 0.0, 20.0)
    out_cruise = model.step(1.0, 5000.0, 115.0, 95.0, 5000.0, 20.0)
    
    # Pressure at cruise should exceed pressure at idle
    assert out_cruise["oil_pressure_bar"] > out_idle["oil_pressure_bar"]


def test_mechanical_vibration_harmonics():
    model = MechanicalPhysicsModel(param_jitter=1.0)
    
    # Baseline nominal
    out_nominal = model.step(1.0, 5000.0, 75.0, 1.05, bearing_wear_severity=0.0)
    # With severe bearing wear
    out_worn = model.step(1.0, 5000.0, 75.0, 1.05, bearing_wear_severity=0.8)
    
    assert out_worn["vibration_rms_g"] > out_nominal["vibration_rms_g"]
    assert out_worn["vib_1x_g"] > out_nominal["vib_1x_g"]
    assert out_worn["vibration_crest_factor"] > out_nominal["vibration_crest_factor"]
