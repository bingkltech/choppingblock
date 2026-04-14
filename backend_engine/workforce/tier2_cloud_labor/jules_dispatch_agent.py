"""
🔮 jules_dispatch_agent.py — The Jules Dispatch Agent (Tier 2 Cloud Laborer)

Orchestrates the complete Jules workflow:
1. Reads ARCHITECTURE.md + RULES.md (Stigmergic context)
2. Enriches the task prompt with project context
3. Dispatches to Jules API via primitive_jules.py
4. Tracks sessions in the SQLite Ledger
5. Polls for completion and broadcasts state via heartbeat
"""

import os
import sys
import logging
from typing import Optional
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from anatomy.agent_core import BaseAgent, AgentState
from caveman_tools.primitive_jules import (
    create_session, get_session, approve_plan, send_message, list_sessions
)
from database.db_manager import (
    create_jules_session, update_jules_session,
    get_jules_session, get_active_jules_sessions, get_all_jules_sessions,
    log_activity, create_alert,
)

logger = logging.getLogger(__name__)

# ==========================================
# 🧠 THE SOUL (SYSTEM PROMPT)
# ==========================================
JULES_DISPATCH_SOUL = """
[IDENTITY]
You are the Jules Dispatch Agent, a Tier-2 Cloud Laborer coordinator within the
Paperclip Reborn Foundry. Your job is to receive coding tasks from the CEO's
ARCHITECTURE.md, enrich them with full project context and rules, then dispatch
them to Google's Jules AI coding agent via its REST API.

[OPERATIONAL RULES]
1. Always read ARCHITECTURE.md and RULES.md before dispatching any task.
2. Include the full project context in every Jules prompt so it understands
   the codebase conventions.
3. Track every session in the Ledger database.
4. Never dispatch more than 3 concurrent sessions (API rate limits).
5. If a session fails, log it as an alert and retry once.
6. Never leak API keys in logs — mask them.

[STIGMERGIC PARADIGM]
You communicate by modifying the shared repository state, not by chatting.
Your dispatched Jules sessions produce Pull Requests that modify the repo.
The QA Agent will review those PRs. You close the loop.
"""

# Maximum concurrent Jules sessions
MAX_CONCURRENT_SESSIONS = 3


