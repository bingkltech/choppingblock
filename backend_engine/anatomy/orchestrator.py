"""
🎯 orchestrator.py — The Task Orchestrator
The foreman of the workforce. Polls the Task_Queue, matches tasks to idle agents,
dispatches work, and reports results. Runs as an async background loop inside FastAPI.
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from database.db_manager import (
    get_pending_tasks, get_running_tasks, claim_task, start_task,
    complete_task, fail_task, retry_task, log_activity, get_agent,
    update_agent_status,
)

logger = logging.getLogger(__name__)

# ==========================================
# 🗺️ TASK → AGENT ROUTING MAP
# ==========================================
# Maps task_type to the agent_id that can handle it.
TASK_AGENT_MAP = {
    "WRITE_ARCH":   "ceo",           # CEO writes ARCHITECTURE.md
    "CODE":         "jules_dispatch", # Jules dispatches cloud coding
    "TEST_PR":      "qa",            # QA tests PRs in Docker
    "MERGE_PR":     "ops",           # Ops merges approved PRs
    "HEAL":         "god",           # God Agent self-heals crashes
    "GENERAL":      "ceo",           # Default to CEO for untyped tasks
}

# Polling interval in seconds
POLL_INTERVAL = 5


class Orchestrator:
    """
    The Orchestrator — assigns tasks to agents and monitors execution.

    Lifecycle:
        1. Poll Task_Queue every POLL_INTERVAL seconds
        2. For each PENDING task, find the best available agent
        3. Claim the task for that agent
        4. Execute the agent's method in a background asyncio task
        5. Mark DONE or FAILED based on result
    """

    def __init__(self):
        self.running = False
        self._active_tasks: dict[str, asyncio.Task] = {}  # task_id -> asyncio.Task
        logger.info("🎯 Orchestrator initialized")

    async def start(self):
        """Main orchestration loop. Call this as a background task."""
        self.running = True
        logger.info("🎯 Orchestrator started (polling every %ds)", POLL_INTERVAL)

        while self.running:
            try:
                await self._poll_cycle()
            except Exception as e:
                logger.error("🎯 Orchestrator poll error: %s", e)

            await asyncio.sleep(POLL_INTERVAL)

    async def stop(self):
        """Graceful shutdown."""
        self.running = False
        # Cancel any in-flight tasks
        for task_id, atask in self._active_tasks.items():
            atask.cancel()
            logger.info("🎯 Cancelled in-flight task: %s", task_id)
        self._active_tasks.clear()
        logger.info("🎯 Orchestrator stopped")

    async def _poll_cycle(self):
        """One poll iteration: check pending tasks, assign to agents."""
        pending = get_pending_tasks(limit=10)
        if not pending:
            return

        for task in pending:
            task_id = task["task_id"]
            task_type = task["task_type"]

            # Skip if we're already executing this task
            if task_id in self._active_tasks:
                continue

            # Find the right agent
            agent_id = task.get("assigned_agent")
            if not agent_id:
                agent_id = TASK_AGENT_MAP.get(task_type)
            if not agent_id:
                logger.warning("🎯 No agent mapped for task_type=%s and no assigned_agent", task_type)
                continue

            # Check if the agent exists and is available
            agent_record = get_agent(agent_id)
            if not agent_record:
                logger.warning("🎯 Agent %s not found in database", agent_id)
                continue

            agent_state = agent_record.get("state", "IDLE")
            if agent_state not in ("IDLE", "SUCCESS", "ERROR"):
                # Agent is busy — skip for now
                continue

            # Claim the task
            if not claim_task(task_id, agent_id):
                continue  # Another process already claimed it

            # Update agent state
            update_agent_status(agent_id, state="CODING", current_task=task.get("description", "")[:100])
            log_activity(agent_id, "TASK_CLAIMED", f"Claimed task: {task_id} ({task_type})")

            # Execute in background
            atask = asyncio.create_task(self._execute_task(task, agent_id))
            self._active_tasks[task_id] = atask

    async def _execute_task(self, task: dict, agent_id: str):
        """Execute a single task using the appropriate agent."""
        task_id = task["task_id"]
        task_type = task["task_type"]
        description = task.get("description", "")
        input_data = task.get("input_data", "{}")

        try:
            # Parse input data
            try:
                inputs = json.loads(input_data) if isinstance(input_data, str) else input_data
            except json.JSONDecodeError:
                inputs = {}

            # Mark as RUNNING
            start_task(task_id)
            update_agent_status(agent_id, state="CODING", current_task=description[:100])

            # Route to the correct agent method
            result = await self._dispatch_to_agent(task_type, agent_id, description, inputs)

            # Mark complete
            output_json = json.dumps(result) if isinstance(result, dict) else json.dumps({"result": str(result)})
            complete_task(task_id, output_json)
            update_agent_status(agent_id, state="IDLE", current_task=None)
            log_activity(agent_id, "TASK_DONE", f"Completed task: {task_id}")

            # --- THE QA SELF-CORRECTION LOOP ---
            import uuid
            from database.db_manager import create_task
            
            # 1. If an Agency worker finishes coding, spawn a QA check
            if agent_id and agent_id.startswith("agency-") and task_type != "TEST_WORKSPACE":
                qa_task_id = f"qa_check_{uuid.uuid4().hex[:8]}"
                create_task(
                    task_id=qa_task_id,
                    task_type="TEST_WORKSPACE",
                    description=f"Verify workspace code after task: {description[:50]}...",
                    priority=2, # High priority verification
                    assigned_agent="qa",
                    input_data=json.dumps({
                        "original_agent": agent_id,
                        "original_task_desc": description
                    })
                )
                logger.info("🎯 Spawning QA verification task %s for %s", qa_task_id, agent_id)
                
            # 2. If the QA check itself FAILED, spawn an auto-fix task for the original worker
            elif task_type == "TEST_WORKSPACE" and isinstance(result, dict) and not result.get("passed", True):
                fix_task_id = f"fix_bug_{uuid.uuid4().hex[:8]}"
                orig_agent = inputs.get("original_agent", "ceo")
                orig_desc = inputs.get("original_task_desc", "Unknown")
                
                create_task(
                    task_id=fix_task_id,
                    task_type="GENERAL",
                    description=f"URGENT BUG FIX! Your previous code for '{orig_desc}' failed QA testing.\n\nTEST FAILURE OUTPUT:\n{result.get('output', 'No output')}\n\nPlease fix the errors immediately.",
                    priority=1, # Highest priority to unblock pipeline
                    assigned_agent=orig_agent
                )
                logger.warning("🎯 QA Failed! Spawning auto-fix task %s for agent %s", fix_task_id, orig_agent)


        except Exception as e:
            error_msg = str(e)
            logger.error("🎯 Task %s execution failed: %s", task_id, error_msg)
            fail_task(task_id, error_msg)
            update_agent_status(agent_id, state="ERROR", current_task=f"Failed: {error_msg[:80]}")
            log_activity(agent_id, "TASK_FAILED", f"Task {task_id} failed: {error_msg[:200]}", severity="ERROR")

            # Auto-retry if eligible
            retry_task(task_id)

        finally:
            self._active_tasks.pop(task_id, None)

    async def _dispatch_to_agent(self, task_type: str, agent_id: str, description: str, inputs: dict) -> dict:
        """
        Route a task to the correct agent method.
        Runs the synchronous agent code in a thread pool to avoid blocking the event loop.
        """
        loop = asyncio.get_event_loop()

        if agent_id and agent_id.startswith("agency-"):
            from workforce.agency.agency_worker import AgencyWorker
            worker = AgencyWorker(agent_id=agent_id)
            result = await loop.run_in_executor(None, worker.execute_task, description, inputs)
            return result

        if task_type == "WRITE_ARCH":
            from workforce.executives.ceo_agent import CEOAgent
            ceo = CEOAgent()
            result = await loop.run_in_executor(None, ceo.write_architecture, description)
            return {"architecture": result[:2000] if result else ""}

        elif task_type == "CODE":
            from workforce.system_agents.jules_dispatch_agent import JulesDispatchAgent
            jules = JulesDispatchAgent()
            repo = inputs.get("repo", "")
            branch = inputs.get("branch", "main")
            result = await loop.run_in_executor(None, jules.dispatch_task, description, repo, branch)
            return result

        elif task_type == "TEST_PR":
            from workforce.system_agents.qa_agent import QAAgent
            qa = QAAgent()
            pr_number = inputs.get("pr_number", 0)
            repo_path = inputs.get("repo_path", ".")
            result = await loop.run_in_executor(None, qa.test_pr, pr_number, repo_path)
            return result

        elif task_type == "TEST_WORKSPACE":
            from workforce.system_agents.qa_agent import QAAgent
            qa = QAAgent()
            result = await loop.run_in_executor(None, qa.test_workspace)
            return result

        elif task_type == "MERGE_PR":
            from workforce.system_agents.ops_agent import OpsAgent
            ops = OpsAgent()
            pr_number = inputs.get("pr_number", 0)
            repo_path = inputs.get("repo_path", ".")
            result = await loop.run_in_executor(None, ops.merge_pr, pr_number, repo_path)
            return result

        elif task_type == "HEAL":
            from workforce.executives.god_agent import GodAgent
            god = GodAgent()
            traceback = inputs.get("traceback", description)
            auto_apply = inputs.get("auto_apply", False)
            result = await loop.run_in_executor(None, god.heal, traceback, auto_apply)
            return result

        elif task_type == "GENERAL":
            from workforce.executives.ceo_agent import CEOAgent
            ceo = CEOAgent()
            result = await loop.run_in_executor(None, ceo.write_architecture, description)
            return {"result": result[:2000] if result else ""}

        else:
            return {"status": "SKIPPED", "reason": f"Unknown task_type: {task_type}"}

    @property
    def status(self) -> dict:
        """Return current orchestrator state for the dashboard."""
        return {
            "running": self.running,
            "active_tasks": len(self._active_tasks),
            "active_task_ids": list(self._active_tasks.keys()),
        }
