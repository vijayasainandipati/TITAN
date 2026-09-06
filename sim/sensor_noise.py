"""
TITAN Sensor Noise & Measurement Corruption Engine
Simulates realistic avionics sensor noise, ADC quantization,
calibration bias, thermal drift, intermittent dropouts, and EMI spikes.
"""

import numpy as np
from typing import Dict, Optional


class SensorNoiseEngine:
    def __init__(self,
                 sensor_bias: Optional[Dict[str, float]] = None,
                 sensor_noise_sigma: Optional[Dict[str, float]] = None,
                 dropout_prob: float = 0.0005,
                 spike_prob: float = 0.001):
        
        self.sensor_bias = sensor_bias or {}
        self.sensor_noise_sigma = sensor_noise_sigma or {
            "cht_1_c": 0.45, "cht_2_c": 0.45, "cht_3_c": 0.45, "cht_4_c": 0.45,
            "egt_1_c": 2.5, "egt_2_c": 2.5, "egt_3_c": 2.5, "egt_4_c": 2.5,
            "oil_pressure_bar": 0.035,
            "oil_temp_c": 0.35,
            "coolant_temp_c": 0.30,
            "vibration_rms_g": 0.040,
            "fuel_flow_lph": 0.25
        }
        self.dropout_prob = dropout_prob
        self.spike_prob = spike_prob
        
        # State memory for frozen sensor detection
        self.last_valid_readings: Dict[str, float] = {}

    def corrupt_measurements(self,
                             clean_sensors: Dict[str, float],
                             sensor_drift_dict: Optional[Dict] = None,
                             rng: Optional[np.random.RandomState] = None) -> Dict[str, float]:
        """
        Applies bias, Gaussian white noise, quantization, drift, and dropouts.
        """
        if rng is None:
            rng = np.random.RandomState()
            
        corrupted = {}
        drift_channel = None
        drift_val = 0.0
        if sensor_drift_dict:
            drift_channel = sensor_drift_dict.get("channel")
            drift_val = sensor_drift_dict.get("drift_value", 0.0)
            
        for key, val in clean_sensors.items():
            # Apply systematic bias
            bias = self.sensor_bias.get(key, 0.0)
            sigma = self.sensor_noise_sigma.get(key, 0.05 * abs(val) if val != 0 else 0.05)
            
            noisy_val = val + bias + rng.normal(0.0, sigma)
            
            # Apply sensor drift if this channel is faulted
            if key == drift_channel:
                noisy_val += drift_val
                
            # Intermittent EMI ignition spike
            if rng.uniform(0.0, 1.0) < self.spike_prob:
                spike_mag = rng.uniform(3.0, 8.0) * sigma
                noisy_val += spike_mag
                
            # Intermittent dropout (returns 0.0 or stuck value)
            if rng.uniform(0.0, 1.0) < self.dropout_prob:
                # Intermittent wire disconnect
                noisy_val = 0.0
                
            # Realistic ADC Quantization
            if "pressure" in key:
                noisy_val = round(noisy_val, 2) # 0.01 bar ADC
            elif "temp" in key or "cht" in key or "egt" in key:
                noisy_val = round(noisy_val, 1) # 0.1 C thermocouple ADC
            elif "vibration" in key:
                noisy_val = round(noisy_val, 3) # 0.001 G accelerometer ADC
            else:
                noisy_val = round(noisy_val, 2)
                
            corrupted[key] = float(noisy_val)
            self.last_valid_readings[key] = float(noisy_val)
            
        return corrupted
