import { useState, useEffect, useRef, useCallback } from 'react';

const WS_URL = `ws://${window.location.hostname}:8000/ws/heartbeat`;

/**
 * useHeartbeat — WebSocket hook for real-time dashboard updates.
 * Connects to the backend WebSocket and provides live state.
 */
export function useHeartbeat() {
  const [connected, setConnected] = useState(false);
  const [agents, setAgents] = useState([]);
  const [projects, setProjects] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [activity, setActivity] = useState([]);
  const [apiUsage, setApiUsage] = useState([]);
  const [shift, setShift] = useState({ mode: 'BOSS', is_god_mode: false, pending_approvals: 0, pending_items: [] });
  const [fleetStats, setFleetStats] = useState({ total_agents: 0, active: 0, idle: 0, error: 0, fleet_health_pct: 100, utilization_pct: 0 });
  
  const wsRef = useRef(null);
  const reconnectTimeout = useRef(null);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('🔌 WebSocket connected');
        setConnected(true);
      };

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        
        switch (msg.type) {
          case 'init':
          case 'full_state':
            setAgents(msg.agents || []);
            setProjects(msg.projects || []);
            setAlerts(msg.alerts || []);
            setActivity(msg.activity || []);
            setApiUsage(msg.api_usage || []);
            setShift(msg.shift || shift);
            setFleetStats(msg.fleet_stats || fleetStats);
            break;
          case 'agent_update':
            setAgents(msg.agents || []);
            break;
          case 'shift_update':
            setShift(msg.shift || shift);
            break;
          case 'alert_update':
            setAlerts(msg.alerts || []);
            break;
          case 'heartbeat':
            // Single agent heartbeat — merge into agents array
            setAgents(prev => prev.map(a => 
              a.agent_id === msg.agent_id ? { ...a, ...msg } : a
            ));
            break;
          default:
            console.log('Unknown WS message type:', msg.type);
        }
      };

      ws.onclose = () => {
        console.log('🔌 WebSocket disconnected. Reconnecting in 3s...');
        setConnected(false);
        reconnectTimeout.current = setTimeout(connect, 3000);
      };

      ws.onerror = (err) => {
        console.error('🔌 WebSocket error:', err);
        ws.close();
      };
    } catch (err) {
      console.error('🔌 WebSocket connection failed:', err);
      reconnectTimeout.current = setTimeout(connect, 3000);
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
    };
  }, [connect]);

  // Send commands to the backend
  const sendCommand = useCallback((command, data = {}) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ command, ...data }));
    }
  }, []);

  return {
    connected,
    agents,
    projects,
    alerts,
    activity,
    apiUsage,
    shift,
    fleetStats,
    sendCommand,
  };
}
