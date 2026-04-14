"""
⚙️ config.py — Centralized Configuration
All constants, timeouts, URLs, and defaults live here.
Reads from environment variables (.env) with sensible fallbacks.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (one level above backend_engine)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)

# ==========================================
# 🌐 SERVER
# ==========================================
BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
BACKEND_URL = f"http://localhost:{BACKEND_PORT}"

# ==========================================
# 🦙 OLLAMA (Local Inference)
# ==========================================
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))
DEFAULT_OLLAMA_MODEL = os.getenv("DEFAULT_OLLAMA_MODEL", "qwen3.5:9b")

# ==========================================
# 👑 GOD AGENT / WATCHDOG
# ==========================================
GOD_MAX_RESTARTS = int(os.getenv("GOD_MAX_RESTARTS", "10"))
GOD_RESTART_COOLDOWN = int(os.getenv("GOD_RESTART_COOLDOWN", "5"))
GOD_CRASH_WINDOW = int(os.getenv("GOD_CRASH_WINDOW", "60"))
GOD_HEALTH_POLL_INTERVAL = int(os.getenv("GOD_HEALTH_POLL_INTERVAL", "60"))
GOD_STALE_THRESHOLD = int(os.getenv("GOD_STALE_THRESHOLD", "120"))

# ==========================================
# 🔮 JULES (Cloud Labor)
# ==========================================
JULES_MAX_CONCURRENT = int(os.getenv("JULES_MAX_CONCURRENT", "3"))

# ==========================================
# 🔀 SHIFT MODE
# ==========================================
DEFAULT_SHIFT_MODE = os.getenv("DEFAULT_SHIFT_MODE", "BOSS")

# ==========================================
# 📁 PATHS
# ==========================================
PROJECT_ROOT = str(_PROJECT_ROOT)
BACKEND_DIR = str(Path(__file__).resolve().parent)
SHARED_WORKSPACE = str(Path(BACKEND_DIR) / "shared_workspace")
CRASH_LOGS_DIR = str(Path(BACKEND_DIR) / "crash_logs")
DATABASE_DIR = str(Path(BACKEND_DIR) / "database")
