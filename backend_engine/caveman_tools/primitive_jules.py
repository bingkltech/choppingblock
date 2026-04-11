"""
🔮 primitive_jules.py — Jules AI Agent API Wrapper
Wraps the Jules REST API (jules.googleapis.com) for dispatching coding tasks,
polling session status, approving plans, and sending follow-up messages.

This is a Caveman Primitive — a pure HTTP wrapper with no agent logic.
The Jules Dispatch Agent decides how and when to call these functions.
"""

import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

JULES_BASE_URL = "https://jules.googleapis.com/v1alpha"
JULES_TIMEOUT = 60  # seconds — Jules clones repos server-side, can be slow


def _jules_headers(api_key: str) -> dict:
    """Build standard headers for Jules API requests."""
    return {
        "X-Goog-Api-Key": api_key,
        "Content-Type": "application/json",
    }


def _mask_key(api_key: str) -> str:
    """Mask API key for safe logging (show last 4 chars only)."""
    if len(api_key) > 4:
        return f"***{api_key[-4:]}"
    return "****"


def _safe_request(method: str, url: str, api_key: str, **kwargs) -> dict:
    """
    Centralized HTTP request handler with error normalization.
    Returns: {"success": bool, "data": dict|None, "error": str|None, "status_code": int|None}
    """
    try:
        resp = requests.request(
            method, url,
            headers=_jules_headers(api_key),
            timeout=kwargs.pop("timeout", JULES_TIMEOUT),
            **kwargs,
        )
        resp.raise_for_status()
        data = resp.json() if resp.content else {}
        return {"success": True, "data": data, "error": None, "status_code": resp.status_code}

    except requests.exceptions.ConnectionError:
        logger.error("🔮 JULES: Connection failed to %s", url)
        return {"success": False, "data": None, "error": "Connection failed — is the API reachable?", "status_code": None}

    except requests.exceptions.Timeout:
        logger.error("🔮 JULES: Request timed out after %ds to %s", JULES_TIMEOUT, url)
        return {"success": False, "data": None, "error": f"Timeout after {JULES_TIMEOUT}s", "status_code": None}

    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else None
        body = ""
        try:
            body = e.response.json().get("error", {}).get("message", str(e)) if e.response else str(e)
        except Exception:
            body = e.response.text[:500] if e.response else str(e)
        logger.error("🔮 JULES: HTTP %s — %s", status, body)
        return {"success": False, "data": None, "error": f"HTTP {status}: {body}", "status_code": status}

    except Exception as e:
        logger.error("🔮 JULES: Unexpected error — %s", str(e))
        return {"success": False, "data": None, "error": str(e), "status_code": None}


# ==========================================
# 🔮 CORE API FUNCTIONS
# ==========================================

def create_session(
    api_key: str,
    prompt: str,
    repo_owner: str,
    repo_name: str,
    branch: str = "main",
    title: str = "",
    require_plan_approval: bool = True,
    automation_mode: str = "AUTO_CREATE_PR",
) -> dict:
    """
    Create a new Jules coding session.

    POST https://jules.googleapis.com/v1alpha/sessions

    Args:
        api_key: Jules API key from jules.google settings.
        prompt: The coding task description.
        repo_owner: GitHub repository owner.
        repo_name: GitHub repository name.
        branch: Starting branch (default: main).
        title: Session title (auto-generated if empty).
        require_plan_approval: If True, Jules waits for plan approval before executing.
        automation_mode: AUTO_CREATE_PR to auto-open a PR when done.

    Returns:
        {"success": bool, "session_id": str|None, "status": str, "raw": dict|None, "error": str|None}
    """
    if not title:
        title = prompt[:80] + ("..." if len(prompt) > 80 else "")

    source = f"sources/github/{repo_owner}/{repo_name}"

    logger.info("🔮 JULES > Creating session for %s/%s (branch: %s, key: %s)",
                repo_owner, repo_name, branch, _mask_key(api_key))
    logger.info("🔮 JULES > Prompt: %s", prompt[:120])

    body = {
        "prompt": prompt,
        "title": title,
        "sourceContext": {
            "source": source,
            "githubRepoContext": {
                "startingBranch": branch,
            },
        },
        "requirePlanApproval": require_plan_approval,
        "automationMode": automation_mode,
    }

    result = _safe_request("POST", f"{JULES_BASE_URL}/sessions", api_key, json=body)

    if result["success"]:
        data = result["data"]
        session_id = data.get("name", data.get("sessionId", ""))
        status = data.get("state", data.get("status", "CREATED"))
        logger.info("🔮 JULES ✅ Session created: %s (status: %s)", session_id, status)
        return {
            "success": True,
            "session_id": session_id,
            "status": status,
            "raw": data,
            "error": None,
        }
    else:
        return {
            "success": False,
            "session_id": None,
            "status": "FAILED",
            "raw": None,
            "error": result["error"],
        }


