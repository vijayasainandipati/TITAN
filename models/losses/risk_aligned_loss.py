"""
TITAN Loss Functions — Risk-Aligned Asymmetric Loss
Flight safety demands that late prediction of engine degradation or failure
is penalized far more severely than early prediction (alpha_late >> alpha_early).
"""

import torch
import torch.nn as nn


class RiskAlignedAsymmetricLoss(nn.Module):
    """
    Asymmetric penalty loss for degradation / RUL estimation:
    If predicted RUL > true RUL (late detection / underestimating degradation),
    loss is scaled by alpha_late (default 5.0).
    If predicted RUL <= true RUL (conservative / early alert),
    loss is scaled by alpha_early (default 1.0).
    """
    def __init__(self, alpha_late: float = 5.0, alpha_early: float = 1.0):
        super().__init__()
        self.alpha_late = alpha_late
        self.alpha_early = alpha_early

    def forward(self, y_pred: torch.Tensor, y_true: torch.Tensor) -> torch.Tensor:
        error = y_pred - y_true
        # Positive error means y_pred > y_true -> predicted engine is healthier / longer RUL than reality (DANGEROUS)
        weights = torch.where(error > 0, self.alpha_late, self.alpha_early)
        loss = weights * (error ** 2)
        return torch.mean(loss)


class PinballLoss(nn.Module):
    """
    Pinball (Quantile) loss for conformal / calibrated quantile regression:
    L_q(y, y_hat) = max(q * (y - y_hat), (q - 1) * (y - y_hat))
    Used for 10th and 90th percentile bounds to achieve target 90% PICP.
    """
    def __init__(self, quantile: float = 0.5):
        super().__init__()
        self.quantile = quantile

    def forward(self, y_pred: torch.Tensor, y_true: torch.Tensor) -> torch.Tensor:
        diff = y_true - y_pred
        loss = torch.max((self.quantile - 1.0) * diff, self.quantile * diff)
        return torch.mean(loss)
