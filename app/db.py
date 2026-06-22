"""SQLite connection and schema management.

Schema:
- model_configs: one row per stage ('outline' | 'ppt')
- outlines: history of generated/edited outlines
- generations: history of generated PPTs (.pptx / .pdf paths)
"""
from __future__ import annotations

import os
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS model_configs (
    stage TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    base_url TEXT,
    api_key TEXT NOT NULL,
    model_name TEXT NOT NULL,
    extra_params TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS outlines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    requirements TEXT,
    content_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS generations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outline_id INTEGER REFERENCES outlines(id),
    style TEXT,
    image_mode TEXT,
    pptx_path TEXT,
    pdf_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def default_db_path() -> Path:
    data_dir = Path(os.environ.get("PPTM_DATA_DIR", "data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "app.db"


def init_db(path: Path | None = None) -> Path:
    """Create schema if missing. Returns the db path used."""
    db_path = path or default_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
    return db_path


@contextmanager
def get_connection(path: Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    db_path = path or default_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
