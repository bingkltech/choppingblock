# 🚀 ChoppingBlock: "The Agency" Overhaul Plan

This is the master specification to overhaul ChoppingBlock's structure, agents, and documentation to fully support the newly introduced **184 Agency Agents**.

## 🎯 Primary Objectives
1. **Migrate from 9 Hardcoded Agents to 184 Dynamic Agency Agents**
2. **Restructure the Repository** to support dynamic skill loading and a generalized Agent Orchestrator pattern.
3. **Overhaul the Visual HQ (Frontend)** to handle a massive agent roster (filtering, pagination, dynamic skill assignment).
4. **Rewrite the Documentation** (`README.md` and `ARCHITECTURE.md`) to reflect the new paradigm.

---

## 🔪 Phase 1: Database & Anatomy Overhaul
The current ledger (`db_manager.py`) and agent core only support the 9 hardcoded primitive agents (`ceo`, `god`, `jules`, `qa`, `ops`). 
- **Sub-task 1.1**: Update `db_manager.py`'s `seed_default_agents()` to dynamically parse and seed the 184 `agency-*` skills from the system directory.
- **Sub-task 1.2**: Refactor `Agent_Status` table to support extended metadata (e.g., department, specialization).
- **Sub-task 1.3**: Update `anatomy/agent_core.py` to seamlessly execute tools defined in the `agency-*` `.md` skill files.

## 🏢 Phase 2: Workforce Structure Rearrangement
Currently, `backend_engine/workforce` is hardcoded to `tier1_executives`, `tier2_cloud_labor`, and `tier3_local_swarm`.
- **Sub-task 2.1**: Abolish the hardcoded tiers. Rearrange the structure into organizational departments: `engineering/`, `marketing/`, `design/`, `product/`, etc.
- **Sub-task 2.2**: Implement the `agency-agents-orchestrator` logic as the new master router, replacing the old `jules_router.py`.

## 👁️ Phase 3: Visual HQ (React Frontend) Overhaul
The frontend was designed for 9 agents. 184 agents will break the UI.
- **Sub-task 3.1**: Overhaul `OfficeMap.jsx` to support dynamic clustering or scrolling for 184 avatars.
- **Sub-task 3.2**: Overhaul `AgentDossier.jsx` to show Agency profiles, parsed from the `SKILL.md` descriptions.
- **Sub-task 3.3**: Add a "Department Filter" to easily find UI Designers, Backend Architects, or SEO Specialists.

## 📖 Phase 4: Documentation Rewrite
- **Sub-task 4.1**: Rewrite `README.md` to introduce the "Agency Agents" infrastructure.
- **Sub-task 4.2**: Update `backend_engine/shared_workspace/ARCHITECTURE.md` to reflect the new pipeline and orchestrator logic.
- **Sub-task 4.3**: Overhaul `StructureCode.txt` with the new file tree.
