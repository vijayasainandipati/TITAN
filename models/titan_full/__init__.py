"""
TITAN Full Model — Unified Physics-Informed Digital Twin Neural Architecture
Combines:
- Temporal Attention Backbone
- Tier 1: Anomaly Detection Head
- Tier 2: FMEA Fault Classification Head
- Tier 3: Degradation & RUL Head (Risk-aligned loss)
- Tier 4a: Calibrated Uncertainty & Conformal OOD Manager
- Tier 4b: Physics Explainability & Residual Attribution
"""

import torch
import torch.nn as nn
from typing import Dict, Tuple

from .backbone import TemporalAttentionBackbone
from .head_anomaly import AnomalyDetectionHead
from .head_fault import FaultClassificationHead
from .head_degradation_rul import DegradationRULHead
from .confidence_ood import UncertaintyOODManager
from .explainability import PhysicalExplainabilityEngine


class TitanFullModel(nn.Module):
    def __init__(self,
                 feature_dim: int = 24, # Cycle features + physics residuals
                 phase_dim: int = 8,
                 hidden_dim: int = 96,
                 num_fault_classes: int = 8):
        super().__init__()
        
        self.backbone = TemporalAttentionBackbone(
            feature_dim=feature_dim,
            phase_dim=phase_dim,
            hidden_dim=hidden_dim
        )
        self.head_anomaly = AnomalyDetectionHead(hidden_dim=hidden_dim)
        self.head_fault = FaultClassificationHead(hidden_dim=hidden_dim, num_fault_classes=num_fault_classes)
        self.head_rul = DegradationRULHead(hidden_dim=hidden_dim)
        
        # Uncertainty and explainability components
        self.uncertainty_mgr = UncertaintyOODManager(residual_dim=6)
        self.explainability_engine = PhysicalExplainabilityEngine()

    def forward(self,
                x_features: torch.Tensor,
                phase_ids: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Full multi-tier forward pass.
        """
        latent_repr, attn_weights = self.backbone(x_features, phase_ids)
        
        anomaly_out = self.head_anomaly(latent_repr)
        fault_out = self.head_fault(latent_repr)
        rul_out = self.head_rul(latent_repr)
        
        return {
            "latent_repr": latent_repr,
            "attn_weights": attn_weights,
            # Tier 1
            "anomaly_prob": anomaly_out["anomaly_prob"],
            "anomaly_score": anomaly_out["anomaly_score"],
            "kl_div": anomaly_out["kl_divergence"],
            # Tier 2
            "fault_logits": fault_out["fault_logits"],
            "fault_probs": fault_out["fault_probs"],
            "predicted_fault_class": fault_out["predicted_class"],
            "fault_confidence": fault_out["fault_confidence"],
            # Tier 3
            "rul_hours": rul_out["rul_hours"],
            "rul_q05": rul_out["rul_q05"],
            "rul_q95": rul_out["rul_q95"],
            "health_index": rul_out["health_index"],
            "subsystem_degradations": rul_out["subsystem_degradations"]
        }


__all__ = [
    "TitanFullModel",
    "TemporalAttentionBackbone",
    "AnomalyDetectionHead",
    "FaultClassificationHead",
    "DegradationRULHead",
    "UncertaintyOODManager",
    "PhysicalExplainabilityEngine"
]
