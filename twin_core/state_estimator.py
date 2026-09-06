"""
TITAN Digital Twin Core — Physics State Estimator
Virtual Engine Mirror computing nominal expected states:
[CHT_hat, EGT_hat, Coolant_hat, Oil_Press_hat, Oil_Temp_hat, Vibration_RMS_hat]
given operating conditions and atmospheric parameters.
Also monitors operational envelope bounds (PRD C.4).
"""

import numpy as np
from typing import Dict, Tuple
from sim.physics_models.thermal import ThermalPhysicsModel
from sim.physics_models.lubrication import LubricationPhysicsModel
from sim.physics_models.mechanical import MechanicalPhysicsModel


class DigitalTwinStateEstimator:
    def __init__(self,
                 nominal_rpm: float = 4800.0,
                 max_altitude_ft: float = 24500.0,
                 min_temp_c: float = -40.0,
                 max_temp_c: float = 48.0):
        
        # Nominal baseline physics models (un-degraded, un-corrupted)
        self.thermal_twin = ThermalPhysicsModel(param_jitter=1.0)
        self.lube_twin = LubricationPhysicsModel(param_jitter=1.0)
        self.mech_twin = MechanicalPhysicsModel(param_jitter=1.0)
        
        # Operational envelope limits
        self.max_alt = max_altitude_ft
        self.min_temp = min_temp_c
        self.max_temp = max_temp_c

    def reset(self, ambient_temp_c: float = 20.0):
        self.thermal_twin.reset(ambient_temp_c)
        self.lube_twin.reset(ambient_temp_c)

    def check_envelope(self, altitude_ft: float, ambient_temp_c: float, rpm: float) -> Tuple[bool, str]:
        """
        Validates whether operating conditions are within the physics model's verified domain.
        Returns (is_valid, envelope_status_message).
        """
        if altitude_ft > self.max_alt:
            return False, f"OUTSIDE VALIDATED ENVELOPE: Altitude {altitude_ft:.0f} ft exceeds verified ceiling ({self.max_alt:.0f} ft)"
        if ambient_temp_c < self.min_temp:
            return False, f"OUTSIDE VALIDATED ENVELOPE: Ambient {ambient_temp_c:.1f} C below calibrated low temp ({self.min_temp:.1f} C)"
        if ambient_temp_c > self.max_temp:
            return False, f"OUTSIDE VALIDATED ENVELOPE: Ambient {ambient_temp_c:.1f} C exceeds calibrated high temp ({self.max_temp:.1f} C)"
        if rpm > 6200.0:
            return False, f"OUTSIDE VALIDATED ENVELOPE: RPM {rpm:.0f} exceeds maximum certified limit (6200 RPM)"
            
        return True, "VALID_ENVELOPE"

    def estimate_expected_state(self,
                                dt: float,
                                rpm: float,
                                map_bar: float,
                                throttle_pct: float,
                                tas_kts: float,
                                altitude_ft: float,
                                ambient_temp_c: float) -> Dict:
        """
        Computes the physics-based expected uncorrupted engine state.
        """
        is_valid_envelope, envelope_msg = self.check_envelope(altitude_ft, ambient_temp_c, rpm)
        
        # Step nominal thermal twin (no degradation, no misfire)
        therm_expected = self.thermal_twin.step(
            dt=dt,
            rpm=rpm,
            map_bar=map_bar,
            throttle_pct=throttle_pct,
            tas_kts=tas_kts,
            altitude_ft=altitude_ft,
            ambient_temp_c=ambient_temp_c,
            cooling_degradation_factor=1.0,
            misfire_cylinder=None
        )
        
        # Step nominal lubrication twin (no bearing wear, no oil leak)
        lube_expected = self.lube_twin.step(
            dt=dt,
            rpm=rpm,
            cht_mean_c=therm_expected["cht_mean_c"],
            tas_kts=tas_kts,
            altitude_ft=altitude_ft,
            ambient_temp_c=ambient_temp_c,
            bearing_wear_multiplier=1.0,
            oil_leak_severity=0.0
        )
        
        # Step nominal mechanical twin (no bearing wear, no misfire)
        mech_expected = self.mech_twin.step(
            dt=dt,
            rpm=rpm,
            throttle_pct=throttle_pct,
            map_bar=map_bar,
            bearing_wear_severity=0.0,
            misfire_active=False,
            blowby_active=False
        )
        
        return {
            "expected_state": {
                "cht_1_c": therm_expected["cht_1_c"],
                "cht_2_c": therm_expected["cht_2_c"],
                "cht_3_c": therm_expected["cht_3_c"],
                "cht_4_c": therm_expected["cht_4_c"],
                "cht_mean_c": therm_expected["cht_mean_c"],
                "egt_1_c": therm_expected["egt_1_c"],
                "egt_2_c": therm_expected["egt_2_c"],
                "egt_3_c": therm_expected["egt_3_c"],
                "egt_4_c": therm_expected["egt_4_c"],
                "egt_mean_c": therm_expected["egt_mean_c"],
                "coolant_temp_c": therm_expected["coolant_temp_c"],
                "oil_pressure_bar": lube_expected["oil_pressure_bar"],
                "oil_temp_c": lube_expected["oil_temp_c"],
                "vibration_rms_g": mech_expected["vibration_rms_g"],
                "vibration_peak_g": mech_expected["vibration_peak_g"]
            },
            "is_valid_envelope": is_valid_envelope,
            "envelope_status": envelope_msg
        }
