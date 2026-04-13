from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import db_manager
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class ModelConfig(BaseModel):
    model: str

class RenameConfig(BaseModel):
    name: str

class UpdateAgentRequest(BaseModel):
    name: str
    role: str
    model: str
    custom_skills: str
    custom_tools: list[str]

@router.get("/api/agents")
async def get_agents():
    return {"agents": db_manager.get_all_agents()}

@router.post("/api/agents/{agent_id}/toggle")
async def toggle_agent(agent_id: str):
    agent = db_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Toggle between IDLE and OFFLINE
    current_state = agent.get("state", "IDLE")
    new_state = "OFFLINE" if current_state != "OFFLINE" else "IDLE"
    
    db_manager.update_agent_status(agent_id, state=new_state)
    return {"agent": db_manager.get_agent(agent_id)}

@router.post("/api/agents/{agent_id}/terminate")
async def terminate_agent(agent_id: str):
    try:
        db_manager.terminate_agent(agent_id)
        return {"success": True, "message": f"Agent {agent_id} terminated."}
    except ValueError as e:
        # God Agent protection
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/agents/{agent_id}/config")
async def update_agent_config(agent_id: str, config: ModelConfig):
    agent = db_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    db_manager.upsert_agent_profile(agent_id, brain_model=config.model)
    return {"agent": db_manager.get_agent(agent_id)}

@router.put("/api/agents/{agent_id}/rename")
async def rename_agent(agent_id: str, config: RenameConfig):
    agent = db_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    db_manager.upsert_agent_profile(agent_id, agent_name=config.name)
    return {"agent": db_manager.get_agent(agent_id)}

@router.put("/api/agents/{agent_id}/update")
async def update_agent_full(agent_id: str, config: UpdateAgentRequest):
    agent = db_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    db_manager.upsert_agent_profile(
        agent_id,
        agent_name=config.name,
        role=config.role,
        brain_model=config.model,
        custom_skills=config.custom_skills,
        equipped_tools=config.custom_tools
    )
    return {"agent": db_manager.get_agent(agent_id)}
