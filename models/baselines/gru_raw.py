"""
TITAN Ablation Model A — GRU on Raw Telemetry
Baseline architecture: Direct multi-layer Gated Recurrent Unit (GRU)
operating on un-normalized raw sensor streams.
"""

import torch
import torch.nn as nn
from typing import Dict, Tuple


class GRURawBaseline(nn.Module):
    def __init__(self,
                 input_dim: int = 14, # Raw sensor channels
                 hidden_dim: int = 64,
                 num_layers: int = 2,
                 num_fault_classes: int = 8):
        super().__init__()
        self.gru = nn.GRU(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.15 if num_layers > 1 else 0.0
        )
        
        # Heads
        self.fc_anomaly = nn.Linear(hidden_dim, 1)        # Binary anomaly logit
        self.fc_fault = nn.Linear(hidden_dim, num_fault_classes) # FMEA fault logits
        self.fc_rul = nn.Linear(hidden_dim, 1)            # Continuous RUL estimate
        self.fc_hi = nn.Linear(hidden_dim, 1)             # Health index estimate

    def forward(self, x_seq: torch.Tensor) -> Dict[str, torch.Tensor]:
        # x_seq shape: (batch_size, seq_len, input_dim)
        gru_out, _ = self.gru(x_seq)
        last_hidden = gru_out[:, -1, :]
        
        anomaly_logit = self.fc_anomaly(last_hidden)
        fault_logits = self.fc_fault(last_hidden)
        rul_pred = torch.relu(self.fc_rul(last_hidden))
        hi_pred = torch.sigmoid(self.fc_hi(last_hidden))
        
        return {
            "anomaly_prob": torch.sigmoid(anomaly_logit),
            "fault_logits": fault_logits,
            "rul_hours": rul_pred.squeeze(-1),
            "health_index": hi_pred.squeeze(-1)
        }
