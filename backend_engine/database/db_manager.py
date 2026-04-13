"""
🗄️ db_manager.py — The Ledger
SQLite database manager for tracking API usage across 5 Jules accounts
and real-time agent status for the Visual HQ dashboard.
"""

import sqlite3
import os
import logging
from datetime import datetime, date
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "ledger.db")


def get_connection() -> sqlite3.Connection:
    """Returns a connection to the ledger database with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_database() -> None:
    """Creates all tables if they don't exist. Safe to call on every boot."""
    conn = get_connection()
    cursor = conn.cursor()

    # --- Table 1: API Usage Tracker (Tier 2 Cloud Labor) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS API_Usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT NOT NULL UNIQUE,
            api_key_env_var TEXT NOT NULL,
            tokens_used_today INTEGER DEFAULT 0,
            requests_today INTEGER DEFAULT 0,
            last_request_at TEXT,
            last_reset_date TEXT,
            status TEXT DEFAULT 'IDLE',
            api_key_override TEXT DEFAULT '',
            model_provider TEXT DEFAULT 'gemini-1.5-pro',
            github_pat_override TEXT DEFAULT ''
        )
    """)

    # Safe alter for migrations (in case DB already exists)
    for col, ctype, default in [
        ("api_key_override", "TEXT", "''"),
        ("model_provider", "TEXT", "'gemini-1.5-pro'"),
        ("github_pat_override", "TEXT", "''")
    ]:
        try:
            cursor.execute(f"ALTER TABLE API_Usage ADD COLUMN {col} {ctype} DEFAULT {default}")
        except sqlite3.OperationalError:
            pass  # Column already exists

    # --- Table 2: Agent Status (All Tiers) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Agent_Status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL UNIQUE,
            agent_name TEXT NOT NULL,
            tier INTEGER NOT NULL,
            brain_model TEXT,
            current_task TEXT DEFAULT 'Idle',
            state TEXT DEFAULT 'IDLE',
            health_pct REAL DEFAULT 100.0,
            language TEXT DEFAULT 'Python',
            last_heartbeat TEXT,
            equipped_tools TEXT DEFAULT '[]',
            error_log TEXT
        )
    """)

    # --- Table 3: Activity Log (for the Activity Feed panel) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Activity_Log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            message TEXT NOT NULL,
            severity TEXT DEFAULT 'INFO'
        )
    """)

    # --- Table 4: Projects (for the Active Projects panel) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            status TEXT DEFAULT 'Planning',
            language TEXT DEFAULT 'Python',
            active_agents INTEGER DEFAULT 0,
            current_task TEXT DEFAULT 'Initializing',
            health_pct REAL DEFAULT 100.0,
            pipeline_stage TEXT DEFAULT 'Plan',
            created_at TEXT,
            updated_at TEXT
        )
    """)

    # --- Table 5: Alerts (for Critical Alerts panel) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            agent_id TEXT,
            alert_type TEXT NOT NULL,
            message TEXT NOT NULL,
            resolved INTEGER DEFAULT 0,
            resolved_at TEXT
        )
    """)

    # --- Table 6: Jules Sessions (Dispatched coding tasks) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Jules_Sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL UNIQUE,
            task_prompt TEXT NOT NULL,
            repo_source TEXT NOT NULL,
            branch TEXT DEFAULT 'main',
            status TEXT DEFAULT 'PENDING',
            plan_approved INTEGER DEFAULT 0,
            pr_url TEXT,
            dispatched_at TEXT NOT NULL,
            completed_at TEXT,
            api_key_used TEXT,
            error_log TEXT
        )
    """)

    conn.commit()
    conn.close()
    logger.info("📦 Ledger database initialized at %s", DB_PATH)


# ==========================================
# 📊 API USAGE HELPERS
# ==========================================

def seed_jules_accounts() -> None:
    """Seeds the 5 Jules cloud accounts into the API_Usage table."""
    conn = get_connection()
    accounts = [
        ("jules_account_1", "JULES_KEY_1"),
        ("jules_account_2", "JULES_KEY_2"),
        ("jules_account_3", "JULES_KEY_3"),
        ("jules_account_4", "JULES_KEY_4"),
        ("jules_account_5", "JULES_KEY_5"),
    ]
    today = str(date.today())
    account_data = [(name, env_var, today) for name, env_var in accounts]
    conn.executemany(
        "INSERT OR IGNORE INTO API_Usage (account_name, api_key_env_var, last_reset_date) VALUES (?, ?, ?)",
        account_data
    )
    conn.commit()
    conn.close()
    logger.info("🌱 Seeded 5 Jules cloud accounts.")


