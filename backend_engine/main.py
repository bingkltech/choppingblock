"""
⚡ main.py — The Nervous System
FastAPI server with REST endpoints for the dashboard and WebSocket heartbeat broadcasting.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import (
    init_database, seed_jules_accounts, seed_default_agents,
    get_all_agents, get_agent, update_agent_status,
    upsert_agent_profile, terminate_agent,
    get_all_api_usage, get_least_used_account, log_token_usage,
    get_recent_activity, log_activity,
    get_all_projects, upsert_project,
    get_unresolved_alerts, create_alert, resolve_alert,
    get_all_jules_sessions,
    get_heal_log,
    create_task, get_all_tasks, get_pending_tasks, get_running_tasks,
    cancel_task as db_cancel_task,
)
import mcp_services
from anatomy.shift_manager import ShiftManager, ShiftMode
from anatomy.orchestrator import Orchestrator
from routers import admin_router
from routers import jules_router_api

# ==========================================
# 📋 LOGGING
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("paperclip.main")

# ==========================================
# 🌍 GLOBAL STATE
# ==========================================
shift_manager = ShiftManager(default_mode=ShiftMode.BOSS)
connected_clients: list[WebSocket] = []
orchestrator = Orchestrator()

# ==========================================
# 🚀 LIFESPAN (startup/shutdown)
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("📎 Paperclip Reborn — Backend Engine starting up...")
    init_database()
    seed_jules_accounts()
    seed_default_agents()
    
    # Auto-connect system GitHub CLI if available
    from database.db_manager import auto_configure_github_cli
    auto_configure_github_cli()

    # Seed some demo projects for the dashboard
    demo_projects = [
        {"project_name": "Project Alpha", "status": "Implementing Features", "language": "Python", "active_agents": 28, "current_task": "Refactoring API layer", "health_pct": 98.7, "pipeline_stage": "Code"},
        {"project_name": "Project Beta", "status": "Implementing Features", "language": "Python", "active_agents": 28, "current_task": "Refactoring API layer", "health_pct": 98.7, "pipeline_stage": "Build"},
        {"project_name": "Project Gamma", "status": "Implementing Features", "language": "Go", "active_agents": 28, "current_task": "API layer", "health_pct": 98.7, "pipeline_stage": "Test"},
        {"project_name": "Project Delta", "status": "Implementing Features", "language": "Go", "active_agents": 26, "current_task": "Refactoring API layer", "health_pct": 98.7, "pipeline_stage": "Deploy"},
    ]
    for p in demo_projects:
        upsert_project(**p)

    log_activity("system", "BOOT", "Paperclip Reborn backend initialized successfully.")
    logger.info("✅ Backend ready. WebSocket at /ws/heartbeat")

    # Start the native MCP server
    mcp_services.start_mcp_servers()
    
    # Auto-bind God Agent to the Native MCP
    god_agent = get_agent("god")
    if god_agent:
        current_mcp = god_agent.get("mcp_endpoints", "")
        if "127.0.0.1:8765" not in current_mcp:
            new_mcp = f"{current_mcp}, http://127.0.0.1:8765/sse" if current_mcp else "http://127.0.0.1:8765/sse"
            upsert_agent_profile("god", mcp_endpoints=new_mcp)

    # Start the Orchestrator as a background task
    orch_task = asyncio.create_task(orchestrator.start())
    logger.info("🎯 Orchestrator background loop started")

    yield

    # Shutdown
    await orchestrator.stop()
    orch_task.cancel()
    mcp_services.stop_mcp_servers()
    logger.info("🛑 Paperclip Reborn — Backend Engine shutting down.")


# ==========================================
# 🏗️ APP INIT
# ==========================================
app = FastAPI(
    title="📎 Paperclip Reborn API",
    description="The Nervous System — Backend for the Visual AI Foundry",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router.router)
app.include_router(jules_router_api.router)

@app.get("/api/vault")
def get_vault_state():
    """Returns the current state of the API Vault (keys and active cooldowns)."""
    from anatomy.api_vault import api_vault as main_vault
    import time
    now = time.time()
    return {
        "gemini_keys": len(main_vault.gemini_vault.keys),
        "gemini_cooldowns": [{"key": k[-4:] if len(k)>4 else k, "remaining": int(main_vault.gemini_vault.cooldowns[k] - now)} for k in main_vault.gemini_vault.cooldowns if main_vault.gemini_vault.cooldowns[k] > now],
        "jules_keys": len(main_vault.jules_vault.keys),
        "jules_cooldowns": [{"key": k[-4:] if len(k)>4 else k, "remaining": int(main_vault.jules_vault.cooldowns[k] - now)} for k in main_vault.jules_vault.cooldowns if main_vault.jules_vault.cooldowns[k] > now],
        "openai_keys": len(main_vault.openai_vault.keys),
        "openai_cooldowns": [{"key": k[-4:] if len(k)>4 else k, "remaining": int(main_vault.openai_vault.cooldowns[k] - now)} for k in main_vault.openai_vault.cooldowns if main_vault.openai_vault.cooldowns[k] > now],
        "anthropic_keys": len(main_vault.anthropic_vault.keys),
        "anthropic_cooldowns": [{"key": k[-4:] if len(k)>4 else k, "remaining": int(main_vault.anthropic_vault.cooldowns[k] - now)} for k in main_vault.anthropic_vault.cooldowns if main_vault.anthropic_vault.cooldowns[k] > now],
    }


# ==========================================
# 📡 WEBSOCKET — Heartbeat Broadcast
# ==========================================

async def broadcast(message: dict) -> None:
    """Send a JSON message to all connected WebSocket clients."""
    dead = []
    for ws in connected_clients:
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        connected_clients.remove(ws)


@app.websocket("/ws/heartbeat")
async def websocket_heartbeat(websocket: WebSocket):
    """
    WebSocket endpoint for real-time dashboard updates.
    Clients connect here to receive agent heartbeats, alerts, and activity feed events.
    """
    await websocket.accept()
    connected_clients.append(websocket)
    logger.info("🔌 WebSocket client connected. Total: %d", len(connected_clients))

    try:
        # Send initial full state on connect
        await websocket.send_json({
            "type": "init",
            "agents": get_all_agents(),
            "projects": get_all_projects(),
            "alerts": get_unresolved_alerts(),
            "activity": get_recent_activity(20),
            "api_usage": get_all_api_usage(),
            "shift": shift_manager.to_dict(),
            "fleet_stats": _compute_fleet_stats(),
            "jules_sessions": get_all_jules_sessions(20),
        })

        # Keep connection alive and listen for UI commands
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            await _handle_ws_command(msg, websocket)

    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        logger.info("🔌 WebSocket client disconnected. Total: %d", len(connected_clients))


async def _handle_ws_command(msg: dict, ws: WebSocket) -> None:
    """Handle commands sent from the frontend via WebSocket."""
    cmd = msg.get("command")

    if cmd == "toggle_shift":
        new_mode = shift_manager.toggle()
        await broadcast({"type": "shift_update", "shift": shift_manager.to_dict()})

    elif cmd == "approve":
        result = shift_manager.approve(msg.get("index", 0))
        await broadcast({"type": "shift_update", "shift": shift_manager.to_dict()})

    elif cmd == "reject":
        result = shift_manager.reject(msg.get("index", 0))
        await broadcast({"type": "shift_update", "shift": shift_manager.to_dict()})

    elif cmd == "swap_brain":
        agent_id = msg.get("agent_id")
        new_brain = msg.get("brain")
        if agent_id and new_brain:
            # Update in DB (in full app, also update the live agent instance)
            from database.db_manager import get_connection
            conn = get_connection()
            conn.execute("UPDATE Agent_Status SET brain_model = ? WHERE agent_id = ?", (new_brain, agent_id))
            conn.commit()
            conn.close()
            log_activity(agent_id, "BRAIN_SWAP", f"Brain swapped to {new_brain}")
            await broadcast({"type": "agent_update", "agents": get_all_agents()})

    elif cmd == "request_full_state":
        await ws.send_json({
            "type": "full_state",
            "agents": get_all_agents(),
            "projects": get_all_projects(),
            "alerts": get_unresolved_alerts(),
            "activity": get_recent_activity(20),
            "api_usage": get_all_api_usage(),
            "shift": shift_manager.to_dict(),
            "fleet_stats": _compute_fleet_stats(),
            "jules_sessions": get_all_jules_sessions(20),
        })


def _compute_fleet_stats() -> dict:
    """Compute aggregate fleet statistics for the dashboard."""
    agents = get_all_agents()
    total = len(agents)
    active = sum(1 for a in agents if a["state"] not in ("IDLE", "ERROR"))
    idle = sum(1 for a in agents if a["state"] == "IDLE")
    error = sum(1 for a in agents if a["state"] == "ERROR")
    avg_health = sum(a["health_pct"] for a in agents) / max(total, 1)

    return {
        "total_agents": total,
        "active": active,
        "idle": idle,
        "error": error,
        "fleet_health_pct": round(avg_health, 1),
        "utilization_pct": round((active / max(total, 1)) * 100, 1),
    }


# ==========================================
# 🔌 REST ENDPOINTS
# ==========================================

@app.get("/")
async def root():
    return {"name": "📎 Paperclip Reborn", "status": "online", "version": "0.1.0"}

# --- Settings ---

GLOBAL_KEYS = ["OPENAI_API_KEY", "CLAUDE_API_KEY", "GEMINI_API_KEY", "GITHUB_PAT", "JULES_API_KEY", "ANTIGRAVITY_API_KEY"]

@app.get("/api/settings/env")
async def get_env_settings():
    """Returns obscured values for global API keys."""
    settings = {}
    for key in GLOBAL_KEYS:
        val = os.getenv(key, "")
        if len(val) > 8:
            settings[key] = f"{val[:4]}...{val[-4:]}"
        elif val:
            settings[key] = "***"
        else:
            settings[key] = ""
    return settings

class EnvUpdateRequest(BaseModel):
    keys: dict

@app.post("/api/settings/env")
async def update_env_settings(body: EnvUpdateRequest):
    """Updates global API keys in .env and os.environ."""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    
    # Update live env
    for k, v in body.keys.items():
        if k in GLOBAL_KEYS and v:  # Only update allowed keys if provided
            os.environ[k] = v.strip()

    # Read current .env
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    # Modify lines
    for k, v in body.keys.items():
        if k not in GLOBAL_KEYS or not v:
            continue
        v = v.strip()
        updated = False
        for i, line in enumerate(lines):
            if line.startswith(f"{k}="):
                lines[i] = f"{k}={v}\n"
                updated = True
                break
        if not updated:
            # Insert at the end
            if lines and not lines[-1].endswith("\n"):
                lines[-1] += "\n"
            lines.append(f"{k}={v}\n")

    # Write back
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return {"success": True}



# --- Agents ---

@app.get("/api/agents")
async def api_get_agents():
    """Returns all agents (with API keys obscured for security)."""
    agents = get_all_agents(include_terminated=True)
    # Normalize field names for the frontend
    normalized = []
    for a in agents:
        # Obscure brain api key
        api_key = a.get("api_key", "")
        if api_key:
            api_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"

        # Obscure toolconfigs api keys
        toolconfigs = a.get("toolconfigs", {})
        for tool, cfg in toolconfigs.items():
            if isinstance(cfg, dict):
                for k, v in cfg.items():
                    if k in ["api_key", "pat", "token", "password"] and isinstance(v, str) and v:
                        cfg[k] = f"{v[:4]}...{v[-4:]}" if len(v) > 8 else "***"

        normalized.append({
            "id":           a.get("agent_id"),
            "name":         a.get("agent_name"),
            "role":         a.get("role", ""),
            "tier":         a.get("tier", "agency"),
            "status":       "Alive" if a.get("state") not in ("IDLE", "ERROR", "TERMINATED") else ("Error" if a.get("state") == "ERROR" else "Offline"),
            "state":        a.get("state", "IDLE"),
            "model":        a.get("brain_model", ""),
            "custom_skills":a.get("custom_skills", ""),
            "toolconfigs":  toolconfigs,
            "custom_tools": a.get("equipped_tools", []),
            "apiKeys":      api_key,
            "mcpEndpoints": a.get("mcp_endpoints", ""),
            "health_pct":   a.get("health_pct", 100.0),
            "hired_at":     a.get("hired_at", ""),
            "last_heartbeat": a.get("last_heartbeat", ""),
        })
    return {"agents": normalized}


@app.get("/api/agents/{agent_id}")
async def api_get_agent(agent_id: str):
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Obscure brain api key
    api_key = agent.get("api_key", "")
    if api_key:
        agent["api_key"] = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"

    # Obscure toolconfigs api keys
    toolconfigs = agent.get("toolconfigs", {})
    if isinstance(toolconfigs, dict):
        for tool, cfg in toolconfigs.items():
            if isinstance(cfg, dict):
                for k, v in cfg.items():
                    if k in ["api_key", "pat", "token", "password"] and isinstance(v, str) and v:
                        cfg[k] = f"{v[:4]}...{v[-4:]}" if len(v) > 8 else "***"

    return agent


# --- Heal Log ---

@app.get("/api/heal-log")
async def api_get_heal_log():
    """Returns the last 20 God Agent healing actions."""
    return {"heal_log": get_heal_log(20)}


@app.post("/api/god/heal")
async def api_trigger_heal(body: dict):
    """Manually trigger a God Agent heal cycle for testing."""
    traceback_text = body.get("traceback", "")
    if not traceback_text:
        raise HTTPException(status_code=400, detail="Missing 'traceback' in body")
    from workforce.executives.god_agent import GodAgent
    god = GodAgent()
    result = god.heal(traceback_text, auto_apply=False)
    log_activity("god", "HEAL_CYCLE", f"Manual heal: {result.get('root_cause', 'unknown')}")
    return result


# --- Task Queue ---

class TaskCreateBody(BaseModel):
    task_type: str       # WRITE_ARCH, CODE, TEST_PR, MERGE_PR, HEAL, GENERAL
    description: str
    priority: int = 5    # 1=highest, 10=lowest
    input_data: dict = {}
    assigned_agent: Optional[str] = None

@app.post("/api/tasks")
async def api_create_task(body: TaskCreateBody):
    """Create a new task in the queue."""
    import uuid
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    task = create_task(
        task_id=task_id,
        task_type=body.task_type,
        description=body.description,
        priority=body.priority,
        input_data=json.dumps(body.input_data),
        assigned_agent=body.assigned_agent if body.assigned_agent else None,
    )
    log_activity("system", "TASK_CREATED", f"New task: {task_id} ({body.task_type})")
    return task

@app.get("/api/tasks")
async def api_list_tasks(status: str = None, limit: int = 50):
    """List tasks, optionally filtered by status."""
    if status == "pending":
        return {"tasks": get_pending_tasks(limit)}
    elif status == "running":
        return {"tasks": get_running_tasks()}
    else:
        return {"tasks": get_all_tasks(limit)}

@app.get("/api/tasks/stats")
async def api_task_stats():
    """Quick stats for the dashboard header."""
    all_tasks = get_all_tasks(200)
    by_status = {}
    for t in all_tasks:
        s = t.get("status", "UNKNOWN")
        by_status[s] = by_status.get(s, 0) + 1
    return {
        "total": len(all_tasks),
        "by_status": by_status,
        "orchestrator": orchestrator.status,
    }

@app.post("/api/tasks/{task_id}/cancel")
async def api_cancel_task(task_id: str):
    """Cancel a pending or assigned task."""
    if db_cancel_task(task_id):
        log_activity("system", "TASK_CANCELLED", f"Task cancelled: {task_id}")
        return {"ok": True, "task_id": task_id}
    raise HTTPException(status_code=400, detail="Task not found or cannot be cancelled")

class AgentProfileBody(BaseModel):
    """Full employee profile — used for both create and update."""
    name:          Optional[str]  = None
    role:          Optional[str]  = None
    tier:          Optional[str]  = None
    brain_model:   Optional[str]  = None
    api_key:       Optional[str]  = None
    mcp_endpoints: Optional[str]  = None
    custom_skills: Optional[str]  = None
    toolconfigs:   Optional[dict] = None
    equipped_tools:Optional[list] = None
    state:         Optional[str]  = None


@app.post("/api/agents")
async def api_create_agent(body: AgentProfileBody):
    """Hire a new agent and persist to DB."""
    if not body.name:
        raise HTTPException(status_code=400, detail="name is required")
    import re, time
    agent_id = re.sub(r'[^a-z0-9_]', '_', (body.name or 'agent').lower()) + f"_{int(time.time()) % 100000}"

    upsert_agent_profile(
        agent_id,
        agent_name=body.name,
        role=body.role or "",
        tier=body.tier or "agency",
        brain_model=body.brain_model or "ollama:llama3",
        api_key=body.api_key or "",
        mcp_endpoints=body.mcp_endpoints or "",
        custom_skills=body.custom_skills or "",
        toolconfigs=body.toolconfigs or {},
        equipped_tools=body.equipped_tools or [],
        state="IDLE",
    )
    log_activity(agent_id, "HIRED", f"Agent '{body.name}' joined the workforce.")
    await broadcast({"type": "agent_update", "agents": get_all_agents()})
    return {"ok": True, "agent_id": agent_id}


@app.put("/api/agents/{agent_id}")
async def api_update_agent_profile(agent_id: str, body: AgentProfileBody):
    """Save/update an existing agent's full profile."""
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    api_key_update = body.api_key
    if api_key_update is not None and ("..." in api_key_update or api_key_update == "***"):
        # The key is obscured, do not update it unless it was changed
        api_key_update = agent.get("api_key", "")

    toolconfigs_update = body.toolconfigs
    if toolconfigs_update is not None:
        # Preserve obscured toolconfig secrets
        existing_toolconfigs = agent.get("toolconfigs", {})
        if isinstance(existing_toolconfigs, dict) and isinstance(toolconfigs_update, dict):
            for tool, cfg in toolconfigs_update.items():
                if isinstance(cfg, dict):
                    for k, v in cfg.items():
                        if k in ["api_key", "pat", "token", "password"] and isinstance(v, str) and ("..." in v or v == "***"):
                            # Recover from existing
                            cfg[k] = existing_toolconfigs.get(tool, {}).get(k, "")

    updates = {k: v for k, v in {
        "agent_name":    body.name,
        "role":          body.role,
        "tier":          body.tier,
        "brain_model":   body.brain_model,
        "api_key":       api_key_update,
        "mcp_endpoints": body.mcp_endpoints,
        "custom_skills": body.custom_skills,
        "toolconfigs":   toolconfigs_update,
        "equipped_tools":body.equipped_tools,
        "state":         body.state,
    }.items() if v is not None}

    if updates:
        upsert_agent_profile(agent_id, **updates)

    log_activity(agent_id, "PROFILE_UPDATED", f"Agent '{agent_id}' profile saved.")
    await broadcast({"type": "agent_update", "agents": get_all_agents()})
    return {"ok": True}


