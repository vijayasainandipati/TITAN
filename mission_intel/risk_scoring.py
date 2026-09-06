"""
TITAN Mission Intelligence — Tactical Risk Scoring
Calculates operational safety margins, component limit headroom,
and tactical GO / CAUTION / NO-GO status for MALE UAV flight controllers.
"""

from typing import Dict


class TacticalRiskScorer:
    def __init__(self):
        # Rotax 914 / MALE UAV certified limits
        self.limits = {
            "cht_max_c": 135.0,
            "egt_max_c": 880.0,
            "oil_press_min_bar": 1.5,
            "oil_temp_max_c": 130.0,
            "coolant_temp_max_c": 115.0,
            "vibration_max_g": 2.5
        }

    def compute_margins(self, current_sensors: Dict[str, float]) -> Dict:
        """
        Evaluates distance to critical operating boundaries.
        Margin in [0.0, 1.0] where 1.0 = full safety headroom, 0.0 = limit breached.
        """
        cht = max([current_sensors.get(f"cht_{i}_c", 110.0) for i in range(1, 5)] + [current_sensors.get("cht_mean_c", 110.0)])
        egt = max([current_sensors.get(f"egt_{i}_c", 720.0) for i in range(1, 5)] + [current_sensors.get("egt_mean_c", 720.0)])
        oil_p = current_sensors.get("oil_pressure_bar", 3.8)
        oil_t = current_sensors.get("oil_temp_c", 85.0)
        coolant = current_sensors.get("coolant_temp_c", 80.0)
        vib = current_sensors.get("vibration_rms_g", 1.2)
        
        # Margins
        cht_margin = max(self.limits["cht_max_c"] - cht, 0.0) / (self.limits["cht_max_c"] - 90.0)
        oil_p_margin = max(oil_p - self.limits["oil_press_min_bar"], 0.0) / (4.0 - self.limits["oil_press_min_bar"])
        oil_t_margin = max(self.limits["oil_temp_max_c"] - oil_t, 0.0) / (self.limits["oil_temp_max_c"] - 75.0)
        coolant_margin = max(self.limits["coolant_temp_max_c"] - coolant, 0.0) / (self.limits["coolant_temp_max_c"] - 70.0)
        vib_margin = max(self.limits["vibration_max_g"] - vib, 0.0) / (self.limits["vibration_max_g"] - 1.0)
        
        margins = {
            "thermal_headroom": round(float(min(cht_margin, coolant_margin)), 3),
            "lubrication_headroom": round(float(min(oil_p_margin, oil_t_margin)), 3),
            "mechanical_headroom": round(float(vib_margin), 3)
        }
        
        min_margin = min(margins.values())
        
        if min_margin > 0.40:
            status = "GO"
            summary = "All propulsion parameters within wide safety margins."
        elif min_margin > 0.15:
            status = "CAUTION"
            summary = "Reduced operating margins detected. Avoid high-power continuous climb."
        else:
            status = "NO_GO"
            summary = "Critical propulsion limit breach imminent. Abort or divert to nearest airfield."
            
        return {
            "tactical_status": status,
            "min_margin_ratio": round(float(min_margin), 3),
            "margins": margins,
            "summary": summary
        }
