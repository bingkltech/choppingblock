"""
👑 god_process.py — The Watchdog
Wraps the backend engine. If the AI crashes its own framework, the God Agent
catches the Python traceback, patches the source, and hot-restarts the server.

USAGE: python god_process.py
Never run main.py directly. Always use this wrapper.
"""

import subprocess
import sys
import os
import time
import logging
import threading
import glob
from datetime import datetime

# Force UTF-8 for Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Ensure backend_engine is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend_engine'))


from backend_engine.workforce.executives.god_agent import GodAgent
from backend_engine.config import GOD_MAX_RESTARTS, GOD_RESTART_COOLDOWN, GOD_CRASH_WINDOW, GOD_HEALTH_POLL_INTERVAL, GOD_STALE_THRESHOLD, BACKEND_URL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [GOD] %(message)s"
)
logger = logging.getLogger("god_process")

# ==========================================
# CONFIGURATION (from config.py)
# ==========================================
BACKEND_ENTRY = os.path.join(os.path.dirname(__file__), "backend_engine", "main.py")
MAX_RESTARTS = GOD_MAX_RESTARTS
RESTART_COOLDOWN = GOD_RESTART_COOLDOWN
CRASH_WINDOW = GOD_CRASH_WINDOW

# ==========================================
# 👑 THE WATCHDOG LOOP
# ==========================================

def run_backend() -> int:
    """Launches the backend as a subprocess and monitors it."""
    logger.info("Launching backend: %s", BACKEND_ENTRY)

    # Force UTF-8 I/O on the child process to handle emoji in log output
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    process = subprocess.Popen(
        [sys.executable, "-u", BACKEND_ENTRY],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,   # Merge stderr into stdout to prevent buffer deadlock
        text=True,
        encoding="utf-8",
        errors="replace",           # Never crash on un-encodable chars
        cwd=os.path.dirname(os.path.abspath(__file__)),  # Run from project root
        env=env,
    )

    # Accumulate stderr-like lines for crash detection
    recent_lines: list[str] = []

    # Stream merged output in real-time
    try:
        while True:
            line = process.stdout.readline()
            if line:
                stripped = line.strip()
                try:
                    print(f"[BACKEND] {stripped}")
                except UnicodeEncodeError:
                    print(f"[BACKEND] {stripped.encode('ascii', errors='replace').decode()}")
                # Keep a rolling buffer of recent lines for crash analysis
                recent_lines.append(stripped)
                if len(recent_lines) > 200:
                    recent_lines.pop(0)

            # Check if process has terminated
            retcode = process.poll()
            if retcode is not None:
                # Drain any remaining output
                for remaining in process.stdout:
                    stripped = remaining.strip()
                    if stripped:
                        print(f"[BACKEND] {stripped}")
                        recent_lines.append(stripped)

                if retcode != 0 and recent_lines:
                    crash_text = "\n".join(recent_lines[-50:])
                    logger.error("🔴 CRASH DETECTED:\n%s", crash_text)
                    _log_crash(crash_text)
                return retcode

    except KeyboardInterrupt:
        logger.info("🛑 Keyboard interrupt — shutting down backend.")
        process.terminate()
        process.wait(timeout=10)
        return 0


