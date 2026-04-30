"""
agency_worker.py — Generalized Agency Worker
Dynamically loads the SKILL.md definition for any of the 184 Agency agents.
"""

from anatomy.agent_core import BaseAgent, AgentState
from database.db_manager import get_agent
from anatomy.brain_dispatcher import query_brain
import logging

logger = logging.getLogger(__name__)

class AgencyWorker(BaseAgent):
    def __init__(self, agent_id: str):
        # Fetch the agent profile from DB
        profile = get_agent(agent_id)
        if not profile:
            raise ValueError(f"Agent {agent_id} not found in Ledger DB.")
            
        super().__init__(
            agent_id=profile["agent_id"],
            agent_name=profile["agent_name"],
            soul=profile.get("custom_skills", ""),  # Fallback soul, we will load full skill
            brain=profile.get("brain_model", "gemini-1.5-pro"),
            tier=profile.get("tier", "agency"),
            department=profile.get("department", "Agency Operations"),
            specialization=profile.get("specialization", ""),
            hands=profile.get("equipped_tools", ["bash", "github"])
        )
        
        # Load the actual skill instructions from SKILL.md
        self.soul = self.load_agency_skill()
        logger.info(f"Loaded Agency Skill for {self.agent_name}")

    def execute_task(self, description: str, inputs: dict) -> dict:
        """
        Executes a dynamic task based on the loaded SKILL.md instructions.
        Uses a ReAct-style loop to utilize equipped tools (hands) before concluding.
        """
        self.set_state(AgentState.INGESTING, f"Executing: {description[:50]}")
        
        from anatomy.brain_dispatcher import query_brain, extract_json
        
        tools_instruction = "You have the following tools available. To use a tool, you MUST output a single JSON block and nothing else.\n"
        if "bash" in self.hands:
            tools_instruction += "- To run a shell command (which you can use to read/write files), output: {\"action\": \"bash\", \"command\": \"your command here\"}\n"
        if "github" in self.hands:
            tools_instruction += "- To run a github cli command, output: {\"action\": \"github\", \"command\": \"your gh command here\"}\n"
        
        tools_instruction += "- To query the semantic codebase graph for a function/class definition, output: {\"action\": \"query_graph\", \"query\": \"keyword\"}\n"
        tools_instruction += "- When you are completely finished with the task, output: {\"action\": \"done\", \"result\": \"final answer or summary\"}\n"
        
        system_prompt = f"{self.soul}\n\n[TOOL CALLING INSTRUCTIONS]\n{tools_instruction}"
        
        conversation = f"## Your Task:\n{description}\n\n## Inputs:\n{inputs}\n"
        
        max_loops = 5
        loop_count = 0
        final_result = ""
        
        while loop_count < max_loops:
            loop_count += 1
            prompt = conversation + "\n\nWhat is your next action? (Remember to output ONLY JSON)"
            
            self.set_state(AgentState.CODING, f"Thinking (Step {loop_count})")
            
            try:
                response = query_brain(prompt, system=system_prompt, model=self.brain)
                if not response:
                    return {"status": "FAILED", "error": "LLM returned empty response."}
                
                action_data = extract_json(response)
                
                if not action_data:
                    # If no JSON was returned, force exit to avoid infinite loops
                    logger.warning(f"[{self.agent_id}] returned non-JSON response.")
                    final_result = response
                    break
                    
                action = action_data.get("action")
                
                if action == "done":
                    final_result = action_data.get("result", str(action_data))
                    from caveman_tools.primitive_graph import build_knowledge_graph
                    import os
                    workspace = os.path.join(os.path.dirname(__file__), '..', '..', 'shared_workspace')
                    build_knowledge_graph(workspace)
                    break
                    
                elif action == "bash" and "bash" in self.hands:
                    from caveman_tools.primitive_bash import run_bash
                    import os
                    workspace = os.path.join(os.path.dirname(__file__), '..', '..', 'shared_workspace')
                    if not os.path.exists(workspace):
                        os.makedirs(workspace, exist_ok=True)
                        
                    cmd = action_data.get("command", "echo 'no command'")
                    self.set_state(AgentState.CODING, f"Running bash: {cmd[:20]}")
                    res = run_bash(cmd, cwd=workspace)
                    
                    tool_output = f"\n[BASH RESULT]\nSTDOUT:\n{res['stdout']}\nSTDERR:\n{res['stderr']}\n"
                    conversation += f"\n\nAssistant Action:\n```json\n{response}\n```\n{tool_output}"
                    
                elif action == "github" and "github" in self.hands:
                    from caveman_tools.primitive_bash import run_bash
                    import os
                    workspace = os.path.join(os.path.dirname(__file__), '..', '..', 'shared_workspace')
                    cmd = action_data.get("command", "gh --help")
                    if not cmd.startswith("gh "):
                        cmd = f"gh {cmd}"
                    self.set_state(AgentState.CODING, f"Running gh: {cmd[:20]}")
                    res = run_bash(cmd, cwd=workspace)
                    
                    tool_output = f"\n[GITHUB RESULT]\nSTDOUT:\n{res['stdout']}\nSTDERR:\n{res['stderr']}\n"
                    conversation += f"\n\nAssistant Action:\n```json\n{response}\n```\n{tool_output}"
                    
                elif action == "query_graph":
                    from caveman_tools.primitive_graph import query_graph
                    import os
                    workspace = os.path.join(os.path.dirname(__file__), '..', '..', 'shared_workspace')
                    q = action_data.get("query", "")
                    self.set_state(AgentState.CODING, f"Querying graph: {q[:20]}")
                    res = query_graph(workspace, q)
                    tool_output = f"\n[GRAPH RESULT]\n{res}\n"
                    conversation += f"\n\nAssistant Action:\n```json\n{response}\n```\n{tool_output}"
                    
                else:
                    tool_output = f"\n[ERROR] Unknown action '{action}' or tool not equipped. Your hands: {self.hands}\n"
                    conversation += f"\n\nAssistant Action:\n```json\n{response}\n```\n{tool_output}"
                    
            except Exception as e:
                error_msg = str(e)
                self.set_state(AgentState.ERROR, f"Execution failed: {error_msg[:50]}")
                return {"status": "FAILED", "error": error_msg}
                
        self.set_state(AgentState.SUCCESS, "Task execution complete")
        return {"status": "SUCCESS", "result": final_result}
