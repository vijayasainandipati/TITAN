"""
TITAN Physics Models — Thermal Engine
Coupled lumped-parameter differential equations for 4-cylinder aero-piston engine:
- Cylinder Head Temperatures (CHT 1..4)
- Exhaust Gas Temperatures (EGT 1..4)
- Coolant Temperature with ram-air radiator heat rejection
"""

import numpy as np
from typing import Dict, Tuple, Optional


class ThermalPhysicsModel:
    def __init__(self,
                 m_cyl_cp: float = 1800.0,       # J/K effective thermal capacitance per cylinder
                 m_cool_cp: float = 6500.0,      # J/K effective thermal capacitance coolant loop
                 h_cool_area: float = 48.0,      # W/K cylinder-to-coolant heat transfer
                 h_air_fin: float = 12.0,        # W/K cylinder-to-ambient fin convection
                 rad_effectiveness: float = 0.72,# Radiator heat exchanger effectiveness
                 rad_area_duct: float = 0.045,   # m^2 radiator duct area
                 lhv_fuel: float = 43.5e6,       # J/kg Lower Heating Value of Avgas 100LL
                 eta_thermal_base: float = 0.31, # Indicated thermal efficiency
                 param_jitter: float = 1.0):     # Engine tolerance multiplier
        
        # Apply engine-instance manufacturing tolerance jitter
        self.m_cyl_cp = m_cyl_cp * param_jitter
        self.m_cool_cp = m_cool_cp * param_jitter
        self.h_cool_area = h_cool_area * param_jitter
        self.h_air_fin = h_air_fin * param_jitter
        self.rad_effectiveness = rad_effectiveness
        self.rad_area_duct = rad_area_duct
        self.lhv_fuel = lhv_fuel
        self.eta_thermal_base = eta_thermal_base
        
        # State vector: [CHT1, CHT2, CHT3, CHT4, T_coolant, EGT1, EGT2, EGT3, EGT4] in Celsius
        self.state = np.array([85.0, 85.0, 85.0, 85.0, 75.0, 650.0, 650.0, 650.0, 650.0], dtype=float)

    def reset(self, ambient_temp_c: float = 20.0):
        """Reset state to ambient equilibrium."""
        self.state = np.array([
            ambient_temp_c, ambient_temp_c, ambient_temp_c, ambient_temp_c,
            ambient_temp_c, ambient_temp_c, ambient_temp_c, ambient_temp_c, ambient_temp_c
        ], dtype=float)

    def air_density_isa(self, altitude_ft: float) -> float:
        """Standard atmosphere density at altitude (kg/m^3)."""
        alt_m = altitude_ft * 0.3048
        t_isa = 288.15 - 0.0065 * alt_m
        p_isa = 101325.0 * (t_isa / 288.15) ** 5.2561
        rho = p_isa / (287.05 * max(t_isa, 180.0))
        return max(rho, 0.1)

    def compute_fuel_flow(self, rpm: float, map_bar: float, throttle_pct: float) -> float:
        """Estimated fuel mass flow rate (kg/s) for 1.35L displacement."""
        # V_disp = 1.352e-3 m^3, 4-stroke -> 2 revs/cycle
        v_disp = 1.352e-3
        eta_vol = 0.82 + 0.10 * (map_bar - 1.0)
        rho_charge = map_bar * 1e5 / (287.05 * 310.0) # Approx manifold charge density
        air_mass_flow = (v_disp / 2.0) * (rpm / 60.0) * rho_charge * eta_vol
        air_fuel_ratio = 13.5 # Slightly rich for cooling under climb/cruise
        fuel_flow = air_mass_flow / air_fuel_ratio
        return max(fuel_flow, 0.0005)

    def step(self,
             dt: float,
             rpm: float,
             map_bar: float,
             throttle_pct: float,
             tas_kts: float,
             altitude_ft: float,
             ambient_temp_c: float,
             cooling_degradation_factor: float = 1.0,
             misfire_cylinder: Optional[int] = None) -> Dict[str, float]:
        """
        Advances the thermal state by dt seconds.
        cooling_degradation_factor: < 1.0 indicates clogged radiator or degraded water pump.
        misfire_cylinder: 1..4 cylinder index experiencing misfire (reduces combustion heat).
        """
        tas_mps = max(tas_kts * 0.514444, 5.0) # Min 5 m/s prop blast
        rho_air = self.air_density_isa(altitude_ft)
        
        fuel_flow_total = self.compute_fuel_flow(rpm, map_bar, throttle_pct)
        fuel_flow_cyl = fuel_flow_total / 4.0
        
        # Ram air cooling through radiator
        m_dot_rad = rho_air * self.rad_area_duct * tas_mps * 0.85
        cp_air = 1005.0 # J/(kg*K)
        q_rad = m_dot_rad * cp_air * self.rad_effectiveness * max(self.state[4] - ambient_temp_c, 0.0)
        q_rad *= cooling_degradation_factor
        
        # Cylinder head dynamics
        q_cool_total = 0.0
        for i in range(4):
            cyl_num = i + 1
            is_misfire = (misfire_cylinder == cyl_num)
            
            # Heat generation in cylinder
            if is_misfire:
                q_comb = fuel_flow_cyl * self.lhv_fuel * 0.05 # Unburnt fuel carries minimal heat
            else:
                q_comb = fuel_flow_cyl * self.lhv_fuel * (1.0 - self.eta_thermal_base) * 0.28 # ~28% heat to head
            
            # Heat rejection to coolant and ambient fin convection
            q_to_cool = self.h_cool_area * (self.state[i] - self.state[4])
            q_to_air = self.h_air_fin * (self.state[i] - ambient_temp_c) * (1.0 + 0.015 * tas_mps)
            
            q_cool_total += q_to_cool
            
            # d(CHT_i)/dt
            d_cht = (q_comb - q_to_cool - q_to_air) / self.m_cyl_cp
            self.state[i] += d_cht * dt
            self.state[i] = np.clip(self.state[i], ambient_temp_c, 240.0) # Physical bounds
            
            # EGT dynamic tracking (fast first-order lag towards combustion temperature)
            if is_misfire:
                target_egt = ambient_temp_c + 80.0 # Rapid cooling on misfire
            else:
                # EGT scales with power setting, MAP, and throttle
                power_ratio = (rpm / 5500.0) * (map_bar / 1.15)
                target_egt = 450.0 + 380.0 * power_ratio + (ambient_temp_c - 15.0) * 0.5
            
            egt_idx = 5 + i
            tau_egt = 1.8 # Fast sensor response
            alpha_egt = 1.0 - np.exp(-dt / tau_egt)
            self.state[egt_idx] += (target_egt - self.state[egt_idx]) * alpha_egt
        
        # Coolant loop dynamics: d(T_cool)/dt = (Q_cool_in - Q_rad_out) / m_cool_cp
        d_tcool = (q_cool_total - q_rad) / self.m_cool_cp
        self.state[4] += d_tcool * dt
        self.state[4] = np.clip(self.state[4], ambient_temp_c, 130.0)
        
        return {
            "cht_1_c": float(self.state[0]),
            "cht_2_c": float(self.state[1]),
            "cht_3_c": float(self.state[2]),
            "cht_4_c": float(self.state[3]),
            "cht_mean_c": float(np.mean(self.state[0:4])),
            "coolant_temp_c": float(self.state[4]),
            "egt_1_c": float(self.state[5]),
            "egt_2_c": float(self.state[6]),
            "egt_3_c": float(self.state[7]),
            "egt_4_c": float(self.state[8]),
            "egt_mean_c": float(np.mean(self.state[5:9])),
            "fuel_flow_lph": float(fuel_flow_total * 3600.0 / 0.72) # liters per hour (density ~0.72 kg/L)
        }
