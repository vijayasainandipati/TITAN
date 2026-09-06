"""
TITAN Hierarchical Aggregation — Cycle Features
Aggregates continuous high-frequency telemetry into cycle-level statistical features:
- Mean, standard deviation, peak-to-peak, crest factor, skewness, slew rate
- Stabilizes continuous noisy streams for sequence modeling (SAM-IPA pattern).
"""

import numpy as np
from typing import Dict, List, Optional
import pandas as pd


class CycleFeatureExtractor:
    def __init__(self, window_size: int = 10):
        self.window_size = window_size

    def extract_features_from_window(self, telemetry_window: List[Dict[str, float]]) -> Dict[str, float]:
        """
        Computes statistical features over a window of telemetry samples.
        """
        if not telemetry_window:
            return {}
            
        keys_to_process = [
            "cht_1_c", "cht_2_c", "cht_3_c", "cht_4_c",
            "egt_1_c", "egt_2_c", "egt_3_c", "egt_4_c",
            "oil_pressure_bar", "oil_temp_c", "coolant_temp_c",
            "vibration_rms_g", "rpm", "map_bar"
        ]
        
        feats = {}
        for k in keys_to_process:
            vals = [s[k] for s in telemetry_window if k in s]
            if not vals:
                continue
            arr = np.array(vals, dtype=float)
            
            mean_v = float(np.mean(arr))
            std_v = float(np.std(arr))
            p2p_v = float(np.ptp(arr))
            
            feats[f"{k}_mean"] = mean_v
            feats[f"{k}_std"] = std_v
            feats[f"{k}_p2p"] = p2p_v
            
            # Slew rate (change from start to end of window)
            feats[f"{k}_slew"] = float((arr[-1] - arr[0]) / max(len(arr), 1))
            
        # Cross-cylinder CHT spread in window
        if "cht_1_c_mean" in feats:
            cht_means = [feats[f"cht_{i}_c_mean"] for i in range(1, 5)]
            feats["cht_spread_mean"] = float(max(cht_means) - min(cht_means))
            
        # Cross-cylinder EGT spread in window
        if "egt_1_c_mean" in feats:
            egt_means = [feats[f"egt_{i}_c_mean"] for i in range(1, 5)]
            feats["egt_spread_mean"] = float(max(egt_means) - min(egt_means))
            
        return feats

    def process_dataframe(self, df: pd.DataFrame, step: int = 5) -> pd.DataFrame:
        """
        Processes a full flight dataframe into windowed cycle features.
        """
        rows = []
        n = len(df)
        for i in range(0, n - self.window_size + 1, step):
            window_slice = df.iloc[i : i + self.window_size].to_dict(orient="records")
            feats = self.extract_features_from_window(window_slice)
            
            # Preserve central timestamp, engine_id, and ground truth
            mid_row = df.iloc[i + self.window_size // 2]
            feats["timestamp"] = mid_row["timestamp"]
            feats["engine_id"] = mid_row["engine_id"]
            feats["flight_phase"] = mid_row["flight_phase"]
            
            for gt_col in [c for c in df.columns if c.startswith("gt_")]:
                feats[gt_col] = mid_row[gt_col]
                
            rows.append(feats)
            
        return pd.DataFrame(rows)
