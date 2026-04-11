"""
🔧 ops_agent.py — The Tier 3 Local Worker: Ops Agent
Merges approved PRs, cleans stale branches, enforces repo hygiene.
Uses local Ollama (qwen2.5-coder) for zero-cost ops decisions.
"""

import logging

from ..anatomy.agent_core import BaseAgent, AgentState

logger = logging.getLogger(__name__)

OPS_SOUL = """
[IDENTITY]
You are the Ops Agent. You are the janitor and gatekeeper of the Git repository.
You do not write code. You manage the repository lifecycle.

[OPERATIONAL RULES]
1. When a PR is marked QA_PASS, merge it via squash and delete the branch.
2. Periodically scan for stale branches (> 3 days without commits) and delete them.
3. Ensure the `main` branch is always clean and deployable.
4. Report all merge operations to the activity feed.
"""


class OpsAgent(BaseAgent):
    """
    The Ops Agent — merges PRs and enforces repo hygiene.
    """

    def __init__(self):
        super().__init__(
            agent_id="ops",
            agent_name="Ops Agent",
            soul=OPS_SOUL,
            brain="qwen2.5-coder",
            tier=3,
            hands=["primitive_gh", "primitive_bash"],
        )

    def merge_pr(self, pr_number: int, repo_path: str) -> dict:
        """Merge a QA-approved PR and clean up the branch."""
        from ..caveman_tools.primitive_gh import merge_pr

        self.set_state(AgentState.PUSHING, f"Merging PR #{pr_number}")

        result = merge_pr(pr_number, method="squash", cwd=repo_path)

        if result["success"]:
            self.set_state(AgentState.SUCCESS, f"PR #{pr_number} merged")
            logger.info("🔧 Ops: Merged PR #%d", pr_number)
        else:
            self.set_state(AgentState.ERROR, f"Merge failed for PR #{pr_number}")
            logger.error("🔧 Ops: Failed to merge PR #%d: %s", pr_number, result["stderr"])

        return result

    def clean_stale_branches(self, repo_path: str) -> list[str]:
        """Delete branches with no recent activity."""
        from ..caveman_tools.primitive_bash import run_bash

        self.set_state(AgentState.TESTING, "Scanning for stale branches")

        # List merged branches (safe to delete)
        result = run_bash("git branch --merged main | grep -v main", cwd=repo_path)

        cleaned = []
        if result["success"] and result["stdout"]:
            branches = [b.strip() for b in result["stdout"].split("\n") if b.strip()]
            for branch in branches:
                if branch.startswith("*"):
                    continue
                from ..caveman_tools.primitive_gh import delete_branch
                delete_branch(branch, cwd=repo_path)
                cleaned.append(branch)
                logger.info("🔧 Ops: Cleaned branch: %s", branch)

        self.set_state(AgentState.SUCCESS, f"Cleaned {len(cleaned)} branches")
        return cleaned


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ops = OpsAgent()
    print(f"Ops Agent ready: {ops}")
