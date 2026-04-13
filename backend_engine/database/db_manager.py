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
import json
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

KEY_FILE = os.path.join(os.path.dirname(__file__), ".secret.key")
_FERNET: Optional[Fernet] = None

def get_fernet() -> Fernet:
    global _FERNET
    if _FERNET is None:
        if not os.path.exists(KEY_FILE):
            key = Fernet.generate_key()
            with open(KEY_FILE, "wb") as f:
                f.write(key)
        else:
            with open(KEY_FILE, "rb") as f:
                key = f.read()
        _FERNET = Fernet(key)
    return _FERNET

def encrypt_val(val: str) -> str:
    if not val:
        return ""
    try:
        return get_fernet().encrypt(val.encode('utf-8')).decode('utf-8')
    except Exception:
        return val

def decrypt_val(val: str) -> str:
    if not val:
        return ""
    try:
        return get_fernet().decrypt(val.encode('utf-8')).decode('utf-8')
    except Exception:
        return val

DB_PATH = os.path.join(os.path.dirname(__file__), "ledger.db")


def get_connection() -> sqlite3.Connection:
    """Returns a connection to the ledger database with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _safe_add_columns(cursor, table: str, cols: list) -> None:
    """Idempotently ALTERs a table to add missing columns."""
    for col, ctype, default in cols:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ctype} DEFAULT {default}")
        except Exception:
            pass  # already exists


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
            tier TEXT DEFAULT 'tier3',
            brain_model TEXT,
            role TEXT DEFAULT '',
            current_task TEXT DEFAULT 'Idle',
            state TEXT DEFAULT 'IDLE',
            health_pct REAL DEFAULT 100.0,
            language TEXT DEFAULT 'Python',
            last_heartbeat TEXT,
            equipped_tools TEXT DEFAULT '[]',
            custom_skills TEXT DEFAULT '',
            toolconfigs TEXT DEFAULT '{}',
            api_key TEXT DEFAULT '',
            mcp_endpoints TEXT DEFAULT '',
            terminated INTEGER DEFAULT 0,
            hired_at TEXT,
            terminated_at TEXT,
            error_log TEXT
        )
    """)

    # Safe migrations for any pre-existing DB
    _safe_add_columns(cursor, 'Agent_Status', [
        ('role',          'TEXT',    "''"),
        ('custom_skills', 'TEXT',    "''"),
        ('toolconfigs',   'TEXT',    "'{}'"),
        ('api_key',       'TEXT',    "''"),
        ('mcp_endpoints', 'TEXT',    "''"),
        ('terminated',    'INTEGER', '0'),
        ('hired_at',      'TEXT',    "''"),
        ('terminated_at', 'TEXT',    "''"),
    ])

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

    # --- Table 7: Heal Log (God Agent self-healing audit trail) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Heal_Log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            crash_file TEXT,
            root_cause TEXT,
            patch_applied INTEGER DEFAULT 0,
            rule_written INTEGER DEFAULT 0,
            model_used TEXT,
            raw_response TEXT
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
    """Seeds the default agent roster into Agent_Status (INSERT OR IGNORE — never overwrites custom agents)."""
    import json
    conn = get_connection()
    now = datetime.now().isoformat()
    agents = [
        ("ceo",    "CEO Agent",               "tier1", "claude-3.5-sonnet",  "CEO / Executive Director",  "Strategic planning, delegation, executive oversight", '["bash","github"]'),
        ("god",    "God Agent",               "tier1", "claude-3.5-sonnet",  "System Overseer",           "System monitoring, self-healing, meta-cognition",     '["bash"]'),
        ("jules_1","Antigravity (Jules 1)",   "tier2", "gemini-1.5-pro",     "Cloud Coding Agent",        "Full-Stack Development, API Integration, Code Review", '["jules","github","bash"]'),
        ("jules_2","Cloud Worker (Jules 2)",  "tier2", "gemini-1.5-pro",     "Cloud Coding Agent",        "Full-Stack Development, API Integration",             '["jules","github","bash"]'),
        ("jules_3","Cloud Worker (Jules 3)",  "tier2", "gemini-1.5-pro",     "Cloud Coding Agent",        "Testing, QA, Code Review",                            '["jules","github","bash"]'),
        ("jules_4","Cloud Worker (Jules 4)",  "tier2", "gemini-1.5-pro",     "Cloud Coding Agent",        "DevOps, CI/CD, Docker deployment",                    '["jules","docker","bash"]'),
        ("jules_5","Cloud Worker (Jules 5)",  "tier2", "gemini-1.5-pro",     "Cloud Coding Agent",        "Documentation, Architecture diagrams",                '["jules","browser","bash"]'),
        ("qa",     "QA Agent",                "tier3", "ollama:llama3",      "QA Engineer",               "Testing, Code Review, Linting, Bug Reproduction",     '["docker","bash"]'),
        ("ops",    "Ops Agent",               "tier3", "ollama:qwen2.5-coder","DevOps Engineer",          "CI/CD, GitHub Actions, Docker, Linux Administration", '["github","bash","docker"]'),
    ]
    for (aid, name, tier, brain, role, skills, tools) in agents:
        # Special case: God Agent config from user requirements
        if aid == "god":
            brain = "gemini-3.1-pro"
            skills = "System Overseer, Self-Healing Autonomy, Meta-Cognition, Framework Architect"
            tools = '["bash", "github", "jules", "browser", "docker", "antigravity"]'
            
            conn.execute(
                """INSERT OR IGNORE INTO Agent_Status
                   (agent_id, agent_name, tier, brain_model, role, custom_skills, equipped_tools,
                    toolconfigs, state, hired_at, last_heartbeat)
                   VALUES (?, ?, ?, ?, ?, ?, ?, '{}', 'IDLE', ?, ?)""",
                (aid, name, tier, brain, role, skills, tools, now, now)
            )
        else:
            conn.execute(
                """INSERT OR IGNORE INTO Agent_Status
                   (agent_id, agent_name, tier, brain_model, role, custom_skills, equipped_tools,
                    toolconfigs, state, hired_at, last_heartbeat)
                   VALUES (?, ?, ?, ?, ?, ?, ?, '{}', 'IDLE', ?, ?)""",
                (aid, name, tier, brain, role, skills, tools, now, now)
            )
    conn.commit()
    conn.close()
    logger.info("🤖 Seeded default agents.")


def upsert_agent_profile(agent_id: str, **kwargs) -> None:
    """
    Creates or fully updates an agent's profile in the DB.
    Pass any subset of: agent_name, tier, brain_model, role, custom_skills,
    toolconfigs (dict/str), api_key, mcp_endpoints, equipped_tools, state
    """
    import json
    conn = get_connection()
    now = datetime.now().isoformat()

    # Serialize dicts to JSON strings
    if 'toolconfigs' in kwargs and isinstance(kwargs['toolconfigs'], dict):
        kwargs['toolconfigs'] = encrypt_val(json.dumps(kwargs['toolconfigs']))
    elif 'toolconfigs' in kwargs:
        kwargs['toolconfigs'] = encrypt_val(kwargs['toolconfigs'])
        
    if 'api_key' in kwargs and kwargs['api_key']:
        kwargs['api_key'] = encrypt_val(kwargs['api_key'])

    if 'equipped_tools' in kwargs and isinstance(kwargs['equipped_tools'], list):
        kwargs['equipped_tools'] = json.dumps(kwargs['equipped_tools'])
    if 'equipped_tools' in kwargs and isinstance(kwargs['equipped_tools'], list):
        kwargs['equipped_tools'] = json.dumps(kwargs['equipped_tools'])

    existing = conn.execute(
        "SELECT agent_id FROM Agent_Status WHERE agent_id = ?", (agent_id,)
    ).fetchone()

    if existing:
        sets = ', '.join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [now, agent_id]
        conn.execute(
            f"UPDATE Agent_Status SET {sets}, last_heartbeat = ? WHERE agent_id = ?", vals
        )
    else:
        kwargs['agent_id'] = agent_id
        kwargs.setdefault('hired_at', now)
        kwargs.setdefault('last_heartbeat', now)
        kwargs.setdefault('state', 'IDLE')
        kwargs.setdefault('toolconfigs', '{}')
        kwargs.setdefault('equipped_tools', '[]')
        cols = ', '.join(kwargs.keys())
        placeholders = ', '.join('?' for _ in kwargs)
        conn.execute(
            f"INSERT INTO Agent_Status ({cols}) VALUES ({placeholders})",
            list(kwargs.values())
        )

    conn.commit()
    conn.close()
    logger.info("💾 Upserted agent profile: %s", agent_id)


def terminate_agent(agent_id: str) -> None:
    """Marks agent as terminated. They stay in the DB for audit but won't appear in active roster."""
    if agent_id in ("god", "ceo"):
        logger.warning(f"🚫 Attempt to terminate critical agent {agent_id} blocked.")
        raise ValueError(f"The {agent_id.upper()} Agent is a system-critical executive and cannot be terminated.")

    conn = get_connection()
    conn.execute(
        "UPDATE Agent_Status SET terminated = 1, terminated_at = ?, state = 'TERMINATED' WHERE agent_id = ?",
        (datetime.now().isoformat(), agent_id)
    )
    conn.commit()
    conn.close()
    logger.info("🔴 Agent terminated: %s", agent_id)


def get_god_brain() -> str:
    """Returns the God Agent's configured brain_model from the database.
    Falls back to 'qwen3.5:9b' if not found."""
    conn = get_connection()
    row = conn.execute(
        "SELECT brain_model FROM Agent_Status WHERE agent_id = 'god'"
    ).fetchone()
    conn.close()
    if row and row["brain_model"]:
        return row["brain_model"]
    return "qwen3.5:9b"