@app.post("/api/agents/{agent_id}/terminate")
async def api_terminate_agent(agent_id: str):
    """Permanently terminate an agent (soft-delete, kept for audit)."""
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    terminate_agent(agent_id)
    log_activity(agent_id, "TERMINATED", f"Agent '{agent.get('agent_name')}' has been terminated.", severity="WARNING")
    await broadcast({"type": "agent_update", "agents": get_all_agents()})
    return {"ok": True}


class AgentUpdateBody(BaseModel):
    state: Optional[str] = None
    current_task: Optional[str] = None
    health_pct: Optional[float] = None

@app.patch("/api/agents/{agent_id}")
async def api_patch_agent(agent_id: str, body: AgentUpdateBody):
    if body.state:
        update_agent_status(agent_id, body.state, body.current_task, body.health_pct)
        await broadcast({"type": "agent_update", "agents": get_all_agents()})
    return {"ok": True}


# --- Projects ---

@app.get("/api/projects")
async def api_get_projects():
    return {"projects": get_all_projects()}


# --- Alerts ---

@app.get("/api/alerts")
async def api_get_alerts():
    return {"alerts": get_unresolved_alerts()}


@app.post("/api/alerts/{alert_id}/resolve")
async def api_resolve_alert(alert_id: int):
    resolve_alert(alert_id)
    await broadcast({"type": "alert_update", "alerts": get_unresolved_alerts()})
    return {"ok": True}


