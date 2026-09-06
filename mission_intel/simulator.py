"""
TITAN Mission Intelligence — What-If Flight Simulator
Evaluates pre-mission feasibility, forward degradation trajectory,
and tactical GO / CAUTION / NO-GO recommendations under variable environmental profiles.
"""

import numpy as np
from typing import Dict, List, Optional

from sim.mission_profiles import get_mission_profile
from sim.physics_models.thermal import ThermalPhysicsModel
from sim.physics_models.lubrication import LubricationPhysicsModel
from sim.physics_models.mechanical import MechanicalPhysicsModel


class WhatIfMissionSimulator:
    def __init__(self):
        self.thermal = ThermalPhysicsModel()
        self.lube = LubricationPhysicsModel()
        self.mech = MechanicalPhysicsModel()

    def run_simulation(self,
                       current_hi: float = 0.95,
                       current_subsystems: Optional[Dict[str, float]] = None,
                       mission_profile_name: str = "endurance",
                       planned_duration_hours: float = 12.0,
                       ambient_temp_offset_c: float = 0.0,
                       altitude_ceiling_ft: float = 18000.0,
                       inject_fault: Optional[str] = None,
                       fault_severity: float = 0.0) -> Dict:
        """
        Simulates future mission forward in time, projecting degradation and failure risk.
        """
        current_subsystems = current_subsystems or {
            "thermal": 0.95, "lubrication": 0.95, "mechanical": 0.95, "combustion": 0.95
        }
        
        profile = get_mission_profile(mission_profile_name, duration_hours=planned_duration_hours)
        dt_sim = 60.0 # Step 1 minute intervals for fast simulation
        total_steps = int((planned_duration_hours * 3600.0) / dt_sim)
        
        # Initial degradation states derived from starting health indices
        lube_deg = 1.0 - current_subsystems.get("lubrication", 0.95)
        bearing_wear = 1.0 - current_subsystems.get("mechanical", 0.95)
        cooling_deg = 1.0 - current_subsystems.get("thermal", 0.95)
        
        # Check for simulated fault injection
        if inject_fault:
            f_lower = inject_fault.lower()
            if "oil" in f_lower or "lube" in f_lower:
                lube_deg = max(lube_deg, fault_severity)
            elif "cool" in f_lower or "radiator" in f_lower:
                cooling_deg = max(cooling_deg, fault_severity)
            elif "bear" in f_lower:
                bearing_wear = max(bearing_wear, fault_severity)
                
        trajectory = []
        max_cht = 0.0
        min_oil_p = 99.0
        max_vib = 0.0
        
        hi_current = current_hi
        
        # Fast-forward simulation
        for step in range(total_steps):
            t = step * dt_sim
            cond = profile.get_conditions(t)
            # Apply user weather offset
            cond["ambient_temp_c"] += ambient_temp_offset_c
            
            # Accelerate wear kinetics
            stress = (cond["rpm"] / 5000.0) ** 1.8 * (cond["map_bar"] / 1.0)
            lube_deg += 0.00015 * stress * (1.0 + 3.0 * lube_deg) * (dt_sim / 3600.0)
            bearing_wear += 0.00010 * stress * (dt_sim / 3600.0)
            cooling_deg += 0.00008 * (dt_sim / 3600.0)
            
            # Step physics models periodically
            if step % 10 == 0 or step == total_steps - 1:
                t_out = self.thermal.step(
                    dt=dt_sim,
                    rpm=cond["rpm"],
                    map_bar=cond["map_bar"],
                    throttle_pct=cond["throttle_pct"],
                    tas_kts=cond["tas_kts"],
                    altitude_ft=cond["altitude_ft"],
                    ambient_temp_c=cond["ambient_temp_c"],
                    cooling_degradation_factor=max(1.0 - 0.5 * cooling_deg, 0.4)
                )
                l_out = self.lube.step(
                    dt=dt_sim,
                    rpm=cond["rpm"],
                    cht_mean_c=t_out["cht_mean_c"],
                    tas_kts=cond["tas_kts"],
                    altitude_ft=cond["altitude_ft"],
                    ambient_temp_c=cond["ambient_temp_c"],
                    bearing_wear_multiplier=1.0 + 1.2 * bearing_wear,
                    oil_leak_severity=lube_deg
                )
                m_out = self.mech.step(
                    dt=dt_sim,
                    rpm=cond["rpm"],
                    throttle_pct=cond["throttle_pct"],
                    map_bar=cond["map_bar"],
                    bearing_wear_severity=bearing_wear
                )
                
                max_cht = max(max_cht, t_out["cht_mean_c"])
                min_oil_p = min(min_oil_p, l_out["oil_pressure_bar"])
                max_vib = max(max_vib, m_out["vibration_rms_g"])
                
                # Projected Health Index
                max_d = max(lube_deg, bearing_wear, cooling_deg)
                hi_proj = float(np.clip(1.0 - max_d, 0.05, 1.0))
                
                trajectory.append({
                    "time_hours": round(t / 3600.0, 2),
                    "flight_phase": cond["phase"],
                    "projected_hi": round(hi_proj, 3),
                    "cht_c": round(t_out["cht_mean_c"], 1),
                    "oil_pressure_bar": round(l_out["oil_pressure_bar"], 2),
                    "oil_temp_c": round(l_out["oil_temp_c"], 1),
                    "vibration_rms_g": round(m_out["vibration_rms_g"], 2)
                })
                
        final_hi = trajectory[-1]["projected_hi"] if trajectory else current_hi
        
        # Risk assessment & failure probabilities
        p_lube_fail = float(np.clip(lube_deg * 1.3, 0.0, 0.99))
        p_cool_fail = float(np.clip(cooling_deg * 1.1, 0.0, 0.99))
        p_mech_fail = float(np.clip(bearing_wear * 1.2, 0.0, 0.99))
        
        max_risk = max(p_lube_fail, p_cool_fail, p_mech_fail)
        
        if final_hi >= 0.75 and max_risk < 0.10:
            rec_status = "GO"
            recommendation = "Full mission authorized. Engine health projected to remain within nominal safety margins."
        elif final_hi >= 0.55 and max_risk < 0.25:
            rec_status = "CAUTION"
            recommendation = "Mission authorized with operational constraints (limit high-power loiter / monitor oil pressure)."
        else:
            rec_status = "NO_GO"
            recommendation = "Pre-mission NO-GO advisory. Severe risk of subsystem limit violation or bearing seizure."
            
        projected_post_rul = max(250.0 * final_hi / (1.0 + 3.0 * (1.0 - final_hi)), 5.0)
        
        return {
            "status": rec_status,
            "recommendation": recommendation,
            "initial_hi": round(current_hi, 3),
            "projected_final_hi": round(final_hi, 3),
            "projected_post_mission_rul_hours": round(projected_post_rul, 1),
            "max_cht_c": round(max_cht, 1),
            "min_oil_pressure_bar": round(min_oil_p, 2),
            "max_vibration_g": round(max_vib, 2),
            "failure_probabilities": {
                "lubrication_failure": round(p_lube_fail, 3),
                "thermal_runaway": round(p_cool_fail, 3),
                "mechanical_seizure": round(p_mech_fail, 3)
            },
            "trajectory_samples": trajectory
        }
