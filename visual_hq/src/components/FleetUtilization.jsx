import { AreaChart, Area, ResponsiveContainer, XAxis, YAxis } from 'recharts';
import { motion } from 'framer-motion';

/**
 * FleetUtilization — Utilization percentage, sparkline chart, and footer stats.
 */
export default function FleetUtilization({ fleetStats = {} }) {
  const utilization = fleetStats.utilization_pct || 93;
  const totalAgents = fleetStats.total_agents || 9420;
  const active = fleetStats.active || 8765;
  const idle = fleetStats.idle || 512;

  // Mock sparkline data (in production, this would come from historical stats)
  const sparkData = Array.from({ length: 30 }, (_, i) => ({
    time: i,
    value: 60 + Math.random() * 35 + (i * 0.5),
  }));

  return (
    <motion.div
      className="card utilization-area"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.4 }}
    >
      <div className="card-header">
        <span className="card-title">Fleet Utilization</span>
        <button className="card-menu">⋯</button>
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
        <span className="utilization-value">{utilization}%</span>
        <span className="utilization-live">Live</span>
      </div>

      {/* Sparkline Chart */}
      <div className="utilization-chart">
        <ResponsiveContainer width="100%" height={80}>
          <AreaChart data={sparkData}>
            <defs>
              <linearGradient id="utilGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#14b8a6" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#14b8a6" stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <XAxis dataKey="time" hide />
            <YAxis hide domain={[0, 100]} />
            <Area
              type="monotone"
              dataKey="value"
              stroke="#14b8a6"
              strokeWidth={2}
              fill="url(#utilGradient)"
              dot={false}
              animationDuration={1500}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Y-axis labels */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: '0.6rem',
        color: 'var(--text-muted)',
        padding: '0 4px',
      }}>
        <span>10%</span>
        <span>25%</span>
        <span>50%</span>
        <span>75%</span>
        <span>100%</span>
      </div>

      {/* Footer Stats */}
      <div className="utilization-footer">
        <div className="utilization-stat">
          <div className="utilization-stat-label">Active Agents</div>
          <div className="utilization-stat-value">{active.toLocaleString()}/{totalAgents.toLocaleString()}</div>
        </div>
        <div className="utilization-stat">
          <div className="utilization-stat-label">Idle</div>
          <div className="utilization-stat-value">{idle.toLocaleString()}</div>
        </div>
        <div className="utilization-stat">
          <div className="utilization-stat-label">CPU</div>
          <div className="utilization-stat-value">78%</div>
        </div>
        <div className="utilization-stat">
          <div className="utilization-stat-label">Memory</div>
          <div className="utilization-stat-value">62%</div>
        </div>
      </div>
    </motion.div>
  );
}
