"""
🔐 api_vault.py — API Key Rotation & Load Balancer

Prevents 429 Too Many Requests crashes by pooling available API keys and
round-robining them across concurrent Agency workers. Supports auto-cooldown
for keys that hit quota limits.
"""

import os
import time
import logging
from typing import Optional, List, Dict
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables if not already loaded
load_dotenv()

COOLDOWN_SECONDS = 60

class KeyVault:
    def __init__(self, key_type: str, env_prefix: str):
        self.key_type = key_type
        self.env_prefix = env_prefix
        self.keys: List[str] = []
        self.current_index = 0
        self.cooldowns: Dict[str, float] = {}  # key -> timestamp when cooldown ends
        
        self._load_keys()

    def _load_keys(self):
        """Scans environment variables for keys matching the prefix."""
        # Check for explicit numbered keys (e.g. GEMINI_KEY_1, JULES_API_KEY_1)
        for k, v in os.environ.items():
            if k.startswith(self.env_prefix) and v.strip() and v.strip() != "your_gemini_key_1_here":
                if v not in self.keys:
                    self.keys.append(v)
                    
        # Check for comma-separated lists
        plural_env = f"{self.env_prefix}S"
        if plural_env in os.environ:
            for k in os.environ[plural_env].split(","):
                k = k.strip()
                if k and k not in self.keys:
                    self.keys.append(k)

        # Fallback to singular key without underscore prefix
        singular_fallback = self.env_prefix.rstrip("_")
        if singular_fallback in os.environ and os.environ[singular_fallback].strip():
            k = os.environ[singular_fallback].strip()
            if k not in self.keys:
                self.keys.append(k)

        logger.info("🔐 %s Vault initialized with %d keys.", self.key_type, len(self.keys))

    def get_key(self) -> Optional[str]:
        """Returns the next available key, skipping those in cooldown."""
        if not self.keys:
            return None

        now = time.time()
        attempts = 0
        max_attempts = len(self.keys)

        while attempts < max_attempts:
            key = self.keys[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.keys)
            
            # Check cooldown
            cooldown_end = self.cooldowns.get(key, 0)
            if now >= cooldown_end:
                return key
            
            attempts += 1
            
        logger.warning("🔐 ALL %s keys are currently in cooldown! Returning default anyway to try our luck.", self.key_type)
        # If all in cooldown, just return the first one and hope for the best
        return self.keys[0]

    def report_429(self, key: str):
        """Marks a key as exhausted/rate-limited for 60 seconds."""
        if key in self.keys:
            logger.warning("🔐 %s Key ending in %s hit 429 Rate Limit. Initiating 60s cooldown.", self.key_type, key[-4:] if len(key)>4 else "****")
            self.cooldowns[key] = time.time() + COOLDOWN_SECONDS


class APIVaultManager:
    """Singleton manager for all API vaults."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(APIVaultManager, cls).__new__(cls)
            cls._instance.gemini_vault = KeyVault("Gemini", "GEMINI_KEY_")
            cls._instance.jules_vault = KeyVault("Jules", "JULES_API_KEY_")
            cls._instance.openai_vault = KeyVault("OpenAI", "OPENAI_API_KEY_")
            cls._instance.anthropic_vault = KeyVault("Anthropic", "ANTHROPIC_API_KEY_")
        return cls._instance

# Global Instance
api_vault = APIVaultManager()

def get_gemini_key() -> Optional[str]:
    return api_vault.gemini_vault.get_key()

def report_gemini_429(key: str):
    api_vault.gemini_vault.report_429(key)

def get_jules_key() -> Optional[str]:
    return api_vault.jules_vault.get_key()

def report_jules_429(key: str):
    api_vault.jules_vault.report_429(key)