def log_heal_action(
    crash_file: str = None,
    root_cause: str = None,
    patch_applied: bool = False,
    rule_written: bool = False,
    model_used: str = None,
    raw_response: str = None,
) -> None:
    """Record a God Agent healing action to the Heal_Log table."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO Heal_Log (timestamp, crash_file, root_cause, patch_applied, rule_written, model_used, raw_response) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            datetime.now().isoformat(),
            crash_file,
            root_cause,
            1 if patch_applied else 0,
            1 if rule_written else 0,
            model_used,
            (raw_response or "")[:2000],  # cap raw response size
        ),
    )
    conn.commit()
    conn.close()
    logger.info("🩺 Heal action logged: %s", root_cause or "unknown")


def get_heal_log(limit: int = 20) -> list[dict]:
    """Returns the most recent healing actions."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM Heal_Log ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_agent_status(agent_id: str, state: str, current_task: str = None, health_pct: float = None) -> None:
    """Updates the live state of an agent and timestamps the heartbeat."""
    conn = get_connection()

    # Securely collect updates into a dictionary
    update_data = {
        "state": state,
        "last_heartbeat": datetime.now().isoformat()
    }

    if current_task is not None:
        update_data["current_task"] = current_task
    if health_pct is not None:
        update_data["health_pct"] = health_pct

    # Security: Columns are hardcoded in the dictionary above,
    # but we still use parameterized values for the update.
    sets = ", ".join(f"{k} = ?" for k in update_data.keys())
    params = list(update_data.values()) + [agent_id]

    conn.execute(f"UPDATE Agent_Status SET {sets} WHERE agent_id = ?", params)
    conn.commit()
    conn.close()


def get_all_agents(include_terminated: bool = False) -> list[dict]:
    """Returns all active agents (excludes terminated unless asked)."""
    import json
    conn = get_connection()
    where = "" if include_terminated else "WHERE terminated = 0 OR terminated IS NULL"
    rows = conn.execute(
        f"SELECT * FROM Agent_Status {where} ORDER BY tier, agent_name"
    ).fetchall()
    conn.close()

    result = []
    for r in rows:
        d = dict(r)
        d['api_key'] = decrypt_val(d.get('api_key', ''))
        # Deserialize JSON blobs back to Python objects
        for field in ('toolconfigs', 'equipped_tools'):
            val = d.get(field) or '{}'
            if field == 'toolconfigs':
                val = decrypt_val(val)
            try:
                d[field] = json.loads(val)
            except Exception:
                d[field] = {} if field == 'toolconfigs' else []
        result.append(d)
    return result


def get_agent(agent_id: str) -> Optional[dict]:
    """Returns a single agent's full profile."""
    import json
    conn = get_connection()
    row = conn.execute("SELECT * FROM Agent_Status WHERE agent_id = ?", (agent_id,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d['api_key'] = decrypt_val(d.get('api_key', ''))
    for field in ('toolconfigs', 'equipped_tools'):
        val = d.get(field) or '{}'
        if field == 'toolconfigs':
            val = decrypt_val(val)
        try:
            d[field] = json.loads(val)
        except Exception:
            d[field] = {} if field == 'toolconfigs' else []
    return d


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

    # Security: Allowlist of valid columns to prevent SQL injection via keys
    allowed_cols = {
        "status", "language", "active_agents", "current_task",
        "health_pct", "pipeline_stage", "created_at", "updated_at"
    }
    filtered_kwargs = {k: v for k, v in kwargs.items() if k in allowed_cols}

    now = datetime.now().isoformat()
    if existing:
        if not filtered_kwargs:
            # Only update updated_at if no other changes
            conn.execute("UPDATE Projects SET updated_at = ? WHERE project_name = ?", (now, project_name))
        else:
            sets = ", ".join(f"{k} = ?" for k in filtered_kwargs)
            vals = list(filtered_kwargs.values()) + [now, project_name]
            conn.execute(f"UPDATE Projects SET {sets}, updated_at = ? WHERE project_name = ?", vals)
    else:
        filtered_kwargs["project_name"] = project_name
        filtered_kwargs["created_at"] = now
        filtered_kwargs["updated_at"] = now
        cols = ", ".join(filtered_kwargs.keys())
        placeholders = ", ".join("?" for _ in filtered_kwargs)
        conn.execute(f"INSERT INTO Projects ({cols}) VALUES ({placeholders})", list(filtered_kwargs.values()))

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

    # Securely collect updates into a dictionary
    update_data = {}
    if status is not None:
        update_data["status"] = status
    if pr_url is not None:
        update_data["pr_url"] = pr_url
    if plan_approved is not None:
        update_data["plan_approved"] = 1 if plan_approved else 0
    if error_log is not None:
        update_data["error_log"] = error_log
    if completed:
        update_data["completed_at"] = datetime.now().isoformat()

    if update_data:
        # Security: Columns are hardcoded in the dictionary above,
        # but we still use parameterized values for the update.
        sets = ", ".join(f"{k} = ?" for k in update_data.keys())
        params = list(update_data.values()) + [session_id]

        conn.execute(
            f"UPDATE Jules_Sessions SET {sets} WHERE session_id = ?",
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
