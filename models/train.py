"""
TITAN Unified Training & Model Pipeline
Trains all 5 Ablation variants (A, B, C, D, E) on multi-engine synthetic dataset
using Risk-Aligned Asymmetric Loss and Conformal Pinball Loss.
"""

import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple

from .baselines import (
    GRURawBaseline,
    CNNGRUFeaturesBaseline,
    CNNGRUResidualsBaseline,
    CNNGRUResidualsContextBaseline
)
from .titan_full import TitanFullModel
from .losses.risk_aligned_loss import RiskAlignedAsymmetricLoss, PinballLoss
from aggregation.phase_features import PhaseFeatureProcessor


class MultiEngineTelemetryDataset(Dataset):
    def __init__(self, df: pd.DataFrame, seq_len: int = 16):
        self.seq_len = seq_len
        self.phase_proc = PhaseFeatureProcessor()
        
        # Define channel subsets
        self.raw_cols = [
            "cht_1_c", "cht_2_c", "cht_3_c", "cht_4_c",
            "egt_1_c", "egt_2_c", "egt_3_c", "egt_4_c",
            "coolant_temp_c", "oil_pressure_bar", "oil_temp_c",
            "vibration_rms_g", "rpm", "map_bar"
        ]
        
        # Physics residuals (synthetic zero-centered proxy if not precomputed)
        self.residual_cols = [
            "r_cht_mean", "r_egt_mean", "r_coolant_temp",
            "r_oil_pressure", "r_oil_temp", "r_vibration_rms"
        ]
        
        # Ensure residual columns exist in df
        for r in self.residual_cols:
            if r not in df.columns:
                # Compute on the fly if needed
                df[r] = 0.0
                if "oil_pressure" in r:
                    df[r] = (df["oil_pressure_bar"] - 4.0) / 0.15
                elif "oil_temp" in r:
                    df[r] = (df["oil_temp_c"] - 85.0) / 1.5
                elif "coolant" in r:
                    df[r] = (df["coolant_temp_c"] - 80.0) / 1.2
                elif "vibration" in r:
                    df[r] = (df["vibration_rms_g"] - 1.2) / 0.10
                elif "cht" in r:
                    cht_mean = (df["cht_1_c"] + df["cht_2_c"] + df["cht_3_c"] + df["cht_4_c"]) / 4.0
                    df[r] = (cht_mean - 115.0) / 1.5
                elif "egt" in r:
                    egt_mean = (df["egt_1_c"] + df["egt_2_c"] + df["egt_3_c"] + df["egt_4_c"]) / 4.0
                    df[r] = (egt_mean - 740.0) / 8.0
                    
        # Residual rates
        self.res_rate_cols = [f"d_{r}" for r in self.residual_cols]
        for rc, r in zip(self.res_rate_cols, self.residual_cols):
            df[rc] = df[r].diff().fillna(0.0)
            
        # Extract numpy tensors
        self.raw_data = df[self.raw_cols].values.astype(np.float32)
        # Normalize raw data roughly
        self.raw_data = (self.raw_data - np.mean(self.raw_data, axis=0)) / (np.std(self.raw_data, axis=0) + 1e-4)
        
        # Feature engineered representation (mean + std + p2p rolling)
        df_feat = df[self.raw_cols].rolling(window=5, min_periods=1).mean()
        self.feat_data = np.concatenate([self.raw_data, df_feat.values.astype(np.float32)], axis=-1)
        
        # Residual data (residuals + rates = 12 dims)
        self.res_data = df[self.residual_cols + self.res_rate_cols].values.astype(np.float32)
        
        # Full TITAN features (raw + residuals = 26 dims)
        self.titan_features = np.concatenate([self.raw_data[:, :12], self.res_data], axis=-1)
        
        # Flight phase IDs
        self.phase_ids = np.array([self.phase_proc.get_phase_id(str(p)) for p in df["flight_phase"]], dtype=np.int64)
        
        # Targets
        self.gt_anomaly = df["gt_is_anomaly"].values.astype(np.float32)
        self.gt_fault = df["gt_fault_class"].values.astype(np.int64)
        self.gt_rul = df["gt_rul_hours"].values.astype(np.float32)
        self.gt_hi = df["gt_health_index"].values.astype(np.float32)
        
        self.n_samples = len(df) - seq_len + 1

    def __len__(self):
        return max(self.n_samples, 0)

    def __getitem__(self, idx):
        end = idx + self.seq_len
        return {
            "raw": torch.from_numpy(self.raw_data[idx:end]),
            "features": torch.from_numpy(self.feat_data[idx:end]),
            "residuals": torch.from_numpy(self.res_data[idx:end]),
            "titan_feats": torch.from_numpy(self.titan_features[idx:end]),
            "phase_ids": torch.from_numpy(self.phase_ids[idx:end]),
            "target_anomaly": torch.tensor(self.gt_anomaly[end - 1]),
            "target_fault": torch.tensor(self.gt_fault[end - 1]),
            "target_rul": torch.tensor(self.gt_rul[end - 1]),
            "target_hi": torch.tensor(self.gt_hi[end - 1])
        }


