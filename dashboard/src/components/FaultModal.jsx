import React, { useState } from 'react';

export default function FaultModal({ isOpen, onClose, onInject, activeEngineId }) {
  const [faultType, setFaultType] = useState('LUBE_DEGRADATION');
  const [severity, setSeverity] = useState(0.70);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const faults = [
    { id: 'NORMAL', name: 'Nominal baseline (clear faults)', desc: 'Clears all active degradation kinetics and returns to clean operation' },
    { id: 'LUBE_DEGRADATION', name: 'Incipient lubrication leak / gallery drop', desc: 'Simulates oil line leak, dropping pressure below expected Walther curve' },
    { id: 'MISFIRE', name: 'Cylinder #2 ignition misfire', desc: 'Simulates dropped spark cycles, dropping EGT and spiking 0.5X vibration' },
    { id: 'COOLING_DEGRADATION', name: 'Coolant radiator core fouling', desc: 'Restricts ram-air heat rejection, causing CHT and coolant temperature rise' },
    { id: 'BEARING_WEAR', name: 'Journal bearing spalling & clearance wear', desc: 'Increases hydrodynamic clearance, amplifying 1X/2X order harmonics' },
    { id: 'SENSOR_FAULT', name: 'Isolated oil pressure transducer drift', desc: 'Tests sensor health module by drifting sensor without engine degradation' }
  ];

  const handleSubmit = async () => {
    setIsSubmitting(true);
    await onInject(faultType, severity);
    setIsSubmitting(false);
    onClose();
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0, 0, 0, 0.65)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div className="titan-card" style={{ width: '560px', maxWidth: '92vw', padding: '1.5rem', background: 'var(--bg-base)', border: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
              Live FMEA fault injection
            </h3>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: '0.15rem 0 0 0' }}>
              Target engine: <strong style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{activeEngineId}</strong>
            </p>
          </div>
          <button onClick={onClose} className="titan-btn titan-btn-outline" style={{ padding: '0.25rem 0.55rem', fontSize: '0.75rem' }}>✕</button>
        </div>

        <div className="header-accent-rule" />

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem', marginBottom: '1.25rem' }}>
          {faults.map(f => {
            const isSelected = faultType === f.id;
            return (
              <div
                key={f.id}
                onClick={() => setFaultType(f.id)}
                style={{
                  padding: '0.65rem 0.85rem',
                  borderRadius: '6px',
                  border: `1.5px solid ${isSelected ? 'var(--accent-green)' : 'var(--border-color)'}`,
                  background: isSelected ? 'var(--status-nominal-bg)' : 'var(--bg-surface-1)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: isSelected ? 'var(--accent-green)' : 'var(--text-primary)' }}>
                  {f.name}
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
                  {f.desc}
                </div>
              </div>
            );
          })}
        </div>

        {faultType !== 'NORMAL' && (
          <div style={{ marginBottom: '1.25rem', background: 'var(--bg-surface-1)', padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.3rem' }}>
              <span>Fault severity factor</span>
              <span className="telemetry-val" style={{ color: 'var(--text-primary)' }}>{(severity * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range"
              min={0.2}
              max={1.0}
              step={0.05}
              value={severity}
              onChange={(e) => setSeverity(Number(e.target.value))}
            />
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
          <button onClick={onClose} className="titan-btn titan-btn-outline" style={{ fontSize: '0.8rem' }}>
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="titan-btn titan-btn-primary"
            style={{ fontSize: '0.8rem' }}
          >
            {isSubmitting ? 'Injecting...' : 'Inject fault mode'}
          </button>
        </div>
      </div>
    </div>
  );
}
