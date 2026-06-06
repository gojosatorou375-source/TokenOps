import sqlite3
import re
import time
from tokenops.tracking.recorder import get_db_path

def init_cache_db(conn):
    """Initializes the cache schema if it does not exist."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt TEXT NOT NULL,
            response TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()

def calculate_jaccard_similarity(text1: str, text2: str) -> float:
    """Calculates Jaccard word-level overlap similarity between two strings."""
    words1 = set(re.findall(r"\w+", text1.lower()))
    words2 = set(re.findall(r"\w+", text2.lower()))
    if not words1 or not words2:
        return 0.0
    return len(words1 & words2) / len(words1 | words2)

def lookup_cache(prompt: str, threshold: float = 0.85) -> tuple[str, str, str] | None:
    """
    Looks up a prompt in the SQLite cache. Returns (response, provider, model) on hit, else None.
    """
    db_path = get_db_path()
    if not db_path.exists():
        return None
        
    conn = sqlite3.connect(str(db_path), timeout=10.0)
    try:
        init_cache_db(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT prompt, response, provider, model FROM semantic_cache")
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()
        
    best_match = None
    best_score = 0.0
    
    for row in rows:
        cached_prompt, response, provider, model = row
        score = calculate_jaccard_similarity(prompt, cached_prompt)
        if score > best_score:
            best_score = score
            best_match = (response, provider, model)
            
    if best_score >= threshold:
        return best_match
        
    return None

def save_cache(prompt: str, response: str, provider: str, model: str):
    """Saves a prompt-response entry into the SQLite semantic cache."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path), timeout=15.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        init_cache_db(conn)
        
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO semantic_cache (prompt, response, provider, model, timestamp) VALUES (?, ?, ?, ?, ?)",
            (prompt, response, provider, model, timestamp)
        )
        conn.commit()
    finally:
        conn.close()
