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
    <div className="flex flex-col h-full bg-neutral-900 border-l border-neutral-800">
      {/* Top Banner & Navigation */}
      <header className="bg-neutral-900 border-b border-neutral-800 py-4 px-8 sticky top-0 z-10">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black tracking-tight text-white flex items-center gap-2">
              🤖 Agent Strategy & Workforce
            </h1>
            <p className="text-neutral-400 text-sm mt-1">Hire workers, provision tools, and issue autonomous dispatches.</p>
          </div>

          <div className="flex bg-neutral-800 p-1 rounded-lg border border-neutral-700">
            <button 
              className={`px-6 py-2 rounded-md text-sm font-bold transition-all ${activeTab === 'ROSTER' ? 'bg-neutral-700 text-white shadow' : 'text-neutral-400 hover:text-white'}`}
              onClick={() => setActiveTab('ROSTER')}
            >
              🏢 Agent Roster (Foundry)
            </button>
            <button 
              className={`px-6 py-2 rounded-md text-sm font-bold transition-all flex items-center gap-2 ${activeTab === 'JULES_DISPATCH' ? 'bg-blue-600/20 text-blue-400 shadow ring-1 ring-blue-500/50' : 'text-neutral-400 hover:text-white'}`}
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
          
          <div className="flex justify-between items-center mb-8">
            <h2 className="text-xl font-bold text-white">Active Workforce</h2>
            <button 
              className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2 px-6 rounded-lg transition-colors flex items-center gap-2 shadow-lg"
              onClick={() => setShowHireModal(!showHireModal)}
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
                className="bg-neutral-800 border border-emerald-500/30 rounded-xl p-6 mb-8 shadow-2xl relative overflow-hidden"
              >
                <div className="absolute top-0 right-0 p-4 opacity-10 text-6xl">📝</div>
                <h3 className="text-emerald-400 font-bold mb-4 flex items-center gap-2">
                  <span className="bg-emerald-500/20 p-1 px-2 rounded">Recruitment Form</span>
                  Define Agent Capabilities
                </h3>

                <form onSubmit={handleHireAgent} className="grid grid-cols-1 md:grid-cols-2 gap-6 relative z-10">
                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs font-semibold text-neutral-400 mb-1 uppercase tracking-wide">Agent Name (e.g. Alice, Hermes)</label>
                      <input required type="text" placeholder="Worker Name" value={newAgent.name} onChange={(e) => setNewAgent({...newAgent, name: e.target.value})} className="w-full bg-neutral-900 border border-neutral-700 text-white text-sm rounded-lg p-2.5 outline-none focus:border-emerald-500" />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-neutral-400 mb-1 uppercase tracking-wide">Role Description</label>
                      <input required type="text" placeholder="React & UI/UX Expert" value={newAgent.role} onChange={(e) => setNewAgent({...newAgent, role: e.target.value})} className="w-full bg-neutral-900 border border-neutral-700 text-white text-sm rounded-lg p-2.5 outline-none focus:border-emerald-500" />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-neutral-400 mb-1 uppercase tracking-wide">Capacities & Skills</label>
                      <textarea required placeholder="Tailwind CSS, React Hooks, UI Animations, Microinteractions..." value={newAgent.skills} onChange={(e) => setNewAgent({...newAgent, skills: e.target.value})} className="w-full bg-neutral-900 border border-neutral-700 text-white text-sm rounded-lg p-2.5 outline-none focus:border-emerald-500" rows={3}></textarea>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="flex gap-4">
                      <div className="flex-1">
                        <label className="block text-xs font-semibold text-neutral-400 mb-1 uppercase tracking-wide">Permission Tier</label>
                        <select value={newAgent.tier} onChange={(e) => setNewAgent({...newAgent, tier: e.target.value})} className="w-full bg-neutral-900 border border-neutral-700 text-white text-sm rounded-lg p-2.5 outline-none focus:border-emerald-500">
                          <option>Tier 1 (Executive Override)</option>
                          <option>Tier 2 (Cloud Operations)</option>
                          <option>Tier 3 (Local Swarm)</option>
                        </select>
                      </div>
                      <div className="flex-1">
                        <label className="block text-xs font-semibold text-neutral-400 mb-1 uppercase tracking-wide">Model Provider</label>
                        <select value={newAgent.model} onChange={(e) => setNewAgent({...newAgent, model: e.target.value})} className="w-full bg-neutral-900 border border-neutral-700 text-white text-sm rounded-lg p-2.5 outline-none focus:border-emerald-500">
                          <option value="gpt-4o">GPT-4o</option>
                          <option value="claude-3.5-sonnet">Claude 3.5 Sonnet</option>
                          <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
                          <option value="qwen2.5-coder">Qwen2.5-Coder (Local)</option>
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-neutral-400 mb-2 uppercase tracking-wide">Equip Caveman Primitives (Tools)</label>
                      <div className="grid grid-cols-2 gap-3">
                        <label className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${newAgent.tools.jules ? 'bg-blue-900/40 border-blue-500 text-blue-200' : 'bg-neutral-900 border-neutral-700 text-neutral-400 hover:border-neutral-500'}`}>
                          <input type="checkbox" checked={newAgent.tools.jules} onChange={(e) => setNewAgent({...newAgent, tools: {...newAgent.tools, jules: e.target.checked}})} className="hidden" />
                          <span className="text-xl">🔮</span>
                          <span className="font-semibold text-sm">Jules.Google API</span>
                        </label>
                        <label className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${newAgent.tools.github ? 'bg-neutral-700 border-neutral-400 text-white' : 'bg-neutral-900 border-neutral-700 text-neutral-400 hover:border-neutral-500'}`}>
                          <input type="checkbox" checked={newAgent.tools.github} onChange={(e) => setNewAgent({...newAgent, tools: {...newAgent.tools, github: e.target.checked}})} className="hidden" />
                          <span className="text-xl">🐙</span>
                          <span className="font-semibold text-sm">GitHub CLI (PRs)</span>
                        </label>
                        <label className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${newAgent.tools.bash ? 'bg-amber-900/40 border-amber-500 text-amber-200' : 'bg-neutral-900 border-neutral-700 text-neutral-400 hover:border-neutral-500'}`}>
                          <input type="checkbox" checked={newAgent.tools.bash} onChange={(e) => setNewAgent({...newAgent, tools: {...newAgent.tools, bash: e.target.checked}})} className="hidden" />
                          <span className="text-xl">⌨️</span>
                          <span className="font-semibold text-sm">Bash Terminal</span>
                        </label>
                        <label className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${newAgent.tools.docker ? 'bg-cyan-900/40 border-cyan-500 text-cyan-200' : 'bg-neutral-900 border-neutral-700 text-neutral-400 hover:border-neutral-500'}`}>
                          <input type="checkbox" checked={newAgent.tools.docker} onChange={(e) => setNewAgent({...newAgent, tools: {...newAgent.tools, docker: e.target.checked}})} className="hidden" />
                          <span className="text-xl">🐳</span>
                          <span className="font-semibold text-sm">Docker Sandbox</span>
                        </label>
                      </div>
                    </div>

                    <button type="submit" className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 mt-4 rounded-lg shadow-lg transition-colors">
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
                    className="bg-neutral-800 border border-emerald-500/50 rounded-xl p-6 shadow-2xl relative transition-all"
                  >
                    <div className="flex justify-between items-center mb-4 border-b border-neutral-700 pb-2">
                      <h3 className="text-emerald-400 font-bold">Edit System Configuration</h3>
                      <button onClick={() => setEditingAgent(null)} className="text-neutral-400 hover:text-white">✕</button>
                    </div>

                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-[10px] font-bold text-neutral-500 mb-1 uppercase tracking-wide">Agent Name</label>
                          <input type="text" value={editingAgent.name} onChange={e => setEditingAgent({...editingAgent, name: e.target.value})} className="w-full bg-neutral-900 border border-neutral-700 text-white text-sm rounded p-2" />
                        </div>
                        <div>
                          <label className="block text-[10px] font-bold text-neutral-500 mb-1 uppercase tracking-wide">Role Description</label>
                          <input type="text" value={editingAgent.role} onChange={e => setEditingAgent({...editingAgent, role: e.target.value})} className="w-full bg-neutral-900 border border-neutral-700 text-white text-sm rounded p-2" />
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-[10px] font-bold text-neutral-500 mb-1 uppercase tracking-wide">Model Provider</label>
                          <select value={editingAgent.model} onChange={e => setEditingAgent({...editingAgent, model: e.target.value})} className="w-full bg-neutral-900 border border-neutral-700 text-white text-sm rounded p-2">
                            <option value="gpt-4o">gpt-4o</option>
                            <option value="claude-3.5-sonnet">claude-3.5-sonnet</option>
                            <option value="gemini-1.5-pro">gemini-1.5-pro</option>
                            <option value="qwen2.5-coder">qwen2.5-coder</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-[10px] font-bold text-neutral-500 mb-1 uppercase tracking-wide">Capacities & Skills</label>
                          <input type="text" value={editingAgent.custom_skills} onChange={e => setEditingAgent({...editingAgent, custom_skills: e.target.value})} className="w-full bg-neutral-900 border border-neutral-700 text-white text-sm rounded p-2" />
                        </div>
                      </div>

                      <div>
                        <label className="block text-[10px] font-bold text-neutral-500 mb-1 uppercase tracking-wide">Equipped Tool Primitives</label>
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
                        <button onClick={handleSaveEdit} className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2 rounded-lg transition-colors">
                          💾 Save Configurations
                        </button>
                        <button onClick={() => setEditingAgent(null)} className="flex-1 bg-neutral-700 hover:bg-neutral-600 text-white font-bold py-2 rounded-lg transition-colors">
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
                className="bg-neutral-800 border border-neutral-700 rounded-xl p-6 shadow-xl relative transition-all hover:border-neutral-600 flex flex-col md:flex-row gap-6 group"
              >
                <button 
                  onClick={() => setEditingAgent(agent)}
                  className="absolute top-4 right-4 text-xs font-bold bg-neutral-700 hover:bg-emerald-600 hover:text-white text-neutral-300 py-1.5 px-3 rounded shadow opacity-0 group-hover:opacity-100 transition-all border border-neutral-600"
                >
                  ⚙️ Edit Profile
                </button>

                <div className="flex-1 pt-2">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <h2 className="text-xl font-black tracking-tight text-white mb-1">{agent.name}</h2>
                      <span className="text-xs font-semibold uppercase tracking-wider text-neutral-400">{agent.role}</span>
                    </div>
                    <div className="flex gap-2 items-center lg:pr-20">
                      <span className="text-[10px] uppercase font-bold text-neutral-500">{agent.status}</span>
                      <div className={`w-3 h-3 rounded-full shadow-lg ${agent.status === 'Alive' ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' : 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]'}`}></div>
                    </div>
                  </div>

                  <div className="mt-4">
                    <label className="block text-[10px] font-bold text-neutral-500 mb-1 uppercase tracking-wide">Assigned Brain (Model)</label>
                    <div className="text-sm font-semibold text-white bg-neutral-900 border border-neutral-700 rounded px-3 py-2 cursor-pointer hover:border-neutral-500" onClick={() => setEditingAgent(agent)}>
                      {agent.model}
                    </div>
                  </div>
                  
                  <div className="mt-4">
                    <label className="block text-[10px] font-bold text-neutral-500 mb-1 uppercase tracking-wide">Intrinsic Skills</label>
                    <p className="text-xs text-neutral-300 bg-neutral-900/50 p-2 rounded border border-neutral-700/50 min-h-[40px]">
                      {agent.custom_skills}
                    </p>
                  </div>
                </div>

                <div className="w-px bg-neutral-700 hidden md:block"></div>

                <div className="flex-1 flex flex-col justify-between pt-2">
                  <div>
                    <label className="block text-[10px] font-bold text-neutral-500 mb-2 uppercase tracking-wide">Equipped Primtives (Tools)</label>
                    <div className="flex flex-wrap gap-2">
                      {agent.custom_tools.map(tool => (
                        <span key={tool} className={`text-xs px-2 py-1 rounded font-semibold border
                          ${tool === 'jules' ? 'bg-blue-900/30 border-blue-500/50 text-blue-300' : 
                            tool === 'github' ? 'bg-neutral-700 border-neutral-500 text-white' : 
                            tool === 'docker' ? 'bg-cyan-900/30 border-cyan-500/50 text-cyan-300' : 
                            'bg-amber-900/30 border-amber-500/50 text-amber-300'}`}
                        >
                          {tool === 'jules' ? '🔮 Jules AI' : tool === 'github' ? '🐙 GitHub' : tool === 'docker' ? '🐳 Docker' : '⌨️ Bash'}
                        </span>
                      ))}
                    </div>
                  </div>

                  <button 
                    onClick={() => toggleAgent(agent.id)}
                    className={`mt-6 w-full font-bold py-2 px-4 rounded-lg transition-all duration-300 text-sm border
                      ${agent.status === 'Alive' ? 'bg-neutral-700 text-neutral-300 hover:bg-neutral-600 border-neutral-600' : 'bg-blue-600 hover:bg-blue-500 text-white border-blue-500'}`}
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
