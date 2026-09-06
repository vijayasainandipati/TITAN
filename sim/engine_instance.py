"""
TITAN Engine Instance & Fleet Generator
Generates distinct simulated engine instances with manufacturing tolerance jitter,
baseline wear rate multipliers, and individual sensor bias/noise profiles
to support Part B.3 multi-engine requirements and Part E.2 Leave-Engine-Out validation.
"""

import numpy as np
from typing import Dict, List, Optional
from .physics_models.thermal import ThermalPhysicsModel
from .physics_models.lubrication import LubricationPhysicsModel
from .physics_models.mechanical import MechanicalPhysicsModel


class EngineInstance:
    def __init__(self,
                 engine_id: str,
                 name: str,
                 thermal_jitter: float = 1.0,
                 lube_jitter: float = 1.0,
                 mech_jitter: float = 1.0,
                 wear_rate_multiplier: float = 1.0,
                 sensor_bias: Optional[Dict[str, float]] = None,
                 sensor_noise_sigma: Optional[Dict[str, float]] = None,
                 baseline_flight_hours: float = 50.0):
        
        self.engine_id = engine_id
        self.name = name
        self.thermal_jitter = thermal_jitter
        self.lube_jitter = lube_jitter
        self.mech_jitter = mech_jitter
        self.wear_rate_multiplier = wear_rate_multiplier
        self.flight_hours = baseline_flight_hours
        
        # Sensor calibration systematic biases
        self.sensor_bias = sensor_bias or {
            "cht_1_c": 0.0, "cht_2_c": 0.0, "cht_3_c": 0.0, "cht_4_c": 0.0,
            "egt_1_c": 0.0, "egt_2_c": 0.0, "egt_3_c": 0.0, "egt_4_c": 0.0,
            "oil_pressure_bar": 0.0, "oil_temp_c": 0.0, "coolant_temp_c": 0.0,
            "vibration_rms_g": 0.0
        }
        
        # Sensor Gaussian noise standard deviations
        self.sensor_noise_sigma = sensor_noise_sigma or {
            "cht_c": 0.45,
            "egt_c": 2.2,
            "oil_pressure_bar": 0.035,
            "oil_temp_c": 0.35,
            "coolant_temp_c": 0.30,
            "vibration_rms_g": 0.045
        }
        
        # Instantiated physics twin models with parameter jitter
        self.thermal = ThermalPhysicsModel(param_jitter=self.thermal_jitter)
        self.lubrication = LubricationPhysicsModel(param_jitter=self.lube_jitter)
        self.mechanical = MechanicalPhysicsModel(param_jitter=self.mech_jitter)

    def reset_state(self, ambient_temp_c: float = 20.0):
        self.thermal.reset(ambient_temp_c)
        self.lubrication.reset(ambient_temp_c)

    def to_dict(self) -> Dict:
        return {
            "engine_id": self.engine_id,
            "name": self.name,
            "thermal_jitter": round(self.thermal_jitter, 3),
            "lube_jitter": round(self.lube_jitter, 3),
            "mech_jitter": round(self.mech_jitter, 3),
            "wear_rate_multiplier": round(self.wear_rate_multiplier, 3),
            "flight_hours": round(self.flight_hours, 1),
            "sensor_bias": self.sensor_bias
        }


def create_fleet(num_engines: int = 8, seed: int = 42) -> List[EngineInstance]:
    """
    Creates a fleet of distinct MALE-UAV aero-piston engines
    with physically bounded manufacturing jitter and calibration offsets.
    """
    rng = np.random.RandomState(seed)
    fleet = []
    
    fleet_names = [
        "TAPAS-BH-201 Unit #01 (Air Force Trials)",
        "TAPAS-BH-201 Unit #02 (Navy Maritime Patrol)",
        "Rustom-II Prototype Unit #03 (High Altitude)",
        "Rustom-II Production Unit #04 (Hot Desert Test)",
        "MALE-UAV Fleet Airframe #05 (ISR Endurance)",
        "MALE-UAV Fleet Airframe #06 (Long Loiter)",
        "MALE-UAV Fleet Airframe #07 (Trainer Airframe)",
        "MALE-UAV Fleet Airframe #08 (Evaluation Rig)"
    ]
    
    for i in range(num_engines):
        eng_id = f"ENG-MALE-{i+1:02d}"
        name = fleet_names[i % len(fleet_names)]
        
        # Manufacturing parameter jitter: +/- 4% to 8%
        t_jitter = 1.0 + rng.uniform(-0.06, 0.06)
        l_jitter = 1.0 + rng.uniform(-0.06, 0.06)
        m_jitter = 1.0 + rng.uniform(-0.05, 0.05)
        wear_mult = rng.uniform(0.85, 1.25)
        init_hours = float(rng.uniform(30.0, 320.0))
        
        # Sensor calibration biases
        s_bias = {
            "cht_1_c": float(rng.normal(0.0, 0.8)),
            "cht_2_c": float(rng.normal(0.0, 0.8)),
            "cht_3_c": float(rng.normal(0.0, 0.8)),
            "cht_4_c": float(rng.normal(0.0, 0.8)),
            "egt_1_c": float(rng.normal(0.0, 3.5)),
            "egt_2_c": float(rng.normal(0.0, 3.5)),
            "egt_3_c": float(rng.normal(0.0, 3.5)),
            "egt_4_c": float(rng.normal(0.0, 3.5)),
            "oil_pressure_bar": float(rng.normal(0.0, 0.06)),
            "oil_temp_c": float(rng.normal(0.0, 0.7)),
            "coolant_temp_c": float(rng.normal(0.0, 0.6)),
            "vibration_rms_g": float(rng.normal(0.0, 0.04))
        }
        
        instance = EngineInstance(
            engine_id=eng_id,
            name=name,
            thermal_jitter=t_jitter,
            lube_jitter=l_jitter,
            mech_jitter=m_jitter,
            wear_rate_multiplier=wear_mult,
            sensor_bias=s_bias,
            baseline_flight_hours=init_hours
        )
        fleet.append(instance)
        
    return fleet
