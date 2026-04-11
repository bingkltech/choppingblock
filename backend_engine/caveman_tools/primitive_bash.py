"""
🪨 primitive_bash.py — Sandboxed Terminal Execution
Runs shell commands via subprocess with strict timeout protection.
"""

import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30  # seconds


def run_bash(
    command: str,
    timeout: int = DEFAULT_TIMEOUT,
    cwd: Optional[str] = None,
    shell: bool = True,
) -> dict:
    """
    Executes a bash/shell command in a sandboxed subprocess.
    
    Args:
        command: The shell command string to execute.
        timeout: Max seconds before killing the process (prevents OS freeze).
        cwd: Working directory for the command.
        shell: Whether to run through shell interpreter.
    
    Returns:
        dict with keys: success, stdout, stderr, return_code, timed_out
    """
    logger.info("🪨 BASH > %s (timeout=%ds)", command, timeout)

    try:
        result = subprocess.run(
            command,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )

        output = {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "return_code": result.returncode,
            "timed_out": False,
        }

        if result.returncode == 0:
            logger.info("🪨 BASH ✅ Return code 0")
        else:
            logger.warning("🪨 BASH ⚠️ Return code %d: %s", result.returncode, result.stderr[:200])

        return output

    except subprocess.TimeoutExpired:
        logger.error("🪨 BASH ⏱️ TIMEOUT after %ds: %s", timeout, command)
        return {
            "success": False,
            "stdout": "",
            "stderr": f"TIMEOUT: Command exceeded {timeout}s limit.",
            "return_code": -1,
            "timed_out": True,
        }
    except Exception as e:
        logger.error("🪨 BASH 🔴 EXCEPTION: %s", str(e))
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "return_code": -1,
            "timed_out": False,
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run_bash("echo Hello from the Caveman Primitive", timeout=5))
