"""
SQLite database layer for Profile Portal.

Tables:
  profile              - One row, stores full user profile as JSON
  messages             - Chat history per session
  conversation_meta    - Summary of older messages (auto-compressed)
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "profile_portal.db"

# ---------------------------------------------------------------------------
# Initial profile seeded from user_profile.py data
# ---------------------------------------------------------------------------
INITIAL_PROFILE = {
    "name": "Akash Yadav",
    "email": "akashyadavazm8@gmail.com",
    "phone": "+91 9140331096",
    "location": "Ghaziabad, Uttar Pradesh, India",
    "linkedin": "https://www.linkedin.com/in/akash-yadav-46796a363/",
    "github": "https://github.com/akashcodejames",
    "portfolio": "https://akashcodejames.github.io/portfolio/",
    "education": "B.Tech Computer Science Engineering, NITRA Technical Campus, Ghaziabad (2025) — CGPA: 7.0",
    "experience_years": 1,
    "experience_months": 0,
    "current_ctc": 0,
    "expected_ctc": 600000,
    "notice_period": "Immediate",
    "work_authorization": "Authorized to work in India (No Visa Required)",
    "relocation": True,
    "remote": True,
    "target_roles": [
        "Python Developer",
        "Backend Developer",
        "Software Developer",
        "AI Engineer (Entry Level)",
        "LLM / Generative AI Engineer"
    ],
    "skills": [
        "Python", "Flask", "FastAPI", "Django",
        "LangChain", "LangGraph", "ChromaDB",
        "Docker", "Docker Compose", "Kubernetes (Beginner)",
        "Redis", "Celery", "PostgreSQL", "MySQL", "Nginx",
        "Prompt Engineering", "RAG Systems"
    ],
    "about": (
        "Entry-level backend and AI engineer focused on building scalable Python "
        "backend systems and LLM-powered applications. Hands-on experience with "
        "RESTful API development, async task queues, containerized deployments, "
        "and agentic AI workflows using LangGraph and LangChain."
    ),
    "projects": [
        {
            "name": "LinkedIn Easy Apply Agent",
            "stack": "Python, LangGraph, Playwright, OpenAI GPT-4o-mini",
            "description": "Autonomous job application agent using LangGraph state machine, Pydantic structured output, and Playwright browser automation."
        },
        {
            "name": "College ERP System",
            "stack": "Flask, MySQL, Redis, Docker, Nginx",
            "description": "Full-stack ERP with attendance, library management, and role-based access control."
        },
        {
            "name": "RAG-based YouTube Chat AI",
            "stack": "Python, LangChain, ChromaDB, OpenAI",
            "description": "Context-aware Q&A over YouTube transcripts using Retrieval-Augmented Generation."
        },
        {
            "name": "Library Management System",
            "stack": "Flask, MySQL, Celery, Redis, aiosmtplib",
            "description": "Async overdue book notifications with background task scheduling."
        }
    ]
}


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ---------------------------------------------------------------------------
# Schema init
# ---------------------------------------------------------------------------

def init_db():
    """Create tables and seed initial profile if empty."""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS profile (
                id         INTEGER PRIMARY KEY DEFAULT 1,
                data       TEXT    NOT NULL,
                updated_at TEXT    DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT    NOT NULL,
                role       TEXT    NOT NULL,
                content    TEXT    NOT NULL,
                created_at TEXT    DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS conversation_meta (
                session_id TEXT PRIMARY KEY,
                summary    TEXT DEFAULT '',
                updated_at TEXT DEFAULT (datetime('now'))
            );
        """)

        existing = conn.execute("SELECT id FROM profile WHERE id=1").fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO profile (id, data) VALUES (1, ?)",
                (json.dumps(INITIAL_PROFILE),)
            )
            conn.commit()


# ---------------------------------------------------------------------------
# Profile CRUD
# ---------------------------------------------------------------------------

def get_profile() -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT data FROM profile WHERE id=1").fetchone()
        return json.loads(row["data"]) if row else {}


def update_profile(updates: dict) -> dict:
    """Merge updates into existing profile and persist."""
    profile = get_profile()
    profile.update(updates)
    with get_conn() as conn:
        conn.execute(
            "UPDATE profile SET data=?, updated_at=datetime('now') WHERE id=1",
            (json.dumps(profile),)
        )
        conn.commit()
    return profile


def delete_profile_key(key: str) -> dict:
    """Remove a single key from the profile JSON blob. Silently ignores missing keys."""
    profile = get_profile()
    profile.pop(key, None)
    with get_conn() as conn:
        conn.execute(
            "UPDATE profile SET data=?, updated_at=datetime('now') WHERE id=1",
            (json.dumps(profile),)
        )
        conn.commit()
    return profile


def get_profile_updated_at() -> str:
    with get_conn() as conn:
        row = conn.execute("SELECT updated_at FROM profile WHERE id=1").fetchone()
        return row["updated_at"] if row else ""


# ---------------------------------------------------------------------------
# Messages CRUD
# ---------------------------------------------------------------------------

BUFFER_SIZE = 10  # Keep this many messages verbatim; compress the rest


def add_message(session_id: str, role: str, content: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content)
        )
        conn.commit()


def get_recent_messages(session_id: str, limit: int = BUFFER_SIZE) -> list[dict]:
    """Return the most recent `limit` messages for display / LLM context."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT role, content FROM messages
               WHERE session_id=?
               ORDER BY id DESC LIMIT ?""",
            (session_id, limit)
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def get_all_messages_for_display(session_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content, created_at FROM messages WHERE session_id=? ORDER BY id",
            (session_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def clear_messages(session_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
        conn.execute("DELETE FROM conversation_meta WHERE session_id=?", (session_id,))
        conn.commit()


# ---------------------------------------------------------------------------
# Conversation summary (for long-context compression)
# ---------------------------------------------------------------------------

def get_summary(session_id: str) -> str:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT summary FROM conversation_meta WHERE session_id=?",
            (session_id,)
        ).fetchone()
    return row["summary"] if row else ""


def save_summary(session_id: str, summary: str):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO conversation_meta (session_id, summary, updated_at)
               VALUES (?, ?, datetime('now'))
               ON CONFLICT(session_id) DO UPDATE
               SET summary=excluded.summary, updated_at=excluded.updated_at""",
            (session_id, summary)
        )
        conn.commit()


def get_message_count(session_id: str) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM messages WHERE session_id=?",
            (session_id,)
        ).fetchone()
    return row["cnt"]
