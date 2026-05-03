import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

const SHORTCUTS = [
  { id: 'dashboard', icon: '📊', label: 'Dash', url: 'http://localhost:5173/' },
  { id: 'agents', icon: '🤖', label: 'Agents', url: 'http://localhost:5173/?view=Agents' },
  { id: 'vault', icon: '🔑', label: 'Vault', url: 'http://localhost:5173/?view=Vault' },
  { id: 'settings', icon: '⚙️', label: 'Config', url: 'http://localhost:5173/?view=Settings' },
  { id: 'logs', icon: '📜', label: 'Logs', url: 'http://localhost:8000/logs' },
  { id: 'terminal', icon: '📟', label: 'Term', url: '#' },
];

export default function HermesWidget({ isGlobal = false }) {
  const DASHBOARD_URL = 'http://localhost:5173/';

  const handleLaunch = () => {
    if (window.electronAPI) {
      window.electronAPI.openURL(DASHBOARD_URL);
    } else {
      window.open(DASHBOARD_URL, '_blank');
    }
  };

  return (
    <div className={`hermes-widget-wrapper ${isGlobal ? 'is-global' : ''}`} style={{
      position: isGlobal ? 'relative' : 'fixed',
      bottom: isGlobal ? '0' : '30px',
      right: isGlobal ? '0' : '30px',
      zIndex: 10000,
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      pointerEvents: 'none',
    }}>
      {/* --- MINI ORB (CLICK TO LAUNCH) --- */}
      <motion.div
        onClick={handleLaunch}
        initial={{ scale: 0, opacity: 0, rotate: -180 }}
        animate={{ scale: 1, opacity: 1, rotate: 0 }}
        whileHover={{ scale: 1.1, boxShadow: '0 0 30px rgba(20, 184, 166, 0.6)' }}
        whileTap={{ scale: 0.9 }}
        style={{
          width: '64px',
          height: '64px',
          borderRadius: '24px',
          background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
          border: '2px solid rgba(20, 184, 166, 0.5)',
          boxShadow: '0 10px 25px rgba(0,0,0,0.4)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '2rem',
          WebkitAppRegion: isGlobal ? 'drag' : 'none',
          pointerEvents: 'auto',
          position: 'relative',
          overflow: 'hidden'
        }}
      >
        <div style={{
          position: 'absolute',
          inset: 0,
          background: 'radial-gradient(circle at center, rgba(20, 184, 166, 0.2) 0%, transparent 70%)',
          animation: 'orb-pulse 4s infinite'
        }} />
        <span style={{ zIndex: 1, filter: 'drop-shadow(0 0 8px rgba(20, 184, 166, 0.8))' }}>👑</span>
      </motion.div>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes orb-pulse {
          0%, 100% { opacity: 0.3; transform: scale(1); }
          50% { opacity: 0.6; transform: scale(1.1); }
        }
      `}} />
    </div>
  );
}


const controlButtonStyle = {
  background: 'rgba(255,255,255,0.05)',
  border: 'none',
  color: '#94a3b8',
  fontSize: '1rem',
  cursor: 'pointer',
  padding: '6px',
  borderRadius: '8px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: '32px',
  height: '32px',
  transition: 'all 0.2s'
};

