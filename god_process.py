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
from datetime import datetime

# Force UTF-8 for Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [GOD] %(message)s"
)
logger = logging.getLogger("god_process")

# ==========================================
# CONFIGURATION
# ==========================================
BACKEND_ENTRY = os.path.join(os.path.dirname(__file__), "backend_engine", "main.py")
MAX_RESTARTS = 10
RESTART_COOLDOWN = 5  # seconds between restarts
CRASH_WINDOW = 60     # if MAX_RESTARTS happen within this window, halt

# ==========================================
# 👑 THE WATCHDOG LOOP
# ==========================================

def run_backend() -> int:
    """Launches the backend as a subprocess and monitors it."""
    logger.info("🚀 Launching backend: %s", BACKEND_ENTRY)

    process = subprocess.Popen(
        [sys.executable, BACKEND_ENTRY],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), "backend_engine"),
    )

    # Stream stdout in real-time
    try:
        while True:
            line = process.stdout.readline()
            if line:
                print(f"[BACKEND] {line.strip()}")
            
            # Check if process has terminated
            retcode = process.poll()
            if retcode is not None:
                # Process has exited — capture remaining stderr
                remaining_stderr = process.stderr.read()
                if remaining_stderr:
                    logger.error("🔴 CRASH DETECTED:\n%s", remaining_stderr)
                    _log_crash(remaining_stderr)
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


def main() -> None:
    """The main watchdog loop with restart logic."""
    print("=" * 60)
    print("👑 GOD PROCESS — PAPERCLIP REBORN WATCHDOG")
    print("=" * 60)

    restart_times: list[float] = []
    restart_count = 0

    while restart_count < MAX_RESTARTS:
        now = time.time()

        # Prune restart times outside the crash window
        restart_times = [t for t in restart_times if now - t < CRASH_WINDOW]

        if len(restart_times) >= MAX_RESTARTS:
            logger.critical(
                "🔴 HALT: %d crashes in %d seconds. Entering safe mode.",
                MAX_RESTARTS, CRASH_WINDOW
            )
            logger.critical("🔴 Manual intervention required. Check crash_logs/")
            break

        exit_code = run_backend()

        if exit_code == 0:
            logger.info("✅ Backend exited cleanly (code 0). Shutting down God Process.")
            break

        restart_count += 1
        restart_times.append(time.time())

        logger.warning(
            "⚠️ Backend crashed (exit code %d). Restart %d/%d in %ds...",
            exit_code, restart_count, MAX_RESTARTS, RESTART_COOLDOWN
        )

        # In the full system, the God Agent would:
        # 1. Read the crash log
        # 2. Analyze the traceback with its Premium LLM brain
        # 3. Patch the offending Python file
        # 4. Then this loop restarts the fixed code

        time.sleep(RESTART_COOLDOWN)

    print("=" * 60)
    print("👑 GOD PROCESS — TERMINATED")
    print("=" * 60)


if __name__ == "__main__":
    main()
