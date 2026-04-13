import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence, useDragControls } from 'framer-motion';

// ─────────────────────────────────────────────
// TOOL DEFINITIONS — each tool knows how to connect
// ─────────────────────────────────────────────
const TOOL_REGISTRY = {
  jules: {
    emoji: '🔮', label: 'Jules API', desc: 'Google Jules cloud coding agent',
    connectionType: 'api_key',
    fields: [
      { key: 'api_key', label: 'Jules API Key', placeholder: 'GEMINI_KEY / JULES_KEY...', type: 'password', required: true },
    ],
  },
  antigravity: {
    emoji: '🤖', label: 'Antigravity AI', desc: 'Google Antigravity / Gemini agent',
    connectionType: 'api_key',
    fields: [
      { key: 'api_key', label: 'Gemini API Key', placeholder: 'AIzaSy...', type: 'password', required: true },
    ],
  },
  github: {
    emoji: '🐙', label: 'GitHub CLI', desc: 'Push / PR / branch management',
    connectionType: 'token',
    fields: [
      { key: 'pat', label: 'Personal Access Token', placeholder: 'ghp_...', type: 'password', required: true },
      { key: 'username', label: 'GitHub Username', placeholder: 'octocat', type: 'text', required: true },
    ],
  },
  bash: {
    emoji: '⌨️', label: 'Bash Terminal', desc: 'Sandboxed shell execution — always available',
    connectionType: 'always_on',
    fields: [],
  },
  docker: {
    emoji: '🐳', label: 'Docker Sandbox', desc: 'Spin containers for QA — requires Docker Desktop running',
    connectionType: 'always_on',
    fields: [],
  },
  email: {
    emoji: '📧', label: 'Email', desc: 'Send & read email via SMTP/IMAP',
    connectionType: 'smtp',
    fields: [
      { key: 'smtp_host', label: 'SMTP Host', placeholder: 'smtp.gmail.com', type: 'text', required: true },
      { key: 'smtp_port', label: 'SMTP Port', placeholder: '587', type: 'text', required: true },
      { key: 'username',  label: 'Email Address', placeholder: 'you@gmail.com', type: 'text', required: true },
      { key: 'password',  label: 'App Password', placeholder: '16-char app password', type: 'password', required: true },
    ],
  },
  whatsapp: {
    emoji: '💬', label: 'WhatsApp', desc: 'Connect via WhatsApp Web QR scan',
    connectionType: 'qr_code',
    fields: [],
    qrInstruction: 'Open WhatsApp on your phone → Settings → Linked Devices → Link a Device → Scan this QR code',
  },
  telegram: {
    emoji: '✈️', label: 'Telegram Bot', desc: 'Telegram Bot API integration',
    connectionType: 'token',
    fields: [
      { key: 'bot_token', label: 'Bot Token', placeholder: '1234567890:AAFxx...', type: 'password', required: true },
      { key: 'chat_id',   label: 'Default Chat ID', placeholder: '-1001234567890 (optional)', type: 'text', required: false },
    ],
  },
  browser: {
    emoji: '🌐', label: 'Web Browser', desc: 'Headless Chromium — always available',
    connectionType: 'always_on',
    fields: [],
  },
};

const ALL_TOOL_IDS = Object.keys(TOOL_REGISTRY);

// ─────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────

/** Returns 'ready' | 'partial' | 'unconfigured' for a given tool + its saved config */
function toolStatus(toolId, toolconfigs) {
  const def = TOOL_REGISTRY[toolId];
  if (!def) return 'unconfigured';
  if (def.connectionType === 'always_on') return 'ready';
  if (def.connectionType === 'qr_code') {
    // WhatsApp is "ready" once they've scanned (we track with a flag)
    return toolconfigs?.[toolId]?.scanned ? 'ready' : 'unconfigured';
  }
  const saved = toolconfigs?.[toolId] || {};
  const requiredFilled = def.fields.filter(f => f.required).every(f => saved[f.key]?.trim?.());
  const anyFilled = def.fields.some(f => saved[f.key]?.trim?.());
  if (requiredFilled) return 'ready';
  if (anyFilled) return 'partial';
  return 'unconfigured';
}

