# TITAN Mathematical & Technical Architecture

## 1. Physical Foundations & Differential Equations

TITAN's Digital Twin core mirrors a 4-cylinder, turbocharged four-stroke aero-piston powerplant (115–160 HP class, dry sump lubrication, liquid-cooled cylinder heads, air-cooled barrels, e.g., Rotax 914 / Austro AE300).

### 1.1 Thermal Dynamics ODEs
The cylinder head temperature ($T_{cht,i}$ for cylinder $i \in \{1,2,3,4\}$) is governed by first-law lumped capacitance:

$$m_{cyl} c_{p,cyl} \frac{dT_{cht,i}}{dt} = \dot{Q}_{comb,i} - \dot{Q}_{cool,i} - \dot{Q}_{conv,i}$$

Where:
- $\dot{Q}_{comb,i} = \eta_{ind} \cdot \dot{m}_{f,i} \cdot \text{LHV} \cdot f(\text{RPM}, \text{MAP}, \lambda_i)$ is the instantaneous indicated thermal energy release.
- $\dot{Q}_{cool,i} = h_{cool} A_{cool} (T_{cht,i} - T_{coolant})$ is the heat flux rejected to the liquid cooling jacket.
- $\dot{Q}_{conv,i} = h_{air} A_{fin} (T_{cht,i} - T_{ambient})$ represents ambient convection over the finned barrels.

The liquid coolant energy balance accounts for radiator dissipation:

$$m_{cool} c_{p,cool} \frac{dT_{coolant}}{dt} = \sum_{i=1}^4 \dot{Q}_{cool,i} - \dot{m}_{air,rad} c_{p,air} \varepsilon_{rad} (T_{coolant} - T_{ambient})$$

Where ram air mass flow scales with True Airspeed ($V_{TAS}$) and atmospheric density $\rho(h)$:

$$\dot{m}_{air,rad} = \rho(h) \cdot A_{duct} \cdot V_{TAS} \cdot \eta_{ram}$$

The Exhaust Gas Temperature ($T_{egt,i}$) models the expansion stroke terminal temperature:

$$T_{egt,i} = T_{ambient} + \Delta T_{comb}(\lambda_i, \text{MAP}) \cdot (1 - \eta_{thermal}) \cdot \exp(-\tau_{egt} \cdot \text{RPM})$$

### 1.2 Lubrication Dynamics
Oil viscosity $\mu(T_{oil})$ obeys the Walther/ASTM D341 kinematic relationship:

$$\log \log (\nu + 0.7) = A - B \cdot \log(T_{oil} + 273.15)$$

Oil pump volumetric flow rate from a positive-displacement crankshaft pump:

$$\dot{V}_{pump} = V_{disp} \cdot \text{RPM} \cdot \eta_{vol}$$

The system oil pressure $P_{oil}$ is determined by the hydrodynamic clearance resistance in the crankshaft journal bearings and oil galleries:

$$P_{oil} = P_{crankcase} + \frac{\mu(T_{oil}) \cdot \dot{V}_{pump}}{K_{clearance}} - \Delta P_{filter}$$

Under bearing clearance wear ($\Delta c_b > 0$), $K_{clearance}$ increases, causing a marked drop in $P_{oil}$ at elevated $T_{oil}$ and low RPM.

### 1.3 Mechanical & Rotational Vibration
The engine block vibration follows a multi-degree-of-freedom forced harmonic oscillator:

$$m_{eng} \ddot{x} + c_{damp} \dot{x} + k_{mount} x = F_0 + F_{imb} \cdot \Omega^2 \cos(\Omega t) + \sum_{k=1}^4 F_{k} \cos(k \Omega t + \phi_k)$$

- $1\Omega$ (1X): Crankshaft and propeller unbalance.
- $2\Omega$ (2X): Four-cylinder four-stroke reciprocating inertia forces.
- $0.5\Omega$ (Half-order): Single-cylinder misfire or uneven combustion event.

