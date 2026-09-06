r"""
TITAN Hierarchical Aggregation — Health Index Engine
Computes:
1. Subsystem Health Indicators: HI_thermal, HI_lube, HI_mech, HI_comb in [0.0, 1.0]
2. Phase-dependent risk weighting w_i(phase)
3. Overall Engine Health Index: HI_engine(t) = \sum w_i(phase) * HI_i(t)
4. Recovery/reset updates following maintenance actions.
"""

import numpy as np
from typing import Dict, Optional


PHASE_WEIGHTS: Dict[str, Dict[str, float]] = {
    "TAXI":     {"thermal": 0.20, "lube": 0.30, "mechanical": 0.30, "combustion": 0.20},
    "TAKEOFF":  {"thermal": 0.25, "lube": 0.25, "mechanical": 0.35, "combustion": 0.15},
    "CLIMB":    {"thermal": 0.35, "lube": 0.35, "mechanical": 0.15, "combustion": 0.15},
    "CRUISE":   {"thermal": 0.25, "lube": 0.30, "mechanical": 0.25, "combustion": 0.20},
    "LOITER":   {"thermal": 0.20, "lube": 0.35, "mechanical": 0.20, "combustion": 0.25},
    "DESCENT":  {"thermal": 0.20, "lube": 0.30, "mechanical": 0.30, "combustion": 0.20},
    "LANDING":  {"thermal": 0.20, "lube": 0.25, "mechanical": 0.35, "combustion": 0.20}
}


class HealthIndexCalculator:
    def __init__(self):
        # Baseline state (fully healthy)
        self.hi_subsystems = {
            "thermal": 1.0,
            "lubrication": 1.0,
            "mechanical": 1.0,
            "combustion": 1.0
        }
        self.hi_engine = 1.0

    def compute_health_indices(self,
                               residuals: Dict[str, float],
                               phase_str: str = "CRUISE",
                               sensor_health_ok: bool = True) -> Dict:
        """
        Computes subsystem and engine health indices from physics residuals
        and mission phase weights.
        """
        phase_key = phase_str.upper() if phase_str.upper() in PHASE_WEIGHTS else "CRUISE"
        weights = PHASE_WEIGHTS[phase_key]
        
        # 1. Thermal Health Indicator
        r_cht = abs(residuals.get("r_cht_mean", 0.0))
        r_cool = max(residuals.get("r_coolant_temp", 0.0), 0.0)
        thermal_penalty = 0.08 * r_cht + 0.12 * r_cool
        hi_thermal = float(np.clip(1.0 - thermal_penalty, 0.05, 1.0))
        
        # 2. Lubrication Health Indicator (asymmetric: pressure drop is dangerous)
        r_oil_p = residuals.get("r_oil_pressure", 0.0)
        p_drop_penalty = 0.22 * abs(min(r_oil_p, 0.0)) # Pressure drops penalized heavily
        r_oil_t = max(residuals.get("r_oil_temp", 0.0), 0.0)
        t_rise_penalty = 0.10 * r_oil_t
        hi_lube = float(np.clip(1.0 - (p_drop_penalty + t_rise_penalty), 0.05, 1.0))
        
        # 3. Mechanical Health Indicator
        r_vib = max(residuals.get("r_vibration_rms", 0.0), 0.0)
        mech_penalty = 0.18 * r_vib
        hi_mech = float(np.clip(1.0 - mech_penalty, 0.05, 1.0))
        
        # 4. Combustion Health Indicator
        r_egt = abs(residuals.get("r_egt_mean", 0.0))
        comb_penalty = 0.10 * r_egt
        hi_comb = float(np.clip(1.0 - comb_penalty, 0.05, 1.0))
        
        # If sensor health is compromised, do not attribute sensor error to engine health degradation!
        if not sensor_health_ok:
            # Dampen residual penalties by 70% if isolated sensor fault
            hi_thermal = 0.3 * hi_thermal + 0.7 * self.hi_subsystems["thermal"]
            hi_lube = 0.3 * hi_lube + 0.7 * self.hi_subsystems["lubrication"]
            hi_mech = 0.3 * hi_mech + 0.7 * self.hi_subsystems["mechanical"]
            hi_comb = 0.3 * hi_comb + 0.7 * self.hi_subsystems["combustion"]
            
        self.hi_subsystems = {
            "thermal": round(hi_thermal, 4),
            "lubrication": round(hi_lube, 4),
            "mechanical": round(hi_mech, 4),
            "combustion": round(hi_comb, 4)
        }
        
        # Aggregate engine health with phase-dependent risk weighting
        hi_eng = (
            weights["thermal"] * hi_thermal +
            weights["lube"] * hi_lube +
            weights["mechanical"] * hi_mech +
            weights["combustion"] * hi_comb
        )
        self.hi_engine = round(float(np.clip(hi_eng, 0.05, 1.0)), 4)
        
        return {
            "hi_engine": self.hi_engine,
            "subsystems": self.hi_subsystems,
            "phase_weights": weights,
            "flight_phase": phase_key
        }

    def apply_reset(self, subsystem_name: str, recovered_hi: float = 0.98):
        """
        Applies a maintenance reset to a specified subsystem.
        """
        sub_lower = subsystem_name.lower()
        if "therm" in sub_lower or "cool" in sub_lower:
            self.hi_subsystems["thermal"] = recovered_hi
        elif "lube" in sub_lower or "oil" in sub_lower:
            self.hi_subsystems["lubrication"] = recovered_hi
        elif "mech" in sub_lower or "bear" in sub_lower or "vib" in sub_lower:
            self.hi_subsystems["mechanical"] = recovered_hi
        elif "comb" in sub_lower or "ign" in sub_lower or "plug" in sub_lower:
            self.hi_subsystems["combustion"] = recovered_hi
        elif "all" in sub_lower or "overhaul" in sub_lower:
            for k in self.hi_subsystems:
                self.hi_subsystems[k] = recovered_hi
                
        # Re-compute engine overall with neutral weights
        self.hi_engine = round(float(np.mean(list(self.hi_subsystems.values()))), 4)
