import { useState } from 'react';
import { motion } from 'framer-motion';

/**
 * LivePipeline — Gantt-style CI/CD pipeline table matching dashboard.png.
 */
export default function LivePipeline({ projects = [] }) {
  const [expanded, setExpanded] = useState({});

  const pipelineData = projects.length > 0 ? projects.map(p => ({
    name: p.project_name,
    overallStage: p.pipeline_stage || 'Plan',
    subRows: [
      { env: 'Staging', stage: p.pipeline_stage || 'Active', log: 'Rundtng ...', logTime: '00:35 AM' },
      { env: 'Production', stage: getNextStage(p.pipeline_stage), log: 'Production Fro...', logTime: '5 mins ago' },
    ],
  })) : [
    {
      name: 'Project Alpha',
      overallStage: 'Success',
      subRows: [
        { env: 'Staging', stage: 'Active', log: 'Log: Rundtng ...', logTime: '00:35 AM' },
        { env: 'Production', stage: 'Build', log: 'Ttomipated W...', logTime: '5 mins ago' },
      ],
    },
    {
      name: 'Beta',
      overallStage: 'Success',
      subRows: [
        { env: 'Staging', stage: 'Active', log: 'Log: Rundtng ...', logTime: '08:30 AM' },
        { env: 'Production', stage: 'Running tests', log: 'Production Fro...', logTime: '5 mins ago' },
      ],
    },
    {
      name: 'Gamma',
      overallStage: 'Active',
      subRows: [
        { env: 'Staging', stage: 'Deploy', log: 'Log: Rundtng ...', logTime: '08:35 AM' },
        { env: 'Production', stage: 'Active', log: 'Production Fro...', logTime: '5 mins ago' },
      ],
    },
  ];

  function getNextStage(stage) {
    const stages = ['Plan', 'Code', 'Build', 'Test', 'Deploy'];
    const idx = stages.indexOf(stage);
    return idx >= 0 && idx < stages.length - 1 ? stages[idx + 1] : 'Build';
  }

  function getBadgeClass(stage) {
    if (!stage) return '';
    const s = stage.toLowerCase();
    if (s === 'success') return 'success';
    if (s === 'active') return 'active';
    if (s === 'build') return 'build';
    if (s === 'test' || s === 'running tests') return 'test';
    if (s === 'deploy') return 'deploy';
    return 'active';
  }

  const toggleRow = (name) => {
    setExpanded(prev => ({ ...prev, [name]: !prev[name] }));
  };

  return (
    <motion.div
      className="card pipeline-area"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.1 }}
    >
      <div className="card-header">
        <div>
          <span className="card-title">Live Pipeline & Deployment</span>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            Stage: gantt-chart view for active CI/CD pipelines
          </div>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Active</span>
          <select style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-secondary)',
            padding: '4px 10px',
            borderRadius: 'var(--radius-xs)',
            fontSize: '0.72rem',
          }}>
            <option>CI/CD pipelines</option>
            <option>Build only</option>
            <option>Deploy only</option>
          </select>
          <button className="card-menu" aria-label="Options">⋯</button>
        </div>
      </div>

      <table className="pipeline-table">
        <thead>
          <tr>
            <th>Stage</th>
            <th>Plan</th>
            <th>Code</th>
            <th>Build</th>
            <th>Test</th>
            <th>Deploy</th>
            <th>Log</th>
          </tr>
        </thead>
        <tbody>
          {pipelineData.map((row) => (
            <>
              <tr 
                key={row.name} 
                className="pipeline-toggle-row"
                onClick={() => toggleRow(row.name)}
              >
                <td style={{ fontWeight: 600 }}>
                  <span style={{ marginRight: '6px', fontSize: '0.7rem' }}>
                    {expanded[row.name] ? '▼' : '▶'}
                  </span>
                  {row.name}
                </td>
                <td colSpan={5}>
                  <span className={`pipeline-stage-badge ${getBadgeClass(row.overallStage)}`}>
                    {row.overallStage}
                  </span>
                </td>
                <td className="pipeline-log">Status ▲</td>
              </tr>
              {expanded[row.name] && row.subRows.map((sub, j) => (
                <tr key={`${row.name}-${j}`} className="pipeline-sub-row">
                  <td style={{ color: 'var(--text-muted)' }}>{sub.env}</td>
                  <td colSpan={5}>
                    <span className={`pipeline-stage-badge ${getBadgeClass(sub.stage)}`}>
                      {sub.stage}
                    </span>
                  </td>
                  <td className="pipeline-log">
                    {sub.log} <span style={{ marginLeft: '8px' }}>{sub.logTime}</span>
                  </td>
                </tr>
              ))}
            </>
          ))}
        </tbody>
      </table>
    </motion.div>
  );
}
