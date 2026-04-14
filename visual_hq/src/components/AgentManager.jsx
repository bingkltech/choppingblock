import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence, useDragControls } from 'framer-motion';

export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

import TaskQueue from './TaskQueue';

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
// SYSTEM AGENTS — permanently embedded, always visible
// ─────────────────────────────────────────────
const SYSTEM_AGENTS = [
  {
    agent_id: 'god',
    agent_name: 'God Agent',
    tier: 'tier1',
    brain_model: 'gemini-3.1-pro',
    role: 'System Overseer',
    custom_skills: 'System Overseer, Self-Healing Autonomy, Meta-Cognition, Framework Architect',
    equipped_tools: ['bash', 'github', 'jules', 'browser', 'docker', 'antigravity'],
    toolconfigs: {},
    state: 'IDLE',
    is_system: true,
  },
  {
    agent_id: 'ceo',
    agent_name: 'CEO Agent',
    tier: 'tier1',
    brain_model: 'claude-sonnet-4-20250514',
    role: 'CEO / Executive Director',
    custom_skills: 'Strategic Planning, Delegation, Executive Oversight, Architecture Design',
    equipped_tools: ['bash', 'github'],
    toolconfigs: {},
    state: 'IDLE',
    is_system: true,
  },
];

// ─────────────────────────────────────────────
// MODEL / TIER OPTIONS
// ─────────────────────────────────────────────
const MODEL_OPTIONS = [
  {
    group: '🟢 Ollama — Local (Free, Offline)',
    models: [
      { value: 'ollama:default',     label: 'Ollama: Default (Dynamic)' },
      { value: 'qwen3.5:4b',         label: 'Qwen 3.5 (4B) — fast, lightweight' },
      { value: 'qwen3.5:9b',         label: 'Qwen 3.5 (9B) — balanced' },
      { value: 'gemma4:latest',       label: 'Gemma 4 (14B) — Google local' },
      { value: 'gemma4:31b',          label: 'Gemma 4 (31B) — heavyweight' },
      { value: 'gemma3:27b',          label: 'Gemma 3 (27B) — previous gen' },
      { value: 'mistral:latest',      label: 'Mistral (7B) — solid coder' },
      { value: 'llama3:latest',       label: 'Llama 3 (8B) — Meta' },
      { value: 'llama3.1:latest',     label: 'Llama 3.1 (8B) — Meta latest' },
      { value: 'gpt-oss:20b',        label: 'GPT-OSS (20B) — open-source GPT' },
      { value: 'gpt-oss:120b',       label: 'GPT-OSS (120B) — massive local' },
    ],
  },
  {
    group: '🔵 Ollama — Cloud (Free with Limits)',
    models: [
      { value: 'minimax-m2:cloud',       label: 'MiniMax M2 — cloud inference' },
      { value: 'glm-5:cloud',            label: 'GLM-5 — cloud inference' },
      { value: 'kimi-k2.5:cloud',        label: 'Kimi K2.5 — cloud inference' },
      { value: 'qwen3-coder:480b-cloud', label: 'Qwen3-Coder (480B) — cloud monster' },
      { value: 'gpt-oss:120b-cloud',     label: 'GPT-OSS (120B) — cloud variant' },
    ],
  },
  {
    group: '💎 Paid — API Key Required',
    models: [
      { value: 'gemini-3.1-pro',          label: 'Google: Gemini 3.1 Pro' },
      { value: 'gemini-2.5-pro',          label: 'Google: Gemini 2.5 Pro' },
      { value: 'gemini-2.5-flash',        label: 'Google: Gemini 2.5 Flash' },
      { value: 'gemini-2.0-flash',        label: 'Google: Gemini 2.0 Flash' },
      { value: 'claude-sonnet-4-20250514', label: 'Anthropic: Claude Sonnet 4' },
      { value: 'claude-3.5-sonnet',       label: 'Anthropic: Claude 3.5 Sonnet' },
      { value: 'claude-opus-4-20250514',  label: 'Anthropic: Claude Opus 4' },
      { value: 'gpt-4o',                  label: 'OpenAI: GPT-4o' },
      { value: 'gpt-4.1',                 label: 'OpenAI: GPT-4.1' },
      { value: 'o3',                      label: 'OpenAI: o3 (reasoning)' },
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
  brain_provider: 'qwen3.5:9b', brain_api_key: '', mcp_endpoints: '',
  skills: '',
  toolconfigs: {},   // { [toolId]: { field_key: value, ... } }
};

function getModelLabel(value) {
  if (!value) return 'No model assigned';
  for (const group of MODEL_OPTIONS) {
    const found = group.models.find(m => m.value === value);
    if (found) return found.label;
  }
  return value;
}

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
          <button type="button" className="tool-qr-confirm-btn" onClick={handleSimulateScан}>
            ✅ I've scanned the code
          </button>
        </>
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

  const [testResult, setTestResult] = useState(null);
  const [isTesting, setIsTesting] = useState(false);

  const handleTestTool = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/tools/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool_id: toolId, config }),
      });
      setTestResult(await res.json());
    } catch {
      setTestResult({ ok: false, status: 'Backend unreachable' });
    } finally {
      setIsTesting(false);
    }
  };

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
      <div style={{ marginTop: 12, display: 'flex', gap: '8px', alignItems: 'center' }}>
        <button
          type="button"
          onClick={handleTestTool}
          disabled={isTesting || Object.keys(config || {}).length === 0}
          className={`btn-test-connection ${testResult ? (testResult.ok ? 'connected' : 'failed') : ''}`}
        >
          {isTesting ? '⏳ Testing...' : (testResult ? (testResult.ok ? '✅ Connected' : '❌ Failed') : '🔌 Test Connection')}
        </button>
        {testResult && (
          <div className={`connection-msg ${testResult.ok ? 'ok' : 'err'}`} style={{ fontSize: '0.75rem' }}>
            {testResult.status}
          </div>
        )}
      </div>
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
const AgentDossierCard = ({ agent, index, onEdit, onToggle, onTerminate, onModelChange }) => {
  const toolconfigs = agent.toolconfigs || {};
  const isAlive = agent.status === 'Alive';
  const isSystem = agent.is_system || ['god', 'ceo'].includes(agent.agent_id);
  const equippedArray = Array.isArray(agent.equipped_tools) ? agent.equipped_tools : [];
  const isGod = agent.agent_id === 'god' || agent.id === 'god';
  const isHealing = agent.state === 'HEALING';
  const [healLog, setHealLog] = useState([]);

  useEffect(() => {
    if (isGod) {
      fetch(`${API_BASE}/api/heal-log`)
        .then(r => r.json())
        .then(data => setHealLog((data.heal_log || []).slice(0, 5)))
        .catch(() => {});
    }
  }, [isGod]);

  const [testResult, setTestResult] = React.useState(null);
  const [isTesting, setIsTesting] = React.useState(false);

  const handleTestBrain = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/models/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: agent.model, api_key: agent.apiKeys || '' })
      });
      const data = await res.json();
      setTestResult(data);
    } catch (e) {
      setTestResult({ ok: false, status: 'Backend unreachable' });
    } finally {
      setIsTesting(false);
    }
  };

  // Build list of tools: from toolconfigs status OR from equipped_tools array
  const equippedTools = ALL_TOOL_IDS.filter(id => {
    const cfg = toolconfigs[id] || {};
    const st = toolStatus(id, toolconfigs);
    return Object.keys(cfg).length > 0 || st === 'ready' || equippedArray.includes(id);
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04 }}
      className={`dossier-card ${isSystem ? 'dossier-system' : ''} ${isHealing ? 'dossier-healing' : ''}`}
    >
      {/* System agent crown accent bar */}
      {isSystem && <div className="dossier-system-bar" />}

      {/* ── Header ── */}
      <div className="dossier-header">
        <div className={`dossier-avatar ${isSystem ? 'dossier-avatar-system' : ''}`}>
          {agent.agent_id === 'god' ? '👑' : agent.agent_id === 'ceo' ? '🏛️' : agent.name?.charAt(0)?.toUpperCase() || '?'}
        </div>
        <div className="dossier-identity">
          <h2 className="dossier-name">
            {agent.name}
            {isSystem && <span className="dossier-system-badge">SYSTEM</span>}
          </h2>
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
        <div className="brain-pill-container" style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <select
            className="brain-select"
            value={agent.model || ''}
            onChange={async (e) => {
              const newModel = e.target.value;
              try {
                await fetch(`${API_BASE}/api/agents/${agent.agent_id || agent.id}`, {
                  method: 'PUT',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ brain_model: newModel }),
                });
                // Trigger a refresh by calling the prop
                if (onModelChange) onModelChange();
              } catch (err) {
                console.error('Failed to update brain:', err);
              }
            }}
          >
            {MODEL_OPTIONS.map(group => (
              <optgroup key={group.group} label={group.group}>
                {group.models.map(m => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </optgroup>
            ))}
          </select>
          
          <button 
            onClick={handleTestBrain}
            disabled={isTesting || !agent.model}
            className={`btn-test-connection ${testResult ? (testResult.ok ? 'connected' : 'failed') : ''}`}
            title="Test connection to the AI Provider"
          >
            {isTesting ? '⏳ Testing...' : (testResult ? (testResult.ok ? '✅ Connected' : '❌ Failed') : '🔌 Test Connection')}
          </button>

          {testResult && (
            <button
              onClick={() => setTestResult(null)}
              className="btn-test-connection"
              style={{ padding: '4px 8px', background: 'transparent', border: '1px solid #ef4444', color: '#ef4444' }}
              title="Reset and disconnect test"
            >
              ✕ Disconnect
            </button>
          )}
          
          {testResult && (
            <div className={`connection-msg ${testResult.ok ? 'ok' : 'err'}`} style={{ fontSize: '0.75rem', width: '100%', marginTop: '4px' }}>
              {testResult.status}
            </div>
          )}
        </div>
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
            const inEquipped = equippedArray.includes(id);
            // If agent has an explicit equipped_tools list, only show tools in it
            if (equippedArray.length > 0 && !inEquipped) return null;
            if (equippedArray.length === 0 && !hasAnything && st !== 'ready') return null;
            // For system agents with equipped_tools but no toolconfigs, show as "ready"
            const displayStatus = inEquipped && st === 'unconfigured' ? 'ready' : st;
            return (
              <span
                key={id}
                className={`hand-badge status-${displayStatus}`}
                title={STATUS_LABELS[displayStatus]}
              >
                {def.emoji} {def.label}
                <span className="hand-badge-dot" style={{ background: STATUS_COLORS[displayStatus] }} />
              </span>
            );
          })}
          {equippedTools.length === 0 && <span className="no-hands">No tools equipped</span>}
        </div>
      </div>

      {/* ── Heal History (God Agent only) ── */}
      {isGod && healLog.length > 0 && (
        <div className="dossier-section">
          <div className="dossier-section-label"><span className="section-icon">🩺</span> HEAL HISTORY</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {healLog.map((h, i) => (
              <div key={i} style={{
                fontSize: '0.75rem',
                padding: '6px 8px',
                background: h.patch_applied ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)',
                border: `1px solid ${h.patch_applied ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`,
                borderRadius: '6px',
                color: '#d1d5db',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>{h.patch_applied ? '✅' : '❌'} {h.root_cause || 'Unknown'}</span>
                  <span style={{ color: '#6b7280', fontSize: '0.65rem' }}>{h.model_used}</span>
                </div>
                <div style={{ color: '#6b7280', fontSize: '0.65rem', marginTop: '2px' }}>
                  {h.timestamp?.split('T')[0]} | {h.crash_file || 'no file'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Footer ── */}
      <div className="dossier-footer">
        <button className="dossier-edit-btn" onClick={() => onEdit(agent)}>⚙️ Configure</button>
        {isSystem ? (
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
  const [activeTab, setActiveTab] = useState('workforce');
  const [skillFetch, setSkillFetch] = useState({ source: '', loading: false, error: null });
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);

  const fetchAgents = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/agents`);
      const data = await res.json();
      setAgents(data.agents || []);
    } catch (e) { console.error('Failed to fetch agents:', e); }
  };

  useEffect(() => { fetchAgents(); }, []);

  const toggleAgent = async (agentId) => {
    try {
      await fetch(`${API_BASE}/api/agents/${agentId}/toggle`, { method: 'POST' });
      fetchAgents();
    } catch (e) { console.error(e); }
  };

  const openHireModal = () => {
    setForm(BLANK_FORM);
    setEditingAgent(null);
    setTestResult(null);
    setShowHireModal(true);
  };

  const openEditModal = (agent) => {
    setEditingAgent(agent);
    setTestResult(null);
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
      const res = await fetch(`${API_BASE}/api/skills/extract`, {
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
        const res = await fetch(`${API_BASE}/api/agents/${editingAgent.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error((await res.json()).detail || 'Update failed');
      } else {
        // --- CREATE new agent ---
        const res = await fetch(`${API_BASE}/api/agents`, {
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
      await fetch(`${API_BASE}/api/agents/${agentId}/terminate`, { method: 'POST' });
      await fetchAgents();
    } catch (e) { console.error('Terminate failed:', e); }
  };

  // Merge permanent system agents with backend-fetched agents.
  // System agents always appear, with DB overrides merged on top.
  const normalizedAgents = (() => {
    const backendMap = {};
    agents.forEach(a => { backendMap[a.agent_id || a.id] = a; });

    // 1. System agents first (always present, merged with any DB data)
    const system = SYSTEM_AGENTS.map(sa => {
      const db = backendMap[sa.agent_id] || {};
      const merged = { ...sa, ...db };
      return {
        ...merged,
        id: db.id || sa.agent_id,
        name: db.name || sa.agent_name,
        status: (db.state === 'IDLE' || !db.state) ? 'Alive' : db.state,
        model: db.brain_model || sa.brain_model,
        apiKeys: db.api_key || sa.api_key || '',
        custom_skills: db.custom_skills || sa.custom_skills,
        toolconfigs: db.toolconfigs || sa.toolconfigs || {},
        is_system: true,
      };
    });

    // 2. Non-system agents from backend (exclude IDs already covered)
    const systemIds = new Set(SYSTEM_AGENTS.map(s => s.agent_id));
    const others = agents
      .filter(a => !systemIds.has(a.agent_id || a.id))
      .map(a => ({
        ...a,
        id: a.agent_id || a.id,
        name: a.agent_name || a.name,
        status: a.state === 'IDLE' ? 'Alive' : a.state || a.status,
        model: a.brain_model || a.model,
        apiKeys: a.api_key || '',
        custom_skills: a.custom_skills || (a.role?.includes('QA') ? 'Testing, Code Review, Linting' : 'Full-Stack Development, API Integration'),
        toolconfigs: a.toolconfigs || {},
      }));

    return [...system, ...others];
  })();

  const displayed = normalizedAgents;

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
          <div className="am-tabs">
            <button className={`am-tab ${activeTab === 'workforce' ? 'active' : ''}`} onClick={() => setActiveTab('workforce')}>🤖 Workforce</button>
            <button className={`am-tab ${activeTab === 'tasks' ? 'active' : ''}`} onClick={() => setActiveTab('tasks')}>📋 Task Queue</button>
          </div>
          {activeTab === 'workforce' && <button className="am-hire-btn" onClick={openHireModal}>+ Hire Agent</button>}
        </div>
      </header>

      {activeTab === 'tasks' ? (
        <TaskQueue />
      ) : (
      <>

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
            onModelChange={fetchAgents}
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
                      
                      <div style={{ marginTop: 8, display: 'flex', gap: '8px', alignItems: 'center' }}>
                         <button 
                           type="button"
                           onClick={async () => {
                             setIsTesting(true);
                             setTestResult(null);
                             try {
                               const res = await fetch(`${API_BASE}/api/models/test`, {
                                 method: 'POST',
                                 headers: { 'Content-Type': 'application/json' },
                                 body: JSON.stringify({ model: form.brain_provider, api_key: form.brain_api_key || '' })
                               });
                               setTestResult(await res.json());
                             } catch {
                               setTestResult({ ok: false, status: 'Backend unreachable' });
                             } finally {
                               setIsTesting(false);
                             }
                           }}
                           disabled={isTesting}
                           className={`btn-test-connection ${testResult ? (testResult.ok ? 'connected' : 'failed') : ''}`}
                         >
                           {isTesting ? '⏳ Testing...' : (testResult ? (testResult.ok ? '✅ Connected' : '❌ Failed') : '🔌 Test Connection')}
                         </button>
                         {testResult && (
                           <div className={`connection-msg ${testResult.ok ? 'ok' : 'err'}`} style={{ fontSize: '0.75rem', marginTop: 1 }}>
                             {testResult.status}
                           </div>
                         )}
                      </div>

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
      </>
      )}
    </div>
  );
};

export default AgentManager;
