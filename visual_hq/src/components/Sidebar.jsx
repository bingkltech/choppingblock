import { useState } from 'react';

/**
 * Sidebar — Vertical icon navigation (left sidebar from dashboard.png).
 */
export default function Sidebar({ activeView, setActiveView }) {
  const items = [
    { icon: '📊', label: 'Dashboard' },
    { icon: '🤖', label: 'Agents' },
    { icon: '📁', label: 'Files' },
    { icon: '📋', label: 'Tasks' },
    { icon: '🎯', label: 'Targets' },
    { icon: '🔗', label: 'Connections' },
    { icon: '🔐', label: 'Vault' },
    { icon: '⚙️', label: 'Settings' },
  ];

  return (
    <div className="sidebar">
      {items.map((item, i) => (
        <button
          key={item.label}
          className={`sidebar-item ${activeView === item.label ? 'active' : ''}`}
          onClick={() => setActiveView(item.label)}
          title={item.label}
          aria-label={item.label}
          aria-current={activeView === item.label ? 'page' : undefined}
          id={`sidebar-${item.label.toLowerCase()}`}
        >
          <span style={{ fontSize: '1.1rem' }}>{item.icon}</span>
        </button>
      ))}
      <div className="sidebar-spacer" />
      <button className="sidebar-item" title="Help" aria-label="Help" id="sidebar-help">
        <span style={{ fontSize: '1.1rem' }}>❓</span>
      </button>
      <button className="sidebar-item" title="Logout" aria-label="Logout" id="sidebar-logout">
        <span style={{ fontSize: '1.1rem' }}>🚪</span>
      </button>
    </div>
  );
}
