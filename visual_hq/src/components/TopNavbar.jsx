import { useState, useEffect } from 'react';

/**
 * TopNavbar — Dashboard top navigation bar matching the zZERO design.
 */
export default function TopNavbar({ shift, onToggleShift }) {
  const [time, setTime] = useState(new Date());
  const [activeTab, setActiveTab] = useState('dashboard');

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'projects', label: 'Projects', icon: '💻' },
    { id: 'agents', label: 'Agents', icon: '🤖' },
    { id: 'pipeline', label: 'Pipeline', icon: '🔧' },
    { id: 'assets', label: 'Assets', icon: '📦' },
    { id: 'security', label: 'Security', icon: '🛡️' },
    { id: 'settings', label: 'Settings', icon: '⚙️' },
  ];

  return (
    <div className="topbar">
      <div className="topbar-logo">
        <h1>📎 PAPERCLIP REBORN</h1>
        <span>AI Software Foundry</span>
      </div>

      <nav className="topbar-nav">
        {tabs.map(tab => (
          <button aria-label={tab.label}
            key={tab.id}
            id={`nav-${tab.id}`}
            className={`topbar-nav-item ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span style={{ fontSize: '1.1rem' }}>{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </nav>

      <div className="topbar-right">
        <div className="topbar-clock">
          {time.toLocaleTimeString('en-US', { hour12: false })}
          <small>Real-time system</small>
        </div>

        <div className="shift-toggle" onClick={onToggleShift} id="shift-toggle">
          <div className={`shift-toggle-track ${shift?.is_god_mode ? 'god' : ''}`}>
            <div className="shift-toggle-thumb" />
          </div>
          <span className="shift-toggle-label">
            {shift?.is_god_mode ? '🌙 God Mode' : '☀️ Boss Mode'}
          </span>
        </div>

        <div className="topbar-search">
          <span>🔍</span>
          Search projects, agents, code...
        </div>

        <div className="topbar-user">
          <div className="topbar-user-avatar">AM</div>
          <div className="topbar-user-info">
            Agent Manager<br />
            <small>System Admin</small>
          </div>
        </div>
      </div>
    </div>
  );
}
