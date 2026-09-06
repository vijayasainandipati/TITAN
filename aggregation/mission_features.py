"""
TITAN Hierarchical Aggregation — Mission Features
Aggregates sortie-level cumulative stress and operational fatigue:
- Cumulative thermal excursions (CHT > 130C)
- Time spent at maximum power (> 5200 RPM)
- Cumulative mechanical vibration dose
- Lubrication stress hours
"""

import numpy as np
from typing import Dict, List


class MissionStressTracker:
    def __init__(self):
        self.cumulative_flight_sec = 0.0
        self.high_power_sec = 0.0
        self.thermal_stress_sec = 0.0
        self.vibration_dose = 0.0
        self.low_oil_press_count = 0

    def update(self,
               dt: float,
               rpm: float,
               cht_max_c: float,
               oil_p_bar: float,
               vib_rms_g: float) -> Dict[str, float]:
        """
        Updates cumulative mission metrics with current step.
        """
        self.cumulative_flight_sec += dt
        
        if rpm >= 5200.0:
            self.high_power_sec += dt
            
        if cht_max_c >= 130.0:
            self.thermal_stress_sec += dt
            
        # Accumulate vibration energy dose
        self.vibration_dose += (vib_rms_g ** 2) * dt
        
        if oil_p_bar < 2.2 and rpm > 3000.0:
            self.low_oil_press_count += 1
            
        return self.get_mission_features()

    def get_mission_features(self) -> Dict[str, float]:
        flight_hrs = self.cumulative_flight_sec / 3600.0
        return {
            "mission_flight_hours": round(flight_hrs, 3),
            "mission_high_power_ratio": round(self.high_power_sec / max(self.cumulative_flight_sec, 1.0), 3),
            "mission_thermal_stress_sec": round(self.thermal_stress_sec, 1),
            "mission_vibration_dose": round(self.vibration_dose / 3600.0, 3),
            "mission_low_oil_press_events": self.low_oil_press_count
        }