---

## 2. Sensor Health & Decoupling Logic

Before evaluating physics residuals, the **Sensor Health Module** cross-checks raw telemetry $y(t)$:
1. **Range Validation**: Checks physical plausibility $[y_{min}^{phys}, y_{max}^{phys}]$.
2. **Rate of Change (Slew) Check**: $|\frac{dy_i}{dt}| \le \dot{y}_{max}^{phys}$.
3. **Analytical Redundancy**:
   - Cross-cylinder CHT spread: $|T_{cht,i} - \text{median}(T_{cht})| \le \theta_{spread}$.
   - Thermodynamic coupling: $T_{oil}$ and $T_{coolant}$ must covary during thermal transients.
   - Fluid coupling: $P_{oil}$ must scale monotonically with RPM at constant $T_{oil}$.

If an anomaly occurs on a single sensor channel without thermodynamic cross-coupling, the system flags a **Sensor Fault** (drift, bias, or dropout), invokes **Virtual Sensor Reconstruction**, and attenuates RUL confidence without penalizing engine health.

---

## 3. Physics Residual Engine

Normalized residual vector:

$$r_i(t) = \frac{y_i(t) - \hat{y}_i(t)}{\sigma_{noise,i} + \epsilon}$$

Where $\hat{y}_i(t)$ is the output of the physics twin observer given operational setpoints $[RPM, MAP, V_{TAS}, h, T_{amb}]$.

**Envelope Boundary Flagging**:
If environmental or operational variables exceed the physics model's verified domain:
- $h > 26,000 \text{ ft}$ (critical turbocharger boost limit)
- $T_{amb} < -45^\circ C$ or $> +50^\circ C$
The system explicitly emits the status **"OUTSIDE VALIDATED ENVELOPE"** to prevent misleading confident inferences.

---

## 4. Multi-Tier AI Architecture & Risk-Aligned Loss

### 4.1 Hierarchical Feature Aggregation
- **Cycle Level**: 5-second sliding windows (mean, variance, peak-to-peak, spectral power).
- **Phase Level**: Flight segmentation into `IDLE`, `TAXI`, `TAKEOFF`, `CLIMB`, `CRUISE`, `LOITER`, `DESCENT`, `LANDING`.
- **Engine Health Index**:
  $$HI_{engine}(t) = \sum_{k \in \{therm, lube, mech, comb\}} w_k(phase) \cdot HI_k(t)$$
  Where $w_{lube}(CLIMB) > w_{lube}(LOITER)$ and $w_{mech}(TAKEOFF) > w_{mech}(DESCENT)$.

### 4.2 Multi-Tier Specialized Heads
- **Tier 1 (Anomaly Head)**: VAE latent density estimator detecting emergent drift.
- **Tier 2 (Fault Classification Head)**: 7-class FMEA classification.
- **Tier 3 (Degradation & RUL Head)**: Predicts continuous degradation state and flight hours to critical limit ($HI < 0.35$).
- **Tier 4a (Confidence & OOD)**: Model ensemble variance + conformal quantile regression yielding calibrated 90% confidence bands $[\text{RUL}_{low}, \text{RUL}_{high}]$.
- **Tier 4b (Physical Explainability)**: Computes residual attribution vectors mapping predictions back to physical parameters ($P_{oil}$ drop, CHT rise, 2X harmonic rise).

### 4.3 Risk-Aligned Asymmetric Loss
Late prediction of failure carries catastrophic flight safety consequences:

$$\mathcal{L}_{asym}(y, \hat{y}) = \begin{cases} \alpha_{late} (y - \hat{y})^2 & \text{if } \hat{y} < y \text{ (underestimating degradation / overestimating RUL)} \\ \alpha_{early} (y - \hat{y})^2 & \text{if } \hat{y} \ge y \end{cases}$$

With $\alpha_{late} = 5.0, \alpha_{early} = 1.0$.