class JulesDispatchAgent(BaseAgent):
    """
    The Jules Dispatch Agent — Tier 2 Cloud Laborer.

    Reads stigmergic context (ARCHITECTURE.md + RULES.md), enriches task prompts,
    dispatches them to the Jules API, and tracks everything in the Ledger.
    """

    def __init__(self, api_key_env_var: str = "JULES_API_KEY"):
        super().__init__(
            agent_id="jules_dispatch",
            agent_name="Jules Dispatch Agent",
            soul=JULES_DISPATCH_SOUL,
            brain="jules-api",
            tier=2,
            hands=["primitive_jules", "primitive_gh"],
        )
        self.api_key = os.getenv(api_key_env_var, "")
        self.workspace_path = os.path.join(
            os.path.dirname(__file__), "..", "shared_workspace"
        )
        self.default_repo = os.getenv("JULES_DEFAULT_REPO", "")

    # ------------------------------------------
    # CORE: Full Dispatch Workflow
    # ------------------------------------------

    def dispatch_task(
        self,
        task: str,
        repo: str = "",
        branch: str = "main",
        require_plan_approval: bool = True,
    ) -> dict:
        """
        Full dispatch pipeline:
        1. Validate preconditions (API key, repo, concurrent limit)
        2. Read stigmergic context
        3. Enrich the prompt
        4. Call Jules API
        5. Track in Ledger
        6. Broadcast state changes

        Args:
            task: The coding task description.
            repo: Target GitHub repo in "owner/repo" format. Falls back to JULES_DEFAULT_REPO.
            branch: Starting branch (default: main).
            require_plan_approval: If True, Jules waits for plan approval.

        Returns:
            {"success": bool, "session_id": str|None, "status": str, "error": str|None}
        """
        self.set_state(AgentState.INGESTING, "Validating dispatch preconditions")

        # --- Validate preconditions ---
        if not self.api_key:
            error = "JULES_API_KEY not set. Cannot dispatch."
            logger.error("🔮 %s", error)
            self.set_state(AgentState.ERROR, error)
            return {"success": False, "session_id": None, "status": "ERROR", "error": error}

        repo = repo or self.default_repo
        if not repo or "/" not in repo:
            error = f"Invalid repo format: '{repo}'. Expected 'owner/repo-name'."
            logger.error("🔮 %s", error)
            self.set_state(AgentState.ERROR, error)
            return {"success": False, "session_id": None, "status": "ERROR", "error": error}

        # Check concurrent session limit
        active = get_active_jules_sessions()
        if len(active) >= MAX_CONCURRENT_SESSIONS:
            error = f"Concurrent session limit reached ({MAX_CONCURRENT_SESSIONS}). Wait for active sessions to complete."
            logger.warning("🔮 %s", error)
            self.set_state(AgentState.WAITING, error)
            return {"success": False, "session_id": None, "status": "RATE_LIMITED", "error": error}

        # --- Read stigmergic context ---
        self.set_state(AgentState.INGESTING, "Reading ARCHITECTURE.md + RULES.md")
        context = self._read_stigmergy()

        # --- Enrich the prompt ---
        enriched_prompt = self._enrich_prompt(task, context)

        # --- Parse repo ---
        repo_parts = repo.split("/")
        repo_owner = repo_parts[0]
        repo_name = repo_parts[1]

        # --- Dispatch to Jules ---
        self.set_state(AgentState.CODING, f"Dispatching to Jules: {repo}")

        result = create_session(
            api_key=self.api_key,
            prompt=enriched_prompt,
            repo_owner=repo_owner,
            repo_name=repo_name,
            branch=branch,
            require_plan_approval=require_plan_approval,
        )

        if not result["success"]:
            error_msg = result.get("error", "Unknown error")
            self.set_state(AgentState.ERROR, f"Dispatch failed: {error_msg}")
            log_activity(
                self.agent_id, "DISPATCH_FAILED",
                f"Failed to dispatch to {repo}: {error_msg}",
                severity="ERROR"
            )
            create_alert(self.agent_id, "DISPATCH_FAILURE", f"Jules dispatch failed for {repo}: {error_msg}")
            return {
                "success": False,
                "session_id": None,
                "status": "FAILED",
                "error": error_msg,
            }

        # --- Track in Ledger ---
        session_id = result["session_id"]
        self.set_state(AgentState.PUSHING, f"Session created: {session_id}")

        create_jules_session(
            session_id=session_id,
            task_prompt=task,
            repo_source=repo,
            branch=branch,
            api_key_used=self.api_key[-4:] if self.api_key else "",
        )

        log_activity(
            self.agent_id, "DISPATCH_SUCCESS",
            f"Dispatched task to Jules | Session: {session_id} | Repo: {repo}",
        )

        self.set_state(AgentState.SUCCESS, f"Dispatched → {session_id}")

        return {
            "success": True,
            "session_id": session_id,
            "status": result["status"],
            "error": None,
        }

    # ------------------------------------------
    # CORE: Check Session Status
    # ------------------------------------------

    def check_session(self, session_id: str) -> dict:
        """
        Poll Jules API for session status and update the Ledger.

        Returns:
            {"success": bool, "status": str, "pr_url": str|None, "error": str|None}
        """
        self.set_state(AgentState.INGESTING, f"Checking session: {session_id}")

        result = get_session(self.api_key, session_id)

        if not result["success"]:
            return result

        status = result["status"]
        pr_url = result.get("pr_url")

        # Map Jules status to our internal status
        status_map = {
            "PLANNING": "PLANNING",
            "PLAN_READY": "PLANNING",
            "EXECUTING": "EXECUTING",
            "COMPLETED": "COMPLETED",
            "FAILED": "FAILED",
            "CANCELLED": "FAILED",
        }
        internal_status = status_map.get(status, status)

        # Update ledger
        completed = internal_status in ("COMPLETED", "FAILED")
        update_jules_session(
            session_id=session_id,
            status=internal_status,
            pr_url=pr_url,
            completed=completed,
        )

        if completed:
            if internal_status == "COMPLETED":
                self.set_state(AgentState.SUCCESS, f"Session completed: {session_id}")
                log_activity(self.agent_id, "SESSION_COMPLETED", f"Jules session completed: {session_id} | PR: {pr_url or 'N/A'}")
            else:
                self.set_state(AgentState.ERROR, f"Session failed: {session_id}")
                log_activity(self.agent_id, "SESSION_FAILED", f"Jules session failed: {session_id}", severity="ERROR")
        else:
            self.set_state(AgentState.CODING, f"Session {internal_status}: {session_id}")

        return {
            "success": True,
            "status": internal_status,
            "pr_url": pr_url,
            "raw": result.get("raw"),
            "error": None,
        }

    # ------------------------------------------
    # CORE: Approve Session Plan
    # ------------------------------------------

    def approve_session(self, session_id: str) -> dict:
        """
        Approve a pending plan for a Jules session (Boss Mode gate).

        Returns:
            {"success": bool, "error": str|None}
        """
        self.set_state(AgentState.WAITING, f"Approving plan: {session_id}")

        result = approve_plan(self.api_key, session_id)

        if result["success"]:
            update_jules_session(session_id, plan_approved=True)
            log_activity(self.agent_id, "PLAN_APPROVED", f"Plan approved for session: {session_id}")
            self.set_state(AgentState.SUCCESS, f"Plan approved: {session_id}")
        else:
            self.set_state(AgentState.ERROR, f"Plan approval failed: {session_id}")

        return result

    # ------------------------------------------
    # CORE: Send Follow-up Message
    # ------------------------------------------

    def send_followup(self, session_id: str, message: str) -> dict:
        """
        Send a follow-up message to an active session.
        Used for the QA verification loop.
        """
        self.set_state(AgentState.CODING, f"Sending message to: {session_id}")
        result = send_message(self.api_key, session_id, message)

        if result["success"]:
            log_activity(self.agent_id, "MESSAGE_SENT", f"Follow-up sent to session: {session_id}")
            self.set_state(AgentState.SUCCESS, f"Message sent: {session_id}")
        else:
            self.set_state(AgentState.ERROR, f"Message failed: {session_id}")

        return result

    # ------------------------------------------
    # HELPERS: Stigmergic Context
    # ------------------------------------------

    def _read_stigmergy(self) -> str:
        """Read ARCHITECTURE.md + RULES.md from shared_workspace."""
        context_parts = []

        arch_path = os.path.join(self.workspace_path, "ARCHITECTURE.md")
        if os.path.exists(arch_path):
            with open(arch_path, "r", encoding="utf-8") as f:
                content = f.read()
            context_parts.append(f"[ARCHITECTURE.md]\n{content}")
            logger.info("🔮 Read ARCHITECTURE.md (%d chars)", len(content))
        else:
            logger.warning("🔮 ARCHITECTURE.md not found at %s", arch_path)

        rules_path = os.path.join(self.workspace_path, "RULES.md")
        if os.path.exists(rules_path):
            with open(rules_path, "r", encoding="utf-8") as f:
                content = f.read()
            context_parts.append(f"[RULES.md]\n{content}")
            logger.info("🔮 Read RULES.md (%d chars)", len(content))
        else:
            logger.warning("🔮 RULES.md not found at %s", rules_path)

        return "\n\n---\n\n".join(context_parts) if context_parts else "[No stigmergic context available]"

    def _enrich_prompt(self, task: str, context: str) -> str:
        """Combine task + stigmergic context into a Jules-optimized prompt."""
        return f"""You are working on a coding task within the Paperclip Reborn Foundry.

## Project Context (Stigmergy — Read This First)

{context}

---

## Your Task

{task}

---

## Rules
- Follow all rules in RULES.md strictly. If a rule contradicts standard practice, the rule wins.
- Follow the architecture in ARCHITECTURE.md.
- Write complete, production-ready code. No placeholders, no TODOs.
- Include proper error handling, logging, and type hints.
- Open a Pull Request with a clear title and description when done.
"""

    # ------------------------------------------
    # QUERY HELPERS
    # ------------------------------------------

    def get_active_sessions(self) -> list[dict]:
        """Return all non-completed sessions from the Ledger."""
        return get_active_jules_sessions()

    def get_all_sessions(self, limit: int = 50) -> list[dict]:
        """Return recent sessions from the Ledger."""
        return get_all_jules_sessions(limit)


# ==========================================
# 🧪 STANDALONE TEST
# ==========================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    agent = JulesDispatchAgent()
    print(f"\nAgent: {agent}")
    print(f"API Key set: {'Yes' if agent.api_key else 'No'}")
    print(f"Default repo: {agent.default_repo or 'Not set'}")

    # Test stigmergic read
    context = agent._read_stigmergy()
    print(f"\nStigmergic context loaded: {len(context)} chars")

    # Test dispatch (will fail without valid API key, but tests the flow)
    if agent.api_key:
        print("\n--- Testing dispatch ---")
        result = agent.dispatch_task(
            task="Add a health check endpoint to the FastAPI server",
            repo=agent.default_repo,
            branch="main",
        )
        print(f"Dispatch result: {result}")
    else:
        print("\n[WARN] No JULES_API_KEY set. Skipping live dispatch test.")
        print("Set JULES_API_KEY in your .env to test real dispatches.")
