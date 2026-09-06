"""
TITAN FMEA Fault Taxonomy & Classification Standards
Grounding 8 diagnostic categories for MALE-UAV aero-piston powerplants:
0: NORMAL
1: MISFIRE
2: INJECTOR_CLOGGING
3: LUBE_DEGRADATION
4: COOLING_DEGRADATION
5: BEARING_WEAR
6: COMBUSTION_BLOWBY
7: SENSOR_FAULT
"""

from enum import IntEnum
from typing import Dict, List


class FMEAFaultClass(IntEnum):
    NORMAL = 0
    MISFIRE = 1
    INJECTOR_CLOGGING = 2
    LUBE_DEGRADATION = 3
    COOLING_DEGRADATION = 4
    BEARING_WEAR = 5
    COMBUSTION_BLOWBY = 6
    SENSOR_FAULT = 7


FMEA_METADATA: Dict[FMEAFaultClass, Dict] = {
    FMEAFaultClass.NORMAL: {
        "name": "Normal Nominal Operation",
        "description": "All engine systems and thermodynamic observables operating within nominal tolerances.",
        "affected_subsystem": "None",
        "primary_symptoms": [],
        "characteristic_timescale": "N/A",
        "criticality": "LOW"
    },
    FMEAFaultClass.MISFIRE: {
        "name": "Ignition Misfire",
        "description": "Spark ignition loss or intermittent firing in cylinder 1..4, unburnt charge expelled.",
        "affected_subsystem": "Combustion / Ignition",
        "primary_symptoms": ["Drop in affected cylinder EGT", "Sub-harmonic 0.5X vibration spike", "Slight CHT reduction"],
        "characteristic_timescale": "Seconds (Transient to Fast)",
        "criticality": "HIGH"
    },
    FMEAFaultClass.INJECTOR_CLOGGING: {
        "name": "Fuel Injector Restriction",
        "description": "Partial nozzle clogging leading to lean fuel-air mixture in affected cylinder.",
        "affected_subsystem": "Fuel / Injection",
        "primary_symptoms": ["Elevated EGT in affected cylinder", "Mild CHT elevation", "Power deficit at high MAP"],
        "characteristic_timescale": "Minutes to Hours",
        "criticality": "MEDIUM"
    },
    FMEAFaultClass.LUBE_DEGRADATION: {
        "name": "Lubrication Breakdown / Oil Loss",
        "description": "Oil gallery leakage, viscosity degradation, or scavenge pump aeration.",
        "affected_subsystem": "Lubrication",
        "primary_symptoms": ["Declining oil pressure especially at high oil temp", "Oil temperature elevation", "Viscous friction rise"],
        "characteristic_timescale": "Hours (Incipient to Accelerated)",
        "criticality": "CRITICAL"
    },
    FMEAFaultClass.COOLING_DEGRADATION: {
        "name": "Cooling System Impairment",
        "description": "Radiator core fouling, coolant pump cavitation, or thermostat restriction.",
        "affected_subsystem": "Cooling / Thermal",
        "primary_symptoms": ["Coolant temperature runaway", "All-cylinder CHT elevation", "Loss of ram-air cooling margin"],
        "characteristic_timescale": "Minutes to Hours",
        "criticality": "CRITICAL"
    },
    FMEAFaultClass.BEARING_WEAR: {
        "name": "Connecting Rod / Main Bearing Wear",
        "description": "Journal bearing babbit spalling, increased radial clearance, micro-scuffing.",
        "affected_subsystem": "Mechanical",
        "primary_symptoms": ["1X and 2X vibration amplitude rise", "Oil pressure drop at idle/low RPM", "High-frequency distress noise"],
        "characteristic_timescale": "Tens of Hours",
        "criticality": "HIGH"
    },
    FMEAFaultClass.COMBUSTION_BLOWBY: {
        "name": "Piston Ring Blow-By / Sealing Loss",
        "description": "Compression ring groove sticking or wear, combustion gases blow into crankcase.",
        "affected_subsystem": "Power Cylinder / Crankcase",
        "primary_symptoms": ["Elevated CHT", "Rapid oil blackening / thermal degradation", "High crankcase pressure pulses"],
        "characteristic_timescale": "Hours to Tens of Hours",
        "criticality": "MEDIUM"
    },
    FMEAFaultClass.SENSOR_FAULT: {
        "name": "Sensor Drift / Dropout / Bias",
        "description": "Thermocouple calibration drift, pressure transducer bias, or signal freeze.",
        "affected_subsystem": "Instrumentation / Avionics",
        "primary_symptoms": ["Isolated channel residual without thermodynamic cross-coupling", "Violates sensor slew rate"],
        "characteristic_timescale": "Instantaneous to Slow Drift",
        "criticality": "LOW-MEDIUM"
    }
}


def get_fault_name(class_id: int) -> str:
    try:
        return FMEA_METADATA[FMEAFaultClass(class_id)]["name"]
    except (ValueError, KeyError):
        return "UNKNOWN_FAULT"


def get_fault_metadata(class_id: int) -> Dict:
    return FMEA_METADATA.get(FMEAFaultClass(class_id), FMEA_METADATA[FMEAFaultClass.NORMAL])
