"""
🔀 shift_manager.py — The Day/Night Shift Controller
Toggles between Boss Mode (human approval gates) and God Mode (fully autonomous).
"""

import logging
from enum import Enum
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class ShiftMode(str, Enum):
    """The two operational modes of the Foundry."""
    BOSS = "BOSS"   # ☀️ Day Shift — pauses at critical junctures for human GUI approval
    GOD = "GOD"     # 🌙 Night Shift — God Agent has SUDO, fully autonomous


class ShiftManager:
    """
    Manages the global shift mode for the Foundry.
    
    In BOSS mode, certain operations (merging PRs, patching framework code,
    deploying to production) require human approval through the Visual HQ UI.
    
    In GOD mode, the God Agent has full autonomy — the system never blocks.
    """

    def __init__(self, default_mode: ShiftMode = ShiftMode.BOSS):
        self._mode: ShiftMode = default_mode
        self._approval_callback: Optional[Callable] = None
        self._pending_approvals: list[dict] = []
        logger.info("🔀 Shift Manager initialized in %s mode.", self._mode.value)

    @property
    def mode(self) -> ShiftMode:
        return self._mode

    @property
    def is_boss_mode(self) -> bool:
        return self._mode == ShiftMode.BOSS

    @property
    def is_god_mode(self) -> bool:
        return self._mode == ShiftMode.GOD

    def toggle(self) -> ShiftMode:
        """Switches between BOSS ↔ GOD mode. Returns the new mode."""
        if self._mode == ShiftMode.BOSS:
            self._mode = ShiftMode.GOD
            logger.info("🌙 Shift toggled → GOD MODE (Night Shift). Full autonomy enabled.")
            # Auto-approve all pending items
            for item in self._pending_approvals:
                item["approved"] = True
            self._pending_approvals.clear()
        else:
            self._mode = ShiftMode.BOSS
            logger.info("☀️ Shift toggled → BOSS MODE (Day Shift). Human approval required.")
        return self._mode

    def set_mode(self, mode: ShiftMode) -> None:
        """Explicitly set the shift mode."""
        self._mode = mode
        logger.info("🔀 Shift mode set to %s.", self._mode.value)

    def request_approval(self, agent_id: str, action: str, details: str = "") -> bool:
        """
        Gate for critical operations.
        
        In GOD mode: returns True immediately (auto-approved).
        In BOSS mode: queues the request and returns False (blocks until human approves via UI).
        """
        if self.is_god_mode:
            logger.info("✅ [GOD MODE] Auto-approved: [%s] %s", agent_id, action)
            return True

        approval_request = {
            "agent_id": agent_id,
            "action": action,
            "details": details,
            "approved": False,
        }
        self._pending_approvals.append(approval_request)
        logger.info(
            "⏳ [BOSS MODE] Approval required: [%s] %s — Queued. %d pending.",
            agent_id, action, len(self._pending_approvals)
        )
        return False

    def approve(self, index: int = 0) -> Optional[dict]:
        """Human approves a pending request (called from the UI endpoint)."""
        if 0 <= index < len(self._pending_approvals):
            item = self._pending_approvals.pop(index)
            item["approved"] = True
            logger.info("✅ [BOSS MODE] Human approved: [%s] %s", item["agent_id"], item["action"])
            return item
        return None

    def reject(self, index: int = 0) -> Optional[dict]:
        """Human rejects a pending request."""
        if 0 <= index < len(self._pending_approvals):
            item = self._pending_approvals.pop(index)
            item["approved"] = False
            logger.info("❌ [BOSS MODE] Human rejected: [%s] %s", item["agent_id"], item["action"])
            return item
        return None

    def get_pending_approvals(self) -> list[dict]:
        """Returns all pending approval requests for the UI."""
        return list(self._pending_approvals)

    def to_dict(self) -> dict:
        """Serialize shift state for the API."""
        return {
            "mode": self._mode.value,
            "is_god_mode": self.is_god_mode,
            "pending_approvals": len(self._pending_approvals),
            "pending_items": self._pending_approvals,
        }
