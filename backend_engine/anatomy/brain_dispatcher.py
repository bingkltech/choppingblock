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


def query_ollama(prompt: str, system: str = "", model: str = "", timeout: int = 0, url_override: str = None) -> Optional[str]:
    """
    Query local or cloud Ollama via HTTP API. Returns the model's text response.
    """
    model = model or DEFAULT_OLLAMA_MODEL
    timeout = timeout or OLLAMA_TIMEOUT
    endpoint = url_override or OLLAMA_URL
    try:
        resp = requests.post(
            endpoint,
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
        logger.error("BRAIN: Ollama not reachable at %s", endpoint)
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
    Query Google Gemini via REST API. Uses the API Vault for key rotation and rate-limit handling.
    """
    from anatomy.api_vault import get_gemini_key, report_gemini_429
    
    timeout = timeout or OLLAMA_TIMEOUT
    max_retries = 3
    retries = 0

    while retries < max_retries:
        current_key = api_key or get_gemini_key() or os.environ.get("GOOGLE_API_KEY", "")
        
        if not current_key:
            logger.error("BRAIN: No Gemini API key available in Vault or Environment")
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={current_key}"
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
            
            if resp.status_code == 429:
                logger.warning("BRAIN: Hit 429 Rate Limit for Gemini. Reporting to Vault and retrying...")
                report_gemini_429(current_key)
                retries += 1
                api_key = "" # Clear override to force vault next key
                continue
                
            resp.raise_for_status()
            data = resp.json()
            return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            
        except requests.exceptions.ConnectionError:
            logger.error("BRAIN: Gemini API unreachable")
            return None
        except requests.exceptions.Timeout:
            logger.error("BRAIN: Gemini API timed out after %ds", timeout)
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                report_gemini_429(current_key)
                retries += 1
                api_key = ""
                continue
            logger.error("BRAIN: Gemini query HTTP error: %s", str(e))
            return None
        except Exception as e:
            logger.error("BRAIN: Gemini query failed: %s", str(e))
            return None
            
    logger.error("BRAIN: Failed to get successful Gemini response after %d retries.", max_retries)
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
