"""
TITAN Fleet Aggregation Layer
Collects compressed health summaries from edge UAV agents and produces
tactical swarm-level readiness rollups, health distributions, and subsystem vulnerability rankings.
"""

from typing import List, Dict, Any, Optional
import numpy as np
from .agent_uplink import CompressedHealthSummary


class FleetAggregationEngine:
    """
    Fleet Ground Station aggregation processor.
    Provides single-glance swarm status, risk distributions, and fleet-wide subsystem health.
    """
    def __init__(self):
        pass

    def aggregate_fleet(self, uplinks: List[CompressedHealthSummary]) -> Dict[str, Any]:
        if not uplinks:
            return {
                "total_uavs": 0,
                "operational_count": 0,
                "degraded_count": 0,
                "critical_count": 0,
                "fleet_readiness_pct": 0.0,
                "average_hi_engine": 0.0,
                "min_rul_hours": 0.0,
                "lowest_rul_engine": "N/A",
                "subsystem_fleet_averages": {},
                "vulnerable_subsystems": [],
                "agent_summaries": []
            }

        total_uavs = len(uplinks)
        go_count = sum(1 for u in uplinks if u.tactical_status == "GO")
        caution_count = sum(1 for u in uplinks if u.tactical_status == "CAUTION")
        nogo_count = sum(1 for u in uplinks if u.tactical_status == "NO-GO")
        readiness_pct = round((go_count + 0.5 * caution_count) / total_uavs * 100.0, 1)

        hi_values = [u.hi_engine for u in uplinks]
        avg_hi = round(float(np.mean(hi_values)), 3)

        rul_values = [u.rul_hours for u in uplinks]
        min_rul = round(float(np.min(rul_values)), 1)
        lowest_rul_idx = int(np.argmin(rul_values))
        lowest_rul_engine = uplinks[lowest_rul_idx].engine_id

        # Subsystem averages
        subsystems = ["thermal", "lubrication", "mechanical", "combustion"]
        subsystem_avgs = {}
        for sub in subsystems:
            sub_scores = [u.hi_subsystems.get(sub, 1.0) for u in uplinks]
            subsystem_avgs[sub] = round(float(np.mean(sub_scores)), 3)

        # Sort subsystems by lowest average (highest vulnerability)
        vulnerable_subsystems = sorted(
            [{"subsystem": k, "average_hi": v, "degradation_pct": round((1.0 - v) * 100.0, 1)}
             for k, v in subsystem_avgs.items()],
            key=lambda x: x["average_hi"]
        )

        # Sort agents by urgency: NO-GO first, then CAUTION, then GO, then lowest RUL
        status_priority = {"NO-GO": 0, "CAUTION": 1, "GO": 2}
        sorted_summaries = sorted(
            [u.to_dict() for u in uplinks],
            key=lambda x: (status_priority.get(x["tactical_status"], 3), x["rul_hours"])
        )

        # Bandwidth savings calculation across the fleet
        total_raw_bytes = total_uavs * 6400 # 6.4 KB/s per UAV
        total_uplink_bytes = sum(u.payload_size_bytes for u in uplinks)
        bandwidth_saving_pct = round((total_raw_bytes - total_uplink_bytes) / total_raw_bytes * 100.0, 1)

        return {
            "total_uavs": total_uavs,
            "operational_count": go_count,
            "degraded_count": caution_count,
            "critical_count": nogo_count,
            "fleet_readiness_pct": readiness_pct,
            "average_hi_engine": avg_hi,
            "min_rul_hours": min_rul,
            "lowest_rul_engine": lowest_rul_engine,
            "subsystem_fleet_averages": subsystem_avgs,
            "vulnerable_subsystems": vulnerable_subsystems,
            "bandwidth_metrics": {
                "total_raw_telemetry_bytes_per_sec": total_raw_bytes,
                "fleet_uplink_payload_bytes": total_uplink_bytes,
                "bandwidth_saved_pct": bandwidth_saving_pct,
                "data_locality_enforced": True
            },
            "agent_summaries": sorted_summaries
        }
