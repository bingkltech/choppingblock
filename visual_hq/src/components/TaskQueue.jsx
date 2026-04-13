import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

const STATUS_ICONS = {
  PENDING: '⏳', ASSIGNED: '📋', RUNNING: '⚡', DONE: '✅',
  FAILED: '❌', CANCELLED: '🚫',
};
const STATUS_COLORS = {
  PENDING: '#6b7280', ASSIGNED: '#3b82f6', RUNNING: '#eab308',
  DONE: '#10b981', FAILED: '#ef4444', CANCELLED: '#6b7280',
};
const TYPE_LABELS = {
  WRITE_ARCH: '🏛️ Architecture', CODE: '💻 Code', TEST_PR: '🐳 QA Test',
  MERGE_PR: '🔧 Merge', HEAL: '🩺 Heal', GENERAL: '📌 General',
};

const TaskQueue = () => {
  const [tasks, setTasks] = useState([]);
  const [stats, setStats] = useState({ total: 0, by_status: {}, orchestrator: {} });
  const [showCreate, setShowCreate] = useState(false);
  const [newTask, setNewTask] = useState({ task_type: 'GENERAL', description: '', priority: 5 });

  const fetchTasks = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/tasks`);
      const data = await res.json();
      setTasks(data.tasks || []);
    } catch (e) { console.error(e); }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/tasks/stats`);
      setStats(await res.json());
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    fetchTasks();
    fetchStats();
    const interval = setInterval(() => { fetchTasks(); fetchStats(); }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleCreate = async () => {
    if (!newTask.description.trim()) return;
    try {
      await fetch(`${API_BASE}/api/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newTask),
      });
      setNewTask({ task_type: 'GENERAL', description: '', priority: 5 });
      setShowCreate(false);
      fetchTasks();
      fetchStats();
    } catch (e) { console.error(e); }
  };

  const handleCancel = async (taskId) => {
    try {
      await fetch(`${API_BASE}/api/tasks/${taskId}/cancel`, { method: 'POST' });
      fetchTasks();
      fetchStats();
    } catch (e) { console.error(e); }
  };

  return (
    <div className="tq-container">
      {/* Stats Bar */}
      <div className="tq-stats-bar">
        <div className="tq-stat">
          <span className="tq-stat-value">{stats.total}</span>
          <span className="tq-stat-label">Total</span>
        </div>
        {Object.entries(stats.by_status || {}).map(([status, count]) => (
          <div key={status} className="tq-stat">
            <span className="tq-stat-value" style={{ color: STATUS_COLORS[status] || '#6b7280' }}>
              {count}
            </span>
            <span className="tq-stat-label">{status}</span>
          </div>
        ))}
        <div className="tq-stat" style={{ marginLeft: 'auto' }}>
          <span className="tq-stat-value" style={{ color: stats.orchestrator?.running ? '#10b981' : '#ef4444' }}>
            {stats.orchestrator?.running ? '● LIVE' : '○ OFF'}
          </span>
          <span className="tq-stat-label">Orchestrator</span>
        </div>
      </div>

      {/* Actions */}
      <div className="tq-actions">
        <button className="tq-create-btn" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? '✕ Cancel' : '+ New Task'}
        </button>
      </div>

      {/* Create Task Form */}
      <AnimatePresence>
        {showCreate && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="tq-create-form"
          >
            <div className="tq-form-row">
              <select
                value={newTask.task_type}
                onChange={e => setNewTask(s => ({ ...s, task_type: e.target.value }))}
                className="hire-input"
              >
                <option value="GENERAL">📌 General</option>
                <option value="WRITE_ARCH">🏛️ Write Architecture</option>
                <option value="CODE">💻 Code (Jules)</option>
                <option value="TEST_PR">🐳 Test PR (QA)</option>
                <option value="MERGE_PR">🔧 Merge PR (Ops)</option>
                <option value="HEAL">🩺 Heal (God)</option>
              </select>
              <select
                value={newTask.priority}
                onChange={e => setNewTask(s => ({ ...s, priority: parseInt(e.target.value) }))}
                className="hire-input"
                style={{ width: '120px' }}
              >
                {[1,2,3,4,5,6,7,8,9,10].map(p => (
                  <option key={p} value={p}>P{p} {p <= 3 ? '🔥' : p <= 6 ? '' : '🐌'}</option>
                ))}
              </select>
            </div>
            <textarea
              value={newTask.description}
              onChange={e => setNewTask(s => ({ ...s, description: e.target.value }))}
              placeholder="Describe what the agent should do..."
              className="hire-input"
              rows={3}
            />
            <button className="am-hire-btn" onClick={handleCreate}>🚀 Submit Task</button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Task List */}
      <div className="tq-list">
        {tasks.length === 0 && (
          <div className="am-empty">
            <div className="am-empty-icon">📋</div>
            <p>No tasks in the queue yet. Create one to get your agents working.</p>
          </div>
        )}
        {tasks.map((task, i) => (
          <motion.div
            key={task.task_id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.03 }}
            className={`tq-item tq-status-${(task.status || '').toLowerCase()}`}
          >
            <div className="tq-item-header">
              <span className="tq-item-icon">{STATUS_ICONS[task.status] || '❓'}</span>
              <span className="tq-item-type">{TYPE_LABELS[task.task_type] || task.task_type}</span>
              <span className="tq-item-id">{task.task_id}</span>
              <span className="tq-item-priority" style={{
                color: task.priority <= 3 ? '#ef4444' : task.priority <= 6 ? '#eab308' : '#6b7280'
              }}>
                P{task.priority}
              </span>
              <span className="tq-item-status" style={{ color: STATUS_COLORS[task.status] }}>
                {task.status}
              </span>
            </div>
            <div className="tq-item-desc">{task.description}</div>
            <div className="tq-item-footer">
              <span className="tq-item-agent">
                {task.assigned_agent ? `👤 ${task.assigned_agent}` : '—'}
              </span>
              <span className="tq-item-time">
                {task.created_at?.split('T')[0]}
              </span>
              {(task.status === 'PENDING' || task.status === 'ASSIGNED') && (
                <button className="tq-cancel-btn" onClick={() => handleCancel(task.task_id)}>
                  Cancel
                </button>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default TaskQueue;
