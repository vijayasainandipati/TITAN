"""
Unit Tests for Machine Learning Models, Risk-Aligned Loss, and Metrics Suite
"""

import pytest
import torch
import numpy as np
from models.losses.risk_aligned_loss import RiskAlignedAsymmetricLoss, PinballLoss
from models.titan_full import TitanFullModel
from evaluation.metrics import (
    compute_anomaly_metrics,
    compute_fault_metrics,
    compute_rul_metrics,
    compute_picp_coverage
)


def test_risk_aligned_asymmetric_loss():
    loss_fn = RiskAlignedAsymmetricLoss(alpha_late=5.0, alpha_early=1.0)
    
    y_true = torch.tensor([50.0])
    # Late detection (predicted 60.0 > true 50.0, dangerous error of +10)
    pred_late = torch.tensor([60.0])
    loss_late = loss_fn(pred_late, y_true)
    
    # Early detection (predicted 40.0 < true 50.0, conservative error of -10)
    pred_early = torch.tensor([40.0])
    loss_early = loss_fn(pred_early, y_true)
    
    # Late detection penalty must be 5x larger than early detection penalty
    assert loss_late.item() == pytest.approx(5.0 * loss_early.item(), rel=1e-3)


def test_titan_full_model_forward_pass():
    model = TitanFullModel(feature_dim=24, phase_dim=8, hidden_dim=96, num_fault_classes=8)
    model.eval()
    
    batch_size = 4
    seq_len = 16
    x_features = torch.randn(batch_size, seq_len, 24)
    phase_ids = torch.randint(0, 7, (batch_size, seq_len))
    
    with torch.no_grad():
        out = model(x_features, phase_ids)
        
    assert "anomaly_prob" in out
    assert out["anomaly_prob"].shape == (batch_size,)
    assert "fault_logits" in out
    assert out["fault_logits"].shape == (batch_size, 8)
    assert "rul_hours" in out
    assert out["rul_hours"].shape == (batch_size,)
    # Quantile monotonicity check: q05 <= q50 <= q95
    assert torch.all(out["rul_q05"] <= out["rul_hours"] + 1e-4)
    assert torch.all(out["rul_hours"] <= out["rul_q95"] + 1e-4)


def test_picp_coverage_metric():
    y_true = np.array([50.0, 60.0, 70.0, 80.0, 90.0])
    y_low = np.array([45.0, 55.0, 65.0, 75.0, 95.0]) # 4 of 5 covered
    y_high = np.array([55.0, 65.0, 75.0, 85.0, 105.0])
    
    res = compute_picp_coverage(y_true, y_low, y_high)
    assert res["picp_coverage_ratio"] == 0.8
    assert res["target_coverage_ratio"] == 0.90
