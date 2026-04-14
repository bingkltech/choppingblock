import unittest
import os
import sqlite3
from datetime import datetime
import sys

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import (
    init_database, get_connection, upsert_project,
    update_jules_session, update_agent_status, create_jules_session
)
import database.db_manager as db_manager

class TestDBSecurity(unittest.TestCase):
    def setUp(self):
        # Use a temporary database for testing
        self.original_db_path = db_manager.DB_PATH
        db_manager.DB_PATH = os.path.join(os.path.dirname(db_manager.__file__), "test_ledger.db")
        if os.path.exists(db_manager.DB_PATH):
            os.remove(db_manager.DB_PATH)
        init_database()

    def tearDown(self):
        if os.path.exists(db_manager.DB_PATH):
            os.remove(db_manager.DB_PATH)
        db_manager.DB_PATH = self.original_db_path

    def test_upsert_project_sql_injection(self):
        """Test that malicious keys in upsert_project do not result in SQL injection."""
        project_name = "SecureProject"
        upsert_project(project_name, status="Normal")

        # Malicious injection via key
        malicious_kwargs = {
            "status = 'Injected', language": "Malicious"
        }

        # This should now FAIL to inject, because the key is not in the allowlist.
        upsert_project(project_name, **malicious_kwargs)

        conn = get_connection()
        project = conn.execute("SELECT * FROM Projects WHERE project_name = ?", (project_name,)).fetchone()
        conn.close()

        # After fix, 'status' should still be 'Normal' because the malicious key was filtered out.
        self.assertEqual(project['status'], 'Normal', "Vulnerability should be fixed")

    def test_update_agent_status_functional(self):
        """Test update_agent_status functionality."""
        agent_id = "test_agent"
        # Seed an agent
        conn = get_connection()
        conn.execute(
            "INSERT INTO Agent_Status (agent_id, agent_name, tier) VALUES (?, ?, ?)",
            (agent_id, "Test Agent", 1)
        )
        conn.commit()
        conn.close()

        update_agent_status(agent_id, state="BUSY", current_task="Coding")

        conn = get_connection()
        agent = conn.execute("SELECT * FROM Agent_Status WHERE agent_id = ?", (agent_id,)).fetchone()
        conn.close()

        self.assertEqual(agent['state'], 'BUSY')
        self.assertEqual(agent['current_task'], 'Coding')

    def test_update_jules_session_functional(self):
        """Test update_jules_session functionality."""
        session_id = "test_session"
        create_jules_session(session_id, "task", "repo")

        update_jules_session(session_id, status="COMPLETED", completed=True)

        conn = get_connection()
        session = conn.execute("SELECT * FROM Jules_Sessions WHERE session_id = ?", (session_id,)).fetchone()
        conn.close()

        self.assertEqual(session['status'], 'COMPLETED')
        self.assertIsNotNone(session['completed_at'])

if __name__ == "__main__":
    unittest.main()
