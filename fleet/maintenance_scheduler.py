"""
TITAN Fleet Maintenance Scheduler
Coordinates fleet-wide maintenance priority queue and optimizes depot bay allocations.
Matches engine degradation states and remaining useful life (RUL) against tactical mission profiles.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from .agent_uplink import CompressedHealthSummary


@dataclass
class MaintenanceQueueItem:
    priority_rank: int
    engine_id: str
    engine_name: str
    urgency_score: float  # 0 to 100
    urgency_tier: str     # IMMEDIATE_GROUND, CRITICAL_DEPOT, ELEVATED_INSPECT, ROUTINE
    hi_engine: float
    rul_hours: float
    tactical_status: str
    recommended_action: str
    estimated_downtime_hours: float
    depot_bay_assigned: Optional[str]
    assigned_mission_recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FleetMaintenanceScheduler:
    """
    Fleet Ground Station Maintenance Scheduler.
    Allocates depot slots and matches assets to mission endurance requirements.
    """
    def __init__(self, max_depot_bays: int = 2):
        self.max_depot_bays = max_depot_bays

    def generate_schedule(self, uplinks: List[CompressedHealthSummary]) -> Dict[str, Any]:
        if not uplinks:
            return {
                "queue": [],
                "active_depot_occupancy": 0,
                "total_depot_bays": self.max_depot_bays,
                "mission_readiness_summary": {}
            }

        queue_candidates = []
        for u in uplinks:
            # Urgency score calculation
            status_weight = {"NO-GO": 3.5, "CAUTION": 1.8, "GO": 1.0}.get(u.tactical_status, 1.0)
            hi_penalty = (1.0 - u.hi_engine) * 50.0
            rul_penalty = max(0.0, (200.0 - u.rul_hours) / 200.0) * 35.0
            fault_penalty = 15.0 if u.predicted_fault != "NORMAL" else 0.0

            raw_urgency = (hi_penalty + rul_penalty + fault_penalty) * (status_weight / 2.0)
            urgency_score = min(100.0, max(0.0, round(raw_urgency, 1)))

            # Categorize urgency tier
            if u.tactical_status == "NO-GO" or urgency_score >= 70.0:
                urgency_tier = "IMMEDIATE_GROUND"
            elif u.tactical_status == "CAUTION" or urgency_score >= 45.0:
                urgency_tier = "CRITICAL_DEPOT"
            elif urgency_score >= 25.0:
                urgency_tier = "ELEVATED_INSPECT"
            else:
                urgency_tier = "ROUTINE"

            # Recommended action & downtime
            if u.predicted_fault == "MISFIRE" or "combustion" in u.hi_subsystems and u.hi_subsystems["combustion"] < 0.85:
                rec_action = "Ultrasonic injector clean & dual ignition spark plug replacement"
                downtime = 3.5
            elif u.predicted_fault == "LUBE_DEGRADATION" or "lubrication" in u.hi_subsystems and u.hi_subsystems["lubrication"] < 0.85:
                rec_action = "AeroShell 15W-50 oil flush, filter replace & oil cooler ultrasonic backwash"
                downtime = 2.5
            elif u.predicted_fault == "COOLING_DEGRADATION" or "thermal" in u.hi_subsystems and u.hi_subsystems["thermal"] < 0.85:
                rec_action = "Radiator matrix de-calcification, waterless coolant purge & leak test"
                downtime = 4.0
            elif u.predicted_fault == "BEARING_WEAR" or "mechanical" in u.hi_subsystems and u.hi_subsystems["mechanical"] < 0.85:
                rec_action = "Crankshaft journal micrometer check & magnetic chip detector particle count"
                downtime = 8.0
            elif u.sensor_fault_detected:
                rec_action = "Calibrate thermocouple harness & replace erratic transducer probe"
                downtime = 1.5
            else:
                rec_action = "Pre-flight walkaround, oil level verification & baseline run-up"
                downtime = 0.5

            # Mission endurance matching recommendation
            if u.tactical_status == "NO-GO" or u.rul_hours < 40.0:
                mission_rec = "DO NOT FLY — Induction into Depot Maintenance"
            elif u.rul_hours >= 180.0 and u.hi_engine >= 0.95:
                mission_rec = "Prime Asset: 18h Long-Endurance Strategic ISR"
            elif u.rul_hours >= 110.0:
                mission_rec = "Standard Asset: 10h Tactical Reconnaissance / High-Altitude Patrol"
            else:
                mission_rec = "Restricted Asset: 2h Short-Perimeter Sortie Only"

            queue_candidates.append({
                "engine_id": u.engine_id,
                "engine_name": u.engine_name,
                "urgency_score": urgency_score,
                "urgency_tier": urgency_tier,
                "hi_engine": u.hi_engine,
                "rul_hours": u.rul_hours,
                "tactical_status": u.tactical_status,
                "recommended_action": rec_action,
                "estimated_downtime_hours": downtime,
                "assigned_mission_recommendation": mission_rec
            })

        # Sort queue by highest urgency score
        queue_candidates.sort(key=lambda x: x["urgency_score"], reverse=True)

        # Assign depot bays to top candidates requiring depot attention
        assigned_items: List[MaintenanceQueueItem] = []
        depots_used = 0
        for rank, c in enumerate(queue_candidates, start=1):
            bay_name = None
            if c["urgency_tier"] in ["IMMEDIATE_GROUND", "CRITICAL_DEPOT"] and depots_used < self.max_depot_bays:
                depots_used += 1
                bay_name = f"Depot Bay {depots_used} (Primary Hangar)"

            assigned_items.append(
                MaintenanceQueueItem(
                    priority_rank=rank,
                    engine_id=c["engine_id"],
                    engine_name=c["engine_name"],
                    urgency_score=c["urgency_score"],
                    urgency_tier=c["urgency_tier"],
                    hi_engine=c["hi_engine"],
                    rul_hours=c["rul_hours"],
                    tactical_status=c["tactical_status"],
                    recommended_action=c["recommended_action"],
                    estimated_downtime_hours=c["estimated_downtime_hours"],
                    depot_bay_assigned=bay_name,
                    assigned_mission_recommendation=c["assigned_mission_recommendation"]
                )
            )

        # Tactical mission readiness counts
        prime_count = sum(1 for item in assigned_items if "18h Long-Endurance" in item.assigned_mission_recommendation)
        standard_count = sum(1 for item in assigned_items if "10h Tactical" in item.assigned_mission_recommendation)
        restricted_count = sum(1 for item in assigned_items if "2h Short-Perimeter" in item.assigned_mission_recommendation)
        grounded_count = sum(1 for item in assigned_items if "DO NOT FLY" in item.assigned_mission_recommendation)

        return {
            "queue": [item.to_dict() for item in assigned_items],
            "active_depot_occupancy": depots_used,
            "total_depot_bays": self.max_depot_bays,
            "mission_allocation_breakdown": {
                "strategic_long_endurance_assets": prime_count,
                "tactical_recon_assets": standard_count,
                "restricted_short_sortie_assets": restricted_count,
                "grounded_depot_assets": grounded_count
            }
        }
