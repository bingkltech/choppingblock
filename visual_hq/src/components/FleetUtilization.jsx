import { AreaChart, Area, ResponsiveContainer, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { motion } from 'framer-motion';

/**
 * FleetUtilization — Utilization percentage, sparkline chart, and footer stats.
 */

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    return (
      <div className="custom-tooltip">
        <p className="tooltip-val">{`${payload[0].value.toFixed(1)}%`}</p>
      </div>
    );
  }
  return null;
};

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
        <button className="card-menu" aria-label="Options">⋯</button>
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
        <span className="utilization-value">{utilization}%</span>
        <span className="utilization-live">Live</span>
      </div>

      {/* Sparkline Chart */}
      <div className="utilization-chart">
        <ResponsiveContainer width="100%" height={120}>
          <AreaChart data={sparkData} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="utilGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#14b8a6" stopOpacity={0.5} />
                <stop offset="100%" stopColor="#14b8a6" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(148, 163, 184, 0.1)" />
            <XAxis dataKey="time" hide />
            <YAxis hide domain={[0, 100]} />
            <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(20, 184, 166, 0.5)', strokeWidth: 1, strokeDasharray: '3 3' }} />
            <Area
              type="monotone"
              dataKey="value"
              stroke="#14b8a6"
              strokeWidth={3}
              fill="url(#utilGradient)"
              dot={false}
              activeDot={{ r: 5, fill: "#14b8a6", stroke: "var(--bg-card)", strokeWidth: 2 }}
              animationDuration={1500}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Y-axis labels */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: '0.65rem',
        color: 'var(--text-muted)',
        padding: '8px 4px 0',
        fontWeight: 500
      }}>
        <span>0%</span>
        <span>25%</span>
        <span>50%</span>
        <span>75%</span>
        <span>100%</span>
      </div>

      {/* Footer Stats Grid */}
      <div className="utilization-metrics-grid">
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Active Agents</span>
          </div>
          <div className="metric-value">{active.toLocaleString()}<span className="metric-sub"> / {totalAgents.toLocaleString()}</span></div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Idle</span>
          </div>
          <div className="metric-value">{idle.toLocaleString()}</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">CPU Usage</span>
            <span className="metric-value-small">78%</span>
          </div>
          <div className="progress-bar-bg">
            <div className="progress-bar-fill warning" style={{ width: '78%' }}></div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Memory</span>
            <span className="metric-value-small">62%</span>
          </div>
          <div className="progress-bar-bg">
            <div className="progress-bar-fill active" style={{ width: '62%' }}></div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
