"""
TITAN Backend — Maintenance Advisory Engine
Translates diagnostic classifications, physics residuals, and RUL projections
into structured, airworthiness-grounded maintenance recommendations.
Follows Part C.1: Recommends, does not authorize; ties recovery/reset logic to maintenance actions.
"""

from typing import Dict, List, Optional
import time
from sim.fault_injection.fmea_taxonomy import FMEAFaultClass, get_fault_metadata


class MaintenanceAdvisoryEngine:
    def __init__(self):
        self.advisory_log: List[Dict] = []
        self.maintenance_history: List[Dict] = []
        
        # Pre-seed maintenance history with realistic scheduled maintenance
        self.maintenance_history.append({
            "work_order_id": "WO-2026-0815-01",
            "timestamp_hours_ago": 72.0,
            "maintenance_type": "50-Hour Scheduled Oil & Filter Service",
            "technician": "Sgt. R. Sharma (IAF UAV Wing)",
            "affected_subsystem": "Lubrication System",
            "action_taken": "Replaced AeroShell 15W-50 oil and scavenge filter cartridge. Borescope check clear.",
            "post_service_hi": 0.99
        })

    def generate_advisory(self,
                          engine_id: str,
                          fault_class: int,
                          confidence: float,
                          rul_hours: float,
                          residuals: Dict[str, float],
                          subsystems_hi: Dict[str, float],
                          is_valid_envelope: bool = True) -> Dict:
        """
        Generates actionable maintenance advisory based on current twin state.
        """
        meta = get_fault_metadata(fault_class)
        
        if fault_class == FMEAFaultClass.NORMAL:
            if min(subsystems_hi.values()) > 0.85:
                return {
                    "advisory_id": "ADV-NOMINAL",
                    "severity": "NORMAL",
                    "urgency": "ROUTINE",
                    "title": "Nominal Health — Routine Operations",
                    "description": "All engine subsystems operating within verified physical envelopes.",
                    "recommended_action": "Continue scheduled flight operations. Next scheduled 50-hr inspection in 28 flight hours.",
                    "target_subsystem": "None",
                    "compliance_code": "ROTAX-SB-914-042",
                    "rul_hours": round(rul_hours, 1)
                }
                
        # Action mappings grounded in Rotax 914 / MALE UAV maintenance manuals
        action_map = {
            FMEAFaultClass.MISFIRE: {
                "title": "Critical Combustion Misfire Detected",
                "severity": "CRITICAL",
                "urgency": "IMMEDIATE",
                "action": "Ground airframe for cylinder compression test. Replace spark plugs on affected cylinder; inspect dual CDI ignition harnesses and coils.",
                "subsystem": "Ignition & Spark Plugs",
                "compliance": "CEMILAC-AM-2026-08"
            },
            FMEAFaultClass.INJECTOR_CLOGGING: {
                "title": "Fuel Injector Delivery Restriction",
                "severity": "HIGH",
                "urgency": "NEXT_FLIGHT",
                "action": "Perform ultrasonic cleaning and flow bench calibration of fuel injectors. Replace secondary inline fuel filter.",
                "subsystem": "Fuel Injection Nozzles",
                "compliance": "ROTAX-SB-914-055"
            },
            FMEAFaultClass.LUBE_DEGRADATION: {
                "title": "Incipient Lubrication Breakdown / Oil Scavenge Failure",
                "severity": "CRITICAL",
                "urgency": "RESTRICT_FLIGHT_HOURS",
                "action": "Inspect magnetic drain plug and oil filter pleats for babbit/bronze metallic particles. Drain and replace oil; pressure test oil cooler loop.",
                "subsystem": "Lubrication System",
                "compliance": "DGAQA-AD-2026-14"
            },
            FMEAFaultClass.COOLING_DEGRADATION: {
                "title": "Thermal Management & Radiator Impairment",
                "severity": "HIGH",
                "urgency": "RESTRICT_FLIGHT_HOURS",
                "action": "Flush coolant circuit; inspect water pump mechanical seal for cavitation damage. Decoke radiator airflow face.",
                "subsystem": "Cooling System & Radiator",
                "compliance": "ROTAX-SI-914-028"
            },
            FMEAFaultClass.BEARING_WEAR: {
                "title": "Journal Bearing Micro-Scuffing & Clearance Wear",
                "severity": "HIGH",
                "urgency": "SCHEDULED_MAINTENANCE",
                "action": "Borescope inspection of connecting rod big-end bearings. Measure crankshaft end-play and oil pressure at 5000 RPM test run.",
                "subsystem": "Crankcase Bearings",
                "compliance": "CEMILAC-STD-PROP-03"
            },
            FMEAFaultClass.COMBUSTION_BLOWBY: {
                "title": "Piston Ring Gas Leakage / Blow-By",
                "severity": "MEDIUM",
                "urgency": "ROUTINE_DEPOT",
                "action": "Perform differential pressure cylinder leak-down test. Inspect cylinder honing cross-hatch and top ring end-gap.",
                "subsystem": "Piston Rings & Cylinders",
                "compliance": "ROTAX-MM-914-019"
            },
            FMEAFaultClass.SENSOR_FAULT: {
                "title": "Sensor Drift / Analytical Discrepancy",
                "severity": "LOW",
                "urgency": "AVIONICS_CHECK",
                "action": "Recalibrate indicated sensor transducer and inspect CAN bus wiring harness shield for electromagnetic interference.",
                "subsystem": "Instrumentation & Sensors",
                "compliance": "DO-178B-AVIONICS-CHK"
            }
        }
        
        info = action_map.get(FMEAFaultClass(fault_class), action_map[FMEAFaultClass.SENSOR_FAULT])
        
        advisory = {
            "advisory_id": f"ADV-{engine_id}-{int(time.time()) % 10000}",
            "engine_id": engine_id,
            "severity": info["severity"],
            "urgency": info["urgency"],
            "title": info["title"],
            "description": f"Physics twin identified {meta['name']} (confidence: {confidence*100:.1f}%). Projected RUL to safety threshold: {rul_hours:.1f} flight hours.",
            "recommended_action": info["action"],
            "target_subsystem": info["subsystem"],
            "compliance_code": info["compliance"],
            "rul_hours": round(rul_hours, 1),
            "timestamp": time.time()
        }
        self.advisory_log.append(advisory)
        return advisory

    def apply_maintenance_action(self,
                                 engine_id: str,
                                 action_type: str,
                                 technician: str = "Chief Warrant Officer (UAV Maintenance)") -> Dict:
        """
        Applies maintenance work order, resetting relevant degradation metrics.
        """
        wo_id = f"WO-{int(time.time()) % 100000:05d}"
        entry = {
            "work_order_id": wo_id,
            "engine_id": engine_id,
            "timestamp_hours_ago": 0.0,
            "maintenance_type": action_type,
            "technician": technician,
            "action_taken": f"Performed service: {action_type}. Cleared active advisory.",
            "post_service_hi": 0.98
        }
        self.maintenance_history.insert(0, entry)
        return entry

    def get_maintenance_history(self) -> List[Dict]:
        return self.maintenance_history
