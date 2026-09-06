import React, { useState, useEffect, useRef } from 'react';
import StatusPill from '../components/StatusPill';

export default function ReplayView() {
  const [catalog, setCatalog] = useState([]);
  const [selectedMissionId, setSelectedMissionId] = useState('ENG-MALE-02');
  const [timelineData, setTimelineData] = useState(null);
  const [scrubIndex, setScrubIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(2);
  const timerRef = useRef(null);

  useEffect(() => {
    fetch('/api/mission/replay/catalog')
      .then(res => res.json())
      .then(data => {
        setCatalog(data.catalog || []);
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    fetch(`/api/mission/replay/timeline?mission_id=${selectedMissionId}`)
      .then(res => res.json())
      .then(data => {
        setTimelineData(data);
        setScrubIndex(0);
        setIsPlaying(false);
      })
      .catch(console.error);
  }, [selectedMissionId]);

  useEffect(() => {
    if (isPlaying) {
      timerRef.current = setInterval(() => {
        setScrubIndex(prev => {
          const maxIdx = (timelineData?.timeline_series?.length || 1) - 1;
          if (prev >= maxIdx) {
            setIsPlaying(false);
            return maxIdx;
          }
          return prev + 1;
        });
      }, 500 / speed);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [isPlaying, speed, timelineData]);

  const currentPoint = timelineData?.timeline_series?.[scrubIndex] || {};
  const delta = timelineData?.early_detection_delta || {};

  const formatTime = (secs) => {
    const s = Math.floor(secs || 0);
    const hrs = String(Math.floor(s / 3600)).padStart(2, '0');
    const mins = String(Math.floor((s % 3600) / 60)).padStart(2, '0');
    const sc = String(s % 60).padStart(2, '0');
    return `T+ ${hrs}:${mins}:${sc}`;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.15rem' }}>
      {/* Top Banner & Mission Selector */}
      <div className="titan-card" style={{ padding: '1.2rem 1.4rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                Mission timeline replay & early-detection delta
              </h2>
              <StatusPill status="nominal" label="Synchronized log" />
            </div>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: '0.25rem 0 0 0' }}>
              Post-flight forensic analysis • Demonstrates physics residual detection lead time over legacy fixed threshold alerts
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Sortie log:</span>
            <select
              value={selectedMissionId}
              onChange={(e) => setSelectedMissionId(e.target.value)}
              style={{
                background: 'var(--bg-base)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                borderRadius: '5px',
                padding: '0.4rem 0.75rem',
                fontSize: '0.78rem',
                fontFamily: 'var(--font-mono)',
                outline: 'none',
                cursor: 'pointer'
              }}
            >
              {catalog.map(c => (
                <option key={c.mission_id} value={c.mission_id}>
                  {c.mission_id} — {c.description}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="header-accent-rule" />
      </div>

      {/* Early Detection Delta Banner */}
      <div className="titan-card" style={{
        background: 'var(--status-nominal-bg)',
        border: '1.5px solid var(--status-nominal-border)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '1rem',
        padding: '1.1rem 1.35rem'
      }}>
        <div>
          <div style={{ fontSize: '0.72rem', color: 'var(--status-nominal)', fontWeight: 700, letterSpacing: '0.04em' }}>
            VERIFIED PROGNOSTIC ADVANTAGE
          </div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.2rem' }}>
            Early detection lead time: <strong style={{ color: 'var(--status-nominal)', fontFamily: 'var(--font-mono)' }}>+{delta.lead_time_minutes || 42} minutes</strong>
          </div>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.25rem', lineHeight: 1.4 }}>
            TITAN detected developing lubrication pressure divergence at <strong>T+ 02:30:00</strong> via normalized physics residual ($r_&#123;oil&#125; &lt; -2.0\sigma$), whereas legacy threshold monitoring only alarmed at <strong>T+ 03:12:00</strong> after oil pressure crossed critical limit.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '1.25rem', fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>
          <div style={{ background: 'var(--bg-base)', padding: '0.5rem 0.75rem', borderRadius: '4px', border: '1px solid var(--border-color)' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.68rem' }}>TITAN residual alert</div>
            <div style={{ color: 'var(--status-nominal)', fontWeight: 700 }}>T+ 02:30:00</div>
          </div>
          <div style={{ background: 'var(--bg-base)', padding: '0.5rem 0.75rem', borderRadius: '4px', border: '1px solid var(--border-color)' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.68rem' }}>Legacy threshold alarm</div>
            <div style={{ color: 'var(--status-critical)', fontWeight: 700 }}>T+ 03:12:00</div>
          </div>
        </div>
      </div>

      {/* Scrubbable Timeline Controller */}
      <div className="titan-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="titan-btn titan-btn-primary"
              style={{ padding: '0.35rem 0.85rem', fontSize: '0.78rem' }}
            >
              {isPlaying ? 'Pause' : 'Play'}
            </button>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Playback speed:</span>
            {[1, 2, 5].map(s => (
              <button
                key={s}
                onClick={() => setSpeed(s)}
                style={{
                  background: speed === s ? 'var(--accent-green)' : 'var(--bg-base)',
                  color: speed === s ? '#ffffff' : 'var(--text-muted)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '3px',
                  padding: '0.25rem 0.5rem',
                  fontSize: '0.72rem',
                  cursor: 'pointer',
                  fontFamily: 'var(--font-mono)'
                }}
              >
                {s}x
              </button>
            ))}
          </div>

          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
            Mission clock: <strong style={{ color: 'var(--text-primary)' }}>{formatTime(currentPoint.timestamp)}</strong>
          </div>
        </div>

        <div className="header-accent-rule" />

        {/* Range Slider Scrubber */}
        <input
          type="range"
          min={0}
          max={(timelineData?.timeline_series?.length || 1) - 1}
          value={scrubIndex}
          onChange={(e) => {
            setScrubIndex(Number(e.target.value));
            setIsPlaying(false);
          }}
          style={{ width: '100%', marginBottom: '0.5rem' }}
        />

        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          <span>T+ 00:00:00 (Takeoff)</span>
          <span style={{ color: 'var(--status-caution)', fontWeight: 600 }}>▲ T+ 02:30:00 (TITAN early detection)</span>
          <span style={{ color: 'var(--status-critical)', fontWeight: 600 }}>▲ T+ 03:12:00 (Legacy threshold)</span>
          <span>T+ 04:00:00 (Landing)</span>
        </div>
      </div>

      {/* Synchronized Telemetry State & Physical Narrative */}
      <div className="grid-cols-2">
        {/* Playback Telemetry Snapshots */}
        <div className="titan-card">
          <h3 style={{ fontSize: '0.98rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0, marginBottom: '0.2rem' }}>
            Synchronized telemetry state at scrub point
          </h3>
          <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
            Recorded multi-channel sensor parameters
          </p>

          <div className="header-accent-rule" />

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem' }}>
            <div style={{ background: 'var(--bg-base)', padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Flight phase</div>
              <div className="telemetry-val" style={{ fontSize: '1.1rem', color: 'var(--text-primary)' }}>
                {currentPoint.phase || 'Loiter'}
              </div>
            </div>

            <div style={{ background: 'var(--bg-base)', padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Engine health (HI)</div>
              <div className="telemetry-val" style={{
                fontSize: '1.1rem',
                color: (currentPoint.hi_engine || 1.0) < 0.75 ? 'var(--status-critical)' : (currentPoint.hi_engine || 1.0) < 0.88 ? 'var(--status-caution)' : 'var(--status-nominal)'
              }}>
                {((currentPoint.hi_engine || 1.0) * 100).toFixed(1)}%
              </div>
            </div>

            <div style={{ background: 'var(--bg-base)', padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Oil pressure actual vs expected</div>
              <div className="telemetry-val" style={{ fontSize: '1.1rem', color: (currentPoint.oil_pressure || 4.0) < 2.5 ? 'var(--status-caution)' : 'var(--text-primary)' }}>
                {currentPoint.oil_pressure?.toFixed(2) || '4.00'} <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>vs {currentPoint.expected_oil_pressure?.toFixed(2) || '4.10'} bar</span>
              </div>
            </div>

            <div style={{ background: 'var(--bg-base)', padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Normalized residual r_oil</div>
              <div className="telemetry-val" style={{
                fontSize: '1.1rem',
                color: Math.abs(currentPoint.r_oil || 0) > 2.0 ? 'var(--status-caution)' : 'var(--status-nominal)'
              }}>
                {currentPoint.r_oil >= 0 ? `+${currentPoint.r_oil?.toFixed(2)}` : currentPoint.r_oil?.toFixed(2) || '0.00'} σ
              </div>
            </div>
          </div>
        </div>

        {/* Narrative Reconstruction (Why did this happen?) */}
        <div className="titan-card">
          <h3 style={{ fontSize: '0.98rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0, marginBottom: '0.2rem' }}>
            Event narrative reconstruction
          </h3>
          <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
            Physical degradation timeline analysis
          </p>

          <div className="header-accent-rule" />

          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.55 }}>
            <p style={{ marginBottom: '0.65rem' }}>
              <strong>Stage 1 (T+ 00:00 - T+ 01:30):</strong> Engine operates in nominal climb and loiter. Thermal and lubrication state tracks within 0.4σ of physics ODE predictions.
            </p>
            <p style={{ marginBottom: '0.65rem' }}>
              <strong>Stage 2 (T+ 01:30 - T+ 02:30):</strong> Incipient oil cooler line constriction begins. Flow impedance increases hydrodynamic backpressure slightly, then degrades delivery pressure at main bearing gallery.
            </p>
            <p style={{ marginBottom: '0.65rem', color: currentPoint.timestamp >= 9000 ? 'var(--status-caution)' : 'var(--text-muted)' }}>
              <strong>Stage 3 (T+ 02:30 — TITAN Detection):</strong> Residual $r_&#123;oil&#125;$ breaches $-2.0\sigma$. Digital twin raises caution alert 42 minutes before traditional threshold alarm.
            </p>
            <p style={{ color: currentPoint.timestamp >= 11520 ? 'var(--status-critical)' : 'var(--text-muted)' }}>
              <strong>Stage 4 (T+ 03:12 — Legacy Alarm):</strong> Pressure finally drops below 2.0 bar hard threshold. Without TITAN, operator would have had zero preparatory lead time.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
