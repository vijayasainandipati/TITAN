r"""
TITAN Ablation Model C — CNN-GRU on Physics Residuals
Variant C: 1D-CNN + GRU operating on physics residuals r_i(t) and \dot{r}_i(t),
validating the hypothesis that physics residuals improve early fault detection
over raw/statistical telemetry, but without mission-phase context.
"""

import torch
import torch.nn as nn
from typing import Dict


class CNNGRUResidualsBaseline(nn.Module):
    def __init__(self,
                 input_dim: int = 12, # Residuals r_i and rates d_r_i
                 hidden_dim: int = 64,
                 num_fault_classes: int = 8):
        super().__init__()
        
        self.conv1 = nn.Conv1d(in_channels=input_dim, out_channels=48, kernel_size=3, padding=1)
        self.relu = nn.ReLU()
        self.conv2 = nn.Conv1d(in_channels=48, out_channels=hidden_dim, kernel_size=3, padding=1)
        
        self.gru = nn.GRU(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=2,
            batch_first=True,
            dropout=0.15
        )
        
        # Heads
        self.fc_anomaly = nn.Linear(hidden_dim, 1)
        self.fc_fault = nn.Linear(hidden_dim, num_fault_classes)
        self.fc_rul = nn.Linear(hidden_dim, 1)
        self.fc_hi = nn.Linear(hidden_dim, 1)

    def forward(self, r_seq: torch.Tensor) -> Dict[str, torch.Tensor]:
        # r_seq: (batch_size, seq_len, input_dim)
        r_conv = r_seq.transpose(1, 2)
        h = self.relu(self.conv1(r_conv))
        h = self.relu(self.conv2(h))
        h_seq = h.transpose(1, 2)
        
        gru_out, _ = self.gru(h_seq)
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
