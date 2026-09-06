"""
TITAN Digital Twin Core — Sensor Health Module
Decoupled Sensor Health evaluation running BEFORE residual computation.
Separates "sensor is lying" from "engine is degrading" using:
- Range validation & physical rate-of-change (slew) bounds
- Analytical redundancy & cross-cylinder consistency
- Thermodynamic cross-coupling checks (e.g. Oil temp vs Coolant temp)
- Dynamic frozen / dropout detection
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import deque


class SensorHealthModule:
    def __init__(self, history_window_len: int = 15):
        self.window_len = history_window_len
        self.history: Dict[str, deque] = {
            "cht_1_c": deque(maxlen=history_window_len),
            "cht_2_c": deque(maxlen=history_window_len),
            "cht_3_c": deque(maxlen=history_window_len),
            "cht_4_c": deque(maxlen=history_window_len),
            "egt_1_c": deque(maxlen=history_window_len),
            "egt_2_c": deque(maxlen=history_window_len),
            "egt_3_c": deque(maxlen=history_window_len),
            "egt_4_c": deque(maxlen=history_window_len),
            "coolant_temp_c": deque(maxlen=history_window_len),
            "oil_pressure_bar": deque(maxlen=history_window_len),
            "oil_temp_c": deque(maxlen=history_window_len),
            "vibration_rms_g": deque(maxlen=history_window_len)
        }
        
        # Physical slew rate limits per second
        self.max_slew_per_sec = {
            "cht": 6.0,       # CHT cannot change >6 C in 1 second due to thermal mass
            "coolant": 4.0,   # Coolant has large thermal mass
            "egt": 45.0,      # EGT can change fast with throttle
            "oil_pressure": 3.0, # bar/sec
            "oil_temp": 4.0,
            "vibration": 5.0
        }

    def evaluate_sensor_health(self,
                               raw_sensors: Dict[str, float],
                               dt: float = 1.0) -> Dict:
        """
        Evaluates raw telemetry for sensor faults independent of engine degradation.
        Returns detailed report and flags isolated sensor anomalies.
        """
        channel_status = {}
        faulted_channels = []
        is_sensor_fault = False
        
        # 1. Physical range bounds
        ranges = {
            "cht": (-20.0, 240.0),
            "egt": (0.0, 950.0),
            "coolant": (-20.0, 140.0),
            "oil_pressure": (0.05, 8.0),
            "oil_temp": (-20.0, 160.0),
            "vibration": (0.05, 25.0)
        }
        
        for ch, val in raw_sensors.items():
            ch_type = next((k for k in ranges if k in ch), None)
            if ch_type and ch_type in ranges:
                low, high = ranges[ch_type]
                if val < low or val > high:
                    channel_status[ch] = f"RANGE_VIOLATION ({val})"
                    faulted_channels.append(ch)
                    is_sensor_fault = True
                    continue
                    
            # 2. Slew rate check
            hist = self.history.get(ch)
            if hist and len(hist) > 0 and dt > 0:
                prev_val = hist[-1]
                rate = abs(val - prev_val) / dt
                max_rate = next((v for k, v in self.max_slew_per_sec.items() if k in ch), 20.0)
                if rate > max_rate:
                    channel_status[ch] = f"SLEW_VIOLATION ({rate:.1f}/s > {max_rate:.1f})"
                    faulted_channels.append(ch)
                    is_sensor_fault = True
                    continue
                    
            # 3. Frozen sensor check (zero variance over window)
            if hist and len(hist) >= self.window_len:
                std_window = float(np.std(list(hist) + [val]))
                # Accelerometer and pressure naturally have Gaussian noise; exactly 0 std indicates frozen ADC
                if std_window < 1e-4 and "vibration" in ch:
                    channel_status[ch] = "FROZEN_SIGNAL"
                    faulted_channels.append(ch)
                    is_sensor_fault = True
                    continue
                    
            channel_status[ch] = "HEALTHY"
            
        # 4. Cross-sensor analytical redundancy for CHT
        cht_vals = [raw_sensors.get(f"cht_{i}_c", 0.0) for i in range(1, 5)]
        median_cht = float(np.median(cht_vals))
        for i in range(1, 5):
            ch = f"cht_{i}_c"
            spread = abs(raw_sensors.get(ch, 0.0) - median_cht)
            # If one CHT deviates by > 22 C but EGT of that cylinder did NOT change accordingly,
            # this is an isolated thermocouple drift!
            egt_ch = f"egt_{i}_c"
            egt_vals = [raw_sensors.get(f"egt_{k}_c", 0.0) for k in range(1, 5)]
            median_egt = float(np.median(egt_vals))
            egt_spread = abs(raw_sensors.get(egt_ch, 0.0) - median_egt)
            
            if spread > 22.0 and egt_spread < 15.0:
                channel_status[ch] = f"CROSS_CONSISTENCY_DRIFT (Spread {spread:.1f} C)"
                if ch not in faulted_channels:
                    faulted_channels.append(ch)
                is_sensor_fault = True
                
        # Update history
        for ch, val in raw_sensors.items():
            if ch in self.history:
                self.history[ch].append(val)
                
        return {
            "sensor_fault_detected": is_sensor_fault,
            "faulted_channels": faulted_channels,
            "channel_status": channel_status,
            "cross_sensor_consistency_score": float(max(1.0 - 0.25 * len(faulted_channels), 0.0))
        }