def _log_crash(stderr: str) -> None:
    """Log the crash traceback to a file for the God Agent to analyze."""
    crash_dir = os.path.join(os.path.dirname(__file__), "backend_engine", "crash_logs")
    os.makedirs(crash_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    crash_file = os.path.join(crash_dir, f"crash_{timestamp}.log")

    with open(crash_file, "w", encoding="utf-8") as f:
        f.write(f"CRASH AT: {datetime.now().isoformat()}\n")
        f.write("=" * 60 + "\n")
        f.write(stderr)

    logger.info("📝 Crash log saved: %s", crash_file)


def _get_latest_crash_log() -> str:
    """Read the most recent crash log file."""
    crash_dir = os.path.join(os.path.dirname(__file__), "backend_engine", "crash_logs")
    logs = sorted(glob.glob(os.path.join(crash_dir, "crash_*.log")), reverse=True)
    if not logs:
        return ""
    try:
        with open(logs[0], "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def _health_poll_loop(god: GodAgent) -> None:
    """Background thread: checks agent heartbeats every 60 seconds."""
    import urllib.request
    import json as _json
    while True:
        time.sleep(GOD_HEALTH_POLL_INTERVAL)
        try:
            # ── Self-heartbeat: keep God Agent marked ALIVE in the dashboard ──
            hb_data = _json.dumps({"state": "IDLE", "current_task": "Watching"}).encode()
            hb_req = urllib.request.Request(
                f"{BACKEND_URL}/api/agents/god",
                data=hb_data,
                headers={"Content-Type": "application/json"},
                method="PATCH",
            )
            urllib.request.urlopen(hb_req, timeout=5)
        except Exception:
            pass  # Backend may still be starting up

        try:
            resp = urllib.request.urlopen(f"{BACKEND_URL}/api/agents", timeout=5)
            data = _json.loads(resp.read().decode())
            agents = data.get("agents", [])
            now = datetime.now()
            for agent in agents:
                hb = agent.get("last_heartbeat")
                if not hb:
                    continue
                try:
                    last = datetime.fromisoformat(hb)
                    age = (now - last).total_seconds()
                    if age > GOD_STALE_THRESHOLD and agent.get("state") not in ("IDLE", "TERMINATED"):
                        logger.warning(
                            "GOD HEALTH: Agent %s heartbeat stale (%ds ago)",
                            agent.get("id"), int(age)
                        )
                        # Post an alert
                        alert_data = _json.dumps({
                            "agent_id": agent.get("id"),
                            "alert_type": "STALE_HEARTBEAT",
                            "message": f"Agent {agent.get('name', agent.get('id'))} heartbeat stale ({int(age)}s)"
                        }).encode()
                        req = urllib.request.Request(
                            f"{BACKEND_URL}/api/alerts",
                            data=alert_data,
                            headers={"Content-Type": "application/json"},
                            method="POST",
                        )
                        urllib.request.urlopen(req, timeout=5)
                except (ValueError, TypeError):
                    pass
        except Exception as e:
            logger.debug("GOD HEALTH: Poll failed (backend may be starting): %s", e)


def main() -> None:
    """The main watchdog loop with restart logic."""
    print("=" * 60)
    print("\U0001f451 GOD PROCESS \u2014 PAPERCLIP REBORN WATCHDOG")
    print("=" * 60)

    # Instantiate the God Agent with its DB-configured brain
    god = GodAgent()
    logger.info("\U0001f451 God Agent online | Brain: %s", god.model)

    # Start the health polling thread (daemon so it dies with main)
    health_thread = threading.Thread(target=_health_poll_loop, args=(god,), daemon=True)
    health_thread.start()
    logger.info("\U0001f4a5 Health polling thread started (60s interval)")

    restart_times: list[float] = []
    restart_count = 0

    while restart_count < MAX_RESTARTS:
        now = time.time()

        # Prune restart times outside the crash window
        restart_times = [t for t in restart_times if now - t < CRASH_WINDOW]

        if len(restart_times) >= MAX_RESTARTS:
            logger.critical(
                "\U0001f534 HALT: %d crashes in %d seconds. Entering safe mode.",
                MAX_RESTARTS, CRASH_WINDOW
            )
            logger.critical("\U0001f534 Manual intervention required. Check crash_logs/")
            break

        exit_code = run_backend()

        if exit_code == 0:
            logger.info("\u2705 Backend exited cleanly (code 0). Shutting down God Process.")
            break

        restart_count += 1
        restart_times.append(time.time())

        logger.warning(
            "\u26a0\ufe0f Backend crashed (exit code %d). Restart %d/%d in %ds...",
            exit_code, restart_count, MAX_RESTARTS, RESTART_COOLDOWN
        )

        # GOD AGENT: Read crash log and attempt self-healing
        crash_text = _get_latest_crash_log()
        if crash_text:
            logger.info("\U0001f451 God Agent analyzing crash...")
            try:
                result = god.heal(crash_text, auto_apply=False)  # BOSS mode by default
                if result.get("success"):
                    logger.info(
                        "\U0001f451 God Agent diagnosis: %s | Fixable: %s",
                        result.get("root_cause", "unknown"),
                        result.get("fixable", result.get("applied", False)),
                    )
                else:
                    logger.warning("\U0001f451 God Agent could not analyze crash: %s", result.get("error"))
            except Exception as e:
                logger.error("\U0001f451 God Agent heal() raised: %s", e)
        else:
            logger.info("\U0001f451 No crash log found to analyze")

        time.sleep(RESTART_COOLDOWN)

    print("=" * 60)
    print("\U0001f451 GOD PROCESS \u2014 TERMINATED")
    print("=" * 60)


if __name__ == "__main__":
    main()

