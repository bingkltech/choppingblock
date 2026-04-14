"""
🧪 test_task_queue.py — Tests for the Task Queue system
Covers the CRUD helpers and state machine transitions.
"""

import unittest
import os
import sys

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database.db_manager as db_manager
from database.db_manager import (
    init_database, get_connection,
    create_task, claim_task, start_task, complete_task,
    fail_task, retry_task, cancel_task,
    get_pending_tasks, get_running_tasks, get_all_tasks,
)


class TestTaskQueue(unittest.TestCase):
    """Tests the Task Queue CRUD helpers and state machine."""

    @classmethod
    def setUpClass(cls):
        """Create test DB once for all tests."""
        cls.original_db_path = db_manager.DB_PATH
        db_manager.DB_PATH = os.path.join(os.path.dirname(db_manager.DB_PATH), "test_task_queue.db")
        # Remove stale test DB
        for ext in ['', '-wal', '-shm']:
            p = db_manager.DB_PATH + ext
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
        init_database()

    @classmethod
    def tearDownClass(cls):
        """Clean up test DB after all tests."""
        db_manager.DB_PATH = cls.original_db_path

    def setUp(self):
        """Wipe Task_Queue between tests with retry for locked DB."""
        import time
        for attempt in range(5):
            try:
                conn = get_connection()
                conn.execute("DELETE FROM Task_Queue")
                conn.commit()
                conn.close()
                return
            except Exception:
                time.sleep(0.1)

    # ── CREATE ──

    def test_create_task(self):
        """Tasks are created with PENDING status and correct fields."""
        task = create_task("t1", "CODE", "Build user API", priority=3)
        self.assertEqual(task["task_id"], "t1")
        self.assertEqual(task["task_type"], "CODE")
        self.assertEqual(task["status"], "PENDING")
        self.assertEqual(task["priority"], 3)
        self.assertIsNone(task["assigned_agent"])

    def test_create_duplicate_fails(self):
        """Duplicate task_id raises an error."""
        create_task("dup", "CODE", "First")
        with self.assertRaises(Exception):
            create_task("dup", "CODE", "Second")

    # ── CLAIM ──

    def test_claim_task(self):
        """Claiming a PENDING task assigns it to an agent."""
        create_task("c1", "TEST_PR", "Test things")
        self.assertTrue(claim_task("c1", "qa"))

        conn = get_connection()
        row = conn.execute("SELECT * FROM Task_Queue WHERE task_id = 'c1'").fetchone()
        conn.close()
        self.assertEqual(row["status"], "ASSIGNED")
        self.assertEqual(row["assigned_agent"], "qa")
        self.assertIsNotNone(row["started_at"])

    def test_claim_non_pending_fails(self):
        """Can't claim a task that isn't PENDING."""
        create_task("c2", "CODE", "Already claimed")
        claim_task("c2", "qa")
        # Second claim should fail (already ASSIGNED)
        self.assertFalse(claim_task("c2", "ops"))

    # ── START ──

    def test_start_task(self):
        """Starting an ASSIGNED task moves it to RUNNING."""
        create_task("s1", "MERGE_PR", "Merge it")
        claim_task("s1", "ops")
        self.assertTrue(start_task("s1"))

        conn = get_connection()
        row = conn.execute("SELECT status FROM Task_Queue WHERE task_id = 's1'").fetchone()
        conn.close()
        self.assertEqual(row["status"], "RUNNING")

    # ── COMPLETE ──

    def test_complete_task(self):
        """Completing a RUNNING task marks it DONE."""
        create_task("d1", "CODE", "Done task")
        claim_task("d1", "jules_dispatch")
        start_task("d1")
        self.assertTrue(complete_task("d1", '{"result": "success"}'))

        conn = get_connection()
        row = conn.execute("SELECT * FROM Task_Queue WHERE task_id = 'd1'").fetchone()
        conn.close()
        self.assertEqual(row["status"], "DONE")
        self.assertIn("success", row["output_data"])
        self.assertIsNotNone(row["completed_at"])

    # ── FAIL + RETRY ──

    def test_fail_task(self):
        """Failing a task increments retry_count."""
        create_task("f1", "CODE", "Failing task")
        claim_task("f1", "jules_dispatch")
        start_task("f1")
        self.assertTrue(fail_task("f1", "Connection timeout"))

        conn = get_connection()
        row = conn.execute("SELECT * FROM Task_Queue WHERE task_id = 'f1'").fetchone()
        conn.close()
        self.assertEqual(row["status"], "FAILED")
        self.assertEqual(row["retry_count"], 1)

    def test_retry_task(self):
        """Failed task can be retried if under max_retries."""
        create_task("r1", "CODE", "Retryable")
        claim_task("r1", "jules_dispatch")
        start_task("r1")
        fail_task("r1", "Transient error")

        self.assertTrue(retry_task("r1"))

        conn = get_connection()
        row = conn.execute("SELECT * FROM Task_Queue WHERE task_id = 'r1'").fetchone()
        conn.close()
        self.assertEqual(row["status"], "PENDING")
        self.assertIsNone(row["assigned_agent"])

    def test_retry_exhausted(self):
        """Task that exceeded max_retries cannot be retried."""
        create_task("r2", "CODE", "Exhausted", input_data='{}')
        # Fail it twice (max_retries defaults to 2)
        claim_task("r2", "qa")
        fail_task("r2", "err1")
        retry_task("r2")
        claim_task("r2", "qa")
        fail_task("r2", "err2")

        # Third retry should fail
        self.assertFalse(retry_task("r2"))

    # ── CANCEL ──

    def test_cancel_pending(self):
        """PENDING tasks can be cancelled."""
        create_task("x1", "CODE", "Cancel me")
        self.assertTrue(cancel_task("x1"))

        conn = get_connection()
        row = conn.execute("SELECT status FROM Task_Queue WHERE task_id = 'x1'").fetchone()
        conn.close()
        self.assertEqual(row["status"], "CANCELLED")

    def test_cancel_running_fails(self):
        """RUNNING tasks cannot be cancelled."""
        create_task("x2", "CODE", "Already running")
        claim_task("x2", "qa")
        start_task("x2")
        self.assertFalse(cancel_task("x2"))

    # ── QUERIES ──

    def test_get_pending_tasks(self):
        """Pending tasks are returned sorted by priority."""
        create_task("p1", "CODE", "Low", priority=9)
        create_task("p2", "CODE", "High", priority=1)
        create_task("p3", "CODE", "Medium", priority=5)

        pending = get_pending_tasks()
        self.assertEqual(len(pending), 3)
        self.assertEqual(pending[0]["task_id"], "p2")  # High priority first
        self.assertEqual(pending[2]["task_id"], "p1")  # Low priority last

    def test_get_running_tasks(self):
        """Running tasks query returns only ASSIGNED and RUNNING."""
        create_task("q1", "CODE", "Pending stays out")
        create_task("q2", "CODE", "Is running")
        claim_task("q2", "qa")

        running = get_running_tasks()
        self.assertEqual(len(running), 1)
        self.assertEqual(running[0]["task_id"], "q2")


class TestBrainDispatcher(unittest.TestCase):
    """Test the brain dispatcher routing logic (without live API calls)."""

    def test_extract_json_direct(self):
        from anatomy.brain_dispatcher import extract_json

        result = extract_json('{"root_cause": "missing import", "fixable": true}')
        self.assertIsNotNone(result)
        self.assertEqual(result["root_cause"], "missing import")

    def test_extract_json_markdown_fenced(self):
        from anatomy.brain_dispatcher import extract_json

        text = '```json\n{"root_cause": "typo", "fixable": true}\n```'
        result = extract_json(text)
        self.assertIsNotNone(result)
        self.assertEqual(result["root_cause"], "typo")

    def test_extract_json_with_think_tags(self):
        from anatomy.brain_dispatcher import extract_json

        text = '<think>Let me analyze this...</think>\n{"root_cause": "null ref", "fixable": false}'
        result = extract_json(text)
        self.assertIsNotNone(result)
        self.assertEqual(result["root_cause"], "null ref")

    def test_extract_json_empty(self):
        from anatomy.brain_dispatcher import extract_json
        self.assertIsNone(extract_json(""))
        self.assertIsNone(extract_json(None))


if __name__ == "__main__":
    unittest.main()
