"""SQLite storage layer (stdlib only, no ORM required).

Two tables:
  users  - registered accounts (bcrypt-comparable werkzeug hashes)
  jobs   - every analysis run (config + result JSON, file paths)
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import config


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_db() -> sqlite3.Connection:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(config.DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                email         TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at    TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS jobs (
                id            TEXT PRIMARY KEY,
                owner_id      INTEGER NOT NULL REFERENCES users(id),
                filename      TEXT NOT NULL,
                video_rel     TEXT NOT NULL,          -- path relative to project root
                config_json   TEXT NOT NULL,
                status        TEXT NOT NULL DEFAULT 'queued',  -- queued|processing|done|error
                progress      INTEGER NOT NULL DEFAULT 0,
                result_json   TEXT,
                error_msg     TEXT,
                created_at    TEXT NOT NULL,
                finished_at   TEXT
            );
            """
        )
        conn.commit()


# ---------------------------------------------------------------------------
# users
# ---------------------------------------------------------------------------
def create_user(name: str, email: str, password_hash: str) -> int:
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (name.strip(), email.strip().lower(), password_hash, _utcnow()),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_user_by_email(email: str) -> sqlite3.Row | None:
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()


def get_user_by_id(user_id: int) -> sqlite3.Row | None:
    with get_db() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


# ---------------------------------------------------------------------------
# jobs
# ---------------------------------------------------------------------------
def create_job(job_id: str, owner_id: int, filename: str, video_rel: str, cfg: dict) -> None:
    with get_db() as conn:
        conn.execute(
            """INSERT INTO jobs
               (id, owner_id, filename, video_rel, config_json, status, progress, created_at)
               VALUES (?, ?, ?, ?, ?, 'queued', 0, ?)""",
            (job_id, owner_id, filename, video_rel, json.dumps(cfg), _utcnow()),
        )
        conn.commit()


def set_job_status(job_id: str, status: str, progress: int = 0, error: str | None = None) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE jobs SET status = ?, progress = ?, error_msg = ? WHERE id = ?",
            (status, progress, error, job_id),
        )
        conn.commit()


def set_job_progress(job_id: str, progress: int) -> None:
    with get_db() as conn:
        conn.execute("UPDATE jobs SET progress = ? WHERE id = ?", (progress, job_id))
        conn.commit()


def finish_job(job_id: str, result: dict) -> None:
    with get_db() as conn:
        conn.execute(
            """UPDATE jobs
               SET status = 'done', progress = 100, result_json = ?,
                   finished_at = ?, error_msg = NULL
               WHERE id = ?""",
            (json.dumps(result), _utcnow(), job_id),
        )
        conn.commit()


def fail_job(job_id: str, error: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE jobs SET status = 'error', error_msg = ?, finished_at = ? WHERE id = ?",
            (error[:500], _utcnow(), job_id),
        )
        conn.commit()


def get_job(job_id: str) -> sqlite3.Row | None:
    with get_db() as conn:
        return conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()


def list_jobs(owner_id: int, limit: int = 100) -> list[sqlite3.Row]:
    with get_db() as conn:
        return conn.execute(
            """SELECT * FROM jobs WHERE owner_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (owner_id, limit),
        ).fetchall()


def job_to_dict(row: sqlite3.Row, include_result: bool = True) -> dict:
    result = json.loads(row["result_json"]) if row["result_json"] else None
    return {
        "id": row["id"],
        "filename": row["filename"],
        "status": row["status"],
        "progress": row["progress"],
        "created_at": row["created_at"],
        "finished_at": row["finished_at"],
        "error": row["error_msg"],
        "config": json.loads(row["config_json"]),
        "result": result if include_result else None,
        "summary": (
            {
                "total_vehicles": result.get("total_vehicles", 0),
                "total_violating_vehicles": result.get("total_violating_vehicles", 0),
                "total_violations": result.get("total_violations", 0),
                "violation_counts": result.get("violation_counts", {}),
            }
            if result
            else None
        ),
    }


def project_path(rel: str) -> Path:
    """Resolve a stored relative path against the project root."""
    p = Path(rel)
    return p if p.is_absolute() else config.BASE_DIR / p
