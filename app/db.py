import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "sentinel.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        original_intent TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS tool_fingerprints (
        server_name TEXT NOT NULL,
        tool_name TEXT NOT NULL,
        fingerprint_hash TEXT NOT NULL,
        first_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (server_name, tool_name)
    );

    CREATE TABLE IF NOT EXISTS taint_records (
        session_id TEXT NOT NULL,
        value_ref TEXT NOT NULL,
        source_server TEXT NOT NULL,
        trust_level TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        tool_name TEXT NOT NULL,
        decision TEXT NOT NULL,
        reasons TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    conn.close()