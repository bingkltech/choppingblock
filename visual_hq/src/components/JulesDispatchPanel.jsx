import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * JulesDispatchPanel — Full-page panel for dispatching tasks to Jules AI
 * and monitoring active/completed sessions.
 */

const API_BASE = `http://${window.location.hostname}:8000/api/jules`;

// Status badge colors matching the agent state system
const STATUS_CONFIG = {
  PENDING:   { color: 'var(--text-muted)',      bg: 'rgba(107, 114, 128, 0.15)', label: '⏳ Pending' },
  PLANNING:  { color: 'var(--accent-blue)',      bg: 'rgba(59, 130, 246, 0.15)',  label: '🔵 Planning' },
  EXECUTING: { color: 'var(--accent-amber)',     bg: 'rgba(245, 158, 11, 0.15)',  label: '🟡 Executing' },
  COMPLETED: { color: 'var(--status-success)',   bg: 'rgba(16, 185, 129, 0.15)',  label: '🟢 Completed' },
  FAILED:    { color: 'var(--status-error)',      bg: 'rgba(239, 68, 68, 0.15)',   label: '🔴 Failed' },
};

function StatusBadge({ status }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.PENDING;
  return (
    <span className="jules-status-badge" style={{
      color: config.color,
      background: config.bg,
      border: `1px solid ${config.color}20`,
    }}>
      {config.label}
    </span>
  );
}

