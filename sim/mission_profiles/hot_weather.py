"""
TITAN Mission Profile — Hot Desert Operations (ISA + 15C)
High ambient ground temperatures (+45C) representing desert trials (e.g. Pokhran / Rajasthan).
Stresses thermal margins and oil cooling efficiency.
"""

from typing import Dict


class HotWeatherMissionProfile:
    def __init__(self, duration_hours: float = 8.0, ground_temp_c: float = 46.0):
        self.duration_sec = duration_hours * 3600.0
        self.ground_temp = ground_temp_c
        self.cruise_alt_ft = 15000.0

    def get_phase(self, t: float) -> str:
        fraction = t / max(self.duration_sec, 1.0)
        if fraction < 0.04:
            return "TAXI"
        elif fraction < 0.08:
            return "TAKEOFF"
        elif fraction < 0.20:
            return "CLIMB"
        elif fraction < 0.85:
            return "CRUISE"
        elif fraction < 0.96:
            return "DESCENT"
        else:
            return "LANDING"

    def get_conditions(self, t: float) -> Dict[str, float]:
        fraction = min(t / max(self.duration_sec, 1.0), 1.0)
        phase = self.get_phase(t)
        
        if phase == "TAXI":
            rpm = 1950.0
            throttle = 22.0
            map_bar = 0.68
            tas_kts = 10.0
            altitude_ft = 0.0
        elif phase == "TAKEOFF":
            rpm = 5800.0
            throttle = 100.0
            map_bar = 1.30
            tas_kts = 78.0
            altitude_ft = (fraction - 0.04) / 0.04 * 2000.0
        elif phase == "CLIMB":
            rpm = 5450.0
            throttle = 90.0
            map_bar = 1.20
            tas_kts = 90.0
            altitude_ft = 2000.0 + (fraction - 0.08) / 0.12 * (self.cruise_alt_ft - 2000.0)
        elif phase == "CRUISE":
            rpm = 4900.0
            throttle = 72.0
            map_bar = 1.05
            tas_kts = 96.0
            altitude_ft = self.cruise_alt_ft
        elif phase == "DESCENT":
            rpm = 3500.0
            throttle = 38.0
            map_bar = 0.75
            tas_kts = 108.0
            altitude_ft = self.cruise_alt_ft * (1.0 - (fraction - 0.85) / 0.11)
        else:
            rpm = 2300.0
            throttle = 25.0
            map_bar = 0.70
            tas_kts = 58.0
            altitude_ft = 60.0 * (1.0 - (fraction - 0.96) / 0.04)
            
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
