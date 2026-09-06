"""
TITAN Full Model — Tier 3 Degradation Trajectory & RUL Head
Predicts continuous multi-subsystem degradation and Remaining Useful Life (RUL)
with quantile bounds (q05, q50, q95) for calibrated confidence intervals (PICP).
"""

import torch
import torch.nn as nn
from typing import Dict


class DegradationRULHead(nn.Module):
    def __init__(self, hidden_dim: int = 96):
        super().__init__()
        
        # Subsystem degradation branch: predicts [lube_deg, bearing_wear, cooling_deg]
        self.fc_subsystems = nn.Sequential(
            nn.Linear(hidden_dim, 48),
            nn.ReLU(),
            nn.Linear(48, 3),
            nn.Sigmoid() # Degradation in [0.0, 1.0]
        )
        
        # RUL point estimate and quantiles (q05, q50, q95)
        self.fc_rul = nn.Sequential(
            nn.Linear(hidden_dim, 48),
            nn.ReLU(),
            nn.Linear(48, 3) # [q05, median, q95]
        )
        
        # Health Index projection
        self.fc_hi = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )

    def forward(self, latent_repr: torch.Tensor) -> Dict[str, torch.Tensor]:
        subsystems_deg = self.fc_subsystems(latent_repr)
        rul_raw = torch.relu(self.fc_rul(latent_repr)) # Flight hours non-negative
        
        # Ensure monotonic quantile ordering: q05 <= median <= q95
        q05 = rul_raw[:, 0]
        q50 = torch.max(q05, rul_raw[:, 1])
        q95 = torch.max(q50, rul_raw[:, 2])
        
        hi_pred = self.fc_hi(latent_repr).squeeze(-1)
        
        return {
            "rul_hours": q50,
            "rul_q05": q05,
            "rul_q95": q95,
            "health_index": hi_pred,
            "subsystem_degradations": {
                "lube": subsystems_deg[:, 0],
                "bearing": subsystems_deg[:, 1],
                "cooling": subsystems_deg[:, 2]
            }
        }
