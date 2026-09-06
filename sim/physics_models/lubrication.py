"""
TITAN Physics Models — Lubrication Engine
First-principles lubrication circuit dynamics:
- Temperature-dependent oil viscosity (Walther/ASTM model)
- Positive displacement oil pump flow vs crankshaft RPM
- Hydrodynamic journal bearing clearance resistance
- Oil temperature thermal balance (shear heating vs oil cooler heat rejection)
"""

import numpy as np
from typing import Dict, Tuple


class LubricationPhysicsModel:
    def __init__(self,
                 oil_mass_kg: float = 3.8,            # Dry sump oil reservoir mass
                 c_p_oil: float = 2050.0,             # J/(kg*K) specific heat of synthetic aero oil (AeroShell 15W-50)
                 pump_displacement_cc: float = 8.5,   # cc/rev
                 h_oil_cooler_area: float = 28.0,     # W/K oil cooler heat transfer coefficient * area
                 bearing_clearance_nominal: float = 0.045, # mm nominal journal bearing radial clearance
                 filter_dp_nominal_bar: float = 0.25, # Nominal clean filter pressure drop
                 param_jitter: float = 1.0):          # Manufacturing tolerance jitter
        
        self.oil_mass = oil_mass_kg * param_jitter
        self.c_p_oil = c_p_oil
        self.pump_disp_m3 = (pump_displacement_cc * 1e-6) * param_jitter
        self.h_cooler = h_oil_cooler_area * param_jitter
        self.c_b_nominal = bearing_clearance_nominal * param_jitter
        self.filter_dp = filter_dp_nominal_bar
        
        # State: [T_oil in C, P_oil in bar]
        self.t_oil = 75.0
        self.p_oil = 4.2

    def reset(self, ambient_temp_c: float = 20.0):
        self.t_oil = ambient_temp_c
        self.p_oil = 0.0

    def compute_viscosity_cst(self, temp_c: float) -> float:
        """
        Kinematic viscosity (cSt = mm^2/s) using Walther equation for SAE 15W-50:
        Typical: 130 cSt @ 40C, 18.5 cSt @ 100C.
        """
        t_k = max(temp_c + 273.15, 230.0)
        # Empirical ASTM D341 constants for 15W-50 aero oil:
        # log10(log10(v + 0.7)) = A - B * log10(T_K)
        # Using fitted parameters:
        A = 8.85
        B = 3.32
        log_log = A - B * np.log10(t_k)
        log_v = 10.0 ** log_log
        v_cst = max(10.0 ** log_v - 0.7, 3.0)
        return float(v_cst)

    def step(self,
             dt: float,
             rpm: float,
             cht_mean_c: float,
             tas_kts: float,
             altitude_ft: float,
             ambient_temp_c: float,
             bearing_wear_multiplier: float = 1.0,
             oil_leak_severity: float = 0.0) -> Dict[str, float]:
        """
        Advances the lubrication state by dt seconds.
        bearing_wear_multiplier: >= 1.0 (e.g. 1.3 = 30% increased clearance).
        oil_leak_severity: 0.0 (no leak) to 1.0 (severe oil loss/loss of pressure).
        """
        tas_mps = max(tas_kts * 0.514444, 4.0)
        
        # Effective bearing clearance
        effective_clearance = self.c_b_nominal * bearing_wear_multiplier
        # Flow resistance scales inversely with cube of clearance (Hagen-Poiseuille / journal slot)
        clearance_factor = (self.c_b_nominal / effective_clearance) ** 2.2
        
        # Viscosity
        nu_cst = self.compute_viscosity_cst(self.t_oil)
        rho_oil = 860.0 # kg/m^3
        mu_pa_s = (nu_cst * 1e-6) * rho_oil
        
        # Oil pump delivery
        eta_vol = np.clip(0.88 - 0.001 * max(self.t_oil - 90.0, 0.0), 0.65, 0.95)
        v_dot_pump = (self.pump_disp_m3 * (rpm / 60.0)) * eta_vol
        
        # Hydrodynamic pressure generation: P = mu * Q / K
        # Calibrated nominal Rotax 914 oil pressure: ~2.0 bar at idle (1600 RPM) to ~4.5 bar at cruise (5000 RPM)
        k_hydraulic = 4.2e-11 # Calibrated gallery flow constant
        p_hydro = (mu_pa_s * v_dot_pump / k_hydraulic) * clearance_factor * 1e-5 # in bar
        
        # Pressure relief valve cap at ~5.2 bar, minimum crankcase pressure ~1.0 bar abs (0 gauge)
        p_nominal = np.clip(p_hydro, 0.8, 5.2) - self.filter_dp
        
        # Apply oil leak degradation (pressure collapse and starvation)
        p_target = p_nominal * (1.0 - 0.75 * oil_leak_severity)
        if oil_leak_severity > 0.5:
            # Cavitation / aeration drops pressure sharply
            p_target = max(p_target * 0.6, 0.4)
        
        # First-order pressure sensor response (unconditionally stable exponential filter)
        tau_p = 0.5
        alpha = 1.0 - np.exp(-dt / tau_p)
        self.p_oil += (p_target - self.p_oil) * alpha
        self.p_oil = max(self.p_oil, 0.1)
        
        # Thermal balance of oil
        # Heat input: Viscous shear work in bearings + heat conducted from cylinder heads
        w_shear = 1200.0 * (rpm / 5000.0) ** 1.8 * (mu_pa_s / 0.015)
        q_from_cyl = 35.0 * (cht_mean_c - self.t_oil) # Conduction from cylinder skirt & crankcase
        
        # Heat output: Oil cooler heat dissipation
        # Ram air cooling scaling
        cooler_effectiveness = self.h_cooler * (1.0 + 0.02 * tas_mps)
        q_cooler = cooler_effectiveness * max(self.t_oil - ambient_temp_c, 0.0)
        
        # If oil volume is lost due to leak, thermal mass decreases -> faster overheating
        effective_oil_mass = max(self.oil_mass * (1.0 - 0.6 * oil_leak_severity), 1.2)
        
        d_toil = (w_shear + q_from_cyl - q_cooler) / (effective_oil_mass * self.c_p_oil)
        self.t_oil += d_toil * dt
        self.t_oil = np.clip(self.t_oil, ambient_temp_c, 160.0)
        
        return {
            "oil_pressure_bar": float(self.p_oil),
            "oil_temp_c": float(self.t_oil),
            "oil_viscosity_cst": float(nu_cst)
        }
