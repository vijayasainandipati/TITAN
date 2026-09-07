"""
TITAN Mission Intelligence — Physics-Informed Fast-Time Monte Carlo What-If Simulator
Part I — Frozen v1.0 Specification

Implements the 7-step pipeline:
1. Initialize from current twin state (specific engine's live HI_i, residuals, degradation stage)
2. Expand mission profile into canonical phase timeline with environmental modifiers
3. Forward-integrate physics twin (thermal, lubrication, mechanical) -> peak CHT, min oil pressure, peak vibration
4. Project degradation kinetics forward from engine's actual current wear trajectory
5. Fast-time Monte Carlo ensemble (N=25 iterations) sampling model & parameter uncertainty
   -> per-subsystem risk probabilities = fraction of runs breaching critical safety thresholds
6. Fixed-priority GO / NO_GO decision rule over named configurable constants:
   - Rule 1: Subsystem risk % > SUBSYSTEM_RISK_CRITICAL (25%)
   - Rule 2: Peak/trough breaches hard safety floor (min oil pressure, max CHT, max vibration)
   - Rule 3: Projected health delta > HEALTH_DELTA_MAX (-15% HI)
   - Rule 4: Profile falls outside validated training envelope (OOD flag active)
   - Caution rules (risk > 10% or landing HI < 0.75)
7. Traceable, rule-specific advisory generation explaining which physical parameter fired
"""

import hashlib
import numpy as np
from typing import Dict, List, Optional, Tuple

from sim.mission_profiles import get_mission_profile
from sim.physics_models.thermal import ThermalPhysicsModel
from sim.physics_models.lubrication import LubricationPhysicsModel
from sim.physics_models.mechanical import MechanicalPhysicsModel


# =====================================================================
# NAMED CONFIGURATION CONSTANTS (PRD Part I.3 & I.5)
# Tunable per engine type or mission-criticality class without changing logic
# =====================================================================
SUBSYSTEM_RISK_CRITICAL: float = 0.25      # 25% failure probability threshold for NO_GO
SUBSYSTEM_RISK_CAUTION: float = 0.10       # 10% failure probability threshold for CAUTION
MIN_OIL_PRESSURE_FLOOR: float = 1.20       # bar (hard safety floor)
MAX_CHT_FLOOR: float = 255.0               # °C (hard safety floor)
MAX_VIBRATION_FLOOR: float = 2.80          # g (hard safety floor)
HEALTH_DELTA_MAX: float = 0.15             # 15% HI max single-sortie degradation allowance (-0.15 delta)
HEALTH_LANDING_MIN_GO: float = 0.75        # Min landing HI for unconditional GO
HEALTH_LANDING_MIN_CAUTION: float = 0.55   # Min landing HI for CAUTION (below = NO_GO)
OOD_ALTITUDE_CEILING_MAX: float = 22000.0  # ft (validated training envelope ceiling)
OOD_TEMP_OFFSET_MAX: float = 20.0          # °C (validated training envelope max temp offset)
OOD_TEMP_OFFSET_MIN: float = -15.0         # °C (validated training envelope min temp offset)
MONTE_CARLO_ENSEMBLE_SIZE: int = 25        # N sampled ensemble forward projections


def derive_deterministic_seed(engine_id: str = "ENG-MALE-01",
                             snapshot_id: str = "0",
                             mission_profile: str = "endurance",
                             duration_hours: float = 12.0,
                             ambient_offset_c: float = 0.0,
                             altitude_ceiling_ft: float = 18000.0,
                             inject_fault: Optional[str] = None,
                             fault_severity: float = 0.0) -> int:
    """
    Derives deterministic ensemble random seed per Section I.5.
    seed = hash(engine_id, current_twin_state_snapshot_id, mission_profile,
                sortie_duration, ambient_offset, operating_ceiling)
    """
    key_str = (
        f"{engine_id}|{snapshot_id}|{mission_profile}|"
        f"{round(float(duration_hours), 2)}|{round(float(ambient_offset_c), 1)}|"
        f"{round(float(altitude_ceiling_ft), 0)}|{inject_fault}|{round(float(fault_severity), 2)}"
    )
    digest = hashlib.sha256(key_str.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) & 0x7FFFFFFF


