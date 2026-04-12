import React, { useState, useEffect } from 'react';
import JulesDispatchPanel from './JulesDispatchPanel';
import { motion, AnimatePresence } from 'framer-motion';

const AgentManager = ({ apiUsage = [] }) => {
  const [agents, setAgents] = useState([]);
  const [activeTab, setActiveTab] = useState('ROSTER'); // 'ROSTER' or 'JULES_DISPATCH'
  const [showHireModal, setShowHireModal] = useState(false);

  // Hiring Form State
  const [newAgent, setNewAgent] = useState({
    name: '',
    role: '',
    tier: 'Tier 3 (Local Swarm)',
    model: 'qwen2.5-coder',
    skills: '',
    tools: { jules: false, github: false, bash: false, docker: false }
  });

  // Rename state
  const [editingAgent, setEditingAgent] = useState(null);

  const fetchAgents = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/agents');
      const data = await response.json();
      setAgents(data.agents || []);
    } catch (error) {
      console.error('Failed to fetch agents:', error);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  const toggleAgent = async (agentId) => {
    try {
      const response = await fetch(`http://localhost:8000/api/agents/${agentId}/toggle`, { method: 'POST' });
      if (response.ok) fetchAgents();
    } catch (error) {
      console.error('Failed to toggle agent:', error);
    }
  };

  const updateConfig = async (agentId, model) => {
    try {
      const response = await fetch(`http://localhost:8000/api/agents/${agentId}/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model }),
      });
      if (response.ok) fetchAgents();
    } catch (error) {
      console.error('Failed to update config:', error);
    }
  };

  const handleSaveEdit = async () => {
    if (!editingAgent || !editingAgent.name.trim()) {
      setEditingAgent(null);
      return;
    }
    
    // For custom newly hired agents (not saved in backend DB in this mock)
    if (editingAgent.id.startsWith('custom_')) {
      setAgents(agents.map(a => a.id === editingAgent.id ? editingAgent : a));
      setEditingAgent(null);
      return;
    }

    try {
      const response = await fetch(`http://localhost:8000/api/agents/${editingAgent.id}/update`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: editingAgent.name,
          role: editingAgent.role,
          model: editingAgent.model,
          custom_skills: editingAgent.custom_skills,
          custom_tools: editingAgent.custom_tools
        }),
      });
      if (response.ok) fetchAgents();
    } catch (error) {
      console.error('Failed to update agent:', error);
    } finally {
      setEditingAgent(null);
    }
  };

  const handleHireAgent = (e) => {
    e.preventDefault();
    // Simulate API call to create agent for UX demonstration
    const createdAgent = {
      id: `custom_${Date.now()}`,
      name: newAgent.name,
      role: newAgent.role,
      status: 'Alive',
      model: newAgent.model,
      custom_skills: newAgent.skills,
      custom_tools: Object.keys(newAgent.tools).filter(k => newAgent.tools[k])
    };
    setAgents([createdAgent, ...agents]);
    setShowHireModal(false);
    setNewAgent({ name: '', role: '', tier: 'Tier 3 (Local Swarm)', model: 'qwen2.5-coder', skills: '', tools: { jules: false, github: false, bash: false, docker: false } });
  };

  const currentAgents = agents.map(agent => ({
    ...agent,
    custom_skills: agent.custom_skills || (agent.role.includes('QA') ? 'Testing, Code Review, Linting' : 'Full Stack Development, API Integration'),
    custom_tools: agent.custom_tools || (agent.id === 'jules_dispatch' ? ['jules', 'github'] : ['bash', 'docker'])
  }));

  return (
    <div className="agent-manager-layout">
      {/* Top Banner & Navigation */}
      <header className="agent-header">
        <div className="agent-header-inner">
          <div>
            <h1 className="agent-title">
              🤖 Agent Strategy & Workforce
            </h1>
            <p className="agent-subtitle">Hire workers, provision tools, and issue autonomous dispatches.</p>
          </div>

          <div className="jules-tabs">
            <button 
              className={`jules-tab ${activeTab === 'ROSTER' ? 'active' : ''}`}
              onClick={() => setActiveTab('ROSTER')}
            >
              🏢 Agent Roster (Foundry)
            </button>
            <button 
              className={`jules-tab ${activeTab === 'JULES_DISPATCH' ? 'active' : ''}`}
              onClick={() => setActiveTab('JULES_DISPATCH')}
            >
              🔮 Jules Operations
            </button>
          </div>
        </div>
      </header>

      {/* --- JULES DISPATCH TAB --- */}
      {activeTab === 'JULES_DISPATCH' && (
        <div className="flex-1 overflow-hidden" style={{ minHeight: 0 }}>
          <JulesDispatchPanel apiUsage={apiUsage} />
        </div>
      )}

      {/* --- ROSTER TAB --- */}
      {activeTab === 'ROSTER' && (
        <div className="flex-1 overflow-y-auto p-8 relative">
          
          <div className="agent-roster-header">
            <h2 className="agent-roster-title">Active Workforce</h2>
            <button 
              className="jules-dispatch-btn"
              onClick={() => setShowHireModal(!showHireModal)}
              style={{ width: 'auto', margin: 0, padding: '8px 16px' }}
            >
              {showHireModal ? 'Cancel Hiring' : '+ Hire New AI Worker'}
            </button>
          </div>

          <AnimatePresence>
            {showHireModal && (
              <motion.div 
                initial={{ opacity: 0, height: 0, scale: 0.98 }}
                animate={{ opacity: 1, height: 'auto', scale: 1 }}
                exit={{ opacity: 0, height: 0, scale: 0.98 }}
                className="agent-hire-modal"
              >
                <div className="agent-hire-icon">📝</div>
                <h3 className="agent-hire-title">
                  <span className="agent-hire-badge">Recruitment Form</span>
                  Define Agent Capabilities
                </h3>

                <form onSubmit={handleHireAgent} className="agent-hire-form relative z-10">
                  <div className="agent-hire-col">
                    <div>
                      <label className="jules-form-label">Agent Name (e.g. Alice, Hermes)</label>
                      <input required type="text" placeholder="Worker Name" value={newAgent.name} onChange={(e) => setNewAgent({...newAgent, name: e.target.value})} className="jules-input" />
                    </div>
                    <div>
                      <label className="jules-form-label">Role Description</label>
                      <input required type="text" placeholder="React & UI/UX Expert" value={newAgent.role} onChange={(e) => setNewAgent({...newAgent, role: e.target.value})} className="jules-input" />
                    </div>
                    <div>
                      <label className="jules-form-label">Capacities & Skills</label>
                      <textarea required placeholder="Tailwind CSS, React Hooks, UI Animations, Microinteractions..." value={newAgent.skills} onChange={(e) => setNewAgent({...newAgent, skills: e.target.value})} className="jules-input" rows={3}></textarea>
                    </div>
                  </div>

                  <div className="agent-hire-col">
                    <div className="jules-form-row">
                      <div className="jules-form-half">
                        <label className="jules-form-label">Permission Tier</label>
                        <select value={newAgent.tier} onChange={(e) => setNewAgent({...newAgent, tier: e.target.value})} className="jules-input">
                          <option>Tier 1 (Executive Override)</option>
                          <option>Tier 2 (Cloud Operations)</option>
                          <option>Tier 3 (Local Swarm)</option>
                        </select>
                      </div>
                      <div className="jules-form-half">
                        <label className="jules-form-label">Model Provider</label>
                        <select value={newAgent.model} onChange={(e) => setNewAgent({...newAgent, model: e.target.value})} className="jules-input">
                          <option value="gpt-4o">GPT-4o</option>
                          <option value="claude-3.5-sonnet">Claude 3.5 Sonnet</option>
                          <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
                          <option value="qwen2.5-coder">Qwen2.5-Coder (Local)</option>
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="jules-form-label" style={{ marginBottom: '8px' }}>Equip Caveman Primitives (Tools)</label>
                      <div className="agent-tool-grid">
                        <label className={`agent-tool-option ${newAgent.tools.jules ? "active jules" : ""}`}>
                          <input type="checkbox" checked={newAgent.tools.jules} onChange={(e) => setNewAgent({...newAgent, tools: {...newAgent.tools, jules: e.target.checked}})} className="hidden" />
                          <span className="text-xl">🔮</span>
                          <span className="agent-tool-label">Jules.Google API</span>
                        </label>
                        <label className={`agent-tool-option ${newAgent.tools.github ? "active github" : ""}`}>
                          <input type="checkbox" checked={newAgent.tools.github} onChange={(e) => setNewAgent({...newAgent, tools: {...newAgent.tools, github: e.target.checked}})} className="hidden" />
                          <span className="text-xl">🐙</span>
                          <span className="agent-tool-label">GitHub CLI (PRs)</span>
                        </label>
                        <label className={`agent-tool-option ${newAgent.tools.bash ? "active bash" : ""}`}>
                          <input type="checkbox" checked={newAgent.tools.bash} onChange={(e) => setNewAgent({...newAgent, tools: {...newAgent.tools, bash: e.target.checked}})} className="hidden" />
                          <span className="text-xl">⌨️</span>
                          <span className="agent-tool-label">Bash Terminal</span>
                        </label>
                        <label className={`agent-tool-option ${newAgent.tools.docker ? "active docker" : ""}`}>
                          <input type="checkbox" checked={newAgent.tools.docker} onChange={(e) => setNewAgent({...newAgent, tools: {...newAgent.tools, docker: e.target.checked}})} className="hidden" />
                          <span className="text-xl">🐳</span>
                          <span className="agent-tool-label">Docker Sandbox</span>
                        </label>
                      </div>
                    </div>

                    <button type="submit" className="jules-dispatch-btn" style={{ marginTop: '16px', width: '100%' }}>
                      + Finalize Recruitment & Mount Agent
                    </button>
                  </div>
                </form>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Render Active Agents */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            {currentAgents.map((agent, i) => {
              const isEditing = editingAgent?.id === agent.id;
              
              if (isEditing) {
                return (
                  <motion.div 
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    key={agent.id} 
                    className="agent-edit-modal"
                  >
                    <div className="flex justify-between items-center mb-4 border-b border-neutral-700 pb-2">
                      <h3 className="agent-hire-title" style={{ fontSize: '1rem', margin: 0 }}>Edit System Configuration</h3>
                      <button onClick={() => setEditingAgent(null)} className="text-neutral-400 hover:text-white">✕</button>
                    </div>

                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="jules-form-label" style={{ fontSize: '0.65rem' }}>Agent Name</label>
                          <input type="text" value={editingAgent.name} onChange={e => setEditingAgent({...editingAgent, name: e.target.value})} className="jules-input" style={{ padding: '8px 12px' }} />
                        </div>
                        <div>
                          <label className="jules-form-label" style={{ fontSize: '0.65rem' }}>Role Description</label>
                          <input type="text" value={editingAgent.role} onChange={e => setEditingAgent({...editingAgent, role: e.target.value})} className="jules-input" style={{ padding: '8px 12px' }} />
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="jules-form-label" style={{ fontSize: '0.65rem' }}>Model Provider</label>
                          <select value={editingAgent.model} onChange={e => setEditingAgent({...editingAgent, model: e.target.value})} className="jules-input" style={{ padding: '8px 12px' }}>
                            <option value="gpt-4o">gpt-4o</option>
                            <option value="claude-3.5-sonnet">claude-3.5-sonnet</option>
                            <option value="gemini-1.5-pro">gemini-1.5-pro</option>
                            <option value="qwen2.5-coder">qwen2.5-coder</option>
                          </select>
                        </div>
                        <div>
                          <label className="jules-form-label" style={{ fontSize: '0.65rem' }}>Capacities & Skills</label>
                          <input type="text" value={editingAgent.custom_skills} onChange={e => setEditingAgent({...editingAgent, custom_skills: e.target.value})} className="jules-input" style={{ padding: '8px 12px' }} />
                        </div>
                      </div>

                      <div>
                        <label className="jules-form-label" style={{ fontSize: '0.65rem' }}>Equipped Tool Primitives</label>
                        <div className="flex gap-4">
                          {['jules', 'github', 'bash', 'docker'].map(tool => (
                            <label key={tool} className="flex items-center gap-2 text-xs text-white bg-neutral-900 p-2 rounded border border-neutral-700 cursor-pointer hover:border-neutral-500">
                              <input 
                                type="checkbox" 
                                checked={editingAgent.custom_tools.includes(tool)}
                                onChange={e => {
                                  const newTools = e.target.checked 
                                    ? [...editingAgent.custom_tools, tool]
                                    : editingAgent.custom_tools.filter(t => t !== tool);
                                  setEditingAgent({...editingAgent, custom_tools: newTools});
                                }}
                              />
                              {tool === 'jules' ? '🔮' : tool === 'github' ? '🐙' : tool === 'docker' ? '🐳' : '⌨️'} {tool}
                            </label>
                          ))}
                        </div>
                      </div>

                      <div className="flex gap-4 mt-6">
                        <button onClick={handleSaveEdit} className="jules-dispatch-btn">
                          💾 Save Configurations
                        </button>
                        <button onClick={() => setEditingAgent(null)} className="jules-action-btn" style={{ padding: '10px', width: '100%', fontSize: '0.9rem', background: 'var(--bg-card)' }}>
                          ❌ Cancel
                        </button>
                      </div>
                    </div>
                  </motion.div>
                );
              }

              return (
              <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                key={agent.id} 
                className="agent-card group"
              >
                <button 
                  onClick={() => setEditingAgent(agent)}
                  className="agent-edit-btn opacity-0 group-hover:opacity-100"
                >
                  ⚙️ Edit Profile
                </button>

                <div className="flex-1 pt-2">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <h2 className="agent-card-name">{agent.name}</h2>
                      <span className="agent-card-role">{agent.role}</span>
                    </div>
                    <div className="flex gap-2 items-center lg:pr-20">
                      <span className="agent-status-label">{agent.status}</span>
                      <div className={`agent-status-dot ${agent.status === "Alive" ? "alive" : "dead"}`}></div>
                    </div>
                  </div>

                  <div className="mt-4">
                    <label className="jules-form-label" style={{ fontSize: '0.65rem' }}>Assigned Brain (Model)</label>
                    <div className="jules-input" style={{ padding: '6px 12px', fontSize: '0.8rem', cursor: 'pointer' }} onClick={() => setEditingAgent(agent)}>
                      {agent.model}
                    </div>
                  </div>
                  
                  <div className="mt-4">
                    <label className="jules-form-label" style={{ fontSize: '0.65rem' }}>Intrinsic Skills</label>
                    <p className="agent-card-skills">
                      {agent.custom_skills}
                    </p>
                  </div>
                </div>

                <div className="agent-card-divider hidden md:block"></div>

                <div className="flex-1 flex flex-col justify-between pt-2">
                  <div>
                    <label className="block text-[10px] font-bold text-neutral-500 mb-2 uppercase tracking-wide">Equipped Primtives (Tools)</label>
                    <div className="flex flex-wrap gap-2">
                      {agent.custom_tools.map(tool => (
                        <span key={tool} className={`agent-tool-badge ${tool}`}
                        >
                          {tool === 'jules' ? '🔮 Jules AI' : tool === 'github' ? '🐙 GitHub' : tool === 'docker' ? '🐳 Docker' : '⌨️ Bash'}
                        </span>
                      ))}
                    </div>
                  </div>

                  <button 
                    onClick={() => toggleAgent(agent.id)}
                    className={`agent-action-btn ${agent.status === "Alive" ? "suspend" : "provision"}`}
                  >
                    {agent.status === 'Alive' ? 'Suspend Instance' : 'Provision & Wake Up'}
                  </button>
                </div>
              </motion.div>
            )})}
          </div>

        </div>
      )}
    </div>
  );
};

export default AgentManager;
