"""Tests for the SQLite database initializer."""
import sqlite3

from app.db import init_db, get_connection


def test_init_creates_tables(tmp_dir):
    db_path = tmp_dir / "test.db"
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    names = {r["name"] for r in rows}
    assert "model_configs" in names
    assert "outlines" in names
    assert "generations" in names


def test_init_idempotent(tmp_dir):
    db_path = tmp_dir / "test.db"
    init_db(db_path)
    init_db(db_path)  # second call should not raise
    assert db_path.exists()


def test_get_connection_yields_row_factory(tmp_dir):
    db_path = tmp_dir / "test.db"
    init_db(db_path)
    with get_connection(db_path) as conn:
        conn.execute("INSERT INTO model_configs(stage, provider, api_key, model_name) VALUES ('outline','openai','k','m')")
        row = conn.execute("SELECT * FROM model_configs WHERE stage='outline'").fetchone()
    assert row["stage"] == "outline"
    assert row["api_key"] == "k"


def test_get_connection_invalid_path_raises(tmp_dir):
    import pytest
    with pytest.raises(sqlite3.OperationalError):
        with get_connection(tmp_dir / "nope" / "x.db") as conn:
            conn.execute("SELECT 1")
