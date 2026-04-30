import os
import sys
import subprocess
import threading
import logging
import signal
import time

logger = logging.getLogger("paperclip.mcp_services")

_mcp_process = None

def start_mcp_servers():
    """Starts the native Skill Seekers MCP server in the background."""
    global _mcp_process
    
    # Check if skill-seekers is installed
    try:
        import skill_seekers
    except ImportError:
        logger.warning("⚠️ skill-seekers is not installed. MCP Server will not start. Run: pip install skill-seekers")
        return
    
    logger.info("🚀 Launching Native MCP Server (Skill Seekers) on port 8765...")
    
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    
    # We use fastmcp via http transport on 8765
    _mcp_process = subprocess.Popen(
        [sys.executable, "-m", "skill_seekers.mcp.server_fastmcp", "--http", "--port", "8765"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env
    )
    
    def monitor_mcp():
        for line in _mcp_process.stdout:
            stripped = line.strip()
            if stripped:
                logger.info("[MCP] %s", stripped)
                
        ret = _mcp_process.wait()
        logger.warning("⚠️ MCP Server terminated with code %s", ret)
        
    t = threading.Thread(target=monitor_mcp, daemon=True)
    t.start()

def stop_mcp_servers():
    """Kills the background MCP server."""
    global _mcp_process
    if _mcp_process and _mcp_process.poll() is None:
        logger.info("🛑 Shutting down Native MCP Server...")
        try:
            if os.name == 'nt':
                _mcp_process.send_signal(signal.CTRL_C_EVENT)
            else:
                _mcp_process.send_signal(signal.SIGTERM)
            try:
                _mcp_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                _mcp_process.kill()
        except Exception as e:
            logger.error("Failed to stop MCP Server cleanly: %s", e)
