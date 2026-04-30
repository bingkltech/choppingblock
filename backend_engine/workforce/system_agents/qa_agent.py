"""
🐳 qa_agent.py — The Tier 3 Local Worker: QA Agent
Pulls PRs, runs code in Docker sandboxes, sends pass/fail results.
"""

import os
import sys
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from anatomy.agent_core import BaseAgent, AgentState

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
        from caveman_tools.primitive_bash import run_bash
        from caveman_tools.primitive_docker import run_tests_in_sandbox

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

    def test_workspace(self) -> dict:
        """
        Run tests directly in the local shared_workspace without pulling a PR.
        Used to verify code written by local Agency Agents.
        """
        from caveman_tools.primitive_docker import run_tests_in_sandbox
        
        workspace_path = os.path.join(os.path.dirname(__file__), "..", "..", "shared_workspace")
        self.set_state(AgentState.TESTING, "Testing shared_workspace")

        # By default, we run pytest. We can extend this to detect package.json and run npm test.
        test_command = "python -m pytest -v --tb=short"
        if os.path.exists(os.path.join(workspace_path, "package.json")):
            test_command = "npm test"

        result = run_tests_in_sandbox(
            test_command=test_command,
            project_path=workspace_path,
        )

        if result["passed"]:
            self.set_state(AgentState.SUCCESS, "Workspace tests PASSED")
            logger.info("🐳 QA: Workspace tests PASSED")
            return {
                "passed": True,
                "verdict": "QA_PASS",
                "output": result["test_output"],
            }
        else:
            self.set_state(AgentState.ERROR, "Workspace tests FAILED")
            logger.warning("🐳 QA: Workspace tests FAILED")
            return {
                "passed": False,
                "verdict": "QA_FAIL",
                "output": result["error_output"] or result["test_output"],
            }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    qa = QAAgent()
    print(f"QA Agent ready: {qa}")
