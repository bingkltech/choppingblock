import { motion } from 'framer-motion';

/**
 * ProjectCards — Top row of active project cards matching the dashboard.png layout.
 */
export default function ProjectCards({ projects = [] }) {
  // If no projects from backend, show demo data
  const displayProjects = projects.length > 0 ? projects : [
    { project_name: 'Project Alpha', status: 'Implementing Features', language: 'Python', active_agents: 28, current_task: 'Refactoring API layer', health_pct: 98.7, pipeline_stage: 'Code' },
    { project_name: 'Project Beta', status: 'Implementing Features', language: 'Python', active_agents: 28, current_task: 'Refactoring API layer', health_pct: 98.7, pipeline_stage: 'Build' },
    { project_name: 'Project Gamma', status: 'Implementing Features', language: 'Go', active_agents: 28, current_task: 'API layer', health_pct: 98.7, pipeline_stage: 'Test' },
    { project_name: 'Project Delta', status: 'Implementing Features', language: 'Go', active_agents: 26, current_task: 'Refactoring API layer', health_pct: 98.7, pipeline_stage: 'Deploy' },
  ];

  return (
    <div className="projects-area">
      <div className="projects-header">
        <h2>
          Active Coding Projects
          <span className="count">{displayProjects.length}</span>
        </h2>
        <select style={{ 
          background: 'var(--bg-card)', 
          border: '1px solid var(--border-subtle)', 
          color: 'var(--text-secondary)', 
          padding: '4px 10px', 
          borderRadius: 'var(--radius-xs)',
          fontSize: '0.75rem',
        }}>
          <option>Most projects</option>
          <option>Recent activity</option>
          <option>Health (low first)</option>
        </select>
      </div>

      <div className="projects-grid stagger-children">
        {displayProjects.slice(0, 4).map((project, i) => (
          <motion.div
            key={project.project_name}
            className="card project-card animate-fade-in"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08, duration: 0.4 }}
            id={`project-${i}`}
          >
            <div className="card-header">
              <div className="project-name">{project.project_name}</div>
              <button className="card-menu">⋯</button>
            </div>

            <div className="project-status">
              Status: {project.status}
            </div>

            <div className="project-progress">
              <div 
                className="project-progress-bar" 
                style={{ width: `${Math.min(project.health_pct, 100)}%` }} 
              />
            </div>

            <div className="project-details">
              <span className="project-detail-label">Language</span>
              <span className="project-detail-value">{project.language}</span>
              
              <span className="project-detail-label">Active Agents</span>
              <span className="project-detail-value">{project.active_agents}</span>
              
              <span className="project-detail-label">Current Task</span>
              <span className="project-detail-value">{project.current_task}</span>
            </div>

            <div className="project-health">
              <span className="project-health-dot" />
              <span>Stable, {project.health_pct}%</span>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
