import sqlite3
import json
import time
import os
from pathlib import Path
from tokenops.tracking.recorder import get_db_path, init_db

def read_records() -> list[dict]:
    """Reads all token usage records from the SQLite database."""
    db_path = get_db_path()
    if not db_path.exists():
        return []
    
    conn = sqlite3.connect(str(db_path), timeout=10.0)
    try:
        init_db(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, provider, model, input_tokens, output_tokens, total_tokens, messages FROM usage")
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()
    
    records = []
    for r in rows:
        try:
            msgs = json.loads(r[6] or "[]")
        except json.JSONDecodeError:
            msgs = []
            
        records.append({
            "timestamp": r[0],
            "provider": r[1],
            "model": r[2],
            "input_tokens": r[3],
            "output_tokens": r[4],
            "total_tokens": r[5],
            "messages": msgs
        })
    return records

def get_totals_for_timeframe(days: int = None, current_month_only: bool = False, current_day_only: bool = False) -> int:
    """Calculates total tokens consumed in the specified timeframe."""
    records = read_records()
    now_struct = time.gmtime()
    current_date_str = time.strftime("%Y-%m-%d", now_struct)
    current_month_str = time.strftime("%Y-%m", now_struct)
    
    total = 0
    now_ts = time.time()
    
    for r in records:
        ts_str = r.get("timestamp", "")
        try:
            # Parse ISO UTC timestamp to epoch
            struct_t = time.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ")
            epoch_t = time.mktime(struct_t) - time.timezone
        except Exception:
            epoch_t = 0
            
        if current_day_only:
            if ts_str.startswith(current_date_str):
                total += r.get("total_tokens", 0)
        elif current_month_only:
            if ts_str.startswith(current_month_str):
                total += r.get("total_tokens", 0)
        elif days is not None:
            if now_ts - epoch_t <= days * 24 * 3600:
                total += r.get("total_tokens", 0)
        else:
            total += r.get("total_tokens", 0)
            
    return total

def get_aggregated_by_provider_model() -> dict:
    """Aggregates usage by (provider, model) -> input, output, total."""
    records = read_records()
    agg = {}
    for r in records:
        prov = r.get("provider", "unknown")
        mod = r.get("model", "unknown")
        key = (prov, mod)
        if key not in agg:
            agg[key] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        agg[key]["input_tokens"] += r.get("input_tokens", 0)
        agg[key]["output_tokens"] += r.get("output_tokens", 0)
        agg[key]["total_tokens"] += r.get("total_tokens", 0)
    return agg
