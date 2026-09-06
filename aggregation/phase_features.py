"""
TITAN Hierarchical Aggregation — Phase Features
Normalizes cycle features relative to nominal mission-phase regimes
and generates phase embeddings for context-aware model heads (PRD C.1 & Ablation D/E).
"""

import numpy as np
from typing import Dict, List
import pandas as pd


FLIGHT_PHASES: List[str] = [
    "TAXI", "TAKEOFF", "CLIMB", "CRUISE", "LOITER", "DESCENT", "LANDING"
]

PHASE_TO_ID: Dict[str, int] = {phase: i for i, phase in enumerate(FLIGHT_PHASES)}


class PhaseFeatureProcessor:
    def __init__(self):
        # Nominal baseline operating setpoints per flight phase
        self.phase_baselines = {
            "TAXI":     {"rpm": 1850.0, "map": 0.65, "cht": 90.0,  "oil_p": 2.2, "vib": 0.5},
            "TAKEOFF":  {"rpm": 5800.0, "map": 1.28, "cht": 125.0, "oil_p": 4.5, "vib": 1.8},
            "CLIMB":    {"rpm": 5400.0, "map": 1.18, "cht": 120.0, "oil_p": 4.2, "vib": 1.5},
            "CRUISE":   {"rpm": 4900.0, "map": 1.02, "cht": 115.0, "oil_p": 4.0, "vib": 1.3},
            "LOITER":   {"rpm": 4650.0, "map": 0.98, "cht": 112.0, "oil_p": 3.9, "vib": 1.2},
            "DESCENT":  {"rpm": 3400.0, "map": 0.72, "cht": 98.0,  "oil_p": 3.2, "vib": 0.9},
            "LANDING":  {"rpm": 2200.0, "map": 0.68, "cht": 92.0,  "oil_p": 2.5, "vib": 0.7}
        }

    def get_phase_id(self, phase_str: str) -> int:
        return PHASE_TO_ID.get(phase_str.upper(), PHASE_TO_ID["CRUISE"])

    def get_phase_one_hot(self, phase_str: str) -> np.ndarray:
        vec = np.zeros(len(FLIGHT_PHASES), dtype=np.float32)
        idx = self.get_phase_id(phase_str)
        vec[idx] = 1.0
        return vec

    def normalize_by_phase(self, features: Dict[str, float], phase_str: str) -> Dict[str, float]:
        """
        Normalizes primary observables against phase-specific nominal baselines.
        """
        phase_key = phase_str.upper() if phase_str.upper() in self.phase_baselines else "CRUISE"
        base = self.phase_baselines[phase_key]
        
        normalized = dict(features)
        
        # Delta from phase expected baseline
        if "rpm_mean" in features:
            normalized["rpm_phase_delta"] = features["rpm_mean"] - base["rpm"]
        if "oil_pressure_bar_mean" in features:
            normalized["oil_p_phase_delta"] = features["oil_pressure_bar_mean"] - base["oil_p"]
        if "vibration_rms_g_mean" in features:
            normalized["vib_phase_delta"] = features["vibration_rms_g_mean"] - base["vib"]
            
        normalized["phase_id"] = self.get_phase_id(phase_str)
        return normalized
