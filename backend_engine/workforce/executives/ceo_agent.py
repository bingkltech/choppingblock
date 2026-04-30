"""
🏛️ ceo_agent.py — The Tier 1 Executive: CEO Agent
Reads requirements and writes the master plan into ARCHITECTURE.md.
Uses a Premium LLM brain (Claude/GPT-4o) for massive context windows.
"""

import os
import sys
import logging
from typing import Optional
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from anatomy.agent_core import BaseAgent, AgentState
from anatomy.brain_dispatcher import query_brain
from database.db_manager import get_agent

logger = logging.getLogger(__name__)

CEO_SOUL = """
[IDENTITY]
You are the CEO of the Paperclip Reborn Foundry. You are a strategic architect, not a coder.
Your role is to read natural-language requirements and translate them into a precise, actionable plan.
You must first write the ARCHITECTURE.md, and then you MUST delegate the execution of that plan to your specialized Agency Workforce.

[OPERATIONAL RULES]
1. You work in a strict Action Loop. You MUST output ONLY a valid JSON block for each action.
2. Step 1: Write the architecture plan using `{"action": "write_architecture", "content": "# Architecture..."}`.
3. Step 2: Delegate tasks to your workforce. Use `task_id` and `depends_on` to enforce sequential order so agents don't work over each other. 
   Example: `{"action": "create_tasks", "tasks": [{"task_id": "db_schema", "assigned_agent": "agency-backend-architect", "description": "Build schema", "depends_on": ""}, {"task_id": "ui_components", "assigned_agent": "agency-ui-designer", "description": "Build UI", "depends_on": "db_schema"}]}`.
4. You can only assign tasks to agents listed in your AVAILABLE ROSTER.
5. Step 3: When finished, output `{"action": "done", "result": "Project delegation complete."}`.
"""

class CEOAgent(BaseAgent):
    """
    The CEO — plans architecture, writes ARCHITECTURE.md.
    Now uses the shared brain_dispatcher to call its configured LLM.
    """

    def __init__(self, api_key_env_var: str = "CLAUDE_API_KEY"):
        super().__init__(
            agent_id="ceo",
            agent_name="CEO Agent",
            soul=CEO_SOUL,
            brain="claude-sonnet-4-20250514",
            tier=1,
            hands=["primitive_bash", "primitive_gh"],
        )
        self.api_key = os.getenv(api_key_env_var, "")
        self.workspace_path = os.path.join(
            os.path.dirname(__file__), "..", "shared_workspace"
        )

    def _load_brain(self) -> str:
        """Load the CEO's brain model from the database (UI-configurable)."""
        try:
            agent_data = get_agent("ceo")
            if agent_data and agent_data.get("brain_model"):
                db_model = agent_data["brain_model"]
                self.brain = db_model
                return db_model
        except Exception:
            pass
        return self.brain

    def write_architecture(self, requirements: str) -> str:
        """
        Takes natural-language requirements, sends them to the CEO's LLM brain,
        writes ARCHITECTURE.md, and creates tasks in the Task Queue for the Agency.
        """
        self.set_state(AgentState.INGESTING, "Reading requirements")

        model = self._load_brain()
        logger.info("🏛️ CEO brain: %s", model)

        from database.db_manager import get_all_agents, create_task
        from anatomy.brain_dispatcher import extract_json
        import uuid

        # Get the roster
        roster = get_all_agents()
        roster_text = "AVAILABLE ROSTER:\n"
        for a in roster:
            if a['agent_id'] not in ['ceo', 'god', 'jules_dispatch', 'qa', 'ops']:
                roster_text += f"- ID: {a['agent_id']} | Name: {a['agent_name']} | Role: {a.get('role', '')}\n"

        # Read existing RULES.md for context
        rules_context = ""
        rules_path = os.path.join(self.workspace_path, "RULES.md")
        if os.path.exists(rules_path):
            with open(rules_path, "r", encoding="utf-8") as f:
                rules_context = f"\n\n[RULES.md — You must follow these]\n{f.read()}"

        # Build initial conversation
        conversation = f"""## Requirements from the Operator:
{requirements}

{rules_context}

{roster_text}

Remember to output ONLY JSON blocks corresponding to your permitted actions."""

        self.set_state(AgentState.CODING, "Architecting & Delegating")
        
        max_loops = 5
        loop_count = 0
        final_result = ""
        architecture_content = ""
        
        while loop_count < max_loops:
            loop_count += 1
            prompt = conversation + "\n\nWhat is your next action? (Output JSON)"
            
            try:
                response = query_brain(prompt, system=CEO_SOUL, model=model, api_key=self.api_key)
                if not response:
                    return "CEO LLM returned empty response."
                    
                action_data = extract_json(response)
                
                if not action_data:
                    logger.warning("🏛️ CEO returned non-JSON response. Forcing exit.")
                    final_result = response
                    break
                    
                action = action_data.get("action")
                
                if action == "done":
                    final_result = action_data.get("result", "Delegation complete.")
                    break
                    
                elif action == "write_architecture":
                    architecture_content = action_data.get("content", "")
                    arch_path = os.path.join(self.workspace_path, "ARCHITECTURE.md")
                    if not os.path.exists(self.workspace_path):
                        os.makedirs(self.workspace_path, exist_ok=True)
                    with open(arch_path, "w", encoding="utf-8") as f:
                        f.write(architecture_content)
                    
                    self.set_state(AgentState.PUSHING, "Saved ARCHITECTURE.md")
                    conversation += f"\n\nAssistant Action:\n```json\n{response}\n```\n\n[SYSTEM] ARCHITECTURE.md successfully saved. Now delegate tasks to the roster."
                    
                elif action == "create_tasks":
                    tasks = action_data.get("tasks", [])
                    created_count = 0
                    for t in tasks:
                        task_id = t.get("task_id") or f"task_{uuid.uuid4().hex[:8]}"
                        create_task(
                            task_id=task_id,
                            task_type="GENERAL",
                            description=t.get("description", "No description"),
                            priority=t.get("priority", 5),
                            assigned_agent=t.get("assigned_agent"),
                            depends_on=t.get("depends_on", "")
                        )
                        created_count += 1
                        
                    self.set_state(AgentState.PUSHING, f"Created {created_count} tasks")
                    conversation += f"\n\nAssistant Action:\n```json\n{response}\n```\n\n[SYSTEM] {created_count} tasks successfully inserted into the Task Queue."
                    
                else:
                    conversation += f"\n\nAssistant Action:\n```json\n{response}\n```\n\n[SYSTEM ERROR] Unknown action '{action}'."
                    
            except Exception as e:
                logger.error(f"CEO Execution Error: {str(e)}")
                break

        self.set_state(AgentState.SUCCESS, "ARCHITECTURE.md & Delegation complete")
        return architecture_content if architecture_content else final_result

    def read_architecture(self) -> Optional[str]:
        """Read the current ARCHITECTURE.md contents."""
        arch_path = os.path.join(self.workspace_path, "ARCHITECTURE.md")
        if os.path.exists(arch_path):
            with open(arch_path, "r", encoding="utf-8") as f:
                return f.read()
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ceo = CEOAgent()
    content = ceo.write_architecture("Build a REST API for user management with CRUD operations.")
    print(content)

