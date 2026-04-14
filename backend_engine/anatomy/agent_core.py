"""
🧬 agent_core.py — The Agent DNA
Base class for all agents in the Paperclip Reborn Foundry.
Every agent has a Soul (system prompt), Brain (model), Hands (tools), and Heartbeat (WebSocket).
"""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)


class AgentState(str, Enum):
    """Visual states that map to dashboard colors."""
    IDLE = "IDLE"               # ⚪ Gray
    INGESTING = "INGESTING"     # 🔵 Blue — reading repo context
    CODING = "CODING"           # 🟡 Yellow — generating code
    TESTING = "TESTING"         # 🟣 Purple — running in Docker
    PUSHING = "PUSHING"         # 🟠 Orange — committing/pushing
    WAITING = "WAITING"         # ⏳ Cyan — waiting for approval (Boss Mode)
    SUCCESS = "SUCCESS"         # 🟢 Green — task complete
    ERROR = "ERROR"             # 🔴 Red — crashed or failed
    HEALING = "HEALING"         # 💛 Gold — self-healing in progress
    STALE = "STALE"             # ⚠️  Amber — heartbeat gone silent


class BaseAgent:
    """
    The foundational DNA for every agent in the Foundry.
    
    Attributes:
        agent_id:   Unique identifier (e.g., 'ceo', 'jules_1', 'qa')
        soul:       The system prompt that defines this agent's personality and constraints.
        brain:      The LLM model currently assigned (can be hot-swapped via UI).
        hands:      List of equipped Caveman Primitive tool names.
        state:      Current operational state (maps to dashboard visual).
        tier:       Workforce tier (1=Executive, 2=Cloud, 3=Local).
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        soul: str,
        brain: str,
        tier: int,
        hands: Optional[list[str]] = None,
    ):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.soul = soul
        self.brain = brain
        self.tier = tier
        self.hands: list[str] = hands or []
        self.state: AgentState = AgentState.IDLE
        self.current_task: str = "Idle"
        self.health_pct: float = 100.0
        self.last_heartbeat: str = datetime.now().isoformat()
        self.error_log: Optional[str] = None

        # Callback to broadcast heartbeat over WebSocket (injected by main.py)
        self._heartbeat_callback: Optional[Callable] = None

        logger.info(
            "🧬 Agent [%s] initialized | Tier %d | Brain: %s | Tools: %s",
            self.agent_id, self.tier, self.brain, self.hands
        )

    # ------------------------------------------
    # Heartbeat
    # ------------------------------------------

    def set_heartbeat_callback(self, callback: Callable) -> None:
        """Inject the WebSocket broadcast function from main.py."""
        self._heartbeat_callback = callback

    def broadcast_heartbeat(self) -> dict:
        """
        Pushes the agent's current state to the WebSocket for live UI updates.
        Returns the heartbeat payload for logging/testing.
        """
        self.last_heartbeat = datetime.now().isoformat()

        payload = {
            "type": "heartbeat",
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "tier": self.tier,
            "brain": self.brain,
            "state": self.state.value,
            "current_task": self.current_task,
            "health_pct": self.health_pct,
            "hands": self.hands,
            "last_heartbeat": self.last_heartbeat,
            "error_log": self.error_log,
        }

        if self._heartbeat_callback:
            try:
                self._heartbeat_callback(payload)
            except Exception as e:
                logger.error("❌ Heartbeat broadcast failed for [%s]: %s", self.agent_id, e)

        return payload

    # ------------------------------------------
    # State Transitions
    # ------------------------------------------

    def set_state(self, new_state: AgentState, task: str = None) -> None:
        """Transition to a new state and auto-broadcast."""
        old_state = self.state
        self.state = new_state
        if task:
            self.current_task = task
        if new_state == AgentState.ERROR:
            self.health_pct = max(0, self.health_pct - 10)
        elif new_state == AgentState.SUCCESS:
            self.health_pct = min(100, self.health_pct + 2)

        logger.info(
            "🔄 [%s] %s → %s | Task: %s",
            self.agent_id, old_state.value, new_state.value, self.current_task
        )
        self.broadcast_heartbeat()

    # ------------------------------------------
    # Tool Management (Hot-Swappable via UI)
    # ------------------------------------------

    def equip_tool(self, tool_name: str) -> None:
        """Add a Caveman Primitive to this agent's hands."""
        if tool_name not in self.hands:
            self.hands.append(tool_name)
            logger.info("🪨 [%s] Equipped tool: %s", self.agent_id, tool_name)
            self.broadcast_heartbeat()

    def unequip_tool(self, tool_name: str) -> None:
        """Remove a Caveman Primitive from this agent's hands."""
        if tool_name in self.hands:
            self.hands.remove(tool_name)
            logger.info("🪨 [%s] Unequipped tool: %s", self.agent_id, tool_name)
            self.broadcast_heartbeat()

    # ------------------------------------------
    # Brain Hot-Swap (via UI Dossier)
    # ------------------------------------------

    def swap_brain(self, new_model: str) -> None:
        """Hot-swap the LLM model powering this agent."""
        old = self.brain
        self.brain = new_model
        logger.info("🧠 [%s] Brain swapped: %s → %s", self.agent_id, old, new_model)
        self.broadcast_heartbeat()

    # ------------------------------------------
    # Health Monitoring
    # ------------------------------------------

    def is_stale(self, threshold_seconds: int = 120) -> bool:
        """Returns True if last_heartbeat is older than threshold_seconds."""
        try:
            last = datetime.fromisoformat(self.last_heartbeat)
            return (datetime.now() - last).total_seconds() > threshold_seconds
        except (ValueError, TypeError):
            return True  # If we can't parse the timestamp, assume stale

    # ------------------------------------------
    # Serialization
    # ------------------------------------------

    def to_dict(self) -> dict:
        """Serialize agent state for API responses."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "tier": self.tier,
            "brain": self.brain,
            "state": self.state.value,
            "current_task": self.current_task,
            "health_pct": self.health_pct,
            "hands": self.hands,
            "last_heartbeat": self.last_heartbeat,
            "error_log": self.error_log,
        }

    def __repr__(self) -> str:
        return f"<Agent:{self.agent_id} [{self.state.value}] brain={self.brain}>"
