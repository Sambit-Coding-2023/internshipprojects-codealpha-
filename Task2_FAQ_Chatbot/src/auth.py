"""
Authentication & User Management Module for Task 2: FAQ Chatbot
Provides secure registration, authentication, password hashing, and user session handling via SQLite.
"""

import datetime
import os
import re
import secrets
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from werkzeug.security import check_password_hash, generate_password_hash

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "users.db"


class AuthManager:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initializes tables for users and session tokens."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    avatar TEXT,
                    role TEXT DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)

            # Seed default demo account if no users exist
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            if count == 0:
                demo_hash = generate_password_hash("demo123")
                cursor.execute("""
                    INSERT INTO users (username, email, password_hash, full_name, avatar, role, last_login)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    "demo_user",
                    "demo@example.com",
                    demo_hash,
                    "Demo User",
                    "👤",
                    "user"
                ))
            conn.commit()

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------
    def register(
        self,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Registers a new user.
        Returns: (success: bool, message: str, user_dict: Optional[Dict])
        """
        username = (username or "").strip()
        email = (email or "").strip().lower()
        password = password or ""
        full_name = (full_name or "").strip() or username.title()

        # Validation rules
        if not username or len(username) < 3:
            return False, "Username must be at least 3 characters long.", None
        if not re.match(r"^[a-zA-Z0-9_.-]+$", username):
            return False, "Username may only contain letters, numbers, underscores, and hyphens.", None
        if len(username) > 30:
            return False, "Username must be under 30 characters.", None

        if not email or "@" not in email or "." not in email:
            return False, "Please enter a valid email address.", None

        if len(password) < 6:
            return False, "Password must be at least 6 characters long.", None

        # Check existing user
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE LOWER(username) = ?", (username.lower(),))
            if cursor.fetchone():
                return False, f"Username '{username}' is already taken.", None

            cursor.execute("SELECT id FROM users WHERE LOWER(email) = ?", (email,))
            if cursor.fetchone():
                return False, f"Email '{email}' is already registered.", None

            # Generate avatar emoji
            avatars = ["🚀", "✨", "🌟", "💡", "🎯", "⚡", "🔮", "🍀", "💎", "🎨"]
            avatar = secrets.choice(avatars)

            pw_hash = generate_password_hash(password)
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, full_name, avatar, last_login)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (username, email, pw_hash, full_name, avatar))
            user_id = cursor.lastrowid
            conn.commit()

        user = self.get_user_by_id(user_id)
        return True, "Account created successfully!", user

    # -------------------------------------------------------------------------
    # Authentication & Login
    # -------------------------------------------------------------------------
    def authenticate(
        self,
        username_or_email: str,
        password: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Authenticates a user by username or email and password.
        Returns: (success: bool, message: str, user_dict: Optional[Dict])
        """
        identifier = (username_or_email or "").strip()
        password = password or ""

        if not identifier or not password:
            return False, "Please provide both username/email and password.", None

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, email, password_hash, full_name, avatar, role, created_at
                FROM users
                WHERE LOWER(username) = ? OR LOWER(email) = ?
            """, (identifier.lower(), identifier.lower()))
            row = cursor.fetchone()

            if not row:
                return False, "Invalid username or password.", None

            if not check_password_hash(row["password_hash"], password):
                return False, "Invalid username or password.", None

            # Update last_login
            user_id = row["id"]
            cursor.execute("""
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
            """, (user_id,))
            conn.commit()

        user = self.get_user_by_id(user_id)
        return True, f"Welcome back, {user['username']}!", user

    # -------------------------------------------------------------------------
    # User Profile Lookups
    # -------------------------------------------------------------------------
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, email, full_name, avatar, role, created_at, last_login
                FROM users WHERE id = ?
            """, (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "username": row["username"],
                "email": row["email"],
                "full_name": row["full_name"],
                "avatar": row["avatar"] or "👤",
                "role": row["role"],
                "created_at": str(row["created_at"]),
                "last_login": str(row["last_login"])
            }

    # -------------------------------------------------------------------------
    # Session Management
    # -------------------------------------------------------------------------
    def create_session(self, user_id: int) -> str:
        token = secrets.token_hex(24)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_sessions (session_token, user_id) VALUES (?, ?)
            """, (token, user_id))
            conn.commit()
        return token

    def get_user_by_session_token(self, token: str) -> Optional[Dict[str, Any]]:
        if not token:
            return None
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id FROM user_sessions WHERE session_token = ?
            """, (token,))
            row = cursor.fetchone()
            if not row:
                return None
            return self.get_user_by_id(row["user_id"])

    def delete_session(self, token: str):
        if not token:
            return
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_sessions WHERE session_token = ?", (token,))
            conn.commit()
