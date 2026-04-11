"""
🪨 primitive_gh.py — GitHub CLI Wrapper
Wraps the `gh` CLI tool for PR management, branch ops, and diff fetching.
"""

import logging
from typing import Optional
from .primitive_bash import run_bash

logger = logging.getLogger(__name__)


def create_branch(branch_name: str, cwd: Optional[str] = None) -> dict:
    """Create and checkout a new branch from main."""
    logger.info("🔀 Creating branch: %s", branch_name)
    run_bash("git checkout main && git pull origin main", cwd=cwd)
    return run_bash(f"git checkout -b {branch_name}", cwd=cwd)


def commit_and_push(message: str, branch_name: str, cwd: Optional[str] = None) -> dict:
    """Stage all changes, commit, and push to remote."""
    logger.info("📤 Committing and pushing: %s", message)
    run_bash("git add -A", cwd=cwd)
    run_bash(f'git commit -m "{message}"', cwd=cwd)
    return run_bash(f"git push origin {branch_name}", cwd=cwd, timeout=60)


def create_pr(title: str, body: str = "", base: str = "main", cwd: Optional[str] = None) -> dict:
    """Open a Pull Request using the gh CLI."""
    logger.info("📋 Creating PR: %s", title)
    body_escaped = body.replace('"', '\\"')
    return run_bash(
        f'gh pr create --title "{title}" --body "{body_escaped}" --base {base}',
        cwd=cwd,
        timeout=30,
    )


def list_prs(state: str = "open", cwd: Optional[str] = None) -> dict:
    """List pull requests."""
    return run_bash(f"gh pr list --state {state} --json number,title,state,url", cwd=cwd)


def get_pr_diff(pr_number: int, cwd: Optional[str] = None) -> dict:
    """Fetch the diff of a specific PR."""
    return run_bash(f"gh pr diff {pr_number}", cwd=cwd, timeout=30)


def merge_pr(pr_number: int, method: str = "squash", cwd: Optional[str] = None) -> dict:
    """Merge a pull request."""
    logger.info("🔀 Merging PR #%d via %s", pr_number, method)
    return run_bash(
        f"gh pr merge {pr_number} --{method} --delete-branch",
        cwd=cwd,
        timeout=30,
    )


def delete_branch(branch_name: str, cwd: Optional[str] = None) -> dict:
    """Delete a local and remote branch."""
    run_bash(f"git branch -d {branch_name}", cwd=cwd)
    return run_bash(f"git push origin --delete {branch_name}", cwd=cwd)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = list_prs()
    print(result)
