"""
TITAN Full Model — Tier 1 Anomaly Detection Head
Reconstruction and latent deviation estimator detecting incipient departures
before explicit threshold limits are breached.
"""

import torch
import torch.nn as nn
from typing import Dict, Tuple


class AnomalyDetectionHead(nn.Module):
    def __init__(self, hidden_dim: int = 96, latent_dim: int = 16):
        super().__init__()
        
        # Encoder to latent bottleneck
        self.fc_mu = nn.Linear(hidden_dim, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim, latent_dim)
        
        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, hidden_dim)
        )
        
        # Classification logit
        self.fc_anomaly = nn.Linear(hidden_dim + 1, 1)

    def forward(self, latent_repr: torch.Tensor) -> Dict[str, torch.Tensor]:
        mu = self.fc_mu(latent_repr)
        logvar = self.fc_logvar(latent_repr)
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        z = mu + eps * std
        
        reconstructed = self.decoder(z)
        recon_error = torch.mean((latent_repr - reconstructed) ** 2, dim=-1, keepdim=True)
        
        # Combine latent representation with reconstruction error
        combined = torch.cat([latent_repr, recon_error], dim=-1)
        anomaly_logit = self.fc_anomaly(combined)
        
        # KL divergence: -0.5 * sum(1 + log(sigma^2) - mu^2 - sigma^2)
        kl_div = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp(), dim=-1)
        
        return {
            "anomaly_prob": torch.sigmoid(anomaly_logit).squeeze(-1),
            "anomaly_score": recon_error.squeeze(-1),
            "kl_divergence": kl_div
        }
