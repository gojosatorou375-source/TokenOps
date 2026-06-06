import sqlite3
import json
import time
import os
from pathlib import Path

def get_db_path() -> Path:
    """Returns the path to the SQLite database file, supporting overrides via AI_GUARD_DB_PATH."""
    env_path = os.environ.get("AI_GUARD_DB_PATH")
    if env_path:
        return Path(env_path)
    
    dir_path = Path.home() / ".tokenops"
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path / "usage.db"

def init_db(conn):
    """Initializes the database schema if it does not exist."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            total_tokens INTEGER NOT NULL,
            messages TEXT
        )
    """)
    conn.commit()

def record_usage(provider: str, model: str, input_tokens: int, output_tokens: int, messages: list = None):
    """Records token consumption data into SQLite DB using WAL journaling for high-concurrency safety."""
    db_path = get_db_path()
    
    # Connect with timeout to handle potential busy locks cleanly
    conn = sqlite3.connect(str(db_path), timeout=15.0)
    try:
        # Enable WAL mode for parallel readers and writers
        conn.execute("PRAGMA journal_mode=WAL")
        init_db(conn)
        
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        messages_str = json.dumps(messages or [])
        total_tokens = input_tokens + output_tokens
        
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO usage (timestamp, provider, model, input_tokens, output_tokens, total_tokens, messages) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (timestamp, provider, model, input_tokens, output_tokens, total_tokens, messages_str)
        )
        conn.commit()
    finally:
        conn.close()
