"""
🔮 jules_router_api.py — FastAPI Endpoints for Jules Dispatch
Provides REST endpoints for dispatching tasks to Jules, monitoring sessions,
approving plans, and sending follow-up messages.
"""

import os
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database.db_manager import (
    get_all_jules_sessions, get_jules_session,
    get_active_jules_sessions, update_api_usage_config
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jules", tags=["Jules Dispatch"])

# ==========================================
# 📝 REQUEST MODELS
# ==========================================

class DispatchRequest(BaseModel):
    """Request body for dispatching a task to Jules."""
    task: str
    repo: str = ""
    branch: str = "main"
    require_plan_approval: bool = True


class MessageRequest(BaseModel):
    """Request body for sending a message to an active session."""
    message: str


class FleetConfigRequest(BaseModel):
    """Request body for updating a Jules account configuration."""
    api_key_override: str
    model_provider: str
    github_pat_override: str


class GlobalSettingsRequest(BaseModel):
    """Request body for updating the global JULES_API_KEY."""
    jules_api_key: str


# ==========================================
# 🤖 AGENT SINGLETON (lazy init)
# ==========================================
_dispatch_agent = None


def _get_agent():
    """Lazily initialize the JulesDispatchAgent singleton."""
    global _dispatch_agent
    if _dispatch_agent is None:
        from workforce.system_agents.jules_dispatch_agent import JulesDispatchAgent
        _dispatch_agent = JulesDispatchAgent()
        logger.info("🔮 JulesDispatchAgent initialized for API routes.")
    return _dispatch_agent


# ==========================================
# 🔌 ENDPOINTS
# ==========================================

@router.post("/dispatch")
async def dispatch_task(body: DispatchRequest):
    """
    Dispatch a coding task to Jules AI.

    The agent will:
    1. Read ARCHITECTURE.md + RULES.md for context
    2. Enrich the prompt with project conventions
    3. Create a Jules session via the API
    4. Track the session in the Ledger

    Returns the session_id for monitoring.
    """
    agent = _get_agent()

    result = agent.dispatch_task(
        task=body.task,
        repo=body.repo,
        branch=body.branch,
        require_plan_approval=body.require_plan_approval,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=422,
            detail=result.get("error", "Dispatch failed")
        )

    return result


@router.get("/sessions")
async def get_sessions(active_only: bool = False, limit: int = 50):
    """List tracked Jules sessions."""
    if active_only:
        sessions = get_active_jules_sessions()
    else:
        sessions = get_all_jules_sessions(limit)

    return {"sessions": sessions, "total": len(sessions)}


@router.get("/sessions/{session_id}")
async def get_session_detail(session_id: str, poll: bool = False):
    """
    Get details of a specific Jules session.

    If poll=True, also queries the Jules API for the latest status
    and updates the Ledger.
    """
    if poll:
        agent = _get_agent()
        result = agent.check_session(session_id)
        if result["success"]:
            # Return updated data from the ledger
            session = get_jules_session(session_id)
            if session:
                session["live_status"] = result["status"]
                session["live_pr_url"] = result.get("pr_url")
                return session

    session = get_jules_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session


@router.post("/sessions/{session_id}/approve")
async def approve_session_plan(session_id: str):
    """
    Approve a pending plan for a Jules session.
    Used in Boss Mode when requirePlanApproval=True.
    """
    agent = _get_agent()
    result = agent.approve_session(session_id)

    if not result["success"]:
        raise HTTPException(
            status_code=422,
            detail=result.get("error", "Approval failed")
        )

    return {"ok": True, "session_id": session_id}


@router.post("/sessions/{session_id}/message")
async def send_session_message(session_id: str, body: MessageRequest):
    """
    Send a follow-up message to an active Jules session.
    Used for the QA verification loop — send error logs back to Jules.
    """
    agent = _get_agent()
    result = agent.send_followup(session_id, body.message)

    if not result["success"]:
        raise HTTPException(
            status_code=422,
            detail=result.get("error", "Message failed")
        )

    return {"ok": True, "session_id": session_id}


@router.get("/health")
async def jules_health():
    """
    Health check for the Jules Dispatch subsystem.
    Reports API key status and active session count.
    """
    agent = _get_agent()
    active = get_active_jules_sessions()

    return {
        "api_key_set": bool(agent.api_key),
        "default_repo": agent.default_repo or None,
        "active_sessions": len(active),
        "max_concurrent": 3,
        "agent_state": agent.state.value,
    }

@router.put("/fleet/{account_name}")
async def update_fleet_config(account_name: str, config: FleetConfigRequest):
    """
    Updates the node-specific configuration for a Jules account.
    """
    try:
        update_api_usage_config(
            account_name=account_name,
            api_key=config.api_key_override,
            model=config.model_provider,
            github_pat=config.github_pat_override
            )
        return {"success": True, "account_name": account_name}
    except Exception as e:
        logger.error(f"Failed to update fleet config: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred.")


@router.put("/settings/global")
async def update_global_settings(settings: GlobalSettingsRequest):
    """
    Updates the primary JULES_API_KEY in the environment and writes it to .env
    """
    try:
        new_key = settings.jules_api_key.strip()
        
        # 1. Update active environment
        os.environ["JULES_API_KEY"] = new_key
        
        # Update the active agent if it's already instantiated
        if _dispatch_agent is not None:
            _dispatch_agent.api_key = new_key
            
        # 2. Write to .env file
        env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            updated = False
            for i, line in enumerate(lines):
                if line.startswith("JULES_API_KEY="):
                    lines[i] = f"JULES_API_KEY={new_key}\n"
                    updated = True
                    break
            
            if not updated:
                lines.append(f"\nJULES_API_KEY={new_key}\n")
                
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
                
        return {"success": True, "message": "Global API key updated successfully."}
    except Exception as e:
        logger.error(f"Failed to save global key: {e}")
        raise HTTPException(status_code=500, detail="Failed to save to .env file.")
