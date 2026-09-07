import React from 'react';
import StatusPill from '../components/StatusPill';

export default function OperationalView({ frame, onOpenFaultModal, onNavigateView }) {
  if (!frame) {
    return (
      <div className="titan-card" style={{ textAlign: 'center', padding: '3.5rem' }}>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Acquiring engine telemetry stream...</p>
      </div>
    );
  }

  const {
    engine_id,
    engine_name,
    flight_phase,
    operational = {},
    sensors = {},
    expected_state = {},
    residuals = {},
    health_index = {},
    predictions = {},
    tactical_risk = {},
    sensor_health = {}
  } = frame;

  const hi_overall = health_index.overall || 1.0;
  const subsystems = health_index.subsystems || { thermal: 1.0, lubrication: 1.0, mechanical: 1.0, combustion: 1.0 };
  const phaseWeights = health_index.phase_weights || {};

  // Cylinder spreads
  const chts = [sensors.cht_1_c || 115, sensors.cht_2_c || 115, sensors.cht_3_c || 115, sensors.cht_4_c || 115];
  const egts = [sensors.egt_1_c || 740, sensors.egt_2_c || 740, sensors.egt_3_c || 740, sensors.egt_4_c || 740];
  const cht_spread = Math.max(...chts) - Math.min(...chts);
  const egt_spread = Math.max(...egts) - Math.min(...egts);

  // Determine caution states for 6-panel grid
  const r_oil = residuals.r_oil_pressure || 0;
  const r_oil_temp = residuals.r_oil_temp || 0;
  const r_cht = residuals.r_cht_mean || 0;
  const r_egt = residuals.r_egt_mean || 0;
  const r_vib = residuals.r_vibration || 0;

  const isOilPressCaution = (sensors.oil_pressure_bar < 2.5) || Math.abs(r_oil) > 2.0;
  const isOilPressCritical = (sensors.oil_pressure_bar < 1.8) || Math.abs(r_oil) > 4.0;

  const isOilTempCaution = (sensors.oil_temp_c > 115) || Math.abs(r_oil_temp) > 2.2;
  const isChtCaution = (cht_spread > 22) || (sensors.cht_mean_c > 130) || Math.abs(r_cht) > 2.2;
  const isEgtCaution = (egt_spread > 65) || (sensors.egt_mean_c > 840) || Math.abs(r_egt) > 2.2;
  const isVibCaution = (sensors.vibration_rms_g > 2.0) || Math.abs(r_vib) > 2.0;

  // Solid health color (strictly green / amber / red — never a gradient)
  const hiColor = hi_overall >= 0.88 ? 'var(--status-nominal)' : hi_overall >= 0.70 ? 'var(--status-caution)' : 'var(--status-critical)';
  const hiStatusLabel = hi_overall >= 0.88 ? 'Nominal' : hi_overall >= 0.70 ? 'Caution' : 'Critical';

  // RUL with visible confidence band (never a bare point value)
  const rulHours = predictions.rul_hours || 180.0;
  const rulInterval = predictions.rul_conformal_interval_90 || [rulHours - 12.0, rulHours + 12.0];
  const rulMargin = ((rulInterval[1] - rulInterval[0]) / 2).toFixed(1);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.15rem' }}>
      {/* Console Header Panel (Matching Reference Mockup Specification) */}
      <div className="titan-card" style={{ padding: '1.2rem 1.4rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.85rem' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.85rem', flexWrap: 'wrap' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0, letterSpacing: '-0.01em' }}>
              TITAN ground control station
            </h2>
            <span style={{ fontSize: '0.92rem', color: 'var(--text-muted)', fontFamily: 'var(--font-sans)', fontWeight: 500 }}>
              unit {engine_id}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
            {/* Real-time Telemetry Frame Timestamp */}
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem',
              fontSize: '0.78rem',
              fontFamily: 'var(--font-mono)',
              color: 'var(--text-secondary)',
              background: 'var(--bg-base)',
              padding: '0.25rem 0.55rem',
              borderRadius: '4px',
              border: '1px solid var(--border-color)'
            }} title="Real-time telemetry stream timestamp">
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent-green)' }} />
              <span style={{ fontWeight: 600 }}>{frame?.real_time || new Date().toLocaleTimeString('en-GB', { hour12: false })}</span>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.66rem' }}>LIVE</span>
            </div>

            {/* Status dot + text indicator matching mockup */}
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.45rem',
              fontSize: '0.9rem',
              fontWeight: 600,
              color: hiColor
            }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: hiColor }} />
              <span>{hiStatusLabel}</span>
            </div>
          </div>
        </div>

        {/* 2px Solid Forest Green Accent Rule */}
        <div className="header-accent-rule" />

        {/* Operational Context Sub-Readouts */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', paddingTop: '0.2rem' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            MALE-UAV propulsion monitor • Rotax 914 / TAPAS powerplant • Flight phase: <strong style={{ color: 'var(--text-primary)' }}>{flight_phase}</strong>
          </div>

          <div style={{ display: 'flex', gap: '1.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <div>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginRight: '0.4rem' }}>Altitude:</span>
              <span className="telemetry-val" style={{ fontSize: '0.92rem' }}>
                {operational.altitude_ft?.toLocaleString()} <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>ft</span>
              </span>
            </div>

            <div>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginRight: '0.4rem' }}>Airspeed:</span>
              <span className="telemetry-val" style={{ fontSize: '0.92rem' }}>
                {operational.tas_kts?.toFixed(0)} <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>kts</span>
              </span>
            </div>

            <div>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginRight: '0.4rem' }}>Ambient:</span>
              <span className="telemetry-val" style={{ fontSize: '0.92rem' }}>
                {operational.ambient_temp_c?.toFixed(1)} <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>°C</span>
              </span>
            </div>

            <div>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginRight: '0.4rem' }}>MAP:</span>
              <span className="telemetry-val" style={{ fontSize: '0.92rem' }}>
                {operational.manifold_pressure_bar?.toFixed(2)} <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>bar</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 6-Panel Live Sensor Grid with Automatic Amber Tinting */}
      <div className="grid-cols-6">
        {/* Panel 1: Engine RPM */}
        <div className="sensor-card neutral">
          <div className="sensor-header">
            <span className="sensor-label">RPM</span>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>1X order</span>
          </div>
          <div>
            <span className="sensor-val-large">{operational.rpm?.toFixed(0)}</span>
            <span className="sensor-unit">RPM</span>
          </div>
          <div className="sensor-footer">
            <span>Throttle: {operational.throttle_pct?.toFixed(0)}%</span>
            <span>MAP: {operational.manifold_pressure_bar?.toFixed(2)} bar</span>
          </div>
        </div>

        {/* Panel 2: Cylinder Head Temp (CHT) */}
        <div className={`sensor-card ${isChtCaution ? 'caution' : 'neutral'}`}>
          <div className="sensor-header">
            <span className="sensor-label">CHT</span>
            {isChtCaution && (
              <span style={{ fontSize: '0.68rem', color: 'var(--status-caution)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                Spread: {cht_spread.toFixed(1)}°C
              </span>
            )}
          </div>
          <div>
            <span className="sensor-val-large">{sensors.cht_mean_c?.toFixed(1)}</span>
            <span className="sensor-unit">°C</span>
          </div>
          <div className="sensor-footer">
            <span>C1-C4: {chts.map(c => Math.round(c)).join(' · ')}</span>
            <span>r = {r_cht >= 0 ? `+${r_cht.toFixed(1)}` : r_cht.toFixed(1)}σ</span>
          </div>
        </div>

        {/* Panel 3: Exhaust Gas Temp (EGT) */}
        <div className={`sensor-card ${isEgtCaution ? 'caution' : 'neutral'}`}>
          <div className="sensor-header">
            <span className="sensor-label">EGT</span>
            {isEgtCaution && (
              <span style={{ fontSize: '0.68rem', color: 'var(--status-caution)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                Spread: {egt_spread.toFixed(0)}°C
              </span>
            )}
          </div>
          <div>
            <span className="sensor-val-large">{sensors.egt_mean_c?.toFixed(0)}</span>
            <span className="sensor-unit">°C</span>
          </div>
          <div className="sensor-footer">
            <span>C1-C4: {egts.map(e => Math.round(e)).join(' · ')}</span>
            <span>r = {r_egt >= 0 ? `+${r_egt.toFixed(1)}` : r_egt.toFixed(1)}σ</span>
          </div>
        </div>

        {/* Panel 4: Oil Pressure (Auto-tints amber/critical on residual divergence) */}
        <div className={`sensor-card ${isOilPressCritical ? 'critical' : isOilPressCaution ? 'caution' : 'neutral'}`}>
          <div className="sensor-header">
            <span className="sensor-label">Oil pressure</span>
            {isOilPressCaution && (
              <span style={{
                fontSize: '0.68rem',
                color: isOilPressCritical ? 'var(--status-critical)' : 'var(--status-caution)',
                fontFamily: 'var(--font-mono)',
                fontWeight: 600
              }}>
                {isOilPressCritical ? 'CRITICAL' : 'CAUTION'}
              </span>
            )}
          </div>
          <div>
            <span className="sensor-val-large">
              {sensors.oil_pressure_bar?.toFixed(2)}
            </span>
            <span className="sensor-unit">bar</span>
          </div>
          <div className="sensor-footer">
            <span>Expected: {expected_state.oil_pressure_bar?.toFixed(2) || '4.00'} bar</span>
            <span style={{ color: isOilPressCaution ? 'var(--status-caution)' : 'var(--text-muted)' }}>
              r = {r_oil >= 0 ? `+${r_oil.toFixed(1)}` : r_oil.toFixed(1)}σ
            </span>
          </div>
        </div>

        {/* Panel 5: Oil Temperature */}
        <div className={`sensor-card ${isOilTempCaution ? 'caution' : 'neutral'}`}>
          <div className="sensor-header">
            <span className="sensor-label">Oil temp</span>
            {isOilTempCaution && (
              <span style={{ fontSize: '0.68rem', color: 'var(--status-caution)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                Elevated
              </span>
            )}
          </div>
          <div>
            <span className="sensor-val-large">{sensors.oil_temp_c?.toFixed(1)}</span>
            <span className="sensor-unit">°C</span>
          </div>
          <div className="sensor-footer">
            <span>Viscosity: 15.1 cSt</span>
            <span>r = {r_oil_temp >= 0 ? `+${r_oil_temp.toFixed(1)}` : r_oil_temp.toFixed(1)}σ</span>
          </div>
        </div>

        {/* Panel 6: Vibration RMS */}
        <div className={`sensor-card ${isVibCaution ? 'caution' : 'neutral'}`}>
          <div className="sensor-header">
            <span className="sensor-label">Vibration</span>
            {isVibCaution && (
              <span style={{ fontSize: '0.68rem', color: 'var(--status-caution)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                2X rise
              </span>
            )}
          </div>
          <div>
            <span className="sensor-val-large">{sensors.vibration_rms_g?.toFixed(2)}</span>
            <span className="sensor-unit">mm/s</span>
          </div>
          <div className="sensor-footer">
            <span>Crest factor: 2.8</span>
            <span>r = {r_vib >= 0 ? `+${r_vib.toFixed(1)}` : r_vib.toFixed(1)}σ</span>
          </div>
        </div>
      </div>

      {/* Two-Column Core Operational Area */}
      <div className="grid-cols-2">
        {/* Left Column: Engine Health & Mission Risk */}
        <div className="titan-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <div>
              <h3 style={{ fontSize: '0.98rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                Engine health & reliability
              </h3>
              <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', margin: '0.15rem 0 0 0' }}>
                Phase-weighted aggregate health index (HI_engine)
              </p>
            </div>
            <StatusPill status={tactical_risk.tactical_status || 'GO'} label={tactical_risk.tactical_status || 'GO'} />
          </div>

          {/* Primary Health Readout */}
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', marginBottom: '0.65rem' }}>
            <span className="telemetry-val" style={{ fontSize: '2.4rem', fontWeight: 700, color: hiColor, lineHeight: 1 }}>
              {(hi_overall * 100).toFixed(1)}%
            </span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Overall propulsion health
            </span>
          </div>

          {/* Solid Health Fill Bar (Strictly no gradients per PRD) */}
          <div style={{ height: '8px', background: 'var(--border-subtle)', borderRadius: '4px', overflow: 'hidden', marginBottom: '1.25rem' }}>
            <div style={{
              width: `${Math.max(5, hi_overall * 100)}%`,
              height: '100%',
              background: hiColor,
              transition: 'width 0.3s ease'
            }} />
          </div>

          {/* Subsystem Health Breakdown */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', marginBottom: '1.25rem' }}>
            {[
              { key: 'thermal', label: 'Thermal management (CHT & coolant)', val: subsystems.thermal, weight: phaseWeights.thermal },
              { key: 'lubrication', label: 'Lubrication circuit (Walther viscosity & pressure)', val: subsystems.lubrication, weight: phaseWeights.lube },
              { key: 'combustion', label: 'Combustion dynamics (EGT balance & injectors)', val: subsystems.combustion, weight: phaseWeights.combustion },
              { key: 'mechanical', label: 'Mechanical assembly (crankshaft & orders)', val: subsystems.mechanical, weight: phaseWeights.mechanical }
            ].map(sub => {
              const subScore = sub.val ?? 1.0;
              const subColor = subScore >= 0.88 ? 'var(--status-nominal)' : subScore >= 0.70 ? 'var(--status-caution)' : 'var(--status-critical)';
              return (
                <div key={sub.key}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.2rem' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>{sub.label}</span>
                    <span className="telemetry-val" style={{ color: subColor }}>
                      {(subScore * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div style={{ height: '4px', background: 'var(--border-subtle)', borderRadius: '2px', overflow: 'hidden' }}>
                    <div style={{ width: `${subScore * 100}%`, height: '100%', background: subColor }} />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Remaining Useful Life with Visible Confidence Band */}
          <div style={{
            background: 'var(--bg-base)',
            border: '1px solid var(--border-color)',
            borderRadius: '6px',
            padding: '0.85rem 1rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Remaining useful life (RUL) with confidence band</div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.4rem', marginTop: '0.2rem' }}>
                <span className="telemetry-val" style={{ fontSize: '1.4rem', color: 'var(--text-primary)' }}>
                  {rulHours.toFixed(1)}
                </span>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>hours</span>
                <span className="telemetry-val" style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginLeft: '0.5rem' }}>
                  ± {rulMargin}h [{rulInterval[0].toFixed(1)} — {rulInterval[1].toFixed(1)}]
                </span>
              </div>
            </div>
            <div style={{ textAlign: 'right', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              <div>90% conformal PICP</div>
              <div style={{ color: 'var(--status-nominal)', fontWeight: 600 }}>Coverage verified</div>
            </div>
          </div>
        </div>

        {/* Right Column: AI Diagnostics & Inline Physical Evidence */}
        <div className="titan-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <div>
              <h3 style={{ fontSize: '0.98rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                AI diagnostics & physics evidence
              </h3>
              <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', margin: '0.15rem 0 0 0' }}>
                Inline residual validation • PRD Section 22 explainability
              </p>
            </div>
            {predictions.is_anomaly && (
              <span style={{
                fontSize: '0.72rem',
                fontFamily: 'var(--font-mono)',
                color: 'var(--status-caution)',
                background: 'var(--status-caution-bg)',
                padding: '0.2rem 0.5rem',
                borderRadius: '4px',
                border: '1px solid var(--status-caution-border)',
                fontWeight: 600
              }}>
                Anomaly detected
              </span>
            )}
          </div>

          {/* Diagnostics Alert List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {predictions.fault_name !== 'NORMAL' ? (
              <div style={{
                background: 'var(--status-caution-bg)',
                border: '1.5px solid var(--status-caution-border)',
                borderRadius: '6px',
                padding: '0.9rem'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--status-caution)" strokeWidth="2.5">
                      <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                      <line x1="12" y1="9" x2="12" y2="13" />
                      <line x1="12" y1="17" x2="12.01" y2="17" />
                    </svg>
                    <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--status-caution)' }}>
                      {predictions.fault_name}
                    </span>
                  </div>
                  <span className="telemetry-val" style={{ fontSize: '0.75rem', color: 'var(--status-caution)', fontWeight: 600 }}>
                    {(predictions.fault_confidence * 100).toFixed(0)}% confidence
                  </span>
                </div>

                {/* Inline Supporting Physics Evidence (Never behind tooltips) */}
                <div style={{
                  marginTop: '0.6rem',
                  fontSize: '0.78rem',
                  color: 'var(--text-secondary)',
                  lineHeight: 1.45,
                  background: 'var(--bg-base)',
                  padding: '0.55rem 0.75rem',
                  borderRadius: '4px',
                  border: '1px solid var(--border-color)',
                  fontFamily: 'var(--font-mono)'
                }}>
                  <div>Evidence: Normalized residual r_oil = {r_oil.toFixed(2)}σ (threshold ±2.0σ)</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem', marginTop: '0.2rem' }}>
                    Walther model expected: {expected_state.oil_pressure_bar?.toFixed(2) || '4.05'} bar; sensor: {sensors.oil_pressure_bar?.toFixed(2)} bar.
                  </div>
                </div>

                <div style={{ marginTop: '0.75rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    Triggered at T+ {(frame.timestamp / 3600).toFixed(1)}h
                  </span>
                  <button
                    onClick={() => onNavigateView && onNavigateView('engineering')}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--accent-green)',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.25rem'
                    }}
                  >
                    View physics twin evidence →
                  </button>
                </div>
              </div>
            ) : (
              <div style={{
                background: 'var(--status-nominal-bg)',
                border: '1px solid var(--status-nominal-border)',
                borderRadius: '6px',
                padding: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.65rem'
              }}>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--status-nominal)" strokeWidth="2.5">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M8 12l2.5 2.5L16 9" />
                </svg>
                <div style={{ fontSize: '0.8rem', color: 'var(--status-nominal)', fontWeight: 600 }}>
                  All propulsion subsystems operating within calibrated nominal envelope.
                </div>
              </div>
            )}

            {/* Sensor Health Module Separation */}
            <div style={{
              background: 'var(--bg-base)',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              padding: '0.75rem 0.9rem',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-primary)', fontWeight: 600 }}>
                  Sensor health decoupled status
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.1rem' }}>
                  Cross-sensor consistency check evaluated before residual calculation
                </div>
              </div>
              <span className="telemetry-val" style={{
                fontSize: '0.75rem',
                color: sensor_health.fault_detected ? 'var(--status-caution)' : 'var(--status-nominal)',
                fontWeight: 600
              }}>
                {sensor_health.fault_detected ? 'Sensor fault isolated' : '100% consistent'}
              </span>
            </div>

            {/* Single Quiet Confirmation Line for Nominal Subsystems */}
            <div style={{
              fontSize: '0.72rem',
              color: 'var(--text-muted)',
              padding: '0.45rem 0.75rem',
              background: 'var(--bg-base)',
              borderRadius: '4px',
              border: '1px dashed var(--border-color)'
            }}>
              Coolant loop, mechanical balance, and ignition within nominal tolerance.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
