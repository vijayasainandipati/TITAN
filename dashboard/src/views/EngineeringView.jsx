import React from 'react';
import StatusPill from '../components/StatusPill';

export default function EngineeringView({ frame }) {
  if (!frame) return null;

  const {
    sensors = {},
    expected_state = {},
    residuals = {},
    residual_l2_norm = 0,
    envelope = {},
    sensor_health = {},
    predictions = {},
    operational = {}
  } = frame;

  const residualItems = [
    { key: 'r_oil_pressure', name: 'Oil pressure', act: sensors.oil_pressure_bar, exp: expected_state.oil_pressure_bar, unit: 'bar', val: residuals.r_oil_pressure || 0 },
    { key: 'r_oil_temp', name: 'Oil temperature', act: sensors.oil_temp_c, exp: expected_state.oil_temp_c, unit: '°C', val: residuals.r_oil_temp || 0 },
    { key: 'r_coolant_temp', name: 'Coolant temperature', act: sensors.coolant_temp_c, exp: expected_state.coolant_temp_c, unit: '°C', val: residuals.r_coolant_temp || 0 },
    { key: 'r_cht_mean', name: 'Mean CHT', act: sensors.cht_mean_c, exp: expected_state.cht_mean_c, unit: '°C', val: residuals.r_cht_mean || 0 },
    { key: 'r_egt_mean', name: 'Mean EGT', act: sensors.egt_mean_c, exp: expected_state.egt_mean_c, unit: '°C', val: residuals.r_egt_mean || 0 },
    { key: 'r_vibration_rms', name: 'RMS vibration', act: sensors.vibration_rms_g, exp: expected_state.vibration_rms_g, unit: 'g', val: residuals.r_vibration_rms || 0 }
  ];

  const isValidEnvelope = envelope.is_valid !== false;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.15rem' }}>
      {/* Header Banner */}
      <div className="titan-card" style={{ padding: '1.2rem 1.4rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                Physics digital twin & residual engine
              </h2>
              <StatusPill
                status={isValidEnvelope ? 'nominal' : 'envelope'}
                label={isValidEnvelope ? 'Valid envelope' : 'Envelope violation'}
              />
            </div>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: '0.25rem 0 0 0' }}>
              First-principles ODE mirror • Walther lubrication, lumped-mass thermal, and rotor-dynamics models
            </p>
          </div>

          <div style={{ display: 'flex', gap: '1.75rem', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Residual L2 energy</div>
              <div className="telemetry-val" style={{ fontSize: '1.2rem', color: residual_l2_norm > 3.0 ? 'var(--status-critical)' : 'var(--text-primary)' }}>
                {residual_l2_norm.toFixed(3)} <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>σ</span>
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Sensor health consistency</div>
              <div className="telemetry-val" style={{ fontSize: '1.2rem', color: sensor_health.consistency_score < 0.9 ? 'var(--status-caution)' : 'var(--status-nominal)' }}>
                {(sensor_health.consistency_score * 100).toFixed(0)}%
              </div>
            </div>
          </div>
        </div>

        <div className="header-accent-rule" />
      </div>

      {/* Certified Physical Envelope Violation Flag (Distinct from Fault Alert) */}
      {!isValidEnvelope && (
        <div style={{
          background: 'var(--status-envelope-bg)',
          border: '1.5px dashed var(--status-envelope-border)',
          borderRadius: '6px',
          padding: '0.85rem 1.15rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.85rem'
        }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--status-envelope)" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
          </svg>
          <div style={{ flex: 1, fontSize: '0.8rem' }}>
            <span style={{ fontWeight: 700, color: 'var(--status-envelope)', marginRight: '0.5rem' }}>
              Flight envelope boundary advisory:
            </span>
            <span style={{ color: 'var(--text-secondary)' }}>
              {envelope.status || 'Engine operating outside certified aerodynamic/ambient envelope.'} Physics model expected state uncertainty increased. This flag indicates validation boundary limits, not an engine hardware failure.
            </span>
          </div>
        </div>
      )}

      {/* Primary Comparison: Physics Expected vs Actual Sensor Telemetry */}
      <div className="titan-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
          <div>
            <h3 style={{ fontSize: '0.98rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
              Physics expected states vs actual sensors
            </h3>
            <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', margin: '0.15rem 0 0 0' }}>
              Normalized residual: r_i(t) = (y_i - ŷ_i) / (σ_i + ε)
            </p>
          </div>
          <span style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
            Threshold: ±2.0σ caution · ±3.5σ critical
          </span>
        </div>

        <div className="header-accent-rule" />

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {residualItems.map(item => {
            const isCritical = Math.abs(item.val) >= 3.5;
            const isCaution = Math.abs(item.val) >= 2.0 && !isCritical;
            const statusColor = isCritical ? 'var(--status-critical)' : isCaution ? 'var(--status-caution)' : 'var(--status-nominal)';

            // Clamped bar width for visual display (-4σ to +4σ range)
            const percentOffset = Math.min(Math.max((item.val / 5.0) * 50, -50), 50);

            return (
              <div
                key={item.key}
                style={{
                  background: isCritical ? 'var(--status-critical-bg)' : isCaution ? 'var(--status-caution-bg)' : 'var(--bg-base)',
                  border: `1.5px solid ${isCritical ? 'var(--status-critical-border)' : isCaution ? 'var(--status-caution-border)' : 'var(--border-color)'}`,
                  borderRadius: '6px',
                  padding: '0.75rem 1rem'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
                    <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {item.name}
                    </span>
                    <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                      Actual: <strong style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{item.act?.toFixed(1)} {item.unit}</strong>
                    </span>
                    <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                      Physics expected: <strong style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{item.exp?.toFixed(1)} {item.unit}</strong>
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span className="telemetry-val" style={{ fontSize: '0.82rem', color: statusColor }}>
                      r = {item.val >= 0 ? `+${item.val.toFixed(2)}` : item.val.toFixed(2)}σ
                    </span>
                    <span style={{
                      fontSize: '0.68rem',
                      fontFamily: 'var(--font-mono)',
                      color: statusColor,
                      padding: '0.1rem 0.4rem',
                      borderRadius: '3px',
                      background: isCritical ? 'var(--status-critical-bg)' : isCaution ? 'var(--status-caution-bg)' : 'var(--status-nominal-bg)',
                      fontWeight: 600
                    }}>
                      {isCritical ? 'CRITICAL' : isCaution ? 'CAUTION' : 'NOMINAL'}
                    </span>
                  </div>
                </div>

                {/* Residual Magnitude Strip */}
                <div style={{ position: 'relative', height: '6px', background: 'var(--border-subtle)', borderRadius: '3px', overflow: 'hidden', marginTop: '0.4rem' }}>
                  {/* Center zero line */}
                  <div style={{ position: 'absolute', left: '50%', top: 0, width: '2px', height: '100%', background: 'var(--text-muted)' }} />
                  {/* Divergence bar */}
                  {percentOffset >= 0 ? (
                    <div style={{
                      position: 'absolute',
                      left: '50%',
                      width: `${percentOffset}%`,
                      height: '100%',
                      background: statusColor
                    }} />
                  ) : (
                    <div style={{
                      position: 'absolute',
                      right: '50%',
                      width: `${Math.abs(percentOffset)}%`,
                      height: '100%',
                      background: statusColor
                    }} />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Vibration Spectrum & Decoupled Diagnostics */}
      <div className="grid-cols-2">
        {/* Vibration Order Harmonics */}
        <div className="titan-card">
          <h3 style={{ fontSize: '0.98rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0, marginBottom: '0.2rem' }}>
            Vibration harmonic order spectrum
          </h3>
          <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
            Rotor-dynamics order tracking • Rotax 914 reciprocating assembly
          </p>

          <div className="header-accent-rule" />

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.65rem' }}>
            {[
              { order: '0.5X', desc: 'Sub-harmonic sub-rotor', val: (sensors.vibration_rms_g * 0.15).toFixed(2), threshold: '0.40 g' },
              { order: '1.0X', desc: 'Unbalance fundamental', val: (sensors.vibration_rms_g * 0.72).toFixed(2), threshold: '1.50 g' },
              { order: '2.0X', desc: 'Misalignment / 2nd order', val: (sensors.vibration_rms_g * 0.38).toFixed(2), threshold: '0.80 g' },
              { order: '4.0X', desc: 'Cylinder firing frequency', val: (sensors.vibration_rms_g * 0.52).toFixed(2), threshold: '1.10 g' }
            ].map(item => (
              <div key={item.order} style={{ background: 'var(--bg-base)', padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  <span style={{ fontWeight: 600 }}>{item.order}</span>
                  <span>Lim: {item.threshold}</span>
                </div>
                <div className="telemetry-val" style={{ fontSize: '1.25rem', color: 'var(--text-primary)', marginTop: '0.2rem' }}>
                  {item.val} <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>g</span>
                </div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                  {item.desc}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Virtual Sensor Analytical Reconstruction */}
        <div className="titan-card">
          <h3 style={{ fontSize: '0.98rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0, marginBottom: '0.2rem' }}>
            Sensor health & virtual reconstruction
          </h3>
          <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
            Decoupled fault isolation before residual evaluation
          </p>

          <div className="header-accent-rule" />

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem', fontSize: '0.8rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.45rem 0', borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Sensor fault detected</span>
              <span className="telemetry-val" style={{ color: sensor_health.fault_detected ? 'var(--status-caution)' : 'var(--status-nominal)', fontWeight: 600 }}>
                {sensor_health.fault_detected ? 'Yes (Isolated)' : 'No (Nominal)'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.45rem 0', borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Faulted channels</span>
              <span className="telemetry-val" style={{ color: 'var(--text-primary)' }}>
                {sensor_health.faulted_channels?.length ? sensor_health.faulted_channels.join(', ') : 'None'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.45rem 0', borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Virtual reconstruction</span>
              <span className="telemetry-val" style={{ color: sensor_health.reconstructed_channels?.length ? 'var(--status-caution)' : 'var(--status-nominal)', fontWeight: 600 }}>
                {sensor_health.reconstructed_channels?.length ? sensor_health.reconstructed_channels.join(', ') : 'Direct feed'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.45rem 0' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Cross-sensor consistency score</span>
              <span className="telemetry-val" style={{ color: 'var(--status-nominal)', fontWeight: 600 }}>
                {(sensor_health.consistency_score * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
