"""
TITAN Evaluation Metrics Suite
Computes all quantitative metrics required by PRD Table E.1:
- Anomaly Recall & False Positive Rate (FPR)
- Fault Classification Macro-F1 & Accuracy
- Health Index MAE
- RUL MAE & Risk-Aligned Late-Detection Rate
- Prediction Interval Coverage Probability (PICP) for Calibrated Confidence
"""

import numpy as np
from typing import Dict
from sklearn.metrics import recall_score, precision_score, f1_score, accuracy_score


def compute_anomaly_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> Dict[str, float]:
    y_pred = (y_prob >= threshold).astype(int)
    y_true = y_true.astype(int)
    
    recall = float(recall_score(y_true, y_pred, zero_division=0))
    precision = float(precision_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    
    # False Positive Rate: FP / (FP + TN)
    neg_mask = (y_true == 0)
    fp = np.sum((y_pred == 1) & neg_mask)
    tn = np.sum((y_pred == 0) & neg_mask)
    fpr = float(fp / max(fp + tn, 1))
    
    return {
        "anomaly_recall": round(recall, 4),
        "anomaly_precision": round(precision, 4),
        "anomaly_f1": round(f1, 4),
        "false_positive_rate": round(fpr, 4)
    }


def compute_fault_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    accuracy = float(accuracy_score(y_true, y_pred))
    
    return {
        "fault_macro_f1": round(macro_f1, 4),
        "fault_accuracy": round(accuracy, 4)
    }


def compute_rul_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    errors = y_pred - y_true
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors ** 2)))
    
    # Late detection rate: fraction where predicted RUL is dangerously higher than true RUL (> 5 hours over)
    late_count = np.sum(errors > 5.0)
    late_rate = float(late_count / max(len(errors), 1))
    
    # Risk-aligned asymmetric penalty score
    asym_penalty = np.where(errors > 0, 5.0 * (errors ** 2), 1.0 * (errors ** 2))
    asym_score = float(np.mean(asym_penalty))
    
    return {
        "rul_mae_hours": round(mae, 2),
        "rul_rmse_hours": round(rmse, 2),
        "late_detection_rate": round(late_rate, 4),
        "asymmetric_risk_score": round(asym_score, 2)
    }


def compute_hi_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    mae = float(np.mean(np.abs(y_pred - y_true)))
    return {
        "health_index_mae": round(mae, 4)
    }


def compute_picp_coverage(y_true: np.ndarray, y_low: np.ndarray, y_high: np.ndarray) -> Dict[str, float]:
    covered = (y_true >= y_low) & (y_true <= y_high)
    picp = float(np.mean(covered))
    mean_width = float(np.mean(y_high - y_low))
    
    return {
        "picp_coverage_ratio": round(picp, 4),
        "target_coverage_ratio": 0.90,
        "mean_interval_width_hours": round(mean_width, 1),
        "is_calibrated": bool(picp >= 0.85)
    }
