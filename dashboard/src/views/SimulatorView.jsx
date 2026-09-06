import React, { useState } from 'react';
import StatusPill from '../components/StatusPill';

export default function SimulatorView({ frame }) {
  const [profile, setProfile] = useState('endurance');
  const [duration, setDuration] = useState(12.0);
  const [tempOffset, setTempOffset] = useState(0.0);
  const [altCeiling, setAltCeiling] = useState(18000.0);
  const [faultInjection, setFaultInjection] = useState('NONE');
  const [simResult, setSimResult] = useState(null);
  const [isRunning, setIsRunning] = useState(false);

  const handleRunSimulation = async () => {
    setIsRunning(true);
    try {
      const res = await fetch('/api/mission/what_if', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          engine_id: frame?.engine_id || 'ENG-MALE-01',
          mission_profile: profile,
          duration_hours: duration,
          ambient_temp_offset_c: tempOffset,
          altitude_ceiling_ft: altCeiling,
          inject_fault: faultInjection !== 'NONE' ? faultInjection : null,
          fault_severity: faultInjection !== 'NONE' ? 0.65 : 0.0
        })
      });
      const data = await res.json();
      setSimResult(data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsRunning(false);
    }
  };

  const currentHi = frame?.health_index?.overall || 0.96;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.15rem' }}>
      {/* Header Banner */}
      <div className="titan-card" style={{ padding: '1.2rem 1.4rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
              Pre-mission what-if reliability simulator
            </h2>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: '0.25rem 0 0 0' }}>
              Simulates future flight profiles forward in time to project degradation kinetics and provide pre-flight clearance
            </p>
          </div>

          <button
            onClick={handleRunSimulation}
            disabled={isRunning}
            className="titan-btn titan-btn-primary"
            style={{ padding: '0.55rem 1.25rem', fontSize: '0.85rem' }}
          >
            {isRunning ? 'Running simulation...' : 'Run what-if simulation'}
          </button>
        </div>

        <div className="header-accent-rule" />
      </div>

      {/* Simulator Inputs Grid */}
      <div className="grid-cols-2">
        {/* Mission Profile Selection */}
        <div className="titan-card">
          <h3 style={{ fontSize: '0.98rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0, marginBottom: '0.2rem' }}>
            Mission profile configuration
          </h3>
          <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
            Select tactical archetype and operational envelope bounds
          </p>

          <div className="header-accent-rule" />

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.35rem', fontWeight: 600 }}>
                Profile archetype
              </label>
              <select
                value={profile}
                onChange={(e) => setProfile(e.target.value)}
                style={{
                  width: '100%',
                  background: 'var(--bg-base)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '5px',
                  padding: '0.5rem 0.75rem',
                  fontSize: '0.8rem',
                  outline: 'none'
                }}
              >
                <option value="endurance">Strategic ISR (18-hour endurance loiter)</option>
                <option value="hot_weather">Desert detachment (ISA +15°C ambient thermal stress)</option>
                <option value="high_altitude">High-altitude ceiling (FL240 turbocharger surge stress)</option>
                <option value="rapid_response">Rapid tactical dash (100% continuous throttle)</option>
              </select>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.3rem' }}>
                <span>Sortie duration</span>
                <span className="telemetry-val" style={{ color: 'var(--text-primary)' }}>{duration} hours</span>
              </div>
              <input
                type="range"
                min={2}
                max={20}
                step={0.5}
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
              />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.3rem' }}>
                <span>Ambient temperature offset (ISA delta)</span>
                <span className="telemetry-val" style={{ color: 'var(--text-primary)' }}>
                  {tempOffset >= 0 ? `+${tempOffset}` : tempOffset} °C
                </span>
              </div>
              <input
                type="range"
                min={-15}
                max={25}
                step={1}
                value={tempOffset}
                onChange={(e) => setTempOffset(Number(e.target.value))}
              />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.3rem' }}>
                <span>Operating ceiling</span>
                <span className="telemetry-val" style={{ color: 'var(--text-primary)' }}>{altCeiling.toLocaleString()} ft</span>
              </div>
              <input
                type="range"
                min={5000}
                max={24000}
                step={1000}
                value={altCeiling}
                onChange={(e) => setAltCeiling(Number(e.target.value))}
              />
            </div>
          </div>
        </div>

        {/* Projected Outcome Panel (Generated on Demand) */}
        <div className="titan-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.2rem' }}>
            <div>
              <h3 style={{ fontSize: '0.98rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                Projected mission outcome
              </h3>
              <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', margin: '0.15rem 0 0 0' }}>
                On-demand simulation projection
              </p>
            </div>
            {simResult && (
              <StatusPill
                status={simResult.tactical_clearance?.recommendation === 'GO' ? 'nominal' : 'caution'}
                label={simResult.tactical_clearance?.recommendation || 'CLEARANCE'}
              />
            )}
          </div>

          <div className="header-accent-rule" />

          {simResult ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: '0.75rem',
                background: 'var(--bg-base)',
                padding: '0.85rem',
                borderRadius: '6px',
                border: '1px solid var(--border-color)'
              }}>
                <div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Projected health at landing</div>
                  <div className="telemetry-val" style={{ fontSize: '1.4rem', color: simResult.projected_health_index < 0.75 ? 'var(--status-critical)' : 'var(--status-nominal)' }}>
                    {(simResult.projected_health_index * 100).toFixed(1)}%
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    Delta: -{((currentHi - simResult.projected_health_index) * 100).toFixed(1)}% HI
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Remaining useful life impact</div>
                  <div className="telemetry-val" style={{ fontSize: '1.4rem', color: 'var(--text-primary)' }}>
                    {simResult.projected_rul_hours?.toFixed(1)} <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>h</span>
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    -{duration}h operating wear
                  </div>
                </div>
              </div>

              {/* Clearance Advisory Text */}
              <div style={{
                background: simResult.tactical_clearance?.recommendation === 'GO' ? 'var(--status-nominal-bg)' : 'var(--status-caution-bg)',
                border: `1.5px solid ${simResult.tactical_clearance?.recommendation === 'GO' ? 'var(--status-nominal-border)' : 'var(--status-caution-border)'}`,
                borderRadius: '5px',
                padding: '0.85rem',
                fontSize: '0.78rem',
                color: 'var(--text-secondary)',
                lineHeight: 1.45
              }}>
                <strong style={{ color: 'var(--text-primary)', display: 'block', marginBottom: '0.25rem' }}>
                  Pre-flight operational assessment:
                </strong>
                {simResult.tactical_clearance?.rationale || 'Engine cleared for scheduled profile.'}
              </div>
            </div>
          ) : (
            <div style={{
              background: 'var(--bg-base)',
              border: '1px dashed var(--border-color)',
              borderRadius: '6px',
              padding: '2.5rem 1rem',
              textAlign: 'center',
              color: 'var(--text-muted)',
              fontSize: '0.8rem'
            }}>
              Adjust sortie profile sliders and click "Run what-if simulation" to compute projected degradation kinetics.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