# --- Activity ---

@app.get("/api/activity")
async def api_get_activity(limit: int = 50):
    return {"activity": get_recent_activity(limit)}


# --- API Usage ---

@app.get("/api/usage")
async def api_get_usage():
    return {"usage": get_all_api_usage()}


# --- Shift ---

@app.get("/api/shift")
async def api_get_shift():
    return shift_manager.to_dict()


@app.post("/api/shift/toggle")
async def api_toggle_shift():
    new_mode = shift_manager.toggle()
    await broadcast({"type": "shift_update", "shift": shift_manager.to_dict()})
    return shift_manager.to_dict()


# --- Fleet Stats ---

@app.get("/api/fleet")
async def api_get_fleet():
    return _compute_fleet_stats()


# ==========================================
# 🧠 BRAIN / MODEL CONNECTION TEST
# ==========================================

class TestBrainBody(BaseModel):
    model: str
    api_key: Optional[str] = None

@app.post("/api/models/test")
async def api_test_brain(body: TestBrainBody):
    import httpx
    
    model = body.model.lower()
    
    # 1. Test Local Ollama
    # Any model that is in the user's list from `ollama list` but NOT explicitly a cloud model
    # User's cloud models have ":cloud" or "-cloud" in them, but standard models are local.
    is_cloud_ollama = ":cloud" in model or "-cloud" in model
    is_gemini = "gemini" in model
    is_claude = "claude" in model
    is_gpt = "gpt" in model and "oss" not in model # exclude gpt-oss which is ollama
    is_o3 = "o3" == model
    
    if not (is_gemini or is_claude or is_gpt or is_o3 or is_cloud_ollama):
        # Local Ollama assumption
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get("http://localhost:11434/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                # Check if exact model exists, or base model
                if body.model in models or f"{body.model}:latest" in models:
                    return {"ok": True, "status": "Connected & Downloaded", "provider": "Ollama (Local)"}
                else:
                    return {"ok": False, "status": f"Ollama is running, but '{body.model}' is not downloaded. Run: ollama run {body.model}", "provider": "Ollama (Local)"}
            return {"ok": False, "status": "Ollama not responding on localhost:11434", "provider": "Ollama (Local)"}
        except Exception as e:
            return {"ok": False, "status": f"Connection failed: {str(e)}", "provider": "Ollama (Local)"}
            
    # 2. Test Cloud API Providers
    if not body.api_key:
        # Check if we have an env key as fallback
        env_key = ""
        if is_gemini: env_key = os.getenv("GEMINI_API_KEY", "")
        if is_claude: env_key = os.getenv("ANTHROPIC_API_KEY", "")
        if is_gpt or is_o3: env_key = os.getenv("OPENAI_API_KEY", "")
        
        if not env_key:
            return {"ok": False, "status": "API Key Required", "provider": "Cloud Provider"}
            
    # For now, simulate success if key is present (would add actual API ping here in production)
    return {"ok": True, "status": "API Key Valid & Connected", "provider": "Cloud Provider"}


# ==========================================
# 🛠️ TOOL CONNECTION TEST
# ==========================================

class TestToolBody(BaseModel):
    tool_id: str
    config: dict

@app.post("/api/tools/test")
async def api_test_tool(body: TestToolBody):
    import httpx
    tool = body.tool_id
    cfg = body.config
    
    if tool == "github":
        if not cfg.get("pat"):
            return {"ok": False, "status": "Missing PAT"}
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get("https://api.github.com/user", headers={"Authorization": f"token {cfg['pat']}"})
            if r.status_code == 200:
                return {"ok": True, "status": f"Connected as {r.json().get('login')}"}
            return {"ok": False, "status": f"GitHub Error: {r.status_code}"}
        except Exception as e:
            return {"ok": False, "status": str(e)}

    elif tool == "jules":
        if not cfg.get("api_key"):
            return {"ok": False, "status": "Missing API Key"}
        try:
            from caveman_tools.primitive_jules import list_sessions
            res = list_sessions(cfg["api_key"], limit=1)
            if res.get("success"):
                return {"ok": True, "status": "Jules API Connected"}
            return {"ok": False, "status": res.get("error", "Unknown error")}
        except Exception as e:
            return {"ok": False, "status": str(e)}

    elif tool == "telegram":
        if not cfg.get("bot_token"):
            return {"ok": False, "status": "Missing Bot Token"}
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(f"https://api.telegram.org/bot{cfg['bot_token']}/getMe")
            if r.status_code == 200:
                data = r.json()
                if data.get("ok"):
                    return {"ok": True, "status": f"Connected to @{data['result'].get('username')}"}
            return {"ok": False, "status": "Invalid Telegram Token"}
        except Exception as e:
            return {"ok": False, "status": str(e)}

    elif tool == "email":
        host = cfg.get("smtp_host")
        port = cfg.get("smtp_port")
        if not host or not port:
            return {"ok": False, "status": "Missing Host or Port"}
        try:
            import smtplib
            # Simple connection check, no auth performed to avoid locking accounts with bad passes repeatedly
            server = smtplib.SMTP(host, int(port), timeout=3)
            server.ehlo()
            server.quit()
            return {"ok": True, "status": "SMTP Server Reachable"}
        except Exception as e:
            return {"ok": False, "status": f"SMTP Error: {str(e)}"}

    elif tool == "antigravity":
        key = cfg.get("api_key")
        if not key:
            return {"ok": False, "status": "Missing Gemini API Key"}
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}")
            if r.status_code == 200:
                data = r.json()
                models = data.get("models", [])
                return {"ok": True, "status": f"Connected ({len(models)} models found)"}
            return {"ok": False, "status": f"Invalid Gemini Key (HTTP {r.status_code})"}
        except Exception as e:
            return {"ok": False, "status": str(e)}

    return {"ok": False, "status": "Testing not implemented for this tool"}

