import React, { useState, useEffect } from 'react';
import StatusPill from '../components/StatusPill';

export default function FleetView({ onInspectEngine }) {
  const [fleetData, setFleetData] = useState(null);
  const [correlations, setCorrelations] = useState(null);
  const [maintenanceQueue, setMaintenanceQueue] = useState(null);
  const [federatedStatus, setFederatedStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isSimulating, setIsSimulating] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);

  const fetchFleetData = async () => {
    try {
      const [resStatus, resCorr, resMaint, resFed] = await Promise.all([
        fetch('/api/fleet/status').then(r => r.json()),
        fetch('/api/fleet/correlations').then(r => r.json()),
        fetch('/api/fleet/maintenance_queue').then(r => r.json()),
        fetch('/api/fleet/federated_status').then(r => r.json())
      ]);

      if (resStatus?.fleet) setFleetData(resStatus.fleet);
      if (resCorr?.correlation_analysis) setCorrelations(resCorr.correlation_analysis);
      if (resMaint?.schedule) setMaintenanceQueue(resMaint.schedule);
      if (resFed) setFederatedStatus(resFed);
      setLoading(false);
    } catch (err) {
      console.error('Fleet Ground Station fetch error:', err);
    }
  };

  useEffect(() => {
    fetchFleetData();
    const interval = setInterval(fetchFleetData, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleSimulateSystemic = async (eventType) => {
    setIsSimulating(true);
    try {
      const res = await fetch('/api/fleet/simulate_systemic_event', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_type: eventType,
          affected_engines: ['ENG-MALE-01', 'ENG-MALE-03', 'ENG-MALE-06']
        })
      });
      const data = await res.json();
      setActionMessage(data.message || 'Systemic scenario active');
      await fetchFleetData();
      setTimeout(() => setActionMessage(null), 5000);
    } catch (e) {
      console.error(e);
    } finally {
      setIsSimulating(false);
    }
  };

  const handleClearSystemic = async () => {
    try {
      await fetch('/api/fleet/clear_systemic_event', { method: 'POST' });
      setActionMessage('Systemic correlation alert cleared.');
      await fetchFleetData();
      setTimeout(() => setActionMessage(null), 4000);
    } catch (e) {
      console.error(e);
    }
  };

  if (loading && !fleetData) {
    return (
      <div className="titan-card" style={{ textAlign: 'center', padding: '3.5rem' }}>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Acquiring swarm telemetry datalink...</p>
      </div>
    );
  }

  const {
    total_uavs = 8,
    operational_count = 0,
    degraded_count = 0,
    critical_count = 0,
    fleet_readiness_pct = 100,
    average_hi_engine = 1.0,
    min_rul_hours = 200,
    lowest_rul_engine = 'ENG-MALE-01',
    agent_summaries = []
  } = fleetData || {};

  const systemicAlert = correlations?.systemic_alert;
  const hasSystemic = correlations?.has_systemic_anomaly;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.15rem' }}>
      {/* Fleet Ground Station Command Header */}
      <div className="titan-card" style={{ padding: '1.2rem 1.4rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <div style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: hasSystemic ? 'var(--status-critical)' : 'var(--status-nominal)'
              }} />
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                Fleet overview & cross-engine correlation
              </h2>
              <span style={{
                fontSize: '0.7rem',
                fontFamily: 'var(--font-mono)',
                color: 'var(--accent-green)',
                background: 'var(--status-nominal-bg)',
                padding: '0.15rem 0.45rem',
                borderRadius: '3px',
                border: '1px solid var(--accent-green)',
                fontWeight: 600
              }}>
                Swarm GCS tier-2
              </span>
            </div>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: '0.25rem 0 0 0' }}>
              Autonomous multi-agent digital twins • DRDO TAPAS-BH-201 squadron rollup
            </p>
          </div>

          {/* Quick Simulation Injectors */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Scenario injection:</span>
            <button
              onClick={() => handleSimulateSystemic('CONTAMINATED_FUEL_BATCH')}
              disabled={isSimulating}
              className="titan-btn titan-btn-outline"
              style={{ fontSize: '0.75rem', padding: '0.35rem 0.65rem' }}
              title="Simulate contaminated fuel batch across multiple UAVs"
            >
              Simulate fuel contamination
            </button>
            <button
              onClick={() => handleSimulateSystemic('MANUFACTURING_LOT_DEFECT')}
              disabled={isSimulating}
              className="titan-btn titan-btn-outline"
              style={{ fontSize: '0.75rem', padding: '0.35rem 0.65rem' }}
              title="Simulate crankshaft bearing manufacturing defect"
            >
              Simulate bearing lot defect
            </button>
            {hasSystemic && (
              <button
                onClick={handleClearSystemic}
                className="titan-btn titan-btn-primary"
                style={{ fontSize: '0.75rem', padding: '0.35rem 0.65rem' }}
              >
                Clear event
              </button>
            )}
          </div>
        </div>

        <div className="header-accent-rule" />

        {actionMessage && (
          <div style={{
            marginTop: '0.5rem',
            padding: '0.45rem 0.75rem',
            background: 'var(--status-nominal-bg)',
            border: '1px solid var(--accent-green)',
            borderRadius: '4px',
            fontSize: '0.78rem',
            color: 'var(--accent-green)',
            fontFamily: 'var(--font-mono)'
          }}>
            {actionMessage}
          </div>
        )}
      </div>

      {/* Swarm Readiness Metrics Row */}
      <div className="grid-cols-4">
        <div className="titan-card">
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Fleet readiness</div>
          <div className="telemetry-val" style={{
            fontSize: '1.7rem',
            color: fleet_readiness_pct > 80 ? 'var(--status-nominal)' : 'var(--status-caution)',
            marginTop: '0.15rem'
          }}>
            {fleet_readiness_pct}%
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>
            {operational_count} GO · {degraded_count} CAUTION · {critical_count} NO-GO
          </div>
        </div>

        <div className="titan-card">
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Average health index</div>
          <div className="telemetry-val" style={{
            fontSize: '1.7rem',
            color: average_hi_engine >= 0.85 ? 'var(--status-nominal)' : 'var(--status-caution)',
            marginTop: '0.15rem'
          }}>
            {(average_hi_engine * 100).toFixed(1)}%
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>
            Swarm aggregate HI_engine
          </div>
        </div>

        <div className="titan-card">
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Minimum fleet RUL</div>
          <div className="telemetry-val" style={{
            fontSize: '1.7rem',
            color: min_rul_hours > 50 ? 'var(--text-primary)' : 'var(--status-critical)',
            marginTop: '0.15rem'
          }}>
            {min_rul_hours} <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>hours</span>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>
            Limiting asset: <strong style={{ color: 'var(--text-primary)' }}>{lowest_rul_engine}</strong>
          </div>
        </div>

        <div className="titan-card">
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Tactical datalink bandwidth</div>
          <div className="telemetry-val" style={{ fontSize: '1.7rem', color: 'var(--status-nominal)', marginTop: '0.15rem' }}>
            91.5%
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>
            Saved via compressed health summary
          </div>
        </div>
      </div>

      {/* Cross-Engine Systemic Correlation Alert Banner */}
      {hasSystemic && systemicAlert ? (
        <div style={{
          background: 'var(--status-critical-bg)',
          border: '1.5px solid var(--status-critical-border)',
          borderRadius: '6px',
          padding: '1rem 1.25rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
            <div style={{ flex: 1, minWidth: '280px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{
                  background: 'var(--status-critical)',
                  color: '#ffffff',
                  fontSize: '0.68rem',
                  fontWeight: 700,
                  padding: '0.15rem 0.45rem',
                  borderRadius: '3px',
                  fontFamily: 'var(--font-mono)'
                }}>
                  SYSTEMIC INCIDENT DETECTED
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--status-critical)', fontWeight: 600 }}>
                  Correlation score: {(systemicAlert.correlation_score * 100).toFixed(0)}%
                </span>
              </div>

              <h3 style={{ fontSize: '1.05rem', color: 'var(--status-critical)', marginTop: '0.4rem', marginBottom: '0.25rem', fontWeight: 700 }}>
                {systemicAlert.title}
              </h3>

              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                {systemicAlert.root_cause_hypothesis}
              </p>

              <div style={{
                marginTop: '0.65rem',
                padding: '0.55rem 0.75rem',
                background: 'var(--bg-base)',
                borderRadius: '4px',
                borderLeft: '3px solid var(--status-critical)',
                fontSize: '0.78rem',
                color: 'var(--status-critical)'
              }}>
                <strong>Tactical directive:</strong> {systemicAlert.tactical_action_recommendation}
              </div>
            </div>

            <div style={{ minWidth: '200px', background: 'var(--bg-base)', padding: '0.85rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Affected aircraft units</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', marginTop: '0.4rem' }}>
                {systemicAlert.affected_engines?.map(engId => (
                  <div key={engId} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--status-critical)', fontWeight: 600 }}>{engId}</span>
                    <button
                      onClick={() => onInspectEngine && onInspectEngine(engId)}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: 'var(--accent-green)',
                        fontSize: '0.72rem',
                        cursor: 'pointer',
                        fontWeight: 600
                      }}
                    >
                      Inspect twin →
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div style={{
          background: 'var(--status-nominal-bg)',
          border: '1px solid var(--status-nominal-border)',
          borderRadius: '6px',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          padding: '0.75rem 1.15rem'
        }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--status-nominal)' }} />
          <div style={{ fontSize: '0.78rem', color: 'var(--status-nominal)', fontWeight: 600 }}>
            <strong>Cross-engine correlation nominal:</strong> No multi-aircraft systemic failure patterns detected across active squadron. Engine wear curves are uncorrelated and follow independent component physics.
          </div>
        </div>
      )}

      {/* Fleet Health Map (Grid of UAV Cards) */}
      <div className="titan-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
          <div>
            <h3 style={{ fontSize: '0.98rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
              Squadron health map (sorted by risk)
            </h3>
            <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', margin: '0.15rem 0 0 0' }}>
              Real-time compressed health uplinks from onboard digital twin agents
            </p>
          </div>
          <span style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
            Active fleet: {agent_summaries.length} UAVs
          </span>
        </div>

        <div className="header-accent-rule" />

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(290px, 1fr))', gap: '0.85rem' }}>
          {agent_summaries.map(agent => {
            const hi = agent.hi_engine || 1.0;
            const hiColor = hi >= 0.88 ? 'var(--status-nominal)' : hi >= 0.70 ? 'var(--status-caution)' : 'var(--status-critical)';

            return (
              <div
                key={agent.engine_id}
                style={{
                  background: 'var(--bg-base)',
                  border: `1.5px solid ${agent.tactical_status === 'NO-GO' ? 'var(--status-critical-border)' : agent.tactical_status === 'CAUTION' ? 'var(--status-caution-border)' : 'var(--border-color)'}`,
                  borderRadius: '6px',
                  padding: '0.9rem',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.65rem'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {agent.engine_id}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                      {agent.engine_name} · <span>{agent.flight_phase}</span>
                    </div>
                  </div>
                  <StatusPill status={agent.tactical_status} label={agent.tactical_status} />
                </div>

                {/* Overall Health Bar */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', marginBottom: '0.25rem' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Health index (HI_engine)</span>
                    <span className="telemetry-val" style={{ color: hiColor }}>
                      {(hi * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div style={{ height: '5px', background: 'var(--border-subtle)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ width: `${Math.max(5, hi * 100)}%`, height: '100%', background: hiColor }} />
                  </div>
                </div>

                {/* Subsystem Mini Bars */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.35rem', textAlign: 'center' }}>
                  {['thermal', 'lubrication', 'mechanical', 'combustion'].map(sub => {
                    const subVal = agent.hi_subsystems?.[sub] ?? 1.0;
                    const subCol = subVal >= 0.88 ? 'var(--status-nominal)' : subVal >= 0.70 ? 'var(--status-caution)' : 'var(--status-critical)';
                    return (
                      <div key={sub} style={{ background: 'var(--bg-surface-1)', padding: '0.25rem', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                        <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                          {sub.substring(0, 4)}
                        </div>
                        <div className="telemetry-val" style={{ fontSize: '0.72rem', color: subCol }}>
                          {(subVal * 100).toFixed(0)}%
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* RUL and Active Fault */}
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  background: 'var(--bg-surface-1)',
                  padding: '0.4rem 0.6rem',
                  borderRadius: '4px',
                  border: '1px solid var(--border-subtle)',
                  fontSize: '0.72rem'
                }}>
                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>RUL: </span>
                    <strong style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                      {agent.rul_hours}h
                    </strong>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.68rem', marginLeft: '0.25rem' }}>
                      [{agent.rul_conformal_interval_90?.[0]}–{agent.rul_conformal_interval_90?.[1]}h]
                    </span>
                  </div>
                  <div>
                    <span style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.68rem',
                      fontWeight: 600,
                      color: agent.predicted_fault === 'NORMAL' ? 'var(--status-nominal)' : 'var(--status-critical)'
                    }}>
                      {agent.predicted_fault}
                    </span>
                  </div>
                </div>

                {/* Deep link button */}
                <button
                  onClick={() => onInspectEngine && onInspectEngine(agent.engine_id)}
                  className="titan-btn titan-btn-outline"
                  style={{
                    width: '100%',
                    padding: '0.35rem',
                    fontSize: '0.72rem',
                    marginTop: 'auto'
                  }}
                >
                  Inspect agent twin →
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Fleet Maintenance Priority Queue & Mission Allocator */}
      <div className="titan-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div>
            <h3 style={{ fontSize: '0.98rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
              Fleet maintenance priority queue & sortie allocation
            </h3>
            <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', margin: '0.15rem 0 0 0' }}>
              Automated depot slot allocation, turnaround schedule, and mission matching based on RUL & degradation kinetics
            </p>
          </div>
          <div style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
            Depot capacity: <strong style={{ color: 'var(--text-primary)' }}>{maintenanceQueue?.active_depot_occupancy || 0} / {maintenanceQueue?.total_depot_bays || 2} bays active</strong>
          </div>
        </div>

        <div className="header-accent-rule" />

        <div style={{ overflowX: 'auto' }}>
          <table className="titan-table">
            <thead>
              <tr>
                <th>Priority</th>
                <th>Engine ID</th>
                <th>Urgency tier</th>
                <th>Score</th>
                <th>HI_engine</th>
                <th>RUL</th>
                <th>Depot bay</th>
                <th>Recommended action</th>
                <th>Downtime</th>
                <th>Tactical sortie allocation</th>
              </tr>
            </thead>
            <tbody>
              {maintenanceQueue?.queue?.map(item => {
                const isGrounded = item.urgency_tier === 'IMMEDIATE_GROUND';
                const isCritical = item.urgency_tier === 'CRITICAL_DEPOT';
                const tierColor = isGrounded ? 'var(--status-critical)' : isCritical ? 'var(--status-caution)' : 'var(--text-secondary)';

                return (
                  <tr key={item.engine_id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-primary)' }}>
                      #{item.priority_rank}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                      {item.engine_id}
                    </td>
                    <td>
                      <span style={{
                        fontSize: '0.68rem',
                        fontWeight: 700,
                        color: tierColor,
                        padding: '0.15rem 0.4rem',
                        borderRadius: '3px',
                        background: 'var(--bg-surface-1)',
                        border: `1px solid ${tierColor}`
                      }}>
                        {item.urgency_tier}
                      </span>
                    </td>
                    <td className="telemetry-val">
                      {item.urgency_score}
                    </td>
                    <td className="telemetry-val" style={{ color: item.hi_engine < 0.8 ? 'var(--status-critical)' : 'var(--text-primary)' }}>
                      {(item.hi_engine * 100).toFixed(1)}%
                    </td>
                    <td className="telemetry-val" style={{ color: 'var(--text-primary)' }}>
                      {item.rul_hours}h
                    </td>
                    <td style={{ fontSize: '0.75rem', color: item.depot_bay_assigned ? 'var(--status-caution)' : 'var(--text-muted)' }}>
                      {item.depot_bay_assigned || 'On standby'}
                    </td>
                    <td style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', maxWidth: '260px' }}>
                      {item.recommended_action}
                    </td>
                    <td className="telemetry-val" style={{ fontSize: '0.75rem' }}>
                      {item.estimated_downtime_hours}h
                    </td>
                    <td style={{
                      fontSize: '0.75rem',
                      fontWeight: 500,
                      color: item.assigned_mission_recommendation?.includes('DO NOT FLY') ? 'var(--status-critical)' : item.assigned_mission_recommendation?.includes('18h') ? 'var(--status-nominal)' : 'var(--text-secondary)'
                    }}>
                      {item.assigned_mission_recommendation}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Federated Learning Coordinator Architecture Preview */}
      <div className="titan-card" style={{ padding: '0.9rem 1.15rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{
                fontSize: '0.68rem',
                fontFamily: 'var(--font-mono)',
                background: 'var(--status-envelope-bg)',
                color: 'var(--status-envelope)',
                padding: '0.15rem 0.45rem',
                borderRadius: '3px',
                border: '1px solid var(--status-envelope-border)',
                fontWeight: 600
              }}>
                Future scope architecture
              </span>
              <h4 style={{ fontSize: '0.9rem', color: 'var(--text-primary)', margin: 0, fontWeight: 700 }}>
                Federated learning coordinator (DRDO edge-privacy protocol)
              </h4>
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
              {federatedStatus?.data_locality_enforcement?.defence_compliance} • Algorithm: {federatedStatus?.aggregation_strategy}
            </p>
          </div>

          <div style={{ display: 'flex', gap: '1.25rem', fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
            <div>
              Training round: <strong style={{ color: 'var(--text-primary)' }}>#{federatedStatus?.current_training_round || 4}</strong>
            </div>
            <div>
              Differential privacy ε: <strong style={{ color: 'var(--text-primary)' }}>{federatedStatus?.data_locality_enforcement?.epsilon || 1.5}</strong>
            </div>
            <div>
              Raw telemetry egress: <strong style={{ color: 'var(--status-nominal)' }}>0% (BLOCKED BY POLICY)</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
