"""
TITAN Physics Models — Mechanical & Vibration Engine
Models 4-cylinder aero-piston dynamics, reciprocating imbalance, and harmonic vibration:
- 1X (Crankshaft/Propeller unbalance)
- 2X (Reciprocating mass unbalance)
- 4X (Combustion harmonic)
- 0.5X (Sub-harmonic / Single-cylinder misfire marker)
- Overall RMS, Peak, and Crest Factor acceleration in G's
"""

import numpy as np
from typing import Dict, Optional


class MechanicalPhysicsModel:
    def __init__(self,
                 engine_mass_kg: float = 78.0,        # Dry engine mass (Rotax 914 class)
                 nominal_imbalance_g_mm: float = 35.0,# Residual crankshaft imbalance
                 mount_damping_ratio: float = 0.12,   # Elastomeric engine mount damping
                 mount_natural_freq_hz: float = 24.0, # Mount isolator natural frequency
                 param_jitter: float = 1.0):          # Manufacturing jitter
        
        self.engine_mass = engine_mass_kg * param_jitter
        self.imbalance = nominal_imbalance_g_mm * param_jitter
        self.zeta = mount_damping_ratio
        self.fn = mount_natural_freq_hz
        self.omega_n = 2.0 * np.pi * self.fn

    def step(self,
             dt: float,
             rpm: float,
             throttle_pct: float,
             map_bar: float,
             bearing_wear_severity: float = 0.0,
             misfire_active: bool = False,
             blowby_active: bool = False) -> Dict[str, float]:
        """
        Computes the instantaneous vibration metrics for the current engine state.
        bearing_wear_severity: 0.0 to 1.0 (bearing play, surface distress).
        misfire_active: True if one or more cylinders are dropping combustion strokes.
        blowby_active: True if combustion gas leaking past piston rings.
        """
        f_shaft = max(rpm / 60.0, 10.0) # Fundamental rotational frequency in Hz (e.g. 5000 RPM -> 83.3 Hz)
        omega = 2.0 * np.pi * f_shaft
        
        # Transmissibility magnification factor across engine elastomeric mounts
        r = f_shaft / self.fn
        transmissibility = np.sqrt((1.0 + (2.0 * self.zeta * r) ** 2) / 
                                   (max((1.0 - r ** 2) ** 2 + (2.0 * self.zeta * r) ** 2, 0.01)))
        
        # 1X Unbalance acceleration: a_1x = r_imb * omega^2 * Transmissibility / 9.81 (in G's)
        # Baseline ~0.35 G at 5000 RPM
        a_1x_base = (self.imbalance * 1e-6 * omega ** 2 / (self.engine_mass * 9.81)) * transmissibility * 250.0
        # Bearing wear amplifies 1X unbalance and eccentricity
        a_1x = a_1x_base * (1.0 + 1.8 * bearing_wear_severity)
        
        # 2X Reciprocating inertia harmonic (predominant in flat-4 / inline-4 engines)
        # Scales strongly with RPM squared and throttle
        power_factor = (throttle_pct / 100.0) * (map_bar / 1.0)
        a_2x_base = 0.75 * ((rpm / 5000.0) ** 1.9) * (0.8 + 0.4 * power_factor)
        a_2x = a_2x_base * (1.0 + 2.2 * bearing_wear_severity)
        
        # 4X Combustion order harmonic (cylinder firing pulses)
        a_4x = 0.45 * ((rpm / 5000.0) ** 1.6) * (0.6 + 0.6 * power_factor)
        
        # 0.5X Sub-harmonic: Characteristic diagnostic signature of single-cylinder misfire
        if misfire_active:
            # Unbalanced combustion cycle fires every 2 revolutions -> sharp 0.5 order spike
            a_half = 1.45 * (rpm / 5000.0)
        else:
            a_half = 0.04 * (rpm / 5000.0) # Baseline trace residual
        
        # High-frequency bearing distress noise (spalling, metal contact)
        a_hf_noise = 0.15 + 1.60 * (bearing_wear_severity ** 1.5)
        if blowby_active:
            a_hf_noise += 0.35
            
        # Synthesize RMS vibration (Parseval's sum of harmonic powers + broadband floor)
        vib_rms = np.sqrt(a_1x ** 2 + a_2x ** 2 + a_4x ** 2 + a_half ** 2 + a_hf_noise ** 2)
        
        # Peak vibration and crest factor
        # Under misfire or severe bearing impact, crest factor spikes significantly
        crest_factor_base = 2.1
        if misfire_active:
            crest_factor = 3.6 + 0.5 * np.random.uniform(-0.1, 0.2)
        elif bearing_wear_severity > 0.4:
            crest_factor = 2.8 + 1.2 * bearing_wear_severity
        else:
            crest_factor = crest_factor_base + 0.2 * np.random.uniform(-0.1, 0.1)
            
        vib_peak = vib_rms * crest_factor
        
        return {
            "vibration_rms_g": float(np.clip(vib_rms, 0.1, 15.0)),
            "vibration_peak_g": float(np.clip(vib_peak, 0.2, 35.0)),
            "vibration_crest_factor": float(crest_factor),
            "vib_1x_g": float(a_1x),
            "vib_2x_g": float(a_2x),
            "vib_half_order_g": float(a_half)
        }
