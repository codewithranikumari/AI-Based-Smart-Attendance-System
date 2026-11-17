import hashlib
import hmac
import os
import secrets
import sqlite3
from contextlib import contextmanager


DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smart_attendance.db")
PASSWORD_ITERATIONS = 310_000


def connect():
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def get_connection():
    connection = connect()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def create_tables():
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                roll_no TEXT NOT NULL UNIQUE COLLATE NOCASE,
                class_name TEXT NOT NULL,
                face_registered INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                attendance_date TEXT NOT NULL,
                attendance_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Present',
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
                UNIQUE(student_id, attendance_date)
            );

            CREATE TABLE IF NOT EXISTS performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                term TEXT NOT NULL,
                marks REAL NOT NULL CHECK(marks >= 0 AND marks <= 100),
                recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
                UNIQUE(student_id, term)
            );

            CREATE INDEX IF NOT EXISTS idx_attendance_date
                ON attendance(attendance_date);
            CREATE INDEX IF NOT EXISTS idx_performance_student
                ON performance(student_id, recorded_at);
            """
        )


def has_admins():
    with get_connection() as connection:
        row = connection.execute("SELECT EXISTS(SELECT 1 FROM admins)").fetchone()
        return bool(row[0])


def create_admin(username, password):
    username = str(username).strip()
    if not username:
        raise ValueError("Enter an admin username.")
    if len(password) < 8:
        raise ValueError("Choose a password with at least 8 characters.")

    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    stored_hash = f"{salt.hex()}${password_hash.hex()}"
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
            (username, stored_hash),
        )


def verify_admin(username, password):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT password_hash FROM admins WHERE username = ?",
            (str(username).strip(),),
        ).fetchone()

    if row is None:
        return False

    try:
        salt_hex, expected_hex = row["password_hash"].split("$", maxsplit=1)
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(expected_hex)
    except ValueError:
        return False

    actual_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return hmac.compare_digest(actual_hash, expected_hash)


def list_admins():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, username, created_at FROM admins ORDER BY username"
        ).fetchall()
    return [dict(row) for row in rows]