def get_session(api_key: str, session_id: str) -> dict:
    """
    Get the current status of a Jules session.

    GET https://jules.googleapis.com/v1alpha/sessions/{session_id}

    Returns:
        {"success": bool, "session_id": str, "status": str, "raw": dict|None, "error": str|None}
    """
    logger.info("🔮 JULES > Checking session: %s", session_id)

    result = _safe_request("GET", f"{JULES_BASE_URL}/sessions/{session_id}", api_key)

    if result["success"]:
        data = result["data"]
        status = data.get("state", data.get("status", "UNKNOWN"))
        pr_url = None

        # Try to extract PR URL from session data
        outputs = data.get("outputs", {})
        if isinstance(outputs, dict):
            pr_url = outputs.get("pullRequestUrl", outputs.get("prUrl"))

        logger.info("🔮 JULES > Session %s: %s", session_id, status)
        return {
            "success": True,
            "session_id": session_id,
            "status": status,
            "pr_url": pr_url,
            "raw": data,
            "error": None,
        }
    else:
        return {
            "success": False,
            "session_id": session_id,
            "status": "ERROR",
            "pr_url": None,
            "raw": None,
            "error": result["error"],
        }


def list_sessions(api_key: str, limit: int = 20) -> dict:
    """
    List recent Jules sessions.

    GET https://jules.googleapis.com/v1alpha/sessions

    Returns:
        {"success": bool, "sessions": list[dict], "error": str|None}
    """
    logger.info("🔮 JULES > Listing sessions (limit: %d)", limit)

    result = _safe_request(
        "GET", f"{JULES_BASE_URL}/sessions",
        api_key, params={"pageSize": limit}
    )

    if result["success"]:
        sessions = result["data"].get("sessions", [])
        logger.info("🔮 JULES > Found %d sessions", len(sessions))
        return {"success": True, "sessions": sessions, "error": None}
    else:
        return {"success": False, "sessions": [], "error": result["error"]}


def approve_plan(api_key: str, session_id: str) -> dict:
    """
    Approve a pending plan for a session (when requirePlanApproval=True).

    Returns:
        {"success": bool, "error": str|None}
    """
    logger.info("🔮 JULES > Approving plan for session: %s", session_id)

    result = _safe_request(
        "POST",
        f"{JULES_BASE_URL}/sessions/{session_id}:approvePlan",
        api_key,
    )

    if result["success"]:
        logger.info("🔮 JULES ✅ Plan approved for session: %s", session_id)
    return result


def send_message(api_key: str, session_id: str, message: str) -> dict:
    """
    Send a follow-up message to an active session.
    Used for the QA verification loop: send error logs back to Jules.

    Returns:
        {"success": bool, "error": str|None}
    """
    logger.info("🔮 JULES > Sending message to session %s: %s", session_id, message[:80])

    result = _safe_request(
        "POST",
        f"{JULES_BASE_URL}/sessions/{session_id}:sendMessage",
        api_key,
        json={"message": message},
    )

    if result["success"]:
        logger.info("🔮 JULES ✅ Message sent to session: %s", session_id)
    return result


# ==========================================
# 🧪 STANDALONE TEST
# ==========================================

if __name__ == "__main__":
    import os

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    api_key = os.getenv("JULES_API_KEY", "")
    if not api_key:
        print("\n[WARN] JULES_API_KEY not set. Testing with mock connectivity check.\n")
        # Test that the HTTP machinery works (expect auth failure)
        result = create_session(
            api_key="INVALID_KEY_FOR_TEST",
            prompt="Test prompt",
            repo_owner="test",
            repo_name="test-repo",
        )
        print(f"Expected failure result: {result}")
    else:
        print(f"\n[OK] JULES_API_KEY found (key: {_mask_key(api_key)})")

        # List existing sessions
        sessions = list_sessions(api_key, limit=5)
        print(f"\nSessions: {sessions}")
