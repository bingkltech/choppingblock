"""
⚡ jules_router.py — The Tier 2 Cloud Load Balancer
Routes tasks to the Jules account with the lowest API usage today.
"""

import os
import logging
from typing import Optional

from ...database.db_manager import get_least_used_account, log_token_usage
from .antigravity_worker import CloudLaborer

logger = logging.getLogger(__name__)


class JulesRouter:
    """
    Load-balances tasks across the 5 Jules (Gemini) cloud accounts.
    Picks the account with the lowest token burn today and dispatches the task.
    """

    def __init__(self):
        self.workers: dict[str, CloudLaborer] = {}
        self._init_workers()

    def _init_workers(self) -> None:
        """Initialize a CloudLaborer for each Jules account."""
        for i in range(1, 6):
            account_name = f"jules_account_{i}"
            env_var = f"JULES_KEY_{i}"
            self.workers[account_name] = CloudLaborer(
                account_name=account_name,
                api_key_env_var=env_var,
            )
        logger.info("⚡ JulesRouter initialized with %d workers.", len(self.workers))

    def dispatch(self, task_description: str, repo_context: str) -> Optional[str]:
        """
        Dispatch a task to the least-used Jules account.

        Args:
            task_description: The coding task from the CEO's ARCHITECTURE.md.
            repo_context: Current state of ARCHITECTURE.md + RULES.md.

        Returns:
            The raw CLI command output from the Cloud Laborer, or None on failure.
        """
        account = get_least_used_account()

        if not account:
            logger.error("⚡ JulesRouter: No available accounts!")
            return None

        account_name = account["account_name"]
        worker = self.workers.get(account_name)

        if not worker:
            logger.error("⚡ JulesRouter: Worker not found for %s", account_name)
            return None

        logger.info("⚡ Dispatching to %s (usage: %d tokens today)", account_name, account["tokens_used_today"])

        result = worker.execute_task(task_description, repo_context)

        # Log the token usage (approximate — in production, parse from API response)
        if result:
            estimated_tokens = len(result) // 4  # rough estimate
            log_token_usage(account_name, estimated_tokens)
            logger.info("⚡ Task completed. ~%d tokens used.", estimated_tokens)

        return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from ...database.db_manager import init_database, seed_jules_accounts
    init_database()
    seed_jules_accounts()

    router = JulesRouter()
    print(f"Router ready with {len(router.workers)} workers")