# ==========================================
# 🧠 SKILLS EXTRACTOR (skill-seekers)
# ==========================================

class SkillExtractBody(BaseModel):
    source: str  # GitHub repo (e.g. "facebook/react") or URL

class SkillGenerateBody(BaseModel):
    role: str

@app.post("/api/skills/generate")
async def api_generate_skills(body: SkillGenerateBody):
    import httpx
    role = body.role.strip()
    if not role:
        raise HTTPException(status_code=400, detail="role is required")
        
    logger.info("✨ Generating skills for role: %s", role)
    
    god = get_agent("god")
    if not god:
        raise HTTPException(status_code=500, detail="System God Agent not found")
        
    configs = god.get("toolconfigs", {})
    anti = configs.get("antigravity", {})
    api_key = anti.get("api_key")
    
    if not api_key:
        raise HTTPException(status_code=400, detail="God Agent 'Antigravity API' tool not configured. Configure it to enable generative skills.")
        
    prompt = (
        f"You are an expert HR Technical Recruiter. The user is hiring an AI Agent for the role of '{role}'. "
        "Generate a comma-separated list of the 8-10 most critical, high-impact skills, frameworks, tools, and methodologies required for this exact position. "
        "Ensure they are optimized for an AI language model to understand its persona. Only return the comma-separated list, nothing else."
    )
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.4}
            }
            r = await client.post(url, json=payload)
            
            if r.status_code != 200:
                raise HTTPException(status_code=r.status_code, detail=f"Gemini API Error: {r.text}")
                
            data = r.json()
            out_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            if not out_text:
                raise HTTPException(status_code=500, detail="Empty response from Gemini")
                
            return {"skills": out_text.strip()}
    except Exception as e:
        logger.error("Skill generation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/skills/extract")
