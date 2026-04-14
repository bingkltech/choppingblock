"""
🧠 brain_dispatcher.py — Shared Multi-Provider LLM Dispatcher

Routes prompts to the correct AI provider based on model name prefix:
- "gemini-*"     → Google Gemini REST API
- "claude-*"     → Anthropic Claude (stub → falls back to Ollama)
- "ollama:default"  → Default Ollama model
- anything else  → Ollama (treat as model name)

Used by both the God Agent and CEO Agent.
"""

import os
import re
import json
import logging
import requests
from typing import Optional

from config import OLLAMA_URL, OLLAMA_TIMEOUT, DEFAULT_OLLAMA_MODEL

logger = logging.getLogger(__name__)


def query_ollama(prompt: str, system: str = "", model: str = "", timeout: int = 0) -> Optional[str]:
    """
    Query local Ollama via HTTP API. Returns the model's text response.
    """
    model = model or DEFAULT_OLLAMA_MODEL
    timeout = timeout or OLLAMA_TIMEOUT
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "system": system,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 2048,
                },
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "")
    except requests.exceptions.ConnectionError:
        logger.error("BRAIN: Ollama not reachable at %s", OLLAMA_URL)
        return None
    except requests.exceptions.Timeout:
        logger.error("BRAIN: Ollama timed out after %ds", timeout)
        return None
    except Exception as e:
        logger.error("BRAIN: Ollama query failed: %s", str(e))
        return None


def query_gemini(prompt: str, system: str = "", model: str = "gemini-2.5-flash",
                 api_key: str = "", timeout: int = 0) -> Optional[str]:
    """
    Query Google Gemini via REST API. Returns the model's text response.
    """
    if not api_key:
        api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        logger.error("BRAIN: No Gemini API key configured")
        return None

    timeout = timeout or OLLAMA_TIMEOUT
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    try:
        resp = requests.post(
            url,
            json={
                "system_instruction": {"parts": [{"text": system}]},
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048},
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    except requests.exceptions.ConnectionError:
        logger.error("BRAIN: Gemini API unreachable")
        return None
    except requests.exceptions.Timeout:
        logger.error("BRAIN: Gemini API timed out after %ds", timeout)
        return None
    except Exception as e:
        logger.error("BRAIN: Gemini query failed: %s", str(e))
        return None


def query_brain(prompt: str, system: str = "", model: str = "",
                api_key: str = "", timeout: int = 0) -> Optional[str]:
    """
    Dispatcher: routes to the correct provider based on model name prefix.

    Usage:
        response = query_brain("Fix this bug", system=MY_SOUL, model="gemini-2.5-flash", api_key="...")
        response = query_brain("Plan the architecture", system=CEO_SOUL, model="qwen3.5:9b")
    """
    model = model or DEFAULT_OLLAMA_MODEL

    if model.startswith("gemini-"):
        return query_gemini(prompt, system, model, api_key, timeout)
    elif model.startswith("claude-"):
        logger.warning("BRAIN: Claude provider not yet supported — falling back to Ollama")
        return query_ollama(prompt, system, DEFAULT_OLLAMA_MODEL, timeout)
    elif model == "ollama:default":
        return query_ollama(prompt, system, DEFAULT_OLLAMA_MODEL, timeout)
    else:
        # Assume it's an Ollama model name
        return query_ollama(prompt, system, model, timeout)


def extract_json(text: str) -> Optional[dict]:
    """Extract a JSON object from LLM response (handles markdown fences, thinking tags, etc)."""
    if not text:
        return None

    # Strip <think>...</think> blocks (qwen3.5 does this)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

    # Try direct parse first
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON within markdown fences
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find any JSON object with known keys
    match = re.search(r'\{[^{}]*"root_cause"[^{}]*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # Last resort — find anything between { and }
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    return None
