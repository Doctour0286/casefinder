"""
CaseFinder v1.0 — SQLite Database
Stores users, scores, watchlist, results, and quota tracking.
"""

import sqlite3
import os
import json
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "casefinder.db")


@contextmanager
def get_db():
    """Connect to database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all tables."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                youtube_api_key TEXT,
                channel_handle TEXT,
                channel_id TEXT,
                subscriber_count INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                case_name TEXT NOT NULL,
                vps INTEGER,
                rating TEXT,
                demand INTEGER,
                supply INTEGER,
                emotional INTEGER,
                full_data TEXT,
                scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                case_name TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, case_name)
            );

            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                case_name TEXT NOT NULL,
                views_30d INTEGER,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)


# ═══════════════════════════════════════════════════════════
# USER FUNCTIONS
# ═══════════════════════════════════════════════════════════

def create_user(email: str, username: str, password_hash: str) -> int:
    """Create a new user. Returns user ID."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO users (email, username, password_hash) VALUES (?, ?, ?)",
            (email, username, password_hash)
        )
        return cursor.lastrowid


def get_user_by_email(email: str) -> dict | None:
    """Get user by email."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None


def get_user_by_username(username: str) -> dict | None:
    """Get user by username."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    """Get user by ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def update_user_api_key(user_id: int, api_key: str):
    """Update user's YouTube API key."""
    with get_db() as conn:
        conn.execute("UPDATE users SET youtube_api_key = ? WHERE id = ?", (api_key, user_id))


def update_user_channel(user_id: int, handle: str, channel_id: str, subs: int):
    """Update user's channel info."""
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET channel_handle = ?, channel_id = ?, subscriber_count = ? WHERE id = ?",
            (handle, channel_id, subs, user_id)
        )


def update_last_login(user_id: int):
    """Update last login timestamp."""
    with get_db() as conn:
        conn.execute("UPDATE users SET last_login = ? WHERE id = ?", (datetime.now().isoformat(), user_id))


# ═══════════════════════════════════════════════════════════
# SCORE FUNCTIONS
# ═══════════════════════════════════════════════════════════

def save_score(user_id: int, case_name: str, score_data: dict) -> int:
    """Save or update a case score."""
    with get_db() as conn:
        # Delete old score for this case
        conn.execute("DELETE FROM scores WHERE user_id = ? AND case_name = ?", (user_id, case_name))
        
        cursor = conn.execute(
            """INSERT INTO scores (user_id, case_name, vps, rating, demand, supply, emotional, full_data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id, case_name,
                score_data.get("vps", 0),
                score_data.get("rating", ""),
                score_data.get("demand", 0),
                score_data.get("supply", 0),
                score_data.get("emotional", 0),
                json.dumps(score_data)
            )
        )
        return cursor.lastrowid


def get_user_scores(user_id: int) -> list[dict]:
    """Get all scores for a user, ranked by VPS."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM scores WHERE user_id = ? ORDER BY vps DESC",
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════
# WATCHLIST FUNCTIONS
# ═══════════════════════════════════════════════════════════

def add_to_watchlist(user_id: int, case_name: str) -> bool:
    """Add case to watchlist. Returns True if added."""
    try:
        with get_db() as conn:
            conn.execute("INSERT INTO watchlist (user_id, case_name) VALUES (?, ?)", (user_id, case_name))
            return True
    except sqlite3.IntegrityError:
        return False


def remove_from_watchlist(user_id: int, case_name: str) -> bool:
    """Remove case from watchlist."""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM watchlist WHERE user_id = ? AND case_name = ?", (user_id, case_name))
        return cursor.rowcount > 0


def get_watchlist(user_id: int) -> list[dict]:
    """Get user's watchlist."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM watchlist WHERE user_id = ? ORDER BY added_at DESC", (user_id,)).fetchall()
        return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════
# RESULTS FUNCTIONS
# ═══════════════════════════════════════════════════════════

def save_result(user_id: int, case_name: str, views: int) -> int:
    """Save video performance result."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO results (user_id, case_name, views_30d) VALUES (?, ?, ?)",
            (user_id, case_name, views)
        )
        return cursor.lastrowid


def get_user_results(user_id: int) -> list[dict]:
    """Get all results for a user."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM results WHERE user_id = ? ORDER BY recorded_at DESC", (user_id,)).fetchall()
        return [dict(r) for r in rows]


# Initialize database on import
init_db()