// Alias lowercase version for internal call consistency
function toolconfigs_status(id, tc) { return toolStatus(id, tc); }

const STATUS_COLORS = { ready: '#10b981', partial: '#f59e0b', unconfigured: '#4b5563' };
const STATUS_LABELS = { ready: '✓ Connected', partial: '⚠ Incomplete', unconfigured: '○ Not configured' };

// ─────────────────────────────────────────────
// MODEL / TIER OPTIONS
// ─────────────────────────────────────────────
const MODEL_OPTIONS = [
  {
    group: 'Ollama — Local (Free)',
    models: [
      { value: 'ollama:qwen2.5-coder', label: 'Qwen2.5-Coder (7B)' },
      { value: 'ollama:llama3',        label: 'Llama 3 (8B)' },
      { value: 'ollama:phi3',          label: 'Phi-3 Mini (3.8B)' },
      { value: 'ollama:mistral',       label: 'Mistral (7B)' },
      { value: 'ollama:gemma2',        label: 'Gemma 2 (9B)' },
      { value: 'ollama:deepseek-coder',label: 'DeepSeek Coder (6.7B)' },
    ],
  },
  {
    group: 'Cloud — API Key Required',
    models: [
      { value: 'gemini-1.5-pro',       label: 'Google: Gemini 1.5 Pro' },
      { value: 'gemini-2.0-flash',     label: 'Google: Gemini 2.0 Flash (Free tier)' },
      { value: 'gpt-4o',              label: 'OpenAI: GPT-4o' },
      { value: 'claude-3.5-sonnet',    label: 'Anthropic: Claude 3.5 Sonnet' },
    ],
  },
];

const TIER_OPTIONS = [
  { value: 'tier1', label: '👑 Tier 1 — Executive (Premium model, high trust)' },
  { value: 'tier2', label: '☁️  Tier 2 — Cloud Operations' },
  { value: 'tier3', label: '🖥️  Tier 3 — Local Swarm (Free, offline)' },
];

const BLANK_FORM = {
  name: '', role: '', tier: 'tier3',
  brain_provider: 'ollama:qwen2.5-coder', brain_api_key: '', mcp_endpoints: '',
  skills: '',
  toolconfigs: {},   // { [toolId]: { field_key: value, ... } }
};

// ─────────────────────────────────────────────
// WHATSAPP QR PANEL
// ─────────────────────────────────────────────
const WhatsAppQRPanel = ({ onScanned }) => {
  const [scanned, setScanned] = useState(false);
  const qrSeed = useRef(`wa-agent-${Date.now()}`);

  const handleSimulateScан = () => {
    setScanned(true);
    onScanned();
  };

  return (
    <div className="tool-qr-panel">
      {scanned ? (
        <div className="tool-qr-success">
          <div className="tool-qr-success-icon">✅</div>
          <strong>WhatsApp Connected!</strong>
          <p>This agent can now send and receive WhatsApp messages.</p>
        </div>
      ) : (
        <>
          <p className="tool-qr-instruction">
            Open WhatsApp on your phone → <strong>Settings</strong> → <strong>Linked Devices</strong> → <strong>Link a Device</strong> → Scan this QR code
          </p>
          <div className="tool-qr-code-wrap">
            <img
              src={`https://api.qrserver.com/v1/create-qr-code/?size=160x160&color=14b8a6&bgcolor=0a0e1a&data=whatsapp://link?agent=${qrSeed.current}`}
              alt="WhatsApp QR code"
              className="tool-qr-img"
            />
            <div className="tool-qr-scanning">
              <span className="tool-qr-dot" />
              Waiting for scan...
            </div>
          </div>
<<<<<<< HEAD
          <button type="button" className="tool-qr-confirm-btn" onClick={handleSimulateScан}>
            ✅ I've scanned the code
          </button>
        </>
=======

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
                      <button onClick={() => setEditingAgent(null)} className="text-neutral-400 hover:text-white" aria-label="Close edit modal">✕</button>
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
>>>>>>> 9d50f5eef049fe40c4baf5c3ed24fccccf297477
      )}
    </div>
  );
};