def get_least_used_account() -> Optional[dict]:
    """Returns the Jules account with the lowest token usage today. Resets counters if date has rolled."""
    conn = get_connection()
    today = str(date.today())

    # Reset counters for any account whose last_reset_date is not today
    conn.execute(
        "UPDATE API_Usage SET tokens_used_today = 0, requests_today = 0, last_reset_date = ? WHERE last_reset_date != ?",
        (today, today)
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM API_Usage WHERE status != 'DISABLED' ORDER BY tokens_used_today ASC LIMIT 1"
    ).fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def log_token_usage(account_name: str, tokens_used: int) -> None:
    """Increments token and request counters for a specific Jules account."""
    conn = get_connection()
    conn.execute(
        """UPDATE API_Usage 
           SET tokens_used_today = tokens_used_today + ?, 
               requests_today = requests_today + 1,
               last_request_at = ?,
               status = 'ACTIVE'
           WHERE account_name = ?""",
        (tokens_used, datetime.now().isoformat(), account_name)
    )
    conn.commit()
    conn.close()


def get_all_api_usage() -> list[dict]:
    """Returns the usage stats for all API accounts."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM API_Usage ORDER BY account_name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_api_usage_config(account_name: str, api_key: str, model: str, github_pat: str) -> None:
    """Updates the node-specific configuration for a Jules account."""
    conn = get_connection()
    conn.execute(
        """UPDATE API_Usage 
           SET api_key_override = ?, model_provider = ?, github_pat_override = ?
           WHERE account_name = ?""",
        (api_key, model, github_pat, account_name)
    )
    conn.commit()
    conn.close()
    logger.info("⚙️ Updated configuration for %s", account_name)


# ==========================================
# 🤖 AGENT STATUS HELPERS
# ==========================================

def seed_default_agents() -> None:
    """Seeds the default agent roster into Agent_Status."""
    conn = get_connection()
    agents = [
        ("ceo", "CEO Agent", 1, "claude-sonnet-4-20250514", '["primitive_bash", "primitive_gh"]'),
        ("god", "God Agent", 1, "claude-sonnet-4-20250514", '["primitive_bash", "file_io"]'),
        ("jules_1", "Antigravity (Jules 1)", 2, "gemini-1.5-pro", '["primitive_bash", "primitive_gh"]'),
        ("jules_2", "Cloud Worker (Jules 2)", 2, "gemini-1.5-pro", '["primitive_bash", "primitive_gh"]'),
        ("jules_3", "Cloud Worker (Jules 3)", 2, "gemini-1.5-pro", '["primitive_bash", "primitive_gh"]'),
        ("jules_4", "Cloud Worker (Jules 4)", 2, "gemini-1.5-pro", '["primitive_bash", "primitive_gh"]'),
        ("jules_5", "Cloud Worker (Jules 5)", 2, "gemini-1.5-pro", '["primitive_bash", "primitive_gh"]'),
        ("qa", "QA Agent", 3, "llama3", '["primitive_docker", "primitive_bash"]'),
        ("ops", "Ops Agent", 3, "qwen2.5-coder", '["primitive_gh", "primitive_bash"]'),
    ]
    now = datetime.now().isoformat()
    agent_data = [(a[0], a[1], a[2], a[3], a[4], now) for a in agents]
    conn.executemany(
        """INSERT OR IGNORE INTO Agent_Status
           (agent_id, agent_name, tier, brain_model, equipped_tools, last_heartbeat)
           VALUES (?, ?, ?, ?, ?, ?)""",
        agent_data
    )
    conn.commit()
    conn.close()
    logger.info("🤖 Seeded 9 default agents.")


def update_agent_status(agent_id: str, state: str, current_task: str = None, health_pct: float = None) -> None:
    """Updates the live state of an agent and timestamps the heartbeat."""
    conn = get_connection()
    updates = ["state = ?", "last_heartbeat = ?"]
    params = [state, datetime.now().isoformat()]

    if current_task is not None:
        updates.append("current_task = ?")
        params.append(current_task)
    if health_pct is not None:
        updates.append("health_pct = ?")
        params.append(health_pct)

    params.append(agent_id)
    conn.execute(f"UPDATE Agent_Status SET {', '.join(updates)} WHERE agent_id = ?", params)
    conn.commit()
    conn.close()


def get_all_agents() -> list[dict]:
    """Returns status of all agents for the dashboard."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM Agent_Status ORDER BY tier, agent_name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_agent(agent_id: str) -> Optional[dict]:
    """Returns a single agent's full status."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM Agent_Status WHERE agent_id = ?", (agent_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ==========================================
# 📋 ACTIVITY LOG HELPERS
# ==========================================

def log_activity(agent_id: str, event_type: str, message: str, severity: str = "INFO") -> None:
    """Logs an event to the activity feed."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO Activity_Log (timestamp, agent_id, event_type, message, severity) VALUES (?, ?, ?, ?, ?)",
        (datetime.now().isoformat(), agent_id, event_type, message, severity)
    )
    conn.commit()
    conn.close()


