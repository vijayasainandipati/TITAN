"""
TITAN Full Model — Temporal Multi-Scale Attention Backbone
Shared hierarchical feature representation mapping cycle features,
physics residuals, and mission phase context into rich latent states.
"""

import torch
import torch.nn as nn
from typing import Dict, Tuple


class TemporalAttentionBackbone(nn.Module):
    def __init__(self,
                 feature_dim: int = 24,    # Combined cycle features and residuals
                 phase_dim: int = 8,       # Phase embedding dimension
                 hidden_dim: int = 96,
                 num_heads: int = 4,
                 num_layers: int = 2):
        super().__init__()
        
        self.phase_embed = nn.Embedding(7, phase_dim) # 7 flight phases
        in_dim = feature_dim + phase_dim
        
        self.input_proj = nn.Linear(in_dim, hidden_dim)
        
        # Multi-layer Bidirectional GRU for local temporal dependencies
        self.bi_gru = nn.GRU(
            input_size=hidden_dim,
            hidden_size=hidden_dim // 2,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=0.15
        )
        
        # Multi-head Self-Attention
        self.attn = nn.MultiheadAttention(
            embed_dim=hidden_dim,
            num_heads=num_heads,
            batch_first=True,
            dropout=0.1
        )
        self.layer_norm = nn.LayerNorm(hidden_dim)

    def forward(self,
                x_features: torch.Tensor,
                phase_ids: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        x_features: (batch_size, seq_len, feature_dim)
        phase_ids: (batch_size, seq_len)
        Returns:
            latent_representation: (batch_size, hidden_dim)
            attn_weights: (batch_size, seq_len, seq_len)
        """
        phase_emb = self.phase_embed(phase_ids)
        x_fused = torch.cat([x_features, phase_emb], dim=-1)
        
        h_proj = self.input_proj(x_fused)
        gru_out, _ = self.bi_gru(h_proj)
        
        # Self-attention over temporal sequence
        attn_out, attn_weights = self.attn(gru_out, gru_out, gru_out)
        h_norm = self.layer_norm(gru_out + attn_out)
        
        # Aggregate across sequence using attention-weighted pooling
        pool_weights = torch.softmax(torch.mean(attn_weights, dim=1), dim=-1) # (batch, seq_len)
        latent_repr = torch.bmm(pool_weights.unsqueeze(1), h_norm).squeeze(1) # (batch, hidden_dim)
        
        return latent_repr, attn_weights
