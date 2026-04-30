import React, { useState, useEffect } from 'react';

export default function ApiVault() {
  const [vaultState, setVaultState] = useState(null);

  useEffect(() => {
    const fetchVault = async () => {
      try {
        const res = await fetch(`http://${window.location.hostname}:8000/api/vault`);
        const data = await res.json();
        setVaultState(data);
      } catch (err) {
        console.error(err);
      }
    };
    fetchVault();
    const int = setInterval(fetchVault, 2000);
    return () => clearInterval(int);
  }, []);

  if (!vaultState) return <div className="card p-6" style={{ height: '100%' }}><h2 className="card-title">🔐 Centralized API Vault</h2><p>Loading Vault Engine...</p></div>;

  return (
    <div className="card p-6" style={{ width: '100%', height: '100%', overflowY: 'auto' }}>
      <h2 className="card-title mb-6">🔐 Centralized API Vault</h2>
      <p style={{ color: '#888', marginBottom: '20px' }}>
        The Vault automatically pools all keys found in your environment variables, load-balances them across your 184 agents, and handles 429 Rate Limit cooldowns seamlessly.
      </p>
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* Gemini Vault */}
        <div style={{ background: '#1e1e1e', padding: '20px', borderRadius: '12px', border: '1px solid #333' }}>
          <h3 style={{ fontSize: '1.2rem', marginBottom: '10px', color: '#10b981' }}>Gemini Models</h3>
          <p style={{ color: '#888', marginBottom: '15px' }}>Total Keys Pooled: {vaultState.gemini_keys}</p>
          
          <h4 style={{ fontSize: '0.9rem', color: '#555', marginBottom: '10px' }}>ACTIVE COOLDOWNS (429 Penalty Box)</h4>
          {vaultState.gemini_cooldowns.length === 0 ? (
            <p style={{ color: '#aaa', fontSize: '0.9rem', fontStyle: 'italic' }}>All keys healthy.</p>
          ) : (
            vaultState.gemini_cooldowns.map(cd => (
              <div key={cd.key} style={{ display: 'flex', justifyContent: 'space-between', background: '#2a1a1a', padding: '10px', borderRadius: '6px', marginBottom: '8px', border: '1px solid #ef4444' }}>
                <span style={{ color: '#ffaaaa' }}>Key ending in ...{cd.key}</span>
                <span style={{ color: '#ef4444', fontWeight: 'bold' }}>{cd.remaining}s</span>
              </div>
            ))
          )}
        </div>

        {/* Jules Vault */}
        <div style={{ background: '#1e1e1e', padding: '20px', borderRadius: '12px', border: '1px solid #333' }}>
          <h3 style={{ fontSize: '1.2rem', marginBottom: '10px', color: '#3b82f6' }}>Jules Cloud Laborers</h3>
          <p style={{ color: '#888', marginBottom: '15px' }}>Total Keys Pooled: {vaultState.jules_keys}</p>
          
          <h4 style={{ fontSize: '0.9rem', color: '#555', marginBottom: '10px' }}>ACTIVE COOLDOWNS (429 Penalty Box)</h4>
          {vaultState.jules_cooldowns.length === 0 ? (
            <p style={{ color: '#aaa', fontSize: '0.9rem', fontStyle: 'italic' }}>All keys healthy.</p>
          ) : (
            vaultState.jules_cooldowns.map(cd => (
              <div key={cd.key} style={{ display: 'flex', justifyContent: 'space-between', background: '#2a1a1a', padding: '10px', borderRadius: '6px', marginBottom: '8px', border: '1px solid #ef4444' }}>
                <span style={{ color: '#ffaaaa' }}>Key ending in ...{cd.key}</span>
                <span style={{ color: '#ef4444', fontWeight: 'bold' }}>{cd.remaining}s</span>
              </div>
            ))
          )}
        </div>
        {/* OpenAI Vault */}
        <div style={{ background: '#1e1e1e', padding: '20px', borderRadius: '12px', border: '1px solid #333' }}>
          <h3 style={{ fontSize: '1.2rem', marginBottom: '10px', color: '#a855f7' }}>OpenAI (GPT)</h3>
          <p style={{ color: '#888', marginBottom: '15px' }}>Total Keys Pooled: {vaultState.openai_keys}</p>
          
          <h4 style={{ fontSize: '0.9rem', color: '#555', marginBottom: '10px' }}>ACTIVE COOLDOWNS (429 Penalty Box)</h4>
          {vaultState.openai_cooldowns.length === 0 ? (
            <p style={{ color: '#aaa', fontSize: '0.9rem', fontStyle: 'italic' }}>All keys healthy.</p>
          ) : (
            vaultState.openai_cooldowns.map(cd => (
              <div key={cd.key} style={{ display: 'flex', justifyContent: 'space-between', background: '#2a1a1a', padding: '10px', borderRadius: '6px', marginBottom: '8px', border: '1px solid #ef4444' }}>
                <span style={{ color: '#ffaaaa' }}>Key ending in ...{cd.key}</span>
                <span style={{ color: '#ef4444', fontWeight: 'bold' }}>{cd.remaining}s</span>
              </div>
            ))
          )}
        </div>

        {/* Anthropic Vault */}
        <div style={{ background: '#1e1e1e', padding: '20px', borderRadius: '12px', border: '1px solid #333' }}>
          <h3 style={{ fontSize: '1.2rem', marginBottom: '10px', color: '#f97316' }}>Anthropic (Claude)</h3>
          <p style={{ color: '#888', marginBottom: '15px' }}>Total Keys Pooled: {vaultState.anthropic_keys}</p>
          
          <h4 style={{ fontSize: '0.9rem', color: '#555', marginBottom: '10px' }}>ACTIVE COOLDOWNS (429 Penalty Box)</h4>
          {vaultState.anthropic_cooldowns.length === 0 ? (
            <p style={{ color: '#aaa', fontSize: '0.9rem', fontStyle: 'italic' }}>All keys healthy.</p>
          ) : (
            vaultState.anthropic_cooldowns.map(cd => (
              <div key={cd.key} style={{ display: 'flex', justifyContent: 'space-between', background: '#2a1a1a', padding: '10px', borderRadius: '6px', marginBottom: '8px', border: '1px solid #ef4444' }}>
                <span style={{ color: '#ffaaaa' }}>Key ending in ...{cd.key}</span>
                <span style={{ color: '#ef4444', fontWeight: 'bold' }}>{cd.remaining}s</span>
              </div>
            ))
          )}
        </div>
      </div>
      
      <div style={{ marginTop: '30px', padding: '20px', background: 'rgba(255,255,255,0.02)', borderRadius: '12px', border: '1px dashed #444' }}>
        <h3 style={{ fontSize: '1rem', color: '#aaa', marginBottom: '10px' }}>Add New Provider</h3>
        <p style={{ fontSize: '0.85rem', color: '#666', marginBottom: '15px' }}>
          To add OpenRouter or DeepSeek keys, add them to your <code style={{color: '#888'}}>.env</code> file with standard prefixes (e.g., <code>DEEPSEEK_API_KEY_1</code>). 
          The API Vault singleton will automatically discover them on reboot and add them to the load-balancing pool.
        </p>
        <button className="btn-primary" disabled style={{ opacity: 0.5, cursor: 'not-allowed' }}>
          + Connect New API Cloud
        </button>
      </div>
    </div>
  );
}