def train_ablation_model(variant: str,
                         dataloader: DataLoader,
                         num_epochs: int = 5,
                         lr: float = 1e-3,
                         device: str = "cpu") -> nn.Module:
    """
    Trains one of the 5 ablation variants (A, B, C, D, or E).
    """
    print(f"\n[TITAN TRAIN] Training Ablation Variant {variant} on {device}...")
    
    if variant == "A":
        model = GRURawBaseline(input_dim=14, hidden_dim=64).to(device)
    elif variant == "B":
        model = CNNGRUFeaturesBaseline(input_dim=28, hidden_dim=64).to(device)
    elif variant == "C":
        model = CNNGRUResidualsBaseline(input_dim=12, hidden_dim=64).to(device)
    elif variant == "D":
        model = CNNGRUResidualsContextBaseline(residual_dim=12, phase_embedding_dim=8, hidden_dim=64).to(device)
    elif variant == "E":
        model = TitanFullModel(feature_dim=24, phase_dim=8, hidden_dim=96).to(device)
    else:
        raise ValueError(f"Unknown variant: {variant}")
        
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    loss_asym = RiskAlignedAsymmetricLoss(alpha_late=5.0, alpha_early=1.0)
    loss_ce = nn.CrossEntropyLoss()
    loss_bce = nn.BCELoss()
    loss_pinball_05 = PinballLoss(quantile=0.05)
    loss_pinball_95 = PinballLoss(quantile=0.95)
    
    model.train()
    for epoch in range(num_epochs):
        total_loss = 0.0
        steps = 0
        for batch in dataloader:
            optimizer.zero_grad()
            
            y_anomaly = batch["target_anomaly"].to(device)
            y_fault = batch["target_fault"].to(device)
            y_rul = batch["target_rul"].to(device)
            y_hi = batch["target_hi"].to(device)
            
            if variant == "A":
                out = model(batch["raw"].to(device))
            elif variant == "B":
                out = model(batch["features"].to(device))
            elif variant == "C":
                out = model(batch["residuals"].to(device))
            elif variant == "D":
                out = model(batch["residuals"].to(device), batch["phase_ids"].to(device))
            elif variant == "E":
                out = model(batch["titan_feats"].to(device), batch["phase_ids"].to(device))
                
            # Compute multi-task losses
            l_anom = loss_bce(out["anomaly_prob"], y_anomaly)
            l_fault = loss_ce(out["fault_logits"], y_fault)
            l_rul = loss_asym(out["rul_hours"], y_rul) / 100.0 # Scale regression
            l_hi = loss_asym(out["health_index"], y_hi) * 10.0
            
            loss = l_anom + l_fault + l_rul + l_hi
            
            if variant == "E":
                # Conformal quantile losses
                l_q05 = loss_pinball_05(out["rul_q05"], y_rul) / 100.0
                l_q95 = loss_pinball_95(out["rul_q95"], y_rul) / 100.0
                loss += l_q05 + l_q95
                
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            steps += 1
            if steps >= 50: # Cap steps per epoch for fast verification
                break
                
        avg_loss = total_loss / max(steps, 1)
        print(f"  Epoch [{epoch+1}/{num_epochs}] - Loss: {avg_loss:.4f}")
        
    return model
