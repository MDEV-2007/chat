"""SQLite CRUD: chats, messages, system prompt presets."""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.config import DB_PATH, DEFAULT_MODEL

SCHEMA = """
CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY,
    title TEXT,
    model TEXT DEFAULT 'qwen3:8b',
    system_prompt TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    chat_id INTEGER REFERENCES chats(id),
    role TEXT CHECK(role IN ('user','assistant')),
    content TEXT,
    image_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_prompt_presets (
    id INTEGER PRIMARY KEY,
    name TEXT,
    content TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS profile_facts (
    id INTEGER PRIMARY KEY,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

DEFAULT_PRESETS = [
    ("Coding Assistant", "You are an expert coding assistant. Give precise, working code with brief explanations."),
    ("Umumiy suhbat", "You are a helpful, friendly general-purpose assistant."),
    ("Tarjimon", "You are a professional translator. Translate accurately, preserve tone and meaning."),
    ("Brainstorm", "You are a creative brainstorming partner. Generate diverse, unconventional ideas."),
]


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
        cur = conn.execute("SELECT COUNT(*) FROM system_prompt_presets")
        if cur.fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO system_prompt_presets (name, content) VALUES (?, ?)",
                DEFAULT_PRESETS,
            )
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(messages)")]
        if "embedding" not in cols:
            conn.execute("ALTER TABLE messages ADD COLUMN embedding TEXT")
        conn.commit()
    finally:
        conn.close()


# ---- chats ----

def create_chat(title: str = "New Chat", model: str = DEFAULT_MODEL, system_prompt: str = "") -> int:
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO chats (title, model, system_prompt) VALUES (?, ?, ?)",
            (title, model, system_prompt),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_chats() -> list[sqlite3.Row]:
    conn = get_conn()
    try:
        return conn.execute(
            "SELECT * FROM chats ORDER BY created_at DESC"
        ).fetchall()
    finally:
        conn.close()


def get_chat(chat_id: int) -> Optional[sqlite3.Row]:
    conn = get_conn()
    try:
        return conn.execute("SELECT * FROM chats WHERE id = ?", (chat_id,)).fetchone()
    finally:
        conn.close()


def update_chat_title(chat_id: int, title: str) -> None:
    conn = get_conn()
    try:
        conn.execute("UPDATE chats SET title = ? WHERE id = ?", (title, chat_id))
        conn.commit()
    finally:
        conn.close()


def update_chat_model(chat_id: int, model: str) -> None:
    conn = get_conn()
    try:
        conn.execute("UPDATE chats SET model = ? WHERE id = ?", (model, chat_id))
        conn.commit()
    finally:
        conn.close()


def update_chat_system_prompt(chat_id: int, system_prompt: str) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE chats SET system_prompt = ? WHERE id = ?", (system_prompt, chat_id)
        )
        conn.commit()
    finally:
        conn.close()


def delete_chat(chat_id: int) -> None:
    conn = get_conn()
    try:
        conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
        conn.commit()
    finally:
        conn.close()


# ---- messages ----

def add_message(chat_id: int, role: str, content: str, image_path: Optional[str] = None) -> int:
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO messages (chat_id, role, content, image_path) VALUES (?, ?, ?, ?)",
            (chat_id, role, content, image_path),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_messages(chat_id: int) -> list[sqlite3.Row]:
    conn = get_conn()
    try:
        return conn.execute(
            "SELECT * FROM messages WHERE chat_id = ? ORDER BY created_at ASC, id ASC",
            (chat_id,),
        ).fetchall()
    finally:
        conn.close()


def update_message(message_id: int, content: str) -> None:
    conn = get_conn()
    try:
        conn.execute("UPDATE messages SET content = ? WHERE id = ?", (content, message_id))
        conn.commit()
    finally:
        conn.close()


def set_message_embedding(message_id: int, embedding_json: str) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE messages SET embedding = ? WHERE id = ?", (embedding_json, message_id)
        )
        conn.commit()
    finally:
        conn.close()


def list_messages_with_embeddings(exclude_chat_id: Optional[int] = None) -> list[sqlite3.Row]:
    conn = get_conn()
    try:
        if exclude_chat_id is not None:
            return conn.execute(
                "SELECT m.*, c.title as chat_title FROM messages m "
                "JOIN chats c ON c.id = m.chat_id "
                "WHERE m.embedding IS NOT NULL AND m.chat_id != ?",
                (exclude_chat_id,),
            ).fetchall()
        return conn.execute(
            "SELECT m.*, c.title as chat_title FROM messages m "
            "JOIN chats c ON c.id = m.chat_id "
            "WHERE m.embedding IS NOT NULL"
        ).fetchall()
    finally:
        conn.close()


# ---- presets ----

def list_presets() -> list[sqlite3.Row]:
    conn = get_conn()
    try:
        return conn.execute("SELECT * FROM system_prompt_presets ORDER BY id ASC").fetchall()
    finally:
        conn.close()


def add_preset(name: str, content: str) -> int:
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO system_prompt_presets (name, content) VALUES (?, ?)", (name, content)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


# ---- settings (key/value, used for global default system prompt) ----

def get_setting(key: str, default: str = "") -> str:
    conn = get_conn()
    try:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default
    finally:
        conn.close()


def set_setting(key: str, value: str) -> None:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()


# ---- profile facts (long-term "who is the user" memory) ----

def list_profile_facts() -> list[sqlite3.Row]:
    conn = get_conn()
    try:
        return conn.execute("SELECT * FROM profile_facts ORDER BY id ASC").fetchall()
    finally:
        conn.close()


def add_profile_fact(content: str) -> int:
    conn = get_conn()
    try:
        cur = conn.execute("INSERT INTO profile_facts (content) VALUES (?)", (content,))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def delete_profile_fact(fact_id: int) -> None:
    conn = get_conn()
    try:
        conn.execute("DELETE FROM profile_facts WHERE id = ?", (fact_id,))
        conn.commit()
    finally:
        conn.close()
