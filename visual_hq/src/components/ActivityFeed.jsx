import { motion } from 'framer-motion';

/**
 * ActivityFeed — Real-time chronological event log (right panel).
 */
export default function ActivityFeed({ activity = [] }) {
  const displayActivity = activity.length > 0 ? activity : [
    { id: 1, agent_id: 'delta_4', event_type: 'COMMIT', message: 'Agent Delta-4 committed code to Project Zeta', severity: 'INFO', timestamp: new Date(Date.now() - 120000).toISOString() },
    { id: 2, agent_id: 'epsilon_9', event_type: 'BUILD_FIX', message: 'Agent Epsilon-9 resolved build failure in Beta', severity: 'WARNING', timestamp: new Date(Date.now() - 300000).toISOString() },
    { id: 3, agent_id: 'qa', event_type: 'TEST', message: 'QA Agent completed Docker sandbox test — PASSED', severity: 'INFO', timestamp: new Date(Date.now() - 480000).toISOString() },
    { id: 4, agent_id: 'system', event_type: 'BOOT', message: 'Paperclip Reborn backend initialized', severity: 'INFO', timestamp: new Date(Date.now() - 600000).toISOString() },
  ];

  function getEventColor(severity) {
    switch (severity) {
      case 'ERROR': return 'var(--status-error)';
      case 'WARNING': return 'var(--status-warning)';
      default: return 'var(--status-success)';
    }
  }

  function formatTime(ts) {
    if (!ts) return '';
    const d = new Date(ts);
    const now = new Date();
    const diff = Math.floor((now - d) / 60000);
    if (diff < 1) return 'Just now';
    if (diff < 60) return `${diff} mins ago`;
    return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  }

  return (
    <motion.div
      className="card activity-area"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
    >
      <div className="card-header">
        <span className="card-title">Agent Activity Feed</span>
        <button className="card-menu" aria-label="Options">⋯</button>
      </div>
      <div className="activity-subtitle">Real time log</div>

      <div className="activity-list">
        {displayActivity.map((item, i) => (
          <motion.div
            key={item.id || i}
            className="activity-item"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
          >
            <span className="activity-dot" style={{ background: getEventColor(item.severity) }} />
            <div>
              <div className="activity-text">{item.message}</div>
              <div className="activity-time">
                {item.agent_id && <span style={{ marginRight: '6px', fontWeight: 500 }}>{item.agent_id}</span>}
                | {formatTime(item.timestamp)}
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
