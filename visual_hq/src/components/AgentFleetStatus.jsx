import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { motion } from 'framer-motion';

/**
 * AgentFleetStatus — Donut chart showing Active/Idle/Error agent counts.
 */
export default function AgentFleetStatus({ fleetStats = {}, agents = [] }) {
  const stats = {
    total_agents: fleetStats.total_agents || 9420,
    active: fleetStats.active || 8765,
    idle: fleetStats.idle || 512,
    error: fleetStats.error || 143,
    fleet_health_pct: fleetStats.fleet_health_pct || 99.1,
  };

  const chartData = [
    { name: 'Active', value: stats.active, color: '#14b8a6' },
    { name: 'Idle', value: stats.idle, color: '#3b82f6' },
    { name: 'Error', value: stats.error, color: '#ef4444' },
  ];

  return (
    <motion.div 
      className="card fleet-area"
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="card-header">
        <div className="fleet-title-row">
          <span className="card-title">Agent Fleet Status</span>
          <span className="fleet-total">{stats.total_agents.toLocaleString()} Agents</span>
        </div>
        <button className="card-menu" aria-label="Options">⋯</button>
      </div>

      {/* Subtitle */}
      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
        Real-time stats
      </div>

      {/* Donut Chart */}
      <div className="fleet-chart-container">
        <ResponsiveContainer width="100%" height={180}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={80}
              paddingAngle={3}
              dataKey="value"
              strokeWidth={0}
            >
              {chartData.map((entry, i) => (
                <Cell key={i} fill={entry.color} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Stats Rows */}
      <div className="fleet-stats">
        {chartData.map(item => (
          <div key={item.name} className="fleet-stat-row">
            <span className="fleet-stat-dot" style={{ background: item.color }} />
            <span className="fleet-stat-label">{item.name}:</span>
            <span className="fleet-stat-value">{item.value.toLocaleString()}</span>
          </div>
        ))}
      </div>

      {/* Fleet Health */}
      <div className="fleet-health">
        <div className="fleet-health-value">{stats.fleet_health_pct}%</div>
        <div className="fleet-health-label">Fleet Health</div>
      </div>
    </motion.div>
  );
}
