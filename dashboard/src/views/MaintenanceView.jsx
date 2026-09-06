import React, { useState, useEffect } from 'react';
import StatusPill from '../components/StatusPill';

export default function MaintenanceView({ frame, onRefresh }) {
  const [advisories, setAdvisories] = useState(null);
  const [history, setHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [resetMessage, setResetMessage] = useState('');

  const fetchAdvisories = async () => {
    try {
      const res = await fetch('/api/advisory/active');
      const data = await res.json();
      setAdvisories(data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchHistory = async () => {
    try {
      const res = await fetch('/api/advisory/history');
      const data = await res.json();
      setHistory(data.history || []);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchAdvisories();
    fetchHistory();
  }, [frame?.timestamp]);

  const handleApplyReset = async (actionType) => {
    if (!frame) return;
    setIsLoading(true);
    try {
      const res = await fetch('/api/advisory/apply_reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          engine_id: frame.engine_id,
          action_type: actionType,
          technician: 'Flight line maintenance officer (UAV squadron)'
        })
      });
      const data = await res.json();
      setResetMessage(`Executed: ${actionType}. Relevant subsystem health reset.`);
      setTimeout(() => setResetMessage(''), 4000);
      fetchAdvisories();
      fetchHistory();
      if (onRefresh) onRefresh();
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  if (!frame) return null;

  const { predictions = {}, health_index = {}, engine_id } = frame;
  const subsystems = health_index.subsystems || { thermal: 1.0, lubrication: 1.0, mechanical: 1.0, combustion: 1.0 };
  const rul_hours = predictions.rul_hours || 140;
  const rul_ci = predictions.rul_conformal_interval_90 || [120, 160];
  const rulMargin = ((rul_ci[1] - rul_ci[0]) / 2).toFixed(1);

  // Map subsystem scores to PRD Section 17 degradation stages
  const getDegradationStage = (score) => {
    if (score >= 0.88) return { stage: 'Healthy', color: 'var(--status-nominal)', pct: score };
    if (score >= 0.75) return { stage: 'Incipient', color: 'var(--status-caution)', pct: score };
    if (score >= 0.60) return { stage: 'Moderate', color: 'var(--status-caution)', pct: score };
    return { stage: 'Severe', color: 'var(--status-critical)', pct: score };
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.15rem' }}>
      {/* Top Banner: Remaining Useful Life with Calibrated Confidence Band */}
      <div className="titan-card" style={{ padding: '1.2rem 1.4rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                Remaining useful life (RUL) prognostics
              </h2>
              <StatusPill status="nominal" label="90% PICP calibrated" />
            </div>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: '0.25rem 0 0 0' }}>
              Calibrated uncertainty envelope • Pinball loss estimation on multi-engine synthetic dataset
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'baseline', gap: '1rem' }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Estimated RUL</div>
              <div className="telemetry-val" style={{ fontSize: '2.1rem', fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1 }}>
                {rul_hours.toFixed(1)} <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>hours</span>
              </div>
            </div>
            <div style={{ background: 'var(--bg-base)', padding: '0.45rem 0.75rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>90% confidence band</div>
              <div className="telemetry-val" style={{ fontSize: '0.95rem', color: 'var(--text-primary)' }}>
                [{rul_ci[0].toFixed(1)} — {rul_ci[1].toFixed(1)}] h (±{rulMargin}h)
              </div>
            </div>
          </div>
        </div>

        <div className="header-accent-rule" />

        {/* Confidence Band Range Bar */}
        <div style={{ background: 'var(--bg-base)', padding: '0.75rem 1rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
            <span>0 hours (EoL)</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>Operating point: {rul_hours.toFixed(1)} h</span>
            <span>250 hours (Fresh overhaul)</span>
          </div>
          <div style={{ position: 'relative', height: '8px', background: 'var(--border-subtle)', borderRadius: '4px', overflow: 'hidden' }}>
            {/* Uncertainty band overlay */}
            <div style={{
              position: 'absolute',
              left: `${Math.max(0, (rul_ci[0] / 250) * 100)}%`,
              width: `${Math.min(100, ((rul_ci[1] - rul_ci[0]) / 250) * 100)}%`,
              height: '100%',
              background: 'var(--status-nominal-bg)',
              border: '1px solid var(--accent-green)',
              borderRadius: '2px'
            }} />
            {/* Point estimate marker */}
            <div style={{
              position: 'absolute',
              left: `${Math.max(0, Math.min(100, (rul_hours / 250) * 100))}%`,
              width: '4px',
              height: '100%',
              background: 'var(--text-primary)',
              borderRadius: '2px',
              transform: 'translateX(-50%)'
            }} />
          </div>
        </div>

        {resetMessage && (
          <div style={{
            marginTop: '0.75rem',
            padding: '0.5rem 0.85rem',
            background: 'var(--status-nominal-bg)',
            border: '1px solid var(--status-nominal-border)',
            borderRadius: '4px',
            fontSize: '0.78rem',
            color: 'var(--status-nominal)',
            fontFamily: 'var(--font-mono)'
          }}>
            {resetMessage}
          </div>
        )}
      </div>

      {/* Subsystem Degradation Stage Matrix (PRD Section 17) */}
      <div className="titan-card">
        <h3 style={{ fontSize: '0.98rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0, marginBottom: '0.2rem' }}>
          Subsystem degradation stage classification
        </h3>
        <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
          Classified per PRD Section 17: Healthy (&ge;88%) · Incipient (75–88%) · Moderate (60–75%) · Severe (&lt;60%)
        </p>

        <div className="header-accent-rule" />

        <div className="grid-cols-4">
          {[
            { name: 'Thermal circuit', key: 'thermal', score: subsystems.thermal },
            { name: 'Lubrication circuit', key: 'lubrication', score: subsystems.lubrication },
            { name: 'Combustion dynamics', key: 'combustion', score: subsystems.combustion },
            { name: 'Mechanical assembly', key: 'mechanical', score: subsystems.mechanical }
          ].map(item => {
            const { stage, color, pct } = getDegradationStage(item.score);
            return (
              <div key={item.key} style={{ background: 'var(--bg-base)', padding: '0.85rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', fontWeight: 500 }}>{item.name}</span>
                  <span style={{
                    fontSize: '0.68rem',
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 700,
                    color: color,
                    padding: '0.1rem 0.4rem',
                    borderRadius: '3px',
                    background: 'var(--bg-surface-1)',
                    border: `1px solid ${color}`
                  }}>
                    {stage}
                  </span>
                </div>
                <div className="telemetry-val" style={{ fontSize: '1.4rem', color: 'var(--text-primary)', marginTop: '0.4rem' }}>
                  {(pct * 100).toFixed(1)}%
                </div>
                <div style={{ height: '4px', background: 'var(--border-subtle)', borderRadius: '2px', overflow: 'hidden', marginTop: '0.5rem' }}>
                  <div style={{ width: `${pct * 100}%`, height: '100%', background: color }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Prescriptive Maintenance Advisories (Recommendations, PRD Section 23) */}
      <div className="grid-cols-2">
        {/* Active Advisory Card */}
        <div className="titan-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <div>
              <h3 style={{ fontSize: '0.98rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                Prescriptive maintenance advisory
              </h3>
              <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', margin: '0.15rem 0 0 0' }}>
                Operator advisory recommendation (PRD Section 23 compliance)
              </p>
            </div>
            <span style={{
              fontSize: '0.7rem',
              fontFamily: 'var(--font-mono)',
              color: advisories?.active_advisories?.length ? 'var(--status-caution)' : 'var(--status-nominal)',
              background: advisories?.active_advisories?.length ? 'var(--status-caution-bg)' : 'var(--status-nominal-bg)',
              padding: '0.15rem 0.5rem',
              borderRadius: '3px',
              border: `1px solid ${advisories?.active_advisories?.length ? 'var(--status-caution-border)' : 'var(--status-nominal-border)'}`
            }}>
              {advisories?.active_advisories?.length ? 'Action recommended' : 'No action required'}
            </span>
          </div>

          <div className="header-accent-rule" />

          {advisories?.active_advisories?.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {advisories.active_advisories.map((adv, idx) => (
                <div key={idx} style={{
                  background: 'var(--bg-base)',
                  border: '1.5px solid var(--status-caution-border)',
                  borderRadius: '6px',
                  padding: '0.85rem'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <span style={{
                        fontSize: '0.68rem',
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 700,
                        color: 'var(--status-caution)',
                        marginRight: '0.5rem'
                      }}>
                        [{adv.urgency || 'ELEVATED'}]
                      </span>
                      <strong style={{ fontSize: '0.84rem', color: 'var(--text-primary)' }}>
                        {adv.recommended_action}
                      </strong>
                    </div>
                  </div>

                  <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.45rem', lineHeight: 1.45 }}>
                    {adv.rationale}
                  </p>

                  <div style={{
                    marginTop: '0.65rem',
                    fontSize: '0.72rem',
                    color: 'var(--text-muted)',
                    fontFamily: 'var(--font-mono)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}>
                    <span>Estimated downtime: {adv.estimated_downtime_hours || 2.5} h</span>
                    <button
                      onClick={() => handleApplyReset(adv.action_type || 'OIL_FLUSH')}
                      disabled={isLoading}
                      className="titan-btn titan-btn-primary"
                      style={{ fontSize: '0.72rem', padding: '0.3rem 0.65rem' }}
                    >
                      Execute action & reset kinetics
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{
              background: 'var(--bg-base)',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              padding: '1.25rem',
              textAlign: 'center',
              color: 'var(--text-muted)',
              fontSize: '0.8rem'
            }}>
              No open maintenance advisories. All subsystems are tracking nominal kinetics.
            </div>
          )}
        </div>

        {/* Maintenance Audit Log & Historical Resets */}
        <div className="titan-card">
          <h3 style={{ fontSize: '0.98rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0, marginBottom: '0.2rem' }}>
            Maintenance audit log
          </h3>
          <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
            Permanent record of technician actions and health index resets (DO-178B compliance)
          </p>

          <div className="header-accent-rule" />

          <div style={{ maxHeight: '240px', overflowY: 'auto' }}>
            <table className="titan-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Action</th>
                  <th>Technician</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {history.length > 0 ? (
                  history.slice(-5).reverse().map((h, idx) => (
                    <tr key={idx}>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                        T+ {(h.timestamp / 3600).toFixed(1)}h
                      </td>
                      <td style={{ fontWeight: 500, fontSize: '0.78rem' }}>
                        {h.action_type}
                      </td>
                      <td style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {h.technician}
                      </td>
                      <td>
                        <span style={{ fontSize: '0.7rem', color: 'var(--status-nominal)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                          COMPLETED
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                      No prior maintenance logged in current sortie.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
