import pytest
import sqlite3
from unittest.mock import patch, MagicMock
from backend_engine.database.db_manager import init_database

def test_init_database_happy_path(tmp_path):
    """Test that init_database creates all expected tables in a clean database."""
    db_file = tmp_path / "test_ledger.db"

    with patch('backend_engine.database.db_manager.DB_PATH', str(db_file)):
        # init_database should run without error
        init_database()

        # Verify tables exist
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        expected_tables = {
            'API_Usage', 'Agent_Status', 'Activity_Log',
            'Projects', 'Alerts', 'Jules_Sessions'
        }
        for table in expected_tables:
            assert table in tables, f"Table {table} was not created"

        # Verify specific columns in API_Usage (including those from migration loop)
        cursor.execute("PRAGMA table_info(API_Usage)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "api_key_override" in columns
        assert "model_provider" in columns
        assert "github_pat_override" in columns
        conn.close()

def test_init_database_migration_error_handling():
    """Test that sqlite3.OperationalError during migration is handled gracefully."""
    with patch('backend_engine.database.db_manager.get_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_cursor = mock_conn.cursor.return_value

        # Configure side_effect to raise OperationalError for ALTER TABLE
        def side_effect(sql, *args):
            if "ALTER TABLE API_Usage ADD COLUMN" in sql:
                raise sqlite3.OperationalError("duplicate column name")
            return MagicMock()

        mock_cursor.execute.side_effect = side_effect

        # This should NOT raise an exception because OperationalError is caught
        try:
            init_database()
        except sqlite3.OperationalError:
            pytest.fail("sqlite3.OperationalError was not caught during migration!")

        # Verify that it was called for migrations
        alter_calls = [call for call in mock_cursor.execute.call_args_list if "ALTER TABLE" in call[0][0]]
        assert len(alter_calls) == 3, f"Expected 3 ALTER TABLE calls, got {len(alter_calls)}"
