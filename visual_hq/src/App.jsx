import { useHeartbeat } from './hooks/useHeartbeat';
import TopNavbar from './components/TopNavbar';
import Sidebar from './components/Sidebar';
import ProjectCards from './components/ProjectCards';
import AgentFleetStatus from './components/AgentFleetStatus';
import LivePipeline from './components/LivePipeline';
import AlertsPanel from './components/AlertsPanel';
import ActivityFeed from './components/ActivityFeed';
import FleetUtilization from './components/FleetUtilization';
import AgentManager from './components/AgentManager';
import { useState } from 'react';

/**
 * App — Main dashboard layout assembling all panels.
 * Matches the zZERO command-center design from dashboard.png.
 */
export default function App() {
  const [activeView, setActiveView] = useState('Dashboard');
  const {
    connected,
    agents,
    projects,
    alerts,
    activity,
    apiUsage,
    shift,
    fleetStats,
    sendCommand,
  } = useHeartbeat();

  const handleToggleShift = () => {
    sendCommand('toggle_shift');
  };

  return (
    <div className="app-layout">
      <Sidebar activeView={activeView} setActiveView={setActiveView} />
      <TopNavbar shift={shift} onToggleShift={handleToggleShift} />

      {activeView === 'Agents' ? (
        <div style={{ gridArea: 'main', overflowY: 'auto', width: '100%', height: '100%' }}>
          <AgentManager apiUsage={apiUsage} />
        </div>
      ) : (
        <main className="main-content">
          <ProjectCards projects={projects} />
          <AlertsPanel alerts={alerts} />
          <AgentFleetStatus fleetStats={fleetStats} agents={agents} />
          <LivePipeline projects={projects} />
          <ActivityFeed activity={activity} />
          <FleetUtilization fleetStats={fleetStats} />
        </main>
      )}

      {/* Connection Status Indicator */}
      <div style={{
        position: 'fixed',
        bottom: '12px',
        right: '12px',
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        padding: '6px 12px',
        borderRadius: '20px',
        background: connected ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
        border: `1px solid ${connected ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
        fontSize: '0.7rem',
        color: connected ? '#10b981' : '#ef4444',
        zIndex: 999,
        backdropFilter: 'blur(10px)',
      }}>
        <span style={{
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          background: connected ? '#10b981' : '#ef4444',
          animation: connected ? 'pulse-dot 2s infinite' : 'none',
        }} />
        {connected ? 'Connected' : 'Reconnecting...'}
      </div>
    </div>
  );
}
