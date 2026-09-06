"""
TITAN Degradation Dynamics & Maintenance Recovery/Reset Engine
Models:
1. Multi-rate degradation kinetics:
   - Incipient (slow Weibull/exponential drift)
   - Moderate (progressive linear-quadratic accumulation)
   - Severe (exponential acceleration toward critical failure)
2. Maintenance Event Recovery / Resets:
   - Oil change & filter flush -> Resets lubrication degradation
   - Spark plug / coil replacement -> Resets misfire
   - Injector ultrasonic cleaning -> Resets injector restriction
   - Coolant flush & radiator decoke -> Resets cooling degradation
   - Top-end / bearing overhaul -> Resets mechanical & combustion degradation
"""

import numpy as np
from typing import Dict, List, Optional
from .fmea_taxonomy import FMEAFaultClass


class DegradationManager:
    def __init__(self, wear_multiplier: float = 1.0):
        self.wear_multiplier = wear_multiplier
        
        # Continuous degradation state metrics [0.0 = factory new, 1.0 = functional failure]
        self.lube_degradation = 0.0
        self.bearing_wear = 0.0
        self.cooling_degradation = 0.0
        self.injector_restriction = 0.0
        self.blowby_severity = 0.0
        self.misfire_active = False
        self.misfire_cylinder = None
        
        # Sensor specific faults
        self.sensor_drift = {"channel": None, "drift_value": 0.0}
        self.sensor_frozen = {"channel": None, "frozen_value": None}
        
        # Maintenance event log
        self.maintenance_history: List[Dict] = []

    def inject_fault(self,
                     fault_class: FMEAFaultClass,
                     severity: float = 0.5,
                     target_cylinder: int = 2,
                     target_sensor: Optional[str] = None):
        """Injects a specific FMEA fault mode."""
        severity = np.clip(severity, 0.05, 1.0)
        
        if fault_class == FMEAFaultClass.NORMAL:
            self.misfire_active = False
            self.misfire_cylinder = None
        elif fault_class == FMEAFaultClass.MISFIRE:
            self.misfire_active = True
            self.misfire_cylinder = target_cylinder
        elif fault_class == FMEAFaultClass.INJECTOR_CLOGGING:
            self.injector_restriction = severity
            self.misfire_cylinder = target_cylinder
        elif fault_class == FMEAFaultClass.LUBE_DEGRADATION:
            self.lube_degradation = max(self.lube_degradation, severity)
        elif fault_class == FMEAFaultClass.COOLING_DEGRADATION:
            self.cooling_degradation = max(self.cooling_degradation, severity)
        elif fault_class == FMEAFaultClass.BEARING_WEAR:
            self.bearing_wear = max(self.bearing_wear, severity)
        elif fault_class == FMEAFaultClass.COMBUSTION_BLOWBY:
            self.blowby_severity = max(self.blowby_severity, severity)
        elif fault_class == FMEAFaultClass.SENSOR_FAULT:
            ch = target_sensor or "oil_pressure_bar"
            self.sensor_drift = {"channel": ch, "drift_value": severity * 1.5}

    def apply_maintenance_reset(self, maintenance_type: str, timestamp: float) -> Dict:
        """
        Simulates maintenance action, resetting relevant degradation states back to nominal baseline.
        """
        reset_action = {
            "timestamp": timestamp,
            "maintenance_type": maintenance_type,
            "subsystems_reset": [],
            "previous_degradation": {}
        }
        
        m_upper = maintenance_type.upper()
        if "OIL" in m_upper or "LUBE" in m_upper:
            reset_action["previous_degradation"]["lube"] = self.lube_degradation
            self.lube_degradation = 0.02 # Slight residual age
            reset_action["subsystems_reset"].append("Lubrication System")
            
        if "PLUG" in m_upper or "IGNITION" in m_upper or "MISFIRE" in m_upper:
            self.misfire_active = False
            self.misfire_cylinder = None
            reset_action["subsystems_reset"].append("Ignition / Spark Plugs")
            
        if "INJECTOR" in m_upper or "FUEL" in m_upper:
            reset_action["previous_degradation"]["injector"] = self.injector_restriction
            self.injector_restriction = 0.0
            reset_action["subsystems_reset"].append("Fuel Injection Nozzles")
            
        if "COOL" in m_upper or "RADIATOR" in m_upper:
            reset_action["previous_degradation"]["cooling"] = self.cooling_degradation
            self.cooling_degradation = 0.01
            reset_action["subsystems_reset"].append("Cooling System & Radiator")
            
        if "OVERHAUL" in m_upper or "BEARING" in m_upper:
            reset_action["previous_degradation"]["bearing"] = self.bearing_wear
            reset_action["previous_degradation"]["blowby"] = self.blowby_severity
            self.bearing_wear = 0.01
            self.blowby_severity = 0.01
            reset_action["subsystems_reset"].append("Crankcase Bearings & Piston Rings")
            
        if "SENSOR" in m_upper or "CALIBRAT" in m_upper:
            self.sensor_drift = {"channel": None, "drift_value": 0.0}
            self.sensor_frozen = {"channel": None, "frozen_value": None}
            reset_action["subsystems_reset"].append("Sensors & Instrumentation")
            
        self.maintenance_history.append(reset_action)
        return reset_action

    def step(self, dt_seconds: float, rpm: float, map_bar: float, t_oil: float):
        """
        Advances natural continuous wear according to operating stress.
        """
        dt_hours = dt_seconds / 3600.0
        stress_factor = (rpm / 5000.0) ** 2.0 * (map_bar / 1.0) * self.wear_multiplier
        
        # Extremely slow baseline mechanical and lubrication aging (hours to thousands of hours)
        base_lube_rate = 0.0008 * (1.0 + max(t_oil - 95.0, 0.0) * 0.04)
        base_bearing_rate = 0.0003
        
        # If severe degradation is underway, kinetic rate accelerates exponentially
        if self.lube_degradation > 0.35:
            # Accelerated breakdown
            accel = 1.0 + 4.0 * (self.lube_degradation - 0.35)
            self.lube_degradation += base_lube_rate * stress_factor * accel * dt_hours * 12.0
        else:
            self.lube_degradation += base_lube_rate * stress_factor * dt_hours
            
        if self.bearing_wear > 0.40:
            accel_bear = 1.0 + 5.0 * (self.bearing_wear - 0.40)
            self.bearing_wear += base_bearing_rate * stress_factor * accel_bear * dt_hours * 10.0
        else:
            self.bearing_wear += base_bearing_rate * stress_factor * dt_hours
            
        self.lube_degradation = min(self.lube_degradation, 1.0)
        self.bearing_wear = min(self.bearing_wear, 1.0)
        self.cooling_degradation = min(self.cooling_degradation, 1.0)
        self.injector_restriction = min(self.injector_restriction, 1.0)
        self.blowby_severity = min(self.blowby_severity, 1.0)

    def get_degradation_state(self) -> Dict:
        return {
            "lube_degradation": float(self.lube_degradation),
            "bearing_wear": float(self.bearing_wear),
            "cooling_degradation": float(self.cooling_degradation),
            "injector_restriction": float(self.injector_restriction),
            "blowby_severity": float(self.blowby_severity),
            "misfire_active": bool(self.misfire_active),
            "misfire_cylinder": self.misfire_cylinder,
            "sensor_drift": self.sensor_drift
        }
