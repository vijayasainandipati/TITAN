"""
TITAN Fleet Ground Station Package
Two-tier multi-agent architecture for MALE-UAV propulsion health monitoring:
- agent_uplink: Bandwidth-optimized compressed health summary & telemetry isolation
- fleet_aggregation: Swarm-level readiness, health rollup, and subsystem rankings
- cross_engine_correlation: Multi-engine systemic anomaly & fault correlation detector
- maintenance_scheduler: Fleet-wide priority queue, depot allocation, and sortie assignment
- federated_coordinator: Edge-privacy federated learning interface stub (Future Scope)
"""

from .agent_uplink import AgentUplinkManager, CompressedHealthSummary
from .fleet_aggregation import FleetAggregationEngine
from .cross_engine_correlation import CrossEngineCorrelationEngine, SystemicAlert
from .maintenance_scheduler import FleetMaintenanceScheduler
from .federated_coordinator import FederatedCoordinatorStub

__all__ = [
    "AgentUplinkManager",
    "CompressedHealthSummary",
    "FleetAggregationEngine",
    "CrossEngineCorrelationEngine",
    "SystemicAlert",
    "FleetMaintenanceScheduler",
    "FederatedCoordinatorStub",
]
