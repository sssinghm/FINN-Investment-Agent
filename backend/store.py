"""Small SQLite persistence layer for alert preferences and research history."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "finn.db"
DEFAULT_RULES = {"price_move_pct": 3.0, "volume_multiple": 2.0, "window_days": 1,
                 "categories": ["results", "M&A", "management_change", "litigation", "fund_raise"],
                 "collapse_routine": True}


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with connect() as con:
        con.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        con.execute("CREATE TABLE IF NOT EXISTS research_runs (id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT NOT NULL, question TEXT NOT NULL, created_at TEXT NOT NULL, status TEXT NOT NULL, answer_json TEXT NOT NULL)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_research_ticker ON research_runs(ticker, created_at DESC)")
        if not con.execute("SELECT 1 FROM settings WHERE key='alert_rules'").fetchone():
            con.execute("INSERT INTO settings(key,value) VALUES('alert_rules',?)", (json.dumps(DEFAULT_RULES),))


def get_alert_rules() -> dict:
    init_db()
    with connect() as con:
        row = con.execute("SELECT value FROM settings WHERE key='alert_rules'").fetchone()
        return json.loads(row["value"]) if row else dict(DEFAULT_RULES)


def save_alert_rules(value: dict) -> dict:
    clean = dict(DEFAULT_RULES)
    clean.update(value)
    clean["price_move_pct"] = max(0.1, min(float(clean["price_move_pct"]), 30.0))
    clean["volume_multiple"] = max(1.0, min(float(clean["volume_multiple"]), 20.0))
    clean["window_days"] = max(1, min(int(clean["window_days"]), 30))
    with connect() as con:
        con.execute("INSERT INTO settings(key,value) VALUES('alert_rules',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (json.dumps(clean),))
    return clean


def save_research_run(ticker: str, question: str, status: str, result: dict) -> int:
    init_db()
    ts = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
    with connect() as con:
        cur = con.execute("INSERT INTO research_runs(ticker,question,created_at,status,answer_json) VALUES(?,?,?,?,?)",
                          (ticker.upper(), question, ts, status, json.dumps(result, ensure_ascii=False)))
        return int(cur.lastrowid)


def recent_research(limit: int = 10) -> list[dict]:
    init_db()
    with connect() as con:
        rows = con.execute("SELECT id,ticker,question,created_at,status FROM research_runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]
