# Context Loading Checklist — Quick Reference

> Paste this into your working notes at the start of any multi-module task.

## Step 1: Load Rules & Laws
- [ ] `README.md` — project overview, prerequisites, boot sequence
- [ ] `RULES.md` — absolute laws of the codebase (God Agent's decrees)
- [ ] `ARCHITECTURE.md` — CEO's current master plan
- [ ] `.env.example` — required API keys and config

## Step 2: Load Map
- [ ] `StructureCode.txt` — full repo directory map
- [ ] `dashboard.png` — visual reference for the UI

## Step 3: Load Module Context (as needed)
- [ ] `database/db_manager.py` — tables: API_Usage, Agent_Status, Activity_Log, Projects, Alerts
- [ ] `anatomy/agent_core.py` — BaseAgent class, AgentState enum, heartbeat callback
- [ ] `anatomy/shift_manager.py` — ShiftMode enum, approval gate, pending approvals
- [ ] `main.py` — FastAPI routes, WebSocket `/ws/heartbeat`, CORS, lifespan
- [ ] `hooks/useHeartbeat.js` — WebSocket hook, state dispatch, sendCommand

## Step 4: Check Stigmergic Memory
- [ ] `ARCHITECTURE.md` — what are we building right now?
- [ ] `RULES.md` — what mistakes have been encoded as laws?

## Step 5: Classify Task Size
| Size | Files | Modules | Approach |
|------|-------|---------|----------|
| Tiny | 1 | 1 | Just do it |
| Small | 1-3 | 1 | Do it, verify |
| Medium | 3-6 | 2-3 | Break into 3-5 sub-tasks |
| Large | 6+ | 3+ | Break into 8-15 sub-tasks |
| Epic | 10+ | 4+ | Write plan → get CEO approval |

## After Completion
```bash
# Backend
python -m py_compile backend_engine/main.py
python backend_engine/database/db_manager.py

# Frontend
cd visual_hq && npm run build

# Diff check
git diff --stat
```
