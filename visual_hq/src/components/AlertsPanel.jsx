import { motion } from 'framer-motion';

/**
 * AlertsPanel — Critical alerts and incidents panel (top-right of dashboard).
 */
export default function AlertsPanel({ alerts = [] }) {
  const displayAlerts = alerts.length > 0 ? alerts : [
    { id: 1, alert_type: 'INCIDENT', message: 'Critical alerts & incidents', severity: 'CRITICAL', timestamp: new Date().toISOString() },
    { id: 2, agent_id: 'delta_4', alert_type: 'COMMIT', message: 'Agent Delta-4 committed code to Project Zeta', severity: 'WARNING', timestamp: new Date(Date.now() - 120000).toISOString() },
    { id: 3, agent_id: 'epsilon_9', alert_type: 'BUILD_FIX', message: 'Agent Epsilon-9 resolved build failure in Beta', severity: 'INFO', timestamp: new Date(Date.now() - 300000).toISOString() },
  ];

  const unresolved = displayAlerts.filter(a => !a.resolved);

  return (
    <motion.div
      className="card alerts-area"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
    >
      <div className="card-header">
        <span className="card-title">Critical Alerts & Incidents</span>
        <span className="alerts-count">{unresolved.length} unresolved</span>
      </div>

      <div className="stagger-children">
        {displayAlerts.map((alert, i) => (
          <motion.div
            key={alert.id || i}
            className="alert-item"
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <span className="alert-icon">⚠️</span>
            <div>
              <div className="alert-text">{alert.message}</div>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
