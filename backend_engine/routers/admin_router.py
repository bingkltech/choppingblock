from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

AGENTS_DB = {
    "ceo": {"id": "ceo", "name": "CEO", "role": "Chief Executive Officer", "status": "Offline", "model": "gpt-4o"},
    "god_agent": {"id": "god_agent", "name": "God Agent", "role": "System Overseer", "status": "Offline", "model": "gpt-4o"},
    "antigravity": {"id": "antigravity", "name": "Antigravity", "role": "Lead Cloud Developer", "status": "Offline", "model": "gemini-1.5-pro"},
    "qa_reviewer": {"id": "qa_reviewer", "name": "QA Reviewer", "role": "Code Quality Assurance", "status": "Offline", "model": "llama3:8b"},
    "ops_master": {"id": "ops_master", "name": "Ops Master", "role": "Operations & Deployment", "status": "Offline", "model": "qwen2.5-coder"}
}

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
    return {"agents": list(AGENTS_DB.values())}

@router.post("/api/agents/{agent_id}/toggle")
async def toggle_agent(agent_id: str):
    if agent_id not in AGENTS_DB:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    current = AGENTS_DB[agent_id]["status"]
    AGENTS_DB[agent_id]["status"] = "Alive" if current == "Offline" else "Offline"
    return {"agent": AGENTS_DB[agent_id]}

@router.put("/api/agents/{agent_id}/config")
async def update_agent_config(agent_id: str, config: ModelConfig):
    if agent_id not in AGENTS_DB:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    AGENTS_DB[agent_id]["model"] = config.model
    return {"agent": AGENTS_DB[agent_id]}

@router.put("/api/agents/{agent_id}/rename")
async def rename_agent(agent_id: str, config: RenameConfig):
    if agent_id not in AGENTS_DB:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    AGENTS_DB[agent_id]["name"] = config.name
    return {"agent": AGENTS_DB[agent_id]}

@router.put("/api/agents/{agent_id}/update")
async def update_agent_full(agent_id: str, config: UpdateAgentRequest):
    if agent_id not in AGENTS_DB:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    AGENTS_DB[agent_id]["name"] = config.name
    AGENTS_DB[agent_id]["role"] = config.role
    AGENTS_DB[agent_id]["model"] = config.model
    AGENTS_DB[agent_id]["custom_skills"] = config.custom_skills
    AGENTS_DB[agent_id]["custom_tools"] = config.custom_tools
    return {"agent": AGENTS_DB[agent_id]}
