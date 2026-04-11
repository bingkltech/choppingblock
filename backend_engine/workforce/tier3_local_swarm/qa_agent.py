"""
🐳 qa_agent.py — The Tier 3 Local Worker: QA Agent
Pulls PRs, runs code in Docker sandboxes, sends pass/fail results.
Uses local Ollama (llama3) for zero-cost code review.
"""

import os
import logging
from typing import Optional

from ..anatomy.agent_core import BaseAgent, AgentState

logger = logging.getLogger(__name__)

QA_SOUL = """
[IDENTITY]
You are the QA Agent of the Paperclip Reborn Foundry. You are a ruthless quality gatekeeper.
You trust no one's code — not even the CEO's. Every PR must survive your Docker sandbox.

[OPERATIONAL RULES]
1. When a PR is submitted, you pull it into a Docker container.
2. You run the full test suite: linting, type checks, unit tests.
3. If the code PASSES: output "QA_PASS" and the test summary.
4. If the code FAILS: output "QA_FAIL" followed by the RAW TERMINAL STACK TRACE. 
   Do not interpret the error. Do not suggest fixes. Just the raw output.
5. The Cloud Laborer will read your raw stack trace and fix it autonomously.

[OUTPUT FORMAT]
QA_PASS: {summary}
or
QA_FAIL: {raw_stack_trace}
"""


class QAAgent(BaseAgent):
    """
    The QA Agent — tests PRs in Docker sandboxes.
    """

    def __init__(self):
        super().__init__(
            agent_id="qa",
            agent_name="QA Agent",
            soul=QA_SOUL,
            brain="llama3",
            tier=3,
            hands=["primitive_docker", "primitive_bash"],
        )

    def test_pr(self, pr_number: int, repo_path: str) -> dict:
        """
        Pull a PR, run it in Docker, return pass/fail with raw output.
        """
        from ..caveman_tools.primitive_bash import run_bash
        from ..caveman_tools.primitive_docker import run_tests_in_sandbox

        self.set_state(AgentState.INGESTING, f"Pulling PR #{pr_number}")

        # Checkout the PR branch
        checkout = run_bash(f"gh pr checkout {pr_number}", cwd=repo_path)
        if not checkout["success"]:
            self.set_state(AgentState.ERROR, f"Failed to checkout PR #{pr_number}")
            return {"passed": False, "output": checkout["stderr"]}

        self.set_state(AgentState.TESTING, f"Testing PR #{pr_number} in Docker")

        # Run tests in Docker sandbox
        result = run_tests_in_sandbox(
            test_command="python -m pytest -v --tb=short",
            project_path=repo_path,
        )

        if result["passed"]:
            self.set_state(AgentState.SUCCESS, f"PR #{pr_number} PASSED")
            logger.info("🐳 QA: PR #%d PASSED", pr_number)
            return {
                "passed": True,
                "verdict": "QA_PASS",
                "output": result["test_output"],
            }
        else:
            self.set_state(AgentState.ERROR, f"PR #{pr_number} FAILED")
            logger.warning("🐳 QA: PR #%d FAILED", pr_number)
            return {
                "passed": False,
                "verdict": "QA_FAIL",
                "output": result["error_output"] or result["test_output"],
            }

    def run_code_review(self, code: str) -> Optional[str]:
        """
        Use local Ollama to do a quick code review (zero cost).
        """
        from ..caveman_tools.primitive_ollama import run_prompt

        self.set_state(AgentState.TESTING, "Running code review via Ollama")

        result = run_prompt(
            prompt=f"Review this code for bugs and security issues. Be concise:\n\n{code}",
            model=self.brain,
            system="You are a senior code reviewer. List only critical issues, one per line.",
        )

        if result["success"]:
            self.set_state(AgentState.SUCCESS, "Code review complete")
            return result["response"]
        else:
            self.set_state(AgentState.ERROR, "Code review failed")
            return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    qa = QAAgent()
    print(f"QA Agent ready: {qa}")
