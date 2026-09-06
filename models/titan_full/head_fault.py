"""
TITAN Full Model — Tier 2 FMEA Fault Classification Head
Multi-class classification head mapping latent representation
to the 8 FMEA categories (Normal, Misfire, Injector, Lube, Cooling, Bearing, Blowby, Sensor).
"""

import torch
import torch.nn as nn
from typing import Dict


class FaultClassificationHead(nn.Module):
    def __init__(self, hidden_dim: int = 96, num_fault_classes: int = 8):
        super().__init__()
        
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, num_fault_classes)
        )

    def forward(self, latent_repr: torch.Tensor) -> Dict[str, torch.Tensor]:
        logits = self.classifier(latent_repr)
        probs = torch.softmax(logits, dim=-1)
        conf, pred_class = torch.max(probs, dim=-1)
        
        return {
            "fault_logits": logits,
            "fault_probs": probs,
            "predicted_class": pred_class,
            "fault_confidence": conf
        }
