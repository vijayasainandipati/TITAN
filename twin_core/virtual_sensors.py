"""
TITAN Digital Twin Core — Virtual Sensors
Reconstructs corrupted, drifting, or disconnected telemetry channels
using analytical redundancy and the Digital Twin expected state.
Also quantifies the resulting confidence reduction (PRD C.1 & F.1).
"""

from typing import Dict, List, Tuple


class VirtualSensorReconstruction:
    def __init__(self):
        pass

    def reconstruct_channels(self,
                             raw_sensors: Dict[str, float],
                             expected_state: Dict[str, float],
                             faulted_channels: List[str]) -> Tuple[Dict[str, float], float, List[str]]:
        """
        Replaces faulted/dropped channels with physics virtual estimates.
        Returns:
            (reconstructed_sensor_dict, confidence_factor, list_of_reconstructed_channels)
        """
        clean_dict = dict(raw_sensors)
        reconstructed = []
        
        for ch in faulted_channels:
            if ch in clean_dict:
                # 1. Individual cylinder CHT reconstruction
                if "cht_" in ch and "_c" in ch:
                    valid_chts = [
                        raw_sensors[f"cht_{i}_c"]
                        for i in range(1, 5)
                        if f"cht_{i}_c" not in faulted_channels and f"cht_{i}_c" in raw_sensors
                    ]
                    if valid_chts:
                        clean_dict[ch] = float(sum(valid_chts) / len(valid_chts))
                    else:
                        clean_dict[ch] = expected_state.get("cht_mean_c", 115.0)
                    reconstructed.append(ch)
                    
                # 2. Individual cylinder EGT reconstruction
                elif "egt_" in ch and "_c" in ch:
                    valid_egts = [
                        raw_sensors[f"egt_{i}_c"]
                        for i in range(1, 5)
                        if f"egt_{i}_c" not in faulted_channels and f"egt_{i}_c" in raw_sensors
                    ]
                    if valid_egts:
                        clean_dict[ch] = float(sum(valid_egts) / len(valid_egts))
                    else:
                        clean_dict[ch] = expected_state.get("egt_mean_c", 750.0)
                    reconstructed.append(ch)
                    
                # 3. Oil Pressure / Oil Temp / Coolant Temp / Vibration reconstruction from Twin
                elif ch in expected_state:
                    clean_dict[ch] = float(expected_state[ch])
                    reconstructed.append(ch)
                    
        # Confidence penalty: -15% per reconstructed channel
        confidence_factor = max(1.0 - 0.15 * len(reconstructed), 0.30)
        return clean_dict, confidence_factor, reconstructed