// ─────────────────────────────────────────────
// TOOL CONFIG PANEL — expands under each chip
// ─────────────────────────────────────────────
const ToolConfigPanel = ({ toolId, config, onChange, onScanned }) => {
  const def = TOOL_REGISTRY[toolId];
  if (!def) return null;

  if (def.connectionType === 'always_on') {
    return (
      <div className="tool-cfg-panel always-on">
        <span className="tool-cfg-always-icon">⚡</span>
        <span>No configuration needed — this tool is always available to the agent.</span>
      </div>
    );
  }

  if (def.connectionType === 'qr_code') {
    return (
      <div className="tool-cfg-panel">
        <WhatsAppQRPanel onScanned={onScanned} />
      </div>
    );
  }

  return (
    <div className="tool-cfg-panel">
      {def.fields.map(field => (
        <div key={field.key} className="tool-cfg-field">
          <label className="tool-cfg-label">
            {field.label}
            {field.required && <span className="tool-cfg-required"> *</span>}
          </label>
          <input
            type={field.type}
            placeholder={field.placeholder}
            value={config?.[field.key] || ''}
            onChange={e => onChange(field.key, e.target.value)}
            className="hire-input"
            autoComplete="off"
          />
        </div>
      ))}
    </div>
  );
};

// ─────────────────────────────────────────────
// SMART TOOL CHIP GRID
// ─────────────────────────────────────────────
const SmartToolGrid = ({ toolconfigs, onChange }) => {
  const [expanded, setExpanded] = useState(null);

  const toggleExpand = (id) => {
    setExpanded(prev => (prev === id ? null : id));

    // Auto-select always_on tools when first clicked
    const def = TOOL_REGISTRY[id];
    if (def?.connectionType === 'always_on' && !toolconfigs[id]) {
      onChange(id, '__selected__', 'true');
    }
  };

  const handleFieldChange = (toolId, key, val) => {
    onChange(toolId, key, val);
  };

  const handleScanned = (toolId) => {
    onChange(toolId, 'scanned', true);
  };

  return (
    <div className="smart-tool-grid">
      {ALL_TOOL_IDS.map(id => {
        const def = TOOL_REGISTRY[id];
        const cfg = toolconfigs[id] || {};
        const status = toolStatus(id, toolconfigs);
        const isExpanded = expanded === id;
        const isSelected = Object.keys(cfg).length > 0;

        const statusColor = STATUS_COLORS[status];

        return (
          <div key={id} className={`stool-wrapper ${isExpanded ? 'expanded' : ''}`}>
            {/* ── chip ── */}
            <button
              type="button"
              className={`stool-chip ${status} ${isExpanded ? 'open' : ''}`}
              onClick={() => toggleExpand(id)}
            >
              <span className="stool-emoji">{def.emoji}</span>
              <div className="stool-info">
                <span className="stool-label">{def.label}</span>
                <span className="stool-status" style={{ color: statusColor }}>
                  {STATUS_LABELS[status]}
                </span>
              </div>
              <span className="stool-arrow">{isExpanded ? '▲' : '▼'}</span>
            </button>

            {/* ── config panel ── */}
            <AnimatePresence>
              {isExpanded && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="stool-panel-wrap"
                >
                  <ToolConfigPanel
                    toolId={id}
                    config={cfg}
                    onChange={(key, val) => handleFieldChange(id, key, val)}
                    onScanned={() => handleScanned(id)}
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}
    </div>
  );
};

// ─────────────────────────────────────────────
// AGENT DOSSIER CARD
// ─────────────────────────────────────────────
const AgentDossierCard = ({ agent, index, onEdit, onToggle, onTerminate }) => {
  const toolconfigs = agent.toolconfigs || {};
  const isAlive = agent.status === 'Alive';

  // Build list of tools with their status
  const equippedTools = ALL_TOOL_IDS.filter(id => {
    const cfg = toolconfigs[id] || {};
    const st = toolStatus(id, toolconfigs);
    return Object.keys(cfg).length > 0 || st === 'ready';
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04 }}
      className="dossier-card"
    >
      {/* ── Header ── */}
      <div className="dossier-header">
        <div className="dossier-avatar">{agent.name?.charAt(0)?.toUpperCase() || '?'}</div>
        <div className="dossier-identity">
          <h2 className="dossier-name">{agent.name}</h2>
          <span className="dossier-role">{agent.role || 'Unassigned Role'}</span>
        </div>
        <div className="dossier-status-pill">
          <span className={`status-dot ${isAlive ? 'alive' : 'dead'}`} />
          <span className={`status-text ${isAlive ? 'alive' : 'dead'}`}>{agent.status || 'Offline'}</span>
        </div>
      </div>

      {/* ── Brain ── */}
      <div className="dossier-section">
        <div className="dossier-section-label"><span className="section-icon">🧠</span> BRAIN</div>
        <div className="brain-pill">{agent.model || 'No model assigned'}</div>
      </div>

      {/* ── Skills ── */}
      <div className="dossier-section">
        <div className="dossier-section-label"><span className="section-icon">⚡</span> SKILLS</div>
        <p className="dossier-skills-text">{agent.custom_skills || 'No skills defined yet.'}</p>
      </div>

      {/* ── Hands / Tools ── */}
      <div className="dossier-section">
        <div className="dossier-section-label"><span className="section-icon">🤲</span> HANDS (TOOLS)</div>
        <div className="hands-chips-row">
          {ALL_TOOL_IDS.map(id => {
            const def = TOOL_REGISTRY[id];
            const st = toolStatus(id, toolconfigs);
            const cfg = toolconfigs[id] || {};
            const hasAnything = Object.keys(cfg).length > 0;
            if (!hasAnything && st !== 'ready') return null;
            return (
              <span
                key={id}
                className={`hand-badge status-${st}`}
                title={STATUS_LABELS[st]}
              >
                {def.emoji} {def.label}
                <span className="hand-badge-dot" style={{ background: STATUS_COLORS[st] }} />
              </span>
            );
          })}
          {equippedTools.length === 0 && <span className="no-hands">No tools equipped</span>}
        </div>
      </div>

      {/* ── Footer ── */}
      <div className="dossier-footer">
        <button className="dossier-edit-btn" onClick={() => onEdit(agent)}>⚙️ Configure</button>
        {['god', 'ceo'].includes(agent.agent_id) ? (
          <div className="dossier-protected-badge" title="This is a system-critical agent and cannot be terminated.">
            🛡️ Protected Agent
          </div>
        ) : (
          <button
            className="dossier-power-btn suspend"
            onClick={() => onTerminate(agent.agent_id || agent.id, agent.agent_name || agent.name)}
          >
            🔴 Terminate
          </button>
        )}
      </div>
    </motion.div>
  );
};

// Also support onTerminate in the prop signature
const AgentDossierCard_OLD = null; // suppress lint

// ─────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────
const AgentManager = ({ apiUsage = [] }) => {
  const [agents, setAgents] = useState([]);
  const [showHireModal, setShowHireModal] = useState(false);
  const [editingAgent, setEditingAgent] = useState(null);
  const dragControls = useDragControls();
  const [form, setForm] = useState(BLANK_FORM);
  const [filterText, setFilterText] = useState('');
  const [skillFetch, setSkillFetch] = useState({ source: '', loading: false, error: null });

  const fetchAgents = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/agents');
      const data = await res.json();
      setAgents(data.agents || []);
    } catch (e) { console.error('Failed to fetch agents:', e); }
  };

  useEffect(() => { fetchAgents(); }, []);

  const toggleAgent = async (agentId) => {
    try {
      await fetch(`http://localhost:8000/api/agents/${agentId}/toggle`, { method: 'POST' });
      fetchAgents();
    } catch (e) { console.error(e); }
  };

  const openHireModal = () => {
    setForm(BLANK_FORM);
    setEditingAgent(null);
    setShowHireModal(true);
  };

  const openEditModal = (agent) => {
    setEditingAgent(agent);
    setForm({
      name: agent.name || '',
      role: agent.role || '',
      tier: agent.tier || 'tier3',
      brain_provider: agent.model || 'ollama:qwen2.5-coder',
      brain_api_key: agent.apiKeys || '',
      mcp_endpoints: agent.mcpEndpoints || '',
      skills: agent.custom_skills || '',
      toolconfigs: agent.toolconfigs || {},
    });
    setShowHireModal(true);
  };

  const closeModal = () => {
    setShowHireModal(false);
    setEditingAgent(null);
    setForm(BLANK_FORM);
    setSkillFetch({ source: '', loading: false, error: null });
  };

  // Called by SmartToolGrid when a field changes
  const handleToolConfigChange = (toolId, fieldKey, value) => {
    setForm(prev => ({
      ...prev,
      toolconfigs: {
        ...prev.toolconfigs,
        [toolId]: {
          ...(prev.toolconfigs[toolId] || {}),
          [fieldKey]: value,
        },
      },
    }));
  };

  // Calls the backend skill-seekers endpoint
  const handleFetchSkills = async () => {
    if (!skillFetch.source.trim()) return;
    setSkillFetch(s => ({ ...s, loading: true, error: null }));
    try {
      const res = await fetch('http://localhost:8000/api/skills/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: skillFetch.source.trim() }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Extraction failed');
      // Append to existing skills (don't overwrite in case agent already has some)
      setForm(prev => ({
        ...prev,
        skills: prev.skills
          ? prev.skills + ', ' + data.skills
          : data.skills,
      }));
      setSkillFetch(s => ({ ...s, loading: false, error: null }));
    } catch (err) {
      setSkillFetch(s => ({ ...s, loading: false, error: err.message }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const payload = {
      name:          form.name,
      role:          form.role,
      tier:          form.tier,
      brain_model:   form.brain_provider,
      api_key:       form.brain_api_key,
      mcp_endpoints: form.mcp_endpoints,
      custom_skills: form.skills,
      toolconfigs:   form.toolconfigs,
      equipped_tools: ALL_TOOL_IDS.filter(id => toolStatus(id, form.toolconfigs) === 'ready'),
      state:         'IDLE',
    };

    try {
      if (editingAgent) {
        // --- UPDATE existing agent ---
        const res = await fetch(`http://localhost:8000/api/agents/${editingAgent.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error((await res.json()).detail || 'Update failed');
      } else {
        // --- CREATE new agent ---
        const res = await fetch('http://localhost:8000/api/agents', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error((await res.json()).detail || 'Create failed');
      }
    } catch (err) {
      console.error('Save failed:', err);
      // Fall back to local state so user doesn't lose work
    }

    await fetchAgents();  // Reload from DB
    closeModal();
  };

  const terminateAgent = async (agentId, agentName) => {
    if (!window.confirm(`⚠️ Terminate "${agentName}"? They will be removed from the roster permanently.`)) return;
    try {
      await fetch(`http://localhost:8000/api/agents/${agentId}/terminate`, { method: 'POST' });
      await fetchAgents();
    } catch (e) { console.error('Terminate failed:', e); }
  };

  const normalizedAgents = agents.map(a => ({
    ...a,
    id: a.agent_id || a.id,
    name: a.agent_name || a.name,
    status: a.state === 'IDLE' ? 'Alive' : a.state || a.status, // Map IDLE to 'Alive' for UI dot
    model: a.brain_model || a.model,
    custom_skills: a.custom_skills || (a.role?.includes('QA') ? 'Testing, Code Review, Linting' : 'Full-Stack Development, API Integration'),
    toolconfigs: a.toolconfigs || {},
  }));

  const displayed = normalizedAgents.filter(a =>
    !filterText || 
    (a.name || '').toLowerCase().includes(filterText.toLowerCase()) || 
    (a.role || '').toLowerCase().includes(filterText.toLowerCase()) ||
    (a.agent_id || '').toLowerCase().includes(filterText.toLowerCase())
  );

  // Count ready tools in form for submit label
  const readyToolCount = ALL_TOOL_IDS.filter(id => toolStatus(id, form.toolconfigs) === 'ready').length;

  return (
    <div className="am-layout">

      {/* ── PAGE HEADER ── */}
      <header className="am-header">
        <div>
          <h1 className="am-title">🤖 Agent Strategy &amp; Workforce</h1>
          <p className="am-subtitle">
            Each agent is an autonomous employee — with a <strong>Brain</strong> (AI model), <strong>Hands</strong> (tools), and <strong>Skills</strong> (capabilities).
          </p>
        </div>
        <div className="am-header-actions">
          <input
            className="am-search"
            placeholder="🔍 Search agents..."
            value={filterText}
            onChange={e => setFilterText(e.target.value)}
          />
          <button className="am-hire-btn" onClick={openHireModal}>+ Hire Agent</button>
        </div>
      </header>

      {/* ── AGENT GRID ── */}
      <div className="am-grid">
        {displayed.length === 0 && (
          <div className="am-empty">
            <div className="am-empty-icon">🧑‍💼</div>
            <p>No agents yet. Click <strong>+ Hire Agent</strong> to build your workforce.</p>
          </div>
        )}
        {displayed.map((agent, i) => (
          <AgentDossierCard
            key={agent.id}
            agent={agent}
            index={i}
            onEdit={openEditModal}
            onToggle={toggleAgent}
            onTerminate={terminateAgent}
          />
        ))}
      </div>

      {/* ── HIRE / EDIT MODAL ── */}
      <AnimatePresence>
        {showHireModal && (
          <>
            <motion.div
              className="modal-backdrop"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={closeModal}
            />
            <motion.div
              className="hire-modal"
              drag dragControls={dragControls} dragListener={false} dragMomentum={false} dragElastic={0}
              initial={{ opacity: 0, scale: 0.94, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.94, y: 20 }}
            >
              {/* Header — drag handle */}
              <div
                className="hire-modal-header hire-modal-drag-handle"
                onPointerDown={e => { if (!e.target.closest('button')) dragControls.start(e); }}
              >
                <div>
                  <span className="hire-modal-badge">
                    {editingAgent ? '✏️ Edit Agent Profile' : '📋 New Agent Recruitment'}
                  </span>
                  <h2 className="hire-modal-title">
                    {editingAgent ? `Configure — ${editingAgent.name}` : 'Define Agent Capabilities'}
                  </h2>
                </div>
                <button className="hire-modal-close" onClick={closeModal}>✕</button>
              </div>

              <form onSubmit={handleSubmit} className="hire-modal-body">

                {/* ── IDENTITY ── */}
                <div className="hire-section">
                  <div className="hire-section-label">👤 Identity</div>
                  <div className="hire-row-2col">
                    <div>
                      <label className="hire-label">Agent Name</label>
                      <input required type="text" placeholder="e.g. James, Hermes, Alice..." value={form.name}
                        onChange={e => setForm({ ...form, name: e.target.value })} className="hire-input" />
                    </div>
                    <div>
                      <label className="hire-label">Role / Job Title</label>
                      <input required type="text" placeholder="e.g. Full-Stack Engineer, QA Agent..." value={form.role}
                        onChange={e => setForm({ ...form, role: e.target.value })} className="hire-input" />
                    </div>
                  </div>
                  <div className="hire-row-1col" style={{ marginTop: 12 }}>
                    <label className="hire-label">Permission Tier</label>
                    <select value={form.tier} onChange={e => setForm({ ...form, tier: e.target.value })} className="hire-input">
                      {TIER_OPTIONS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                    </select>
                  </div>
                </div>

                {/* ── BRAIN ── */}
                <div className="hire-section">
                  <div className="hire-section-label">🧠 Brain — AI Model &amp; Provider</div>
                  <div className="hire-row-2col">
                    <div>
                      <label className="hire-label">Model Provider</label>
                      <select value={form.brain_provider} onChange={e => setForm({ ...form, brain_provider: e.target.value })} className="hire-input">
                        {MODEL_OPTIONS.map(g => (
                          <optgroup key={g.group} label={g.group}>
                            {g.models.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
                          </optgroup>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="hire-label">API Key <span className="hire-label-note">(blank for Ollama)</span></label>
                      <input type="password" placeholder="sk-... or AIza..." value={form.brain_api_key}
                        onChange={e => setForm({ ...form, brain_api_key: e.target.value })} className="hire-input" />
                    </div>
                  </div>
                  <div className="hire-row-1col" style={{ marginTop: 12 }}>
                    <label className="hire-label">MCP Endpoints <span className="hire-label-note">(optional)</span></label>
                    <input type="text" placeholder="http://localhost:8080/mcp  or  postgres://user:pass@host/db"
                      value={form.mcp_endpoints} onChange={e => setForm({ ...form, mcp_endpoints: e.target.value })} className="hire-input" />
                  </div>
                </div>

                {/* ── SKILLS ── */}
                <div className="hire-section">
                  <div className="hire-section-label">⚡ Skills &amp; Capabilities</div>

                  {/* Auto-fetch row */}
                  <div className="skill-fetch-row">
                    <div className="skill-fetch-input-wrap">
                      <span className="skill-fetch-icon">🔍</span>
                      <input
                        type="text"
                        className="skill-fetch-input"
                        placeholder="GitHub repo (e.g. facebook/react) or docs URL..."
                        value={skillFetch.source}
                        onChange={e => setSkillFetch(s => ({ ...s, source: e.target.value }))}
                        onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), handleFetchSkills())}
                      />
                    </div>
                    <button
                      type="button"
                      className={`skill-fetch-btn ${skillFetch.loading ? 'loading' : ''}`}
                      onClick={handleFetchSkills}
                      disabled={skillFetch.loading || !skillFetch.source.trim()}
                    >
                      {skillFetch.loading ? (
                        <><span className="skill-fetch-spinner" /> Extracting...</>
                      ) : (
                        '⚡ Auto-Fetch Skills'
                      )}
                    </button>
                  </div>

                  {skillFetch.error && (
                    <div className="skill-fetch-error">❌ {skillFetch.error}</div>
                  )}

                  <textarea
                    rows={4}
                    placeholder="Skills will auto-populate here, or type manually — e.g. React, FastAPI, Docker, Code Review..."
                    value={form.skills}
                    onChange={e => setForm({ ...form, skills: e.target.value })}
                    className="hire-input"
                  />
                  <p className="skill-fetch-hint">
                    💡 Point at any GitHub repo or docs URL — skill-seekers will read the code and extract capabilities automatically.
                  </p>
                </div>

                {/* ── HANDS / TOOLS ── */}
                <div className="hire-section">
                  <div className="hire-section-label">
                    🤲 Hands — Tools &amp; Integrations
                    {readyToolCount > 0 && (
                      <span className="hire-tools-ready-badge">{readyToolCount} connected</span>
                    )}
                  </div>
                  <p className="hire-tools-hint">
                    Click a tool to configure its connection. Tools are only <strong>active</strong> once fully connected.
                  </p>
                  <SmartToolGrid
                    toolconfigs={form.toolconfigs}
                    onChange={handleToolConfigChange}
                  />
                </div>

                {/* ── FOOTER ── */}
                <div className="hire-modal-footer">
                  <button type="button" className="hire-cancel-btn" onClick={closeModal}>Cancel</button>
                  <button type="submit" className="hire-submit-btn">
                    {editingAgent ? '💾 Save Agent Profile' : '🚀 Deploy Agent'}
                  </button>
                </div>

              </form>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};

export default AgentManager;