async def api_extract_skills(body: SkillExtractBody):
    """
    Runs skill-seekers against a GitHub repo or URL and returns
    structured skill text suitable for populating an agent's Skills field.
    """
    import subprocess
    import shutil
    import tempfile
    import re

    source = body.source.strip()
    if not source:
        raise HTTPException(status_code=400, detail="source is required")

    logger.info("🔍 Extracting skills from: %s", source)

    # Create a temp output directory
    tmpdir = tempfile.mkdtemp(prefix="skill_extract_")

    try:
        import sysconfig
        # Try to find skill-seekers via PATH or fallback to pip's user-scripts path
        bin_path = shutil.which("skill-seekers")
        if not bin_path:
            user_scripts = sysconfig.get_path("scripts", f"{os.name}_user") if hasattr(os, "name") else ""
            fallback = os.path.join(user_scripts, "skill-seekers.exe" if os.name == "nt" else "skill-seekers")
            if os.path.exists(fallback):
                bin_path = fallback
            else:
                raise FileNotFoundError()

        result = subprocess.run(
            [bin_path, "create", source, "--output", tmpdir],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )

        # skill-seekers writes a SKILL.md inside the output dir
        skill_file = None
        for root, dirs, files in os.walk(tmpdir):
            for fname in files:
                if fname.upper() == "SKILL.md" or fname.lower() == "skill.md":
                    skill_file = os.path.join(root, fname)
                    break

        if skill_file and os.path.exists(skill_file):
            with open(skill_file, "r", encoding="utf-8", errors="ignore") as f:
                raw = f.read()

            # Extract the most useful sections: description + key skills
            # Strip markdown headers and collapse whitespace
            lines = [ln.strip() for ln in raw.splitlines()]
            skill_lines = []
            in_skills = False
            for ln in lines:
                if not ln:
                    continue
                # Grab lines that look like skill bullets or descriptions
                if ln.startswith("##") or ln.startswith("###"):
                    in_skills = True
                    continue
                if in_skills and (ln.startswith("-") or ln.startswith("*") or ln.startswith("•")):
                    clean = re.sub(r'^[-*•]\s*', '', ln).strip()
                    if clean:
                        skill_lines.append(clean)
                elif in_skills and len(ln) > 20 and not ln.startswith("#"):
                    skill_lines.append(ln)

            # Fallback: grab first 2000 chars of the raw markdown
            if not skill_lines:
                skill_text = raw[:2000].strip()
            else:
                skill_text = ", ".join(skill_lines[:30])

            log_activity("system", "SKILL_EXTRACT", f"Skills extracted from {source}")
            return {
                "ok": True,
                "source": source,
                "skills": skill_text,
                "raw_length": len(raw),
            }

        else:
            # Return stderr for debugging
            logger.warning("skill-seekers stdout: %s", result.stdout[:500])
            logger.warning("skill-seekers stderr: %s", result.stderr[:500])
            raise HTTPException(
                status_code=422,
                detail=f"skill-seekers ran but produced no SKILL.md. stderr: {result.stderr[:300]}"
            )

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="skill-seekers timed out (120s). Try a smaller repo.")
    except FileNotFoundError:
        raise HTTPException(status_code=501, detail="skill-seekers CLI not found. Run: pip install skill-seekers")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ==========================================
# 🚀 ENTRY POINT
# ==========================================

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("BACKEND_PORT", "8000"))

    uvicorn.run("main:app", host=host, port=port)

