# Research Notes: NASA C-MAPSS FD001 Pre-Validation

## 1. Context & Purpose
Phase 0 of TITAN's methodology uses the NASA Commercial Modular Aero-Propulsion System Simulation (C-MAPSS) FD001 dataset to benchmark and de-risk the candidate sequence architectures (GRU, CNN-GRU, Multi-Head Temporal Attention) prior to aero-piston twin implementation.

## 2. Dataset Structure: FD001
- Trajectories: 100 train engines, 100 test engines.
- Operating conditions: Sea level, single operating condition (nominal).
- Fault mode: High Pressure Compressor (HPC) degradation.
- Sensor channels: 21 sensor measurements + 3 operational settings.

## 3. Evaluation Metrics
- **Root Mean Squared Error (RMSE)**:
  $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^N (RUL_{true} - RUL_{pred})^2}$$
- **NASA Asymmetric Scoring Function**:
  $$S = \sum_{i=1}^N s_i, \quad s_i = \begin{cases} \exp\left(-\frac{d_i}{13}\right) - 1 & \text{if } d_i < 0 \text{ (early prediction)} \\ \exp\left(\frac{d_i}{10}\right) - 1 & \text{if } d_i \ge 0 \text{ (late prediction)} \end{cases}$$
  Where $d_i = RUL_{pred} - RUL_{true}$.
  Late predictions are exponentially penalized more severely than early predictions, mirroring flight safety criticality.

## 4. Key Takeaways for Aero-Piston Engines
1. Pure sequence modeling on raw sensor noise without physics-based trend extraction leads to high variance and late detections.
2. Normalizing sensor signals by operational setpoints (physics residuals) drastically stabilizes degradation trajectories.
3. This architecture validation directly motivates the Risk-Aligned Loss and the Ablation Suite (A → E) in TITAN.
