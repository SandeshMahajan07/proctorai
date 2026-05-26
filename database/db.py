import sqlite3
import hashlib
import json
import os
from config import DATABASE_PATH

def get_connection():
    """Return a SQLite connection with row_factory for dict-like access."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create all tables and seed default users."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = get_connection()
    cur  = conn.cursor()

    # ── Users ──────────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT    UNIQUE NOT NULL,
            password TEXT    NOT NULL,
            role     TEXT    NOT NULL DEFAULT 'student',  -- 'student' | 'admin'
            email    TEXT,
            created  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── Exam Sessions ──────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exam_sessions (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL,
            started_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
            ended_at       DATETIME,
            score          INTEGER DEFAULT 0,          -- exam score (correct answers)
            cheating_score INTEGER DEFAULT 0,          -- suspicion score
            status         TEXT    DEFAULT 'ongoing',  -- 'ongoing' | 'completed'
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # ── Violation Logs ─────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS violation_logs (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id     INTEGER NOT NULL,
            violation_type TEXT    NOT NULL,   -- e.g. 'TAB_SWITCH', 'NO_FACE'
            description    TEXT,
            points         INTEGER DEFAULT 0,
            timestamp      DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES exam_sessions(id)
        )
    """)

    # ── Exam Answers ───────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exam_answers (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            answer      TEXT,
            is_correct  INTEGER DEFAULT 0,
            FOREIGN KEY(session_id) REFERENCES exam_sessions(id)
        )
    """)

    conn.commit()

    # ── Seed default users ─────────────────────────────────────────────────────
    _seed_users(cur, conn)
    conn.close()

def _seed_users(cur, conn):
    """Insert default admin + student if not exist."""
    users = [
        ("admin",   "admin123",   "admin"),
        ("student1","student123", "student"),
        ("student2","student456", "student"),
    ]
    for username, password, role in users:
        hashed = hashlib.sha256(password.encode()).hexdigest()
        cur.execute(
            "INSERT OR IGNORE INTO users (username, password, role) VALUES (?,?,?)",
            (username, hashed, role)
        )
    conn.commit()

# ─── Auth Helpers ──────────────────────────────────────────────────────────────

def verify_user(username, password):
    """Return user row if credentials match, else None."""
    hashed = hashlib.sha256(password.encode()).hexdigest()
    conn = get_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE username=? AND password=?", (username, hashed)
    ).fetchone()
    conn.close()
    return user

# ─── Session Helpers ───────────────────────────────────────────────────────────

def create_exam_session(user_id):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO exam_sessions (user_id) VALUES (?)", (user_id,)
    )
    session_id = cur.lastrowid
    conn.commit()
    conn.close()
    return session_id

def end_exam_session(session_id, exam_score):
    conn = get_connection()
    conn.execute("""
        UPDATE exam_sessions
        SET ended_at=CURRENT_TIMESTAMP, status='completed', score=?
        WHERE id=?
    """, (exam_score, session_id))
    conn.commit()
    conn.close()

def get_session(session_id):
    conn = get_connection()
    row  = conn.execute(
        "SELECT * FROM exam_sessions WHERE id=?", (session_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_sessions_with_users():
    conn  = get_connection()
    rows  = conn.execute("""
        SELECT es.*, u.username
        FROM exam_sessions es
        JOIN users u ON es.user_id = u.id
        ORDER BY es.started_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─── Violation Helpers ────────────────────────────────────────────────────────

def log_violation(session_id, violation_type, description, points):
    conn = get_connection()
    conn.execute("""
        INSERT INTO violation_logs (session_id, violation_type, description, points)
        VALUES (?,?,?,?)
    """, (session_id, violation_type, description, points))
    # Update cumulative cheating score
    conn.execute("""
        UPDATE exam_sessions
        SET cheating_score = cheating_score + ?
        WHERE id = ?
    """, (points, session_id))
    conn.commit()
    conn.close()

def get_violations(session_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM violation_logs WHERE session_id=? ORDER BY timestamp",
        (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─── Answer Helpers ───────────────────────────────────────────────────────────

def save_answer(session_id, question_id, answer, is_correct):
    conn = get_connection()
    # Upsert — replace if already answered
    conn.execute("""
        INSERT OR REPLACE INTO exam_answers (session_id, question_id, answer, is_correct)
        VALUES (?,?,?,?)
    """, (session_id, question_id, answer, int(is_correct)))
    conn.commit()
    conn.close()

def get_answers(session_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM exam_answers WHERE session_id=?", (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]