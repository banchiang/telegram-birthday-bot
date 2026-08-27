"""SQLite storage layer for the birthday bot.

Everything is keyed by the Telegram user id of whoever added the data
("owner_id"), so the same bot/database can be used by more than one person
without their birthdays or categories mixing.
"""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.environ.get("DB_PATH", Path(__file__).parent / "data" / "birthdays.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    name TEXT NOT NULL COLLATE NOCASE,
    UNIQUE(owner_id, name)
);

CREATE TABLE IF NOT EXISTS birthdays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    year INTEGER,
    color_id INTEGER NOT NULL DEFAULT 1,
    group_id INTEGER REFERENCES groups(id) ON DELETE SET NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS remind_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    chat_id INTEGER NOT NULL,
    chat_title TEXT,
    UNIQUE(chat_id, group_id)
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


# ---------------------------------------------------------------- birthdays

def add_birthday(owner_id, name, month, day, year, color_id, group_id=None):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO birthdays (owner_id, name, month, day, year, color_id, group_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (owner_id, name, month, day, year, color_id, group_id),
        )
        return cur.lastrowid


def delete_birthday(owner_id, birthday_id):
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM birthdays WHERE id = ? AND owner_id = ?",
            (birthday_id, owner_id),
        )
        return cur.rowcount > 0


def get_birthday(owner_id, birthday_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT b.*, g.name AS group_name FROM birthdays b "
            "LEFT JOIN groups g ON g.id = b.group_id "
            "WHERE b.id = ? AND b.owner_id = ?",
            (birthday_id, owner_id),
        ).fetchone()
        return dict(row) if row else None


def list_birthdays(owner_id, month=None, group_id=None):
    query = (
        "SELECT b.*, g.name AS group_name FROM birthdays b "
        "LEFT JOIN groups g ON g.id = b.group_id WHERE b.owner_id = ?"
    )
    params = [owner_id]
    if month is not None:
        query += " AND b.month = ?"
        params.append(month)
    if group_id is not None:
        query += " AND b.group_id = ?"
        params.append(group_id)
    query += " ORDER BY b.month, b.day"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def birthdays_on(owner_id, month, day):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM birthdays WHERE owner_id = ? AND month = ? AND day = ?",
            (owner_id, month, day),
        ).fetchall()
        return [dict(r) for r in rows]


def birthdays_in_month(owner_id, month):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT b.*, g.name AS group_name FROM birthdays b "
            "LEFT JOIN groups g ON g.id = b.group_id "
            "WHERE b.owner_id = ? AND b.month = ? ORDER BY b.day",
            (owner_id, month),
        ).fetchall()
        return [dict(r) for r in rows]


def birthdays_on_in_group(group_id, month, day):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM birthdays WHERE group_id = ? AND month = ? AND day = ?",
            (group_id, month, day),
        ).fetchall()
        return [dict(r) for r in rows]


def list_owners():
    with get_conn() as conn:
        rows = conn.execute("SELECT DISTINCT owner_id FROM birthdays").fetchall()
        return [r["owner_id"] for r in rows]


# ------------------------------------------------------------------ groups

def create_group(owner_id, name):
    with get_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO groups (owner_id, name) VALUES (?, ?)", (owner_id, name)
            )
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None


def get_group_by_name(owner_id, name):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM groups WHERE owner_id = ? AND name = ? COLLATE NOCASE",
            (owner_id, name),
        ).fetchone()
        return dict(row) if row else None


def list_groups(owner_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT g.*, (SELECT COUNT(*) FROM birthdays b WHERE b.group_id = g.id) AS count "
            "FROM groups g WHERE g.owner_id = ? ORDER BY g.name COLLATE NOCASE",
            (owner_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def delete_group(owner_id, name):
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM groups WHERE owner_id = ? AND name = ? COLLATE NOCASE",
            (owner_id, name),
        )
        return cur.rowcount > 0


def assign_group(owner_id, birthday_id, group_id):
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE birthdays SET group_id = ? WHERE id = ? AND owner_id = ?",
            (group_id, birthday_id, owner_id),
        )
        return cur.rowcount > 0


# ------------------------------------------------------------ remind links

def add_remind_target(owner_id, group_id, chat_id, chat_title):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO remind_targets (owner_id, group_id, chat_id, chat_title) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(chat_id, group_id) DO UPDATE SET chat_title = excluded.chat_title",
            (owner_id, group_id, chat_id, chat_title),
        )


def remove_remind_target(owner_id, group_id, chat_id):
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM remind_targets WHERE owner_id = ? AND group_id = ? AND chat_id = ?",
            (owner_id, group_id, chat_id),
        )
        return cur.rowcount > 0


def list_remind_targets(owner_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT rt.*, g.name AS group_name FROM remind_targets rt "
            "JOIN groups g ON g.id = rt.group_id WHERE rt.owner_id = ? "
            "ORDER BY g.name COLLATE NOCASE",
            (owner_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def list_all_remind_targets():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT rt.*, g.name AS group_name FROM remind_targets rt "
            "JOIN groups g ON g.id = rt.group_id"
        ).fetchall()
        return [dict(r) for r in rows]
