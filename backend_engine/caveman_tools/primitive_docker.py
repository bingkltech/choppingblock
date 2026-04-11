"""
🪨 primitive_docker.py — Docker Sandbox Runner
Spins up ephemeral containers for QA testing, captures logs, and destroys them.
"""

import logging
from typing import Optional
from .primitive_bash import run_bash

logger = logging.getLogger(__name__)

DEFAULT_IMAGE = "python:3.11-slim"
DOCKER_TIMEOUT = 120  # seconds


def run_in_container(
    command: str,
    image: str = DEFAULT_IMAGE,
    workdir: str = "/workspace",
    mount_path: Optional[str] = None,
    timeout: int = DOCKER_TIMEOUT,
) -> dict:
    """
    Spins up an ephemeral Docker container, runs a command, captures output, and destroys it.
    
    Args:
        command: The bash command to run inside the container.
        image: Docker image to use (default: python:3.11-slim).
        workdir: Working directory inside the container.
        mount_path: Optional host path to mount at /workspace.
        timeout: Max seconds for the container to run.
    
    Returns:
        dict with success, stdout, stderr, return_code
    """
    logger.info("🐳 Docker sandbox: image=%s, cmd=%s", image, command[:80])

    mount_flag = f'-v "{mount_path}:{workdir}"' if mount_path else ""
    
    docker_cmd = (
        f"docker run --rm {mount_flag} -w {workdir} "
        f"--network none "  # No network access for security
        f"--memory 512m "   # Memory limit
        f"--cpus 1.0 "      # CPU limit
        f"{image} "
        f'bash -c "{command}"'
    )

    result = run_bash(docker_cmd, timeout=timeout)

    if result["success"]:
        logger.info("🐳 Docker ✅ Container exited cleanly.")
    else:
        logger.warning("🐳 Docker ⚠️ Container exit code: %s", result["return_code"])

    return result


def run_tests_in_sandbox(
    test_command: str = "python -m pytest -v",
    project_path: Optional[str] = None,
    image: str = DEFAULT_IMAGE,
) -> dict:
    """
    Convenience function: mount a project into a container and run its test suite.
    Returns structured test results.
    """
    logger.info("🧪 Running tests in Docker sandbox...")

    # Install deps then run tests
    full_command = (
        "pip install -r requirements.txt 2>/dev/null; "
        f"{test_command}"
    )

    result = run_in_container(
        command=full_command,
        image=image,
        mount_path=project_path,
        timeout=DOCKER_TIMEOUT,
    )

    return {
        "passed": result["success"],
        "test_output": result["stdout"],
        "error_output": result["stderr"],
        "timed_out": result.get("timed_out", False),
    }


def check_docker_available() -> bool:
    """Verify Docker is running and accessible."""
    result = run_bash("docker info", timeout=10)
    if result["success"]:
        logger.info("🐳 Docker is available.")
        return True
    else:
        logger.error("🐳 Docker is NOT available: %s", result["stderr"][:200])
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if check_docker_available():
        result = run_in_container("echo 'Hello from the sandbox!'")
        print(result)
    else:
        print("⚠️ Docker not running.")
