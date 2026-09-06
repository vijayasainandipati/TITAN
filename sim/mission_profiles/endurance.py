"""
TITAN Mission Profile — Long Endurance ISR
Models an 18-hour MALE-UAV surveillance sortie:
- Pre-flight / Taxi (0 - 15 min)
- Takeoff & Initial Climb (15 - 45 min)
- En-route Climb to FL180 (45 - 90 min)
- High-Altitude Loiter / Station Keeping (1.5 hr - 16.5 hr)
- Descent (16.5 hr - 17.5 hr)
- Approach, Landing & Cooldown (17.5 hr - 18 hr)
"""

from typing import Dict, Tuple


class EnduranceMissionProfile:
    def __init__(self, duration_hours: float = 18.0, ground_temp_c: float = 24.0):
        self.duration_sec = duration_hours * 3600.0
        self.ground_temp = ground_temp_c
        self.cruise_alt_ft = 18000.0

    def get_phase(self, t: float) -> str:
        fraction = t / max(self.duration_sec, 1.0)
        if fraction < 0.015:
            return "TAXI"
        elif fraction < 0.035:
            return "TAKEOFF"
        elif fraction < 0.10:
            return "CLIMB"
        elif fraction < 0.90:
            return "LOITER"
        elif fraction < 0.97:
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
            map_bar = 1.28 # Turbo boost full
            tas_kts = 75.0
            altitude_ft = (fraction - 0.015) / 0.020 * 1500.0
        elif phase == "CLIMB":
            rpm = 5400.0
            throttle = 88.0
            map_bar = 1.18
            tas_kts = 92.0
            climb_frac = (fraction - 0.035) / 0.065
            altitude_ft = 1500.0 + climb_frac * (self.cruise_alt_ft - 1500.0)
        elif phase == "LOITER":
            # Highly fuel-efficient loiter power setting
            rpm = 4650.0
            throttle = 64.0
            map_bar = 0.98
            tas_kts = 88.0
            altitude_ft = self.cruise_alt_ft
        elif phase == "DESCENT":
            rpm = 3400.0
            throttle = 35.0
            map_bar = 0.72
            tas_kts = 110.0
            desc_frac = (fraction - 0.90) / 0.07
            altitude_ft = self.cruise_alt_ft * (1.0 - desc_frac)
        else: # LANDING
            rpm = 2200.0
            throttle = 22.0
            map_bar = 0.68
            tas_kts = 55.0
            altitude_ft = 50.0 * (1.0 - (fraction - 0.97) / 0.03)
            
        # International Standard Atmosphere lapse rate (-1.98 C / 1000 ft)
        ambient_temp = self.ground_temp - (altitude_ft / 1000.0) * 1.98
        # Ambient pressure lapse
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
