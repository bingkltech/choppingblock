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
    get_all_api_usage, get_least_used_account, log_token_usage,
    get_recent_activity, log_activity,
    get_all_projects, upsert_project,
    get_unresolved_alerts, create_alert, resolve_alert,
    get_all_jules_sessions,
)
from anatomy.shift_manager import ShiftManager, ShiftMode
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

    yield

    # Shutdown
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


# --- Agents ---

@app.get("/api/agents")
async def api_get_agents():
    return {"agents": get_all_agents()}


@app.get("/api/agents/{agent_id}")
async def api_get_agent(agent_id: str):
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


class AgentUpdateBody(BaseModel):
    state: Optional[str] = None
    current_task: Optional[str] = None
    health_pct: Optional[float] = None

@app.patch("/api/agents/{agent_id}")
async def api_update_agent(agent_id: str, body: AgentUpdateBody):
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
# 🚀 ENTRY POINT
# ==========================================

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("BACKEND_PORT", "8000"))

    logger.info("🚀 Starting Paperclip Reborn on %s:%d", host, port)
    uvicorn.run("main:app", host=host, port=port, reload=True)
