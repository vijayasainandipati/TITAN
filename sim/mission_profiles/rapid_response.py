"""
TITAN Mission Profile — Rapid Response & Intercept
Mission with rapid full-throttle climb, frequent power transients, and high thermal stress.
"""

from typing import Dict


class RapidResponseMissionProfile:
    def __init__(self, duration_hours: float = 4.0, ground_temp_c: float = 28.0):
        self.duration_sec = duration_hours * 3600.0
        self.ground_temp = ground_temp_c
        self.cruise_alt_ft = 12000.0

    def get_phase(self, t: float) -> str:
        fraction = t / max(self.duration_sec, 1.0)
        if fraction < 0.04:
            return "TAXI"
        elif fraction < 0.08:
            return "TAKEOFF"
        elif fraction < 0.20:
            return "CLIMB"
        elif fraction < 0.85:
            return "DASH" # High-speed sprint / intercept
        elif fraction < 0.94:
            return "DESCENT"
        else:
            return "LANDING"

    def get_conditions(self, t: float) -> Dict[str, float]:
        fraction = min(t / max(self.duration_sec, 1.0), 1.0)
        phase = self.get_phase(t)
        
        if phase == "TAXI":
            rpm = 1900.0
            throttle = 20.0
            map_bar = 0.65
            tas_kts = 15.0
            altitude_ft = 0.0
        elif phase == "TAKEOFF":
            rpm = 5800.0
            throttle = 100.0
            map_bar = 1.30
            tas_kts = 80.0
            altitude_ft = (fraction - 0.04) / 0.04 * 2500.0
        elif phase == "CLIMB":
            rpm = 5600.0
            throttle = 96.0
            map_bar = 1.25
            tas_kts = 98.0
            altitude_ft = 2500.0 + (fraction - 0.08) / 0.12 * (self.cruise_alt_ft - 2500.0)
        elif phase == "DASH":
            # Fast dash with intermittent power adjustments
            # Cycle every 20 minutes between high dash and cruise
            cycle_phase = (t % 1200.0) / 1200.0
            if cycle_phase < 0.6:
                rpm = 5300.0
                throttle = 85.0
                map_bar = 1.15
                tas_kts = 130.0
            else:
                rpm = 4750.0
                throttle = 68.0
                map_bar = 1.00
                tas_kts = 110.0
            altitude_ft = self.cruise_alt_ft
        elif phase == "DESCENT":
            rpm = 3600.0
            throttle = 40.0
            map_bar = 0.78
            tas_kts = 125.0
            altitude_ft = self.cruise_alt_ft * (1.0 - (fraction - 0.85) / 0.09)
        else:
            rpm = 2250.0
            throttle = 22.0
            map_bar = 0.68
            tas_kts = 55.0
            altitude_ft = 50.0 * (1.0 - (fraction - 0.94) / 0.06)
            
        ambient_temp = self.ground_temp - (altitude_ft / 1000.0) * 1.98
        ambient_pressure = 1.01325 * ((1.0 - 2.25577e-5 * (altitude_ft * 0.3048)) ** 5.25588)
        
        return {
            "phase": phase,
            "rpm": float(rpm),
            "throttle_pct": float(throttle),
            "map_bar": float(map_bar),
            "tas_kts": float(tas_kts),
            "altitude_ft": float(max(altitude_ft, 0.0)),
            "ambient_temp_c": float(ambient_temp),
            "ambient_pressure_bar": float(ambient_pressure)
        }
