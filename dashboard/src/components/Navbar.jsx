import React from 'react';
import StatusPill from './StatusPill';

export default function Navbar({
  currentView,
  onSelectView,
  activeEngineId,
  onSelectEngine,
  fleet = [],
  flightPhase = 'Loiter',
  tacticalStatus = 'GO',
  simTime = 9910,
  onOpenFaultModal,
  theme = 'light',
  onToggleTheme
}) {
  const views = [
    { id: 'operational', label: 'Operational' },
    { id: 'engineering', label: 'Engineering' },
    { id: 'maintenance', label: 'Maintenance' },
    { id: 'replay', label: 'Replay' },
    { id: 'simulator', label: 'Simulator' },
    { id: 'fleet', label: 'Fleet (swarm)' }
  ];

  // Live real-time station clock (HH:MM:SS) updating continuously every second
  const [realTime, setRealTime] = React.useState(() => {
    const now = new Date();
    return now.toLocaleTimeString('en-GB', { hour12: false });
  });

  React.useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setRealTime(now.toLocaleTimeString('en-GB', { hour12: false }));
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  // Format mission clock in monospace HH:MM:SS
  const formatClock = (seconds) => {
    const s = Math.floor(seconds || 0);
    const hrs = String(Math.floor(s / 3600)).padStart(2, '0');
    const mins = String(Math.floor((s % 3600) / 60)).padStart(2, '0');
    const secs = String(s % 60).padStart(2, '0');
    return `T+ ${hrs}:${mins}:${secs}`;
  };

  return (
    <header className="navbar">
      {/* Brand & Project Console Emblem */}
      <div className="brand-section">
        {/* Fixed 32x32 Team/Project Console Emblem Placeholder */}
        <div className="console-emblem" title="TITAN Operator Console">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="9" />
            <polygon points="12 2 15 8 21 9 17 14 18 20 12 17 6 20 7 14 3 9 9 8 12 2" stroke="currentColor" strokeWidth="1.5" />
            <circle cx="12" cy="12" r="2.5" fill="currentColor" />
          </svg>
        </div>
        <div>
          <div className="brand-title">TITAN ground control station</div>
          <div className="brand-subtitle">MALE-UAV propulsion digital twin</div>
        </div>
      </div>

      {/* Navigation Tabs (Sentence case, Forest green active state) */}
      <nav className="nav-tabs" aria-label="Console navigation">
        {views.map(v => (
          <button
            key={v.id}
            onClick={() => onSelectView(v.id)}
            className={`nav-tab ${currentView === v.id ? 'active' : ''}`}
          >
            {v.label}
          </button>
        ))}
      </nav>

      {/* Mission Clock & Tactical Telemetry Status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
        {/* Unit Selector */}
        <select
          value={activeEngineId}
          onChange={(e) => onSelectEngine(e.target.value)}
          aria-label="Select UAV Engine Unit"
          style={{
            background: 'var(--bg-base)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-color)',
            borderRadius: '5px',
            padding: '0.35rem 0.65rem',
            fontSize: '0.78rem',
            fontFamily: 'var(--font-mono)',
            outline: 'none',
            cursor: 'pointer'
          }}
        >
          {fleet.map(e => (
            <option key={e.engine_id} value={e.engine_id}>
              {e.engine_id} ({e.name.split('(')[0].trim()})
            </option>
          ))}
        </select>

        {/* Real-Time Master Station Clock & Mission Elapsed Time in Monospace */}
        <div style={{
          background: 'var(--bg-base)',
          padding: '0.35rem 0.65rem',
          borderRadius: '5px',
          border: '1px solid var(--border-color)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }} title="Real-time master station clock & mission elapsed time">
          <div className="stream-dot" title="Live stream telemetry active" />
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '0.80rem',
            color: 'var(--text-primary)',
            fontWeight: 700,
            letterSpacing: '0.02em'
          }}>
            {realTime}
          </span>
          <span style={{
            fontSize: '0.68rem',
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-muted)',
            borderLeft: '1px solid var(--border-color)',
            paddingLeft: '0.5rem',
            fontWeight: 500
          }}>
            {formatClock(simTime)}
          </span>
        </div>

        {/* Flight Phase */}
        <StatusPill status="envelope" label={flightPhase} />

        {/* Tactical Risk Status */}
        <StatusPill status={tacticalStatus} label={tacticalStatus} />

        {/* Theme Toggle (Standard Light / Dark Console) */}
        <button
          onClick={onToggleTheme}
          className="titan-btn titan-btn-outline"
          style={{ padding: '0.35rem 0.6rem', fontSize: '0.75rem' }}
          title={theme === 'light' ? 'Switch to dark console mode' : 'Switch to primary white/green console'}
        >
          {theme === 'light' ? (
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
            </svg>
          ) : (
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="5" />
              <line x1="12" y1="1" x2="12" y2="3" />
              <line x1="12" y1="21" x2="12" y2="23" />
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
              <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
              <line x1="1" y1="12" x2="3" y2="12" />
              <line x1="21" y1="12" x2="23" y2="12" />
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
              <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
            </svg>
          )}
          <span>{theme === 'light' ? 'Dark' : 'Light'}</span>
        </button>

        {/* Fault Injection Trigger Button */}
        <button
          onClick={onOpenFaultModal}
          className="titan-btn titan-btn-outline"
          style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem' }}
          title="Inject real-time FMEA fault mode"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
          </svg>
          <span>Inject fault</span>
        </button>
      </div>
    </header>
  );
}
