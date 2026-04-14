import { useState, useEffect } from 'react';
import { API_BASE } from './AgentManager';

export default function Settings() {
  const [keys, setKeys] = useState({
    OPENAI_API_KEY: '',
    CLAUDE_API_KEY: '',
    GEMINI_API_KEY: '',
    GITHUB_PAT: '',
    JULES_API_KEY: ''
  });

  const [inputs, setInputs] = useState({});
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchEnv();
  }, []);

  const fetchEnv = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/settings/env`);
      const data = await res.json();
      setKeys(data);
    } catch (e) {
      console.error('Failed to fetch settings', e);
    }
  };

  const handleChange = (e) => {
    setInputs({ ...inputs, [e.target.name]: e.target.value });
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage('');

    // Only send keys that were modified and are not empty
    const updates = {};
    for (const [k, v] of Object.entries(inputs)) {
      if (v.trim()) updates[k] = v.trim();
    }

    if (Object.keys(updates).length === 0) {
      setSaving(false);
      setMessage('No changes to save.');
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/api/settings/env`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keys: updates })
      });

      if (res.ok) {
        setMessage('Settings saved successfully!');
        setInputs({});
        fetchEnv();
      } else {
        setMessage('Failed to save settings.');
      }
    } catch (err) {
      setMessage(`Save failed: ${err.message}`);
    }
    setSaving(false);
  };

  return (
    <div className="section-panel" style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto', gridArea: 'main', overflowY: 'auto' }}>
      <div className="panel-header" style={{ marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: '800', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span>⚙️</span> Global Settings
        </h2>
        <p style={{ color: 'var(--text-secondary)' }}>
          Securely configure your API keys for the entire workspace. These keys are written to the <code style={{color:'var(--accent)'}}>.env</code> file and are automatically loaded by all agents. You won't need to re-enter them.
        </p>
      </div>

      {message && (
        <div style={{
          padding: '1rem',
          marginBottom: '1.5rem',
          borderRadius: '8px',
          background: message.includes('success') ? 'var(--bg-success)' : 'var(--bg-card-hover)',
          color: message.includes('success') ? 'var(--text-success)' : 'var(--text-primary)',
          borderLeft: `4px solid ${message.includes('success') ? 'var(--accent-success)' : 'var(--accent)'}`
        }}>
          {message}
        </div>
      )}

      <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

        {/* OpenAI */}
        <div className="form-group" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <label style={{ fontWeight: '600', color: 'var(--text-primary)' }}>OpenAI API Key (GPT-4o, o3)</label>
          <input
            type="password"
            name="OPENAI_API_KEY"
            placeholder={keys.OPENAI_API_KEY ? `Current: ${keys.OPENAI_API_KEY}` : 'sk-proj-...'}
            value={inputs.OPENAI_API_KEY || ''}
            onChange={handleChange}
            style={{ padding: '0.75rem', borderRadius: '4px', background: 'var(--bg-page)', border: '1px solid var(--border)', color: 'white', fontFamily: 'monospace' }}
          />
        </div>

        {/* Anthropic */}
        <div className="form-group" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <label style={{ fontWeight: '600', color: 'var(--text-primary)' }}>Anthropic API Key (Claude 3.5 Sonnet / Opus)</label>
          <input
            type="password"
            name="CLAUDE_API_KEY"
            placeholder={keys.CLAUDE_API_KEY ? `Current: ${keys.CLAUDE_API_KEY}` : 'sk-ant-...'}
            value={inputs.CLAUDE_API_KEY || ''}
            onChange={handleChange}
            style={{ padding: '0.75rem', borderRadius: '4px', background: 'var(--bg-page)', border: '1px solid var(--border)', color: 'white', fontFamily: 'monospace' }}
          />
        </div>

        {/* Gemini */}
        <div className="form-group" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <label style={{ fontWeight: '600', color: 'var(--text-primary)' }}>Google Gemini API Key (Gemini 2.5 Pro / Flash)</label>
          <input
            type="password"
            name="GEMINI_API_KEY"
            placeholder={keys.GEMINI_API_KEY ? `Current: ${keys.GEMINI_API_KEY}` : 'AIzaSy...'}
            value={inputs.GEMINI_API_KEY || ''}
            onChange={handleChange}
            style={{ padding: '0.75rem', borderRadius: '4px', background: 'var(--bg-page)', border: '1px solid var(--border)', color: 'white', fontFamily: 'monospace' }}
          />
        </div>

        {/* Jules */}
        <div className="form-group" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <label style={{ fontWeight: '600', color: 'var(--text-primary)' }}>Jules Dispatch API Key</label>
          <input
            type="password"
            name="JULES_API_KEY"
            placeholder={keys.JULES_API_KEY ? `Current: ${keys.JULES_API_KEY}` : 'Enter Jules override key...'}
            value={inputs.JULES_API_KEY || ''}
            onChange={handleChange}
            style={{ padding: '0.75rem', borderRadius: '4px', background: 'var(--bg-page)', border: '1px solid var(--border)', color: 'white', fontFamily: 'monospace' }}
          />
        </div>

        {/* GitHub */}
        <div className="form-group" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <label style={{ fontWeight: '600', color: 'var(--text-primary)' }}>GitHub Personal Access Token (for PRs / code syncing)</label>
          <input
            type="password"
            name="GITHUB_PAT"
            placeholder={keys.GITHUB_PAT ? `Current: ${keys.GITHUB_PAT}` : 'ghp_...'}
            value={inputs.GITHUB_PAT || ''}
            onChange={handleChange}
            style={{ padding: '0.75rem', borderRadius: '4px', background: 'var(--bg-page)', border: '1px solid var(--border)', color: 'white', fontFamily: 'monospace' }}
          />
        </div>

        <button
          type="submit"
          disabled={saving}
          style={{
            background: 'var(--accent)',
            color: 'white',
            border: 'none',
            padding: '1rem',
            borderRadius: '4px',
            fontWeight: 'bold',
            cursor: saving ? 'not-allowed' : 'pointer',
            opacity: saving ? 0.7 : 1,
            marginTop: '1rem'
          }}
        >
          {saving ? 'Saving...' : '💾 Securely Save to .env'}
        </button>
      </form>
    </div>
  );
}
