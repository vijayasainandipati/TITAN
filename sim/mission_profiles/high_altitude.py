"""
TITAN Mission Profile — High Altitude Ceiling Sortie
Sortie pushing operational ceiling to FL240 (24,000 ft) testing turbocharger boost limits,
low ambient density, and lean mixture control.
"""

from typing import Dict


class HighAltitudeMissionProfile:
    def __init__(self, duration_hours: float = 10.0, ground_temp_c: float = 20.0):
        self.duration_sec = duration_hours * 3600.0
        self.ground_temp = ground_temp_c
        self.cruise_alt_ft = 24000.0

    def get_phase(self, t: float) -> str:
        fraction = t / max(self.duration_sec, 1.0)
        if fraction < 0.03:
            return "TAXI"
        elif fraction < 0.06:
            return "TAKEOFF"
        elif fraction < 0.22:
            return "CLIMB"
        elif fraction < 0.82:
            return "LOITER"
        elif fraction < 0.96:
            return "DESCENT"
        else:
            return "LANDING"

    def get_conditions(self, t: float) -> Dict[str, float]:
        fraction = min(t / max(self.duration_sec, 1.0), 1.0)
        phase = self.get_phase(t)
        
        if phase == "TAXI":
            rpm = 1850.0
            throttle = 18.0
            map_bar = 0.65
            tas_kts = 12.0
            altitude_ft = 0.0
        elif phase == "TAKEOFF":
            rpm = 5800.0
            throttle = 100.0
            map_bar = 1.28
            tas_kts = 76.0
            altitude_ft = (fraction - 0.03) / 0.03 * 1800.0
        elif phase == "CLIMB":
            # Sustained high throttle climb to ceiling
            rpm = 5500.0
            throttle = 94.0
            map_bar = 1.22
            tas_kts = 94.0
            altitude_ft = 1800.0 + (fraction - 0.06) / 0.16 * (self.cruise_alt_ft - 1800.0)
        elif phase == "LOITER":
            # High-altitude station keeping: True airspeed higher due to low density
            rpm = 4950.0
            throttle = 74.0
            map_bar = 1.08
            tas_kts = 118.0 # TAS higher at high altitude
            altitude_ft = self.cruise_alt_ft
        elif phase == "DESCENT":
            rpm = 3300.0
            throttle = 32.0
            map_bar = 0.68
            tas_kts = 115.0
            altitude_ft = self.cruise_alt_ft * (1.0 - (fraction - 0.82) / 0.14)
        else:
            rpm = 2150.0
            throttle = 20.0
            map_bar = 0.65
            tas_kts = 52.0
            altitude_ft = 50.0 * (1.0 - (fraction - 0.96) / 0.04)
            
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
