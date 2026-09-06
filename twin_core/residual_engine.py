r"""
TITAN Digital Twin Core — Physics Residual Engine
Computes normalized physics residuals:
r_i(t) = (y_i(t) - \hat{y}_i(t)) / (\sigma_i + \epsilon)
and derivative rates \dot{r}_i(t) for all primary aero-piston observables.
"""

import numpy as np
from typing import Dict, Optional


class PhysicsResidualEngine:
    def __init__(self, noise_sigmas: Optional[Dict[str, float]] = None):
        # Default nominal standard deviations for normalization
        self.sigmas = noise_sigmas or {
            "cht_mean_c": 1.2,
            "egt_mean_c": 6.5,
            "coolant_temp_c": 1.0,
            "oil_pressure_bar": 0.12,
            "oil_temp_c": 1.1,
            "vibration_rms_g": 0.08
        }
        self.prev_residuals: Dict[str, float] = {}

    def compute_residuals(self,
                          actual_sensors: Dict[str, float],
                          expected_state: Dict[str, float],
                          dt: float = 1.0) -> Dict:
        """
        Computes normalized residuals and residual rates.
        """
        residuals = {}
        rates = {}
        
        # Calculate mean CHT and EGT from individual actual cylinders if not already aggregated
        act_cht_mean = actual_sensors.get("cht_mean_c")
        if act_cht_mean is None:
            chts = [actual_sensors.get(f"cht_{i}_c", 0.0) for i in range(1, 5)]
            act_cht_mean = float(np.mean(chts)) if any(chts) else 0.0
            
        act_egt_mean = actual_sensors.get("egt_mean_c")
        if act_egt_mean is None:
            egts = [actual_sensors.get(f"egt_{i}_c", 0.0) for i in range(1, 5)]
            act_egt_mean = float(np.mean(egts)) if any(egts) else 0.0
            
        mapping = {
            "r_cht_mean": (act_cht_mean, expected_state.get("cht_mean_c", act_cht_mean), "cht_mean_c"),
            "r_egt_mean": (act_egt_mean, expected_state.get("egt_mean_c", act_egt_mean), "egt_mean_c"),
            "r_coolant_temp": (actual_sensors.get("coolant_temp_c", 0.0), expected_state.get("coolant_temp_c", 0.0), "coolant_temp_c"),
            "r_oil_pressure": (actual_sensors.get("oil_pressure_bar", 0.0), expected_state.get("oil_pressure_bar", 0.0), "oil_pressure_bar"),
            "r_oil_temp": (actual_sensors.get("oil_temp_c", 0.0), expected_state.get("oil_temp_c", 0.0), "oil_temp_c"),
            "r_vibration_rms": (actual_sensors.get("vibration_rms_g", 0.0), expected_state.get("vibration_rms_g", 0.0), "vibration_rms_g")
        }
        
        for r_name, (act, exp, sig_key) in mapping.items():
            sigma = self.sigmas.get(sig_key, 1.0)
            eps = 1e-4
            r_val = (act - exp) / (sigma + eps)
            residuals[r_name] = float(r_val)
            
            # Residual rate (slew)
            prev_r = self.prev_residuals.get(r_name, r_val)
            rates[f"d_{r_name}"] = float((r_val - prev_r) / max(dt, 0.1))
            self.prev_residuals[r_name] = r_val
            
        # Overall residual magnitude (Mahalanobis-style L2 norm)
        norm_r = float(np.sqrt(sum(v ** 2 for v in residuals.values()) / len(residuals)))
        
        return {
            "residuals": residuals,
            "residual_rates": rates,
            "residual_l2_norm": norm_r
        }
