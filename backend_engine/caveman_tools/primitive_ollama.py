"""
🪨 primitive_ollama.py — Local Ollama LLM Wrapper
Wraps the Ollama CLI for zero-cost local inference (Tier 3 agents).
"""

import logging
from typing import Optional
from .primitive_bash import run_bash

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama3"
OLLAMA_TIMEOUT = 120  # seconds — local inference can be slow


def run_prompt(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system: Optional[str] = None,
    timeout: int = OLLAMA_TIMEOUT,
) -> dict:
    """
    Sends a prompt to a local Ollama model and returns the raw response.
    
    Args:
        prompt: The user prompt to send.
        model: Ollama model name (e.g., 'llama3', 'qwen2.5-coder').
        system: Optional system prompt.
        timeout: Max seconds for inference.
    
    Returns:
        dict with success, response text, and metadata
    """
    logger.info("🦙 Ollama [%s]: prompt=%s...", model, prompt[:60])

    # Escape quotes in the prompt for shell safety
    escaped_prompt = prompt.replace('"', '\\"').replace("'", "'\\''")
    
    if system:
        escaped_system = system.replace('"', '\\"').replace("'", "'\\''")
        cmd = f'echo "{escaped_prompt}" | ollama run {model} --system "{escaped_system}"'
    else:
        cmd = f'echo "{escaped_prompt}" | ollama run {model}'

    result = run_bash(cmd, timeout=timeout)

    if result["success"]:
        logger.info("🦙 Ollama ✅ Response received (%d chars).", len(result["stdout"]))
        return {
            "success": True,
            "response": result["stdout"],
            "model": model,
            "timed_out": False,
        }
    else:
        logger.warning("🦙 Ollama ⚠️ Error: %s", result["stderr"][:200])
        return {
            "success": False,
            "response": None,
            "model": model,
            "error": result["stderr"],
            "timed_out": result.get("timed_out", False),
        }


def list_models() -> list[str]:
    """List all locally available Ollama models."""
    result = run_bash("ollama list", timeout=10)
    if result["success"]:
        lines = result["stdout"].strip().split("\n")
        # Skip header row, extract model names
        models = [line.split()[0] for line in lines[1:] if line.strip()]
        return models
    return []


def pull_model(model: str) -> dict:
    """Pull/download a model to the local Ollama instance."""
    logger.info("🦙 Pulling model: %s", model)
    return run_bash(f"ollama pull {model}", timeout=600)  # Can take a while


def check_ollama_available() -> bool:
    """Verify Ollama is running locally."""
    result = run_bash("ollama list", timeout=10)
    if result["success"]:
        logger.info("🦙 Ollama is available.")
        return True
    else:
        logger.error("🦙 Ollama is NOT available: %s", result["stderr"][:200])
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if check_ollama_available():
        models = list_models()
        print(f"Available models: {models}")
    else:
        print("⚠️ Ollama not running.")
