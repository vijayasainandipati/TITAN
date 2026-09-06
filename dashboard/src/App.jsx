import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import FleetView from './views/FleetView';
import OperationalView from './views/OperationalView';
import EngineeringView from './views/EngineeringView';
import MaintenanceView from './views/MaintenanceView';
import ReplayView from './views/ReplayView';
import SimulatorView from './views/SimulatorView';
import FaultModal from './components/FaultModal';

export default function App() {
  const [currentView, setCurrentView] = useState('operational');
  const [activeEngineId, setActiveEngineId] = useState('ENG-MALE-01');
  const [fleet, setFleet] = useState([]);
  const [frame, setFrame] = useState(null);
  const [isFaultModalOpen, setIsFaultModalOpen] = useState(false);
  const [isLiveActive, setIsLiveActive] = useState(true);
  const [theme, setTheme] = useState(() => localStorage.getItem('titan-theme') || 'light');

  // Synchronize theme with root DOM attribute
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('titan-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => (prev === 'light' ? 'dark' : 'light'));
  };

  // Fetch fleet list
  useEffect(() => {
    fetch('/api/telemetry/fleet')
      .then(res => res.json())
      .then(data => {
        setFleet(data.fleet || []);
        if (data.active_engine_id) {
          setActiveEngineId(data.active_engine_id);
        }
      })
      .catch(console.error);
  }, []);

  // Poll live telemetry stream
  useEffect(() => {
    if (!isLiveActive) return;

    const fetchTelemetry = async () => {
      try {
        const res = await fetch(`/api/telemetry/live?engine_id=${activeEngineId}`);
        const data = await res.json();
        setFrame(data);
      } catch (err) {
        console.error('Telemetry fetch error:', err);
      }
    };

    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 1200);
    return () => clearInterval(interval);
  }, [activeEngineId, isLiveActive]);

  const handleSelectEngine = async (engineId) => {
    setActiveEngineId(engineId);
    try {
      await fetch('/api/telemetry/select_engine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ engine_id: engineId })
      });
    } catch (e) {
      console.error(e);
    }
  };

  const handleInspectEngineFromFleet = (engineId) => {
    handleSelectEngine(engineId);
    setCurrentView('operational');
  };

  const handleInjectFault = async (faultType, severity) => {
    try {
      await fetch('/api/telemetry/inject_fault', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          engine_id: activeEngineId,
          fault_type: faultType,
          severity
        })
      });
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg-base)' }}>
      {/* Top Console Navigation */}
      <Navbar
        currentView={currentView}
        onSelectView={setCurrentView}
        activeEngineId={activeEngineId}
        onSelectEngine={handleSelectEngine}
        fleet={fleet}
        flightPhase={frame?.flight_phase || 'Loiter'}
        tacticalStatus={frame?.tactical_risk?.tactical_status || 'GO'}
        simTime={frame?.timestamp || 0}
        onOpenFaultModal={() => setIsFaultModalOpen(true)}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      {/* Main View Area */}
      <main className="dashboard-container" style={{ flex: 1 }}>
        {currentView === 'fleet' && (
          <FleetView onInspectEngine={handleInspectEngineFromFleet} />
        )}
        {currentView === 'operational' && (
          <OperationalView
            frame={frame}
            onOpenFaultModal={() => setIsFaultModalOpen(true)}
            onNavigateView={setCurrentView}
          />
        )}
        {currentView === 'engineering' && (
          <EngineeringView frame={frame} />
        )}
        {currentView === 'maintenance' && (
          <MaintenanceView frame={frame} onRefresh={() => {}} />
        )}
        {currentView === 'replay' && (
          <ReplayView />
        )}
        {currentView === 'simulator' && (
          <SimulatorView frame={frame} />
        )}
      </main>

      {/* Console Footer */}
      <footer style={{
        padding: '1rem 2rem',
        borderTop: '1px solid var(--border-color)',
        background: 'var(--bg-surface-1)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '0.75rem',
        fontSize: '0.75rem',
        color: 'var(--text-muted)'
      }}>
        <div>
          <strong style={{ color: 'var(--text-primary)' }}>TITAN Ground Control Station</strong> — Physics-informed digital twin for MALE-UAV propulsion
        </div>
        <div style={{ display: 'flex', gap: '1.5rem', fontFamily: 'var(--font-mono)' }}>
          <span>DRDO–iDEX / SIH 26054</span>
          <span>CEMILAC & DO-178B Aligned</span>
          <span>Offline defence ready</span>
        </div>
      </footer>

      {/* Live Fault Injection Modal */}
      <FaultModal
        isOpen={isFaultModalOpen}
        onClose={() => setIsFaultModalOpen(false)}
        onInject={handleInjectFault}
        activeEngineId={activeEngineId}
      />
    </div>
  );
}