def get_recent_activity(limit: int = 50) -> list[dict]:
    """Returns the most recent activity log entries."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM Activity_Log ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==========================================
# 🏗️ PROJECT HELPERS
# ==========================================

def upsert_project(project_name: str, **kwargs) -> None:
    """Creates or updates a project record."""
    conn = get_connection()
    existing = conn.execute("SELECT id FROM Projects WHERE project_name = ?", (project_name,)).fetchone()

    now = datetime.now().isoformat()
    if existing:
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [now, project_name]
        conn.execute(f"UPDATE Projects SET {sets}, updated_at = ? WHERE project_name = ?", vals)
    else:
        kwargs["project_name"] = project_name
        kwargs["created_at"] = now
        kwargs["updated_at"] = now
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join("?" for _ in kwargs)
        conn.execute(f"INSERT INTO Projects ({cols}) VALUES ({placeholders})", list(kwargs.values()))

    conn.commit()
    conn.close()


def get_all_projects() -> list[dict]:
    """Returns all projects for the dashboard."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM Projects ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==========================================
# 🚨 ALERTS HELPERS
# ==========================================

def create_alert(agent_id: str, alert_type: str, message: str) -> None:
    """Creates a new alert/incident."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO Alerts (timestamp, agent_id, alert_type, message) VALUES (?, ?, ?, ?)",
        (datetime.now().isoformat(), agent_id, alert_type, message)
    )
    conn.commit()
    conn.close()


def get_unresolved_alerts() -> list[dict]:
    """Returns all unresolved alerts."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM Alerts WHERE resolved = 0 ORDER BY timestamp DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def resolve_alert(alert_id: int) -> None:
    """Marks an alert as resolved."""
    conn = get_connection()
    conn.execute(
        "UPDATE Alerts SET resolved = 1, resolved_at = ? WHERE id = ?",
        (datetime.now().isoformat(), alert_id)
    )
    conn.commit()
    conn.close()


# ==========================================
# 🔮 JULES SESSION HELPERS
# ==========================================

def create_jules_session(
    session_id: str, task_prompt: str, repo_source: str,
    branch: str = "main", api_key_used: str = ""
) -> None:
    """Records a newly dispatched Jules session in the ledger."""
    conn = get_connection()
    conn.execute(
        """INSERT OR IGNORE INTO Jules_Sessions
           (session_id, task_prompt, repo_source, branch, status, dispatched_at, api_key_used)
           VALUES (?, ?, ?, ?, 'PENDING', ?, ?)""",
        (session_id, task_prompt, repo_source, branch, datetime.now().isoformat(), api_key_used)
    )
    conn.commit()
    conn.close()
    logger.info("🔮 Recorded Jules session: %s", session_id)


def update_jules_session(
    session_id: str, status: str = None,
    pr_url: str = None, plan_approved: bool = None,
    error_log: str = None, completed: bool = False
) -> None:
    """Updates the status and metadata of a tracked Jules session."""
    conn = get_connection()
    updates = []
    params = []

    if status is not None:
        updates.append("status = ?")
        params.append(status)
    if pr_url is not None:
        updates.append("pr_url = ?")
        params.append(pr_url)
    if plan_approved is not None:
        updates.append("plan_approved = ?")
        params.append(1 if plan_approved else 0)
    if error_log is not None:
        updates.append("error_log = ?")
        params.append(error_log)
    if completed:
        updates.append("completed_at = ?")
        params.append(datetime.now().isoformat())

    if updates:
        params.append(session_id)
        conn.execute(
            f"UPDATE Jules_Sessions SET {', '.join(updates)} WHERE session_id = ?",
            params
        )
        conn.commit()
    conn.close()


def get_jules_session(session_id: str) -> Optional[dict]:
    """Returns a single tracked Jules session."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM Jules_Sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_active_jules_sessions() -> list[dict]:
    """Returns all non-completed Jules sessions."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM Jules_Sessions WHERE status NOT IN ('COMPLETED', 'FAILED') ORDER BY dispatched_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_jules_sessions(limit: int = 50) -> list[dict]:
    """Returns recent Jules sessions for the dashboard."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM Jules_Sessions ORDER BY dispatched_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==========================================
# 🚀 BOOTSTRAP
# ==========================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_database()
    seed_jules_accounts()
    seed_default_agents()
    print("[OK] Ledger database bootstrapped successfully.")
    print(f"   Agents: {len(get_all_agents())}")
    print(f"   Jules Accounts: {len(get_all_api_usage())}")
    print(f"   Jules Sessions: {len(get_all_jules_sessions())}")