function formatTime(ts) {
  if (!ts) return '—';
  const d = new Date(ts);
  const now = new Date();
  const diff = Math.floor((now - d) / 60000);
  if (diff < 1) return 'Just now';
  if (diff < 60) return `${diff}m ago`;
  if (diff < 1440) return `${Math.floor(diff / 60)}h ago`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export default function JulesDispatchPanel({ apiUsage = [] }) {
  // Dispatch form state
  const [task, setTask] = useState('');
  const [repo, setRepo] = useState('');
  const [branch, setBranch] = useState('main');
  const [requireApproval, setRequireApproval] = useState(true);
  const [dispatching, setDispatching] = useState(false);
  const [dispatchResult, setDispatchResult] = useState(null);

  // UI State
  const [activeTab, setActiveTab] = useState('OPERATIONS'); // 'OPERATIONS' or 'FLEET_CONFIG'

  // Sessions state
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedSession, setSelectedSession] = useState(null);

  // Health state
  const [health, setHealth] = useState(null);

  // Local state for fleet config inputs
  const [localConfigs, setLocalConfigs] = useState({});
  const [globalKey, setGlobalKey] = useState('');
  const [savingGlobal, setSavingGlobal] = useState(false);

  // Sync local config inputs with apiUsage on load/update
  useEffect(() => {
    const newConfigs = { ...localConfigs };
    let hasChanges = false;
    apiUsage.forEach(node => {
      if (!newConfigs[node.account_name]) {
        newConfigs[node.account_name] = {
          apiKey: node.api_key_override || '',
          model: node.model_provider || 'gemini-1.5-pro',
          githubPat: node.github_pat_override || ''
        };
        hasChanges = true;
      }
    });
    if (hasChanges) setLocalConfigs(newConfigs);
  }, [apiUsage]);

  const updateLocalConfig = (accountName, field, value) => {
    setLocalConfigs(prev => ({
      ...prev,
      [accountName]: {
        ...prev[accountName],
        [field]: value
      }
    }));
  };

  const saveFleetConfig = async (accountName) => {
    try {
      const config = localConfigs[accountName];
      const res = await fetch(`${API_BASE}/fleet/${accountName}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_key_override: config.apiKey,
          model_provider: config.model,
          github_pat_override: config.githubPat
        }),
      });
      if (res.ok) {
        // Show success alert or toast if we had one, for now it will just sync via websocket
        console.log(`Saved config for ${accountName}`);
      }
    } catch (err) {
      console.error('Failed to save fleet config:', err);
    }
  };

  const handleSaveGlobalKey = async () => {
    if (!globalKey.trim()) return;
    setSavingGlobal(true);
    try {
      const res = await fetch(`${API_BASE}/settings/global`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jules_api_key: globalKey.trim()
        }),
      });
      if (res.ok) {
        setGlobalKey(''); // Clear it for security, health badge will show it's active
        fetchHealth(); // refresh health badges
      }
    } catch (err) {
      console.error('Failed to save global key:', err);
    } finally {
      setSavingGlobal(false);
    }
  };

  // Fetch sessions
  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/sessions?limit=30`);
      const data = await res.json();
      setSessions(data.sessions || []);
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch health
  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/health`);
      const data = await res.json();
      setHealth(data);
    } catch (err) {
      console.error('Failed to fetch Jules health:', err);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
    fetchHealth();
    const interval = setInterval(fetchSessions, 15000); // Poll every 15s
    return () => clearInterval(interval);
  }, [fetchSessions, fetchHealth]);

  // Dispatch task
  const handleDispatch = async (e) => {
    e.preventDefault();
    if (!task.trim()) return;

    setDispatching(true);
    setDispatchResult(null);

    try {
      const res = await fetch(`${API_BASE}/dispatch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task: task.trim(),
          repo: repo.trim(),
          branch: branch.trim() || 'main',
          require_plan_approval: requireApproval,
        }),
      });

      const data = await res.json();

      if (res.ok) {
        setDispatchResult({ type: 'success', message: `Session created: ${data.session_id}`, data });
        setTask('');
        fetchSessions(); // Refresh the list
      } else {
        setDispatchResult({ type: 'error', message: data.detail || 'Dispatch failed' });
      }
    } catch (err) {
      setDispatchResult({ type: 'error', message: `Network error: ${err.message}` });
    } finally {
      setDispatching(false);
    }
  };

  // Approve plan
  const handleApprove = async (sessionId) => {
    try {
      const res = await fetch(`${API_BASE}/sessions/${sessionId}/approve`, { method: 'POST' });
      if (res.ok) {
        fetchSessions();
      }
    } catch (err) {
      console.error('Failed to approve plan:', err);
    }
  };

  // Poll single session
  const handlePollSession = async (sessionId) => {
    try {
      const res = await fetch(`${API_BASE}/sessions/${sessionId}?poll=true`);
      if (res.ok) {
        fetchSessions();
      }
    } catch (err) {
      console.error('Failed to poll session:', err);
    }
  };

  const activeSessions = sessions.filter(s => !['COMPLETED', 'FAILED'].includes(s.status));
  const completedSessions = sessions.filter(s => ['COMPLETED', 'FAILED'].includes(s.status));

  return (
    <div className="jules-dispatch-layout">
      {/* Header */}
      <div className="jules-header">
        <div className="jules-header-left">
          <h1 className="jules-title">
            <span className="jules-title-icon">🔮</span>
            Jules Dispatch Center
          </h1>
          <span className="jules-subtitle">Autonomous AI Coding Agent • jules.google</span>
        </div>
        <div className="jules-header-right">
          <div className="jules-tabs">
            <button 
              className={`jules-tab ${activeTab === 'OPERATIONS' ? 'active' : ''}`}
              onClick={() => setActiveTab('OPERATIONS')}
            >
              🚀 Operations
            </button>
            <button 
              className={`jules-tab ${activeTab === 'FLEET_CONFIG' ? 'active' : ''}`}
              onClick={() => setActiveTab('FLEET_CONFIG')}
            >
              ⚙️ Fleet Config
            </button>
          </div>
          {health && (
            <div className="jules-health-badges" style={{marginLeft: '16px'}}>
              <span className={`jules-health-badge ${health.api_key_set ? 'ok' : 'err'}`}>
                {health.api_key_set ? '🔑 Primary Key Active' : '⚠️ No Primary Key'}
              </span>
              <span className="jules-health-badge ok">
                {health.active_sessions}/{health.max_concurrent} Active
              </span>
            </div>
          )}
        </div>
      </div>

      {activeTab === 'OPERATIONS' && (
      <div className="jules-body">
        {/* Left column: Dispatch Form */}
        <motion.div
          className="card jules-dispatch-form"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <div className="card-header">
            <span className="card-title">🚀 Dispatch New Task</span>
          </div>

          <form onSubmit={handleDispatch}>
            <label className="jules-form-label">
              Task Description
              <textarea
                className="jules-textarea"
                placeholder="Describe the coding task for Jules to execute autonomously..."
                value={task}
                onChange={(e) => setTask(e.target.value)}
                rows={5}
                required
                id="jules-task-input"
              />
            </label>

            <div className="jules-form-row">
              <label className="jules-form-label jules-form-half">
                Target Repository
                <input
                  className="jules-input"
                  type="text"
                  placeholder="owner/repo-name"
                  value={repo}
                  onChange={(e) => setRepo(e.target.value)}
                  id="jules-repo-input"
                />
              </label>

              <label className="jules-form-label jules-form-quarter">
                Branch
                <input
                  className="jules-input"
                  type="text"
                  placeholder="main"
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                  id="jules-branch-input"
                />
              </label>
            </div>

            <div className="jules-form-row jules-form-options">
              <label className="jules-checkbox-label">
                <input
                  type="checkbox"
                  checked={requireApproval}
                  onChange={(e) => setRequireApproval(e.target.checked)}
                  id="jules-approval-toggle"
                />
                <span className="jules-checkbox-custom" />
                Require Plan Approval
                <span className="jules-checkbox-hint">(Boss Mode gate)</span>
              </label>
            </div>

            <button
              type="submit"
              className={`jules-dispatch-btn ${dispatching ? 'loading' : ''}`}
              disabled={dispatching || !task.trim()}
              id="jules-dispatch-btn"
            >
              {dispatching ? (
                <>
                  <span className="jules-spinner" />
                  Dispatching...
                </>
              ) : (
                '🚀 Dispatch to Jules'
              )}
            </button>
          </form>

          <AnimatePresence>
            {dispatchResult && (
              <motion.div
                className={`jules-result ${dispatchResult.type}`}
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
              >
                {dispatchResult.type === 'success' ? '✅' : '❌'} {dispatchResult.message}
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Right column: Sessions */}
        <div className="jules-sessions-column">
          {/* Active Sessions */}
          <motion.div
            className="card jules-sessions-panel"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
          >
            <div className="card-header">
              <span className="card-title">
                ⚡ Active Sessions
                {activeSessions.length > 0 && (
                  <span className="jules-count-badge">{activeSessions.length}</span>
                )}
              </span>
              <button className="jules-refresh-btn" onClick={fetchSessions} title="Refresh" aria-label="Refresh sessions">
                🔄
              </button>
            </div>

            {loading ? (
              <div className="jules-loading">Loading sessions...</div>
            ) : activeSessions.length === 0 ? (
              <div className="jules-empty-state">
                <span className="jules-empty-icon">🌙</span>
                <span>No active sessions</span>
                <span className="jules-empty-hint">Dispatch a task to get started</span>
              </div>
            ) : (
              <div className="jules-sessions-list">
                {activeSessions.map((session, i) => (
                  <motion.div
                    key={session.session_id}
                    className="jules-session-card"
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.06 }}
                    onClick={() => setSelectedSession(selectedSession === session.session_id ? null : session.session_id)}
                  >
                    <div className="jules-session-header">
                      <StatusBadge status={session.status} />
                      <span className="jules-session-time">{formatTime(session.dispatched_at)}</span>
                    </div>
                    <div className="jules-session-task">{session.task_prompt}</div>
                    <div className="jules-session-meta">
                      <span>📦 {session.repo_source}</span>
                      <span>🔀 {session.branch}</span>
                    </div>
                    <div className="jules-session-actions">
                      {session.status === 'PLANNING' && !session.plan_approved && (
                        <button
                          className="jules-action-btn approve"
                          onClick={(e) => { e.stopPropagation(); handleApprove(session.session_id); }}
                        >
                          ✅ Approve Plan
                        </button>
                      )}
                      <button
                        className="jules-action-btn poll"
                        onClick={(e) => { e.stopPropagation(); handlePollSession(session.session_id); }}
                      >
                        🔄 Poll Status
                      </button>
                    </div>

                    <AnimatePresence>
                      {selectedSession === session.session_id && (
                        <motion.div
                          className="jules-session-details"
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                        >
                          <div className="jules-detail-row">
                            <span className="jules-detail-label">Session ID</span>
                            <span className="jules-detail-value mono">{session.session_id}</span>
                          </div>
                          {session.error_log && (
                            <div className="jules-detail-row">
                              <span className="jules-detail-label">Error</span>
                              <span className="jules-detail-value error">{session.error_log}</span>
                            </div>
                          )}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                ))}
              </div>
            )}
          </motion.div>

          {/* Completed Sessions */}
          <motion.div
            className="card jules-sessions-panel"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.2 }}
          >
            <div className="card-header">
              <span className="card-title">
                📋 History
                {completedSessions.length > 0 && (
                  <span className="jules-count-badge dim">{completedSessions.length}</span>
                )}
              </span>
            </div>

            {completedSessions.length === 0 ? (
              <div className="jules-empty-state small">
                <span>No completed sessions yet</span>
              </div>
            ) : (
              <div className="jules-sessions-list">
                {completedSessions.slice(0, 10).map((session, i) => (
                  <motion.div
                    key={session.session_id}
                    className="jules-session-card completed"
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.04 }}
                  >
                    <div className="jules-session-header">
                      <StatusBadge status={session.status} />
                      <span className="jules-session-time">{formatTime(session.completed_at || session.dispatched_at)}</span>
                    </div>
                    <div className="jules-session-task">{session.task_prompt}</div>
                    {session.pr_url && (
                      <a
                        href={session.pr_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="jules-pr-link"
                        onClick={(e) => e.stopPropagation()}
                      >
                        🔗 View Pull Request
                      </a>
                    )}
                  </motion.div>
                ))}
              </div>
            )}
          </motion.div>
        </div>
      </div>
      )}

      {activeTab === 'FLEET_CONFIG' && (
      <motion.div 
        className="jules-fleet-config-layout stagger-children"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="jules-fleet-header">
          <h2>Jules API Fleet & Labor Node Configurations</h2>
          <p className="jules-subtitle mt-1" style={{textTransform: 'none', letterSpacing: '0', color: 'var(--text-muted)'}}>
            Manage the Load-Balanced cluster of Jules Cloud Laborers. Assign specific API keys, GitHub PATs, and Model configurations to avoid individual rate limits.
          </p>
        </div>

        {/* --- GLOBAL SETTINGS CARD --- */}
        <div className="card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px', border: '1px solid var(--accent-blue)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '1.5rem' }}>🔑</span>
            <div>
              <h3 style={{ margin: 0, color: 'var(--text-primary)', fontSize: '1.1rem' }}>Master Jules API Key</h3>
              <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: '4px' }}>
                Set the global JULES_API_KEY for the system. This key is used by default if a node does not have an override.
              </p>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end' }}>
            <label className="jules-form-label" style={{ flex: 1, margin: 0 }}>
              <input 
                type="password" 
                className="jules-input" 
                placeholder="Paste API Key starting with AIzaSy..." 
                value={globalKey}
                onChange={(e) => setGlobalKey(e.target.value)}
              />
            </label>
            <button 
              className={`jules-dispatch-btn ${savingGlobal ? 'loading' : ''}`}
              style={{ width: 'auto', padding: '10px 24px' }}
              onClick={handleSaveGlobalKey}
              disabled={savingGlobal || !globalKey.trim()}
            >
              {savingGlobal ? 'Saving...' : '💾 Save as Default'}
            </button>
          </div>
        </div>

        {/* --- NODE GRID --- */}
        <div className="jules-fleet-grid">
          {apiUsage.map((node, i) => {
            const lConf = localConfigs[node.account_name] || { apiKey: '', model: 'gemini-1.5-pro', githubPat: '' };
            return (
            <motion.div 
              key={node.account_name}
              className="card jules-fleet-card animate-fade-in"
              style={{ padding: '20px' }}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
            >
              <div className="jules-fleet-card-header" style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
                <div>
                  <div style={{ fontWeight: '700', fontSize: '1.05rem', color: 'var(--text-primary)', textTransform: 'capitalize' }}>
                    {node.account_name.replace(/_/g, ' ')}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Status: {node.status}</div>
                </div>
                <div className={`agent-status-dot ${node.status === "ACTIVE" || node.status === "IDLE" ? "alive" : "dead"}`} style={{ marginTop: "4px" }} />
              </div>

              <div className="jules-fleet-metrics" style={{ display: 'flex', gap: '16px', marginBottom: '20px', paddingBottom: '16px', borderBottom: '1px solid var(--border-subtle)'}}>
                <div>
                  <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Token Burn Today</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: '800', color: 'var(--accent-teal)' }}>{(node.tokens_used_today || 0).toLocaleString()}</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>System Key Hook</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: '800', color: 'var(--text-primary)' }}>{node.api_key_env_var}</div>
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <label className="jules-form-label">
                  Jules API Key (Override)
                  <div style={{ position: 'relative' }}>
                    <input 
                      type="password" 
                      className="jules-input" 
                      placeholder={`Uses default ${node.api_key_env_var} if empty`} 
                      value={lConf.apiKey}
                      onChange={(e) => updateLocalConfig(node.account_name, 'apiKey', e.target.value)}
                    />
                    <span style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', opacity: 0.5 }}>👁️</span>
                  </div>
                </label>

                <label className="jules-form-label">
                  Model Provider
                  <select 
                    className="jules-input" 
                    value={lConf.model}
                    onChange={(e) => updateLocalConfig(node.account_name, 'model', e.target.value)}
                  >
                    <option value="gemini-1.5-pro">Gemini 1.5 Pro (Deep Reasoning)</option>
                    <option value="gemini-1.5-flash">Gemini 1.5 Flash (Fast Execution)</option>
                    <option value="gemini-1.5-flash-8b">Gemini 1.5 Flash-8B (High Throughput)</option>
                    <option value="jules-experimental">Jules Experimental v1alpha</option>
                  </select>
                </label>

                <label className="jules-form-label">
                  Dedicated GitHub PAT (Optional)
                  <input 
                    type="password" 
                    className="jules-input" 
                    placeholder="If empty, uses system default PAT" 
                    value={lConf.githubPat}
                    onChange={(e) => updateLocalConfig(node.account_name, 'githubPat', e.target.value)}
                  />
                </label>
              </div>

              <button 
                className="jules-dispatch-btn" 
                style={{ marginTop: '20px', fontSize: '0.8rem', padding: '8px' }}
                onClick={() => saveFleetConfig(node.account_name)}
              >
                💾 Save Configuration
              </button>
            </motion.div>
          )})}
        </div>
      </motion.div>
      )}
    </div>
  );
}