class WhatIfMissionSimulator:
    def __init__(self, ensemble_size: int = MONTE_CARLO_ENSEMBLE_SIZE):
        self.ensemble_size = ensemble_size

    def run_simulation(self,
                       current_hi: float = 0.95,
                       current_subsystems: Optional[Dict[str, float]] = None,
                       current_residuals: Optional[Dict[str, float]] = None,
                       current_deg_state: Optional[Dict[str, float]] = None,
                       wear_multiplier: float = 1.0,
                       engine_id: str = "ENG-MALE-01",
                       twin_snapshot_id: Optional[str] = None,
                       twin_snapshot_timestamp: Optional[str] = None,
                       mission_profile_name: str = "endurance",
                       planned_duration_hours: float = 12.0,
                       ambient_temp_offset_c: float = 0.0,
                       altitude_ceiling_ft: float = 18000.0,
                       inject_fault: Optional[str] = None,
                       fault_severity: float = 0.0) -> Dict:
        """
        Executes a physics-informed fast-time Monte Carlo forward projection.
        Reuses the Digital Twin physics models and degradation heads in batch mode.
        """
        # -------------------------------------------------------------
        # STEP 1: Initialize from current twin state
        # Pull live subsystem health, residuals, and actual wear trajectory
        # -------------------------------------------------------------
        current_subsystems = current_subsystems or {
            "thermal": 0.95, "lubrication": 0.95, "mechanical": 0.95, "combustion": 0.95
        }
        
        # Base degradation states derived from the live engine's actual condition
        lube_deg_base = 1.0 - current_subsystems.get("lubrication", 0.95)
        bearing_wear_base = 1.0 - current_subsystems.get("mechanical", 0.95)
        cooling_deg_base = 1.0 - current_subsystems.get("thermal", 0.95)

        if current_deg_state:
            lube_deg_base = max(lube_deg_base, current_deg_state.get("lube_degradation", 0.0))
            bearing_wear_base = max(bearing_wear_base, current_deg_state.get("bearing_wear", 0.0))
            cooling_deg_base = max(cooling_deg_base, current_deg_state.get("cooling_degradation", 0.0))

        # Re-anchor baseline wear from live physics residuals if present
        if current_residuals:
            r_oil = current_residuals.get("r_oil_pressure", 0.0)
            if r_oil < -1.2:
                # Negative oil pressure residual indicates elevated oil leakage or bearing clearance
                lube_deg_base = max(lube_deg_base, min(abs(r_oil) * 0.06, 0.45))
            r_cht = current_residuals.get("r_cht", 0.0)
            if r_cht > 1.2:
                cooling_deg_base = max(cooling_deg_base, min(r_cht * 0.05, 0.45))
            r_vib = current_residuals.get("r_vibration", 0.0)
            if r_vib > 1.2:
                bearing_wear_base = max(bearing_wear_base, min(r_vib * 0.06, 0.45))

        # Apply simulated fault injection if requested
        if inject_fault:
            f_lower = inject_fault.lower()
            if "oil" in f_lower or "lube" in f_lower:
                lube_deg_base = max(lube_deg_base, fault_severity)
            elif "cool" in f_lower or "radiator" in f_lower or "thermal" in f_lower:
                cooling_deg_base = max(cooling_deg_base, fault_severity)
            elif "bear" in f_lower or "mech" in f_lower:
                bearing_wear_base = max(bearing_wear_base, fault_severity)

        # -------------------------------------------------------------
        # STEP 2: Expand mission profile into phase timeline
        # Canonical phase sequence scaled to planned duration and ceiling
        # -------------------------------------------------------------
        profile = get_mission_profile(mission_profile_name, duration_hours=planned_duration_hours)
        total_duration_sec = planned_duration_hours * 3600.0
        
        # 24 discrete timeline checkpoints across sortie phases
        n_checkpoints = 24
        time_checkpoints = np.linspace(0.0, total_duration_sec, n_checkpoints)
        dt_segment_hrs = planned_duration_hours / n_checkpoints

        # Precompute profile flight conditions across the timeline
        phase_timeline = []
        for t in time_checkpoints:
            cond = profile.get_conditions(t)
            # Apply ceiling limit
            cond["altitude_ft"] = min(cond["altitude_ft"], altitude_ceiling_ft)
            # Apply ambient temperature modifier
            cond["ambient_temp_c"] += ambient_temp_offset_c
            phase_timeline.append(cond)

        # -------------------------------------------------------------
        # STEP 3 & 4 & 5: Fast-Time Monte Carlo Ensemble Forward Projection
        # Run N iterations with sampled parameter uncertainty and wear kinetics
        # -------------------------------------------------------------
        N = self.ensemble_size
        
        # Track statistics across ensemble runs
        run_peak_chts = []
        run_min_oil_ps = []
        run_peak_vibs = []
        run_final_his = []
        run_final_ruls = []
        
        # Breach counters for empirical probability estimation
        lube_breach_count = 0
        thermal_breach_count = 0
        mech_breach_count = 0
        
        # Section I.5: Deterministic ensemble random seed derived from inputs & twin snapshot
        effective_snapshot_id = twin_snapshot_id or f"{engine_id}_HI{round(current_hi, 4)}"
        deterministic_seed = derive_deterministic_seed(
            engine_id=engine_id,
            snapshot_id=effective_snapshot_id,
            mission_profile=mission_profile_name,
            duration_hours=planned_duration_hours,
            ambient_offset_c=ambient_temp_offset_c,
            altitude_ceiling_ft=altitude_ceiling_ft,
            inject_fault=inject_fault,
            fault_severity=fault_severity
        )
        rng = np.random.RandomState(deterministic_seed)
        median_trajectory = []

        for run_idx in range(N):
            # Sample model parameter jitter (reusing confidence / uncertainty layer C.3)
            jitter_th = float(1.0 + rng.normal(0.0, 0.03))
            jitter_lu = float(1.0 + rng.normal(0.0, 0.04))
            jitter_me = float(1.0 + rng.normal(0.0, 0.04))
            jitter_wear = float(max(wear_multiplier + rng.normal(0.0, 0.05), 0.6))
            temp_noise = float(rng.normal(0.0, 0.6))

            thermal_model = ThermalPhysicsModel(param_jitter=jitter_th)
            lube_model = LubricationPhysicsModel(param_jitter=jitter_lu)
            mech_model = MechanicalPhysicsModel(param_jitter=jitter_me)
            
            init_amb = 25.0 + ambient_temp_offset_c + temp_noise
            thermal_model.reset(ambient_temp_c=init_amb)
            thermal_model.state[0:4] = 120.0 + ambient_temp_offset_c
            thermal_model.state[4] = 75.0 + ambient_temp_offset_c
            lube_model.reset(ambient_temp_c=init_amb)
            lube_model.t_oil = 85.0 + ambient_temp_offset_c
            lube_model.p_oil = max(4.8 * (1.0 - 0.75 * lube_deg_base), 1.5)

            # Degradation states for this run
            lube_deg = float(np.clip(lube_deg_base + rng.normal(0.0, 0.01), 0.0, 1.0))
            bearing_wear = float(np.clip(bearing_wear_base + rng.normal(0.0, 0.01), 0.0, 1.0))
            cooling_deg = float(np.clip(cooling_deg_base + rng.normal(0.0, 0.01), 0.0, 1.0))

            peak_cht_run = 0.0
            min_oil_p_run = 99.0
            peak_vib_run = 0.0
            
            run_lube_breached = False
            run_thermal_breached = False
            run_mech_breached = False

            run_trajectory_samples = []

            for step_idx, cond in enumerate(phase_timeline):
                t_sec = time_checkpoints[step_idx]
                rpm = cond["rpm"]
                map_bar = cond["map_bar"]
                throttle_pct = cond["throttle_pct"]
                tas_kts = cond["tas_kts"]
                alt_ft = cond["altitude_ft"]
                amb_temp = cond["ambient_temp_c"] + temp_noise

                # Stable physics sub-stepping: 4 small 5-second sub-steps per segment
                # prevents Euler integration instability for large dt
                cooling_factor = max(1.0 - 0.55 * cooling_deg, 0.35)
                for _ in range(4):
                    t_out = thermal_model.step(
                        dt=5.0,
                        rpm=rpm,
                        map_bar=map_bar,
                        throttle_pct=throttle_pct,
                        tas_kts=tas_kts,
                        altitude_ft=alt_ft,
                        ambient_temp_c=amb_temp,
                        cooling_degradation_factor=cooling_factor
                    )

                    l_out = lube_model.step(
                        dt=5.0,
                        rpm=rpm,
                        cht_mean_c=t_out["cht_mean_c"],
                        tas_kts=tas_kts,
                        altitude_ft=alt_ft,
                        ambient_temp_c=amb_temp,
                        bearing_wear_multiplier=1.0 + 1.25 * bearing_wear,
                        oil_leak_severity=lube_deg
                    )

                    m_out = mech_model.step(
                        dt=5.0,
                        rpm=rpm,
                        throttle_pct=throttle_pct,
                        map_bar=map_bar,
                        bearing_wear_severity=bearing_wear
                    )

                cht = float(t_out["cht_mean_c"])
                oil_p = float(l_out["oil_pressure_bar"])
                oil_t = float(l_out["oil_temp_c"])
                vib = float(m_out["vibration_rms_g"])

                peak_cht_run = max(peak_cht_run, cht)
                min_oil_p_run = min(min_oil_p_run, oil_p)
                peak_vib_run = max(peak_vib_run, vib)

                # Step 4: Advance wear kinetics forward under operating stress
                stress = (rpm / 5000.0) ** 1.8 * (map_bar / 1.0) * jitter_wear
                # Thermal acceleration: elevated oil temperature accelerates oxidation and viscosity breakdown
                thermal_shear_accel = 1.0 + max(oil_t - 105.0, 0.0) * 0.03
                
                # Wear accumulation per segment
                lube_deg += 0.00045 * stress * (1.0 + 2.5 * lube_deg) * thermal_shear_accel * dt_segment_hrs
                bearing_wear += 0.00030 * stress * (1.0 + 2.0 * bearing_wear) * dt_segment_hrs
                cooling_deg += 0.00025 * (1.0 + 1.5 * cooling_deg) * dt_segment_hrs

                lube_deg = min(lube_deg, 1.0)
                bearing_wear = min(bearing_wear, 1.0)
                cooling_deg = min(cooling_deg, 1.0)

                # Check subsystem threshold crossings during the sortie
                # Critical limits: Oil P <= 1.25 bar, CHT >= 210°C, Vib >= 2.3g, or degradation >= 0.40
                if (oil_p <= 1.25) or (lube_deg >= 0.40) or (oil_t >= 135.0):
                    run_lube_breached = True
                if (cht >= 210.0) or (cooling_deg >= 0.35) or (t_out["coolant_temp_c"] >= 115.0):
                    run_thermal_breached = True
                if (vib >= 2.30) or (bearing_wear >= 0.35):
                    run_mech_breached = True

                # Record samples for median trajectory export (every 2 checkpoints)
                if run_idx == 0 and (step_idx % 2 == 0 or step_idx == n_checkpoints - 1):
                    max_d = max(lube_deg, bearing_wear, cooling_deg)
                    hi_instant = float(np.clip(1.0 - max_d, 0.05, 1.0))
                    run_trajectory_samples.append({
                        "time_hours": round(t_sec / 3600.0, 2),
                        "flight_phase": cond["phase"],
                        "projected_hi": round(hi_instant, 3),
                        "cht_c": round(cht, 1),
                        "oil_pressure_bar": round(oil_p, 2),
                        "oil_temp_c": round(oil_t, 1),
                        "vibration_rms_g": round(vib, 2)
                    })

            # End of run calculations
            final_wear = max(lube_deg, bearing_wear, cooling_deg)
            final_hi_run = float(np.clip(1.0 - final_wear, 0.05, 1.0))
            final_rul_run = max(250.0 * final_hi_run / (1.0 + 3.0 * (1.0 - final_hi_run)), 5.0)

            run_peak_chts.append(peak_cht_run)
            run_min_oil_ps.append(min_oil_p_run)
            run_peak_vibs.append(peak_vib_run)
            run_final_his.append(final_hi_run)
            run_final_ruls.append(final_rul_run)

            if run_lube_breached:
                lube_breach_count += 1
            if run_thermal_breached:
                thermal_breach_count += 1
            if run_mech_breached:
                mech_breach_count += 1

            if run_idx == 0:
                median_trajectory = run_trajectory_samples

        # -------------------------------------------------------------
        # STEP 5 (Cont.): Empirical Probabilities & Ensemble Aggregations
        # -------------------------------------------------------------
        p_lube_fail = float(lube_breach_count / N)
        p_cool_fail = float(thermal_breach_count / N)
        p_mech_fail = float(mech_breach_count / N)
        
        # Worst-case physical extremes expected to be reached across ensemble
        max_cht_worst = float(np.max(run_peak_chts))
        min_oil_p_worst = float(np.min(run_min_oil_ps))
        max_vib_worst = float(np.max(run_peak_vibs))
        
        # Central tendencies for projected health and RUL
        projected_final_hi = float(np.median(run_final_his))
        projected_post_rul = float(np.median(run_final_ruls))
        rul_q05 = float(np.percentile(run_final_ruls, 5))
        rul_q95 = float(np.percentile(run_final_ruls, 95))
        hi_std = float(np.std(run_final_his))
        
        delta_hi = float(current_hi - projected_final_hi)

        # -------------------------------------------------------------
        # STEP 6: GO / NO_GO Decision Rule
        # Evaluated in strict priority order (Part I.3)
        # -------------------------------------------------------------
        status = "GO"
        firing_rule = "NOMINAL_CLEARANCE"
        recommendation = "Full mission authorized. Engine health projected to remain within nominal safety margins across all mission phases."

        # Rule 1: Subsystem failure risk > SUBSYSTEM_RISK_CRITICAL (25%)
        rule1_fired = False
        rule1_reason = ""
        subsystem_risks = [
            ("Thermal runaway", p_cool_fail),
            ("Lubrication breakdown", p_lube_fail),
            ("Mechanical seizure", p_mech_fail)
        ]
        for sub_name, risk_val in subsystem_risks:
            if risk_val >= SUBSYSTEM_RISK_CRITICAL:
                rule1_fired = True
                rule1_reason = f"{sub_name} risk ({risk_val*100:.1f}%) exceeds critical safety threshold ({SUBSYSTEM_RISK_CRITICAL*100:.0f}%)."
                break

        # Rule 2: Hard physics safety floor breached
        rule2_fired = False
        rule2_reason = ""
        if min_oil_p_worst < MIN_OIL_PRESSURE_FLOOR:
            rule2_fired = True
            rule2_reason = f"Projected minimum oil pressure ({min_oil_p_worst:.2f} bar) breaches hard safety floor ({MIN_OIL_PRESSURE_FLOOR:.2f} bar)."
        elif max_cht_worst > MAX_CHT_FLOOR:
            rule2_fired = True
            rule2_reason = f"Projected peak CHT ({max_cht_worst:.1f}°C) breaches maximum thermal limit ({MAX_CHT_FLOOR:.1f}°C)."
        elif max_vib_worst > MAX_VIBRATION_FLOOR:
            rule2_fired = True
            rule2_reason = f"Projected peak vibration ({max_vib_worst:.2f} g) breaches structural safety envelope ({MAX_VIBRATION_FLOOR:.2f} g)."

        # Rule 3: Health delta exceeds operational single-sortie allowance
        rule3_fired = (delta_hi >= HEALTH_DELTA_MAX)
        rule3_reason = f"Projected health degradation (-{delta_hi*100:.1f}% HI) exceeds maximum single-sortie allowance (-{HEALTH_DELTA_MAX*100:.1f}% HI)."

        # Rule 4: Out-Of-Distribution (OOD) envelope breach
        rule4_fired = (
            altitude_ceiling_ft > OOD_ALTITUDE_CEILING_MAX or
            ambient_temp_offset_c > OOD_TEMP_OFFSET_MAX or
            ambient_temp_offset_c < OOD_TEMP_OFFSET_MIN
        )
        rule4_reason = f"Configured flight envelope ({altitude_ceiling_ft:,.0f} ft / {ambient_temp_offset_c:+.0f}°C OAT) exceeds physics twin validated training envelope."

        # Caution checks
        max_risk = max(p_cool_fail, p_lube_fail, p_mech_fail)
        caution_fired = (max_risk >= SUBSYSTEM_RISK_CAUTION or projected_final_hi < HEALTH_LANDING_MIN_GO)

        # -------------------------------------------------------------
        # STEP 7: Advisory Generation
        # Generated from which rule fired and on which parameter
        # -------------------------------------------------------------
        if rule1_fired:
            status = "NO_GO"
            firing_rule = "RULE_1_SUBSYSTEM_RISK"
            recommendation = f"Pre-mission NO-GO advisory: {rule1_reason} Sustained operating stress under configured profile leads to unacceptable probability of in-flight subsystem loss."
        elif rule2_fired:
            status = "NO_GO"
            firing_rule = "RULE_2_PHYSICS_FLOOR"
            recommendation = f"Pre-mission NO-GO advisory: {rule2_reason} Direct physical safety envelope breach projected regardless of empirical probability."
        elif rule3_fired:
            status = "NO_GO"
            firing_rule = "RULE_3_HEALTH_DELTA"
            recommendation = f"Pre-mission NO-GO advisory: {rule3_reason} Sortie wear profile is unsustainable for airframe engine asset."
        elif rule4_fired:
            status = "NO_GO"
            firing_rule = "RULE_4_OOD_ENVELOPE"
            recommendation = f"Pre-mission NO-GO advisory: {rule4_reason} Conservative clearance denial enforced due to untrusted extrapolation beyond validated bounds."
        elif caution_fired:
            status = "CAUTION"
            firing_rule = "CAUTION_CONSTRAINTS"
            caution_factors = []
            if p_cool_fail >= SUBSYSTEM_RISK_CAUTION:
                caution_factors.append(f"thermal risk at {p_cool_fail*100:.1f}%")
            if p_lube_fail >= SUBSYSTEM_RISK_CAUTION:
                caution_factors.append(f"lubrication risk at {p_lube_fail*100:.1f}%")
            if p_mech_fail >= SUBSYSTEM_RISK_CAUTION:
                caution_factors.append(f"mechanical risk at {p_mech_fail*100:.1f}%")
            if projected_final_hi < HEALTH_LANDING_MIN_GO:
                caution_factors.append(f"projected landing health at {projected_final_hi*100:.1f}%")
            factors_str = "; ".join(caution_factors)
            recommendation = f"Pre-flight CAUTION advisory: Mission authorized with operational constraints ({factors_str}). Limit high-power loiter and monitor oil pressure and CHT residuals continuously."
        else:
            status = "GO"
            firing_rule = "NOMINAL_GO"
            recommendation = "Pre-flight clearance authorized: Engine cleared for scheduled profile. All subsystems projected to operate within nominal thermal, lubrication, and mechanical safety margins."

        return {
            "status": status,
            "recommendation": recommendation,
            "firing_rule": firing_rule,
            "snapshot_timestamp": twin_snapshot_timestamp or "00:00:00",
            "snapshot_id": effective_snapshot_id,
            "deterministic_seed": deterministic_seed,
            "initial_hi": round(current_hi, 3),
            "projected_final_hi": round(projected_final_hi, 3),
            "projected_health_index": round(projected_final_hi, 3),
            "projected_post_mission_rul_hours": round(projected_post_rul, 1),
            "projected_rul_hours": round(projected_post_rul, 1),
            "max_cht_c": round(max_cht_worst, 1),
            "min_oil_pressure_bar": round(min_oil_p_worst, 2),
            "max_vibration_g": round(max_vib_worst, 2),
            "failure_probabilities": {
                "lubrication_failure": round(p_lube_fail, 3),
                "thermal_runaway": round(p_cool_fail, 3),
                "mechanical_seizure": round(p_mech_fail, 3)
            },
            "tactical_clearance": {
                "recommendation": status,
                "rationale": recommendation,
                "firing_rule": firing_rule
            },
            "ensemble_stats": {
                "ensemble_runs": N,
                "hi_std": round(hi_std, 4),
                "rul_90_interval": [round(rul_q05, 1), round(rul_q95, 1)]
            },
            "trajectory_samples": median_trajectory
        }
