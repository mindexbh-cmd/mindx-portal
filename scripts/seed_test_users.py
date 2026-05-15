#!/usr/bin/env python3
"""Idempotent test-user seed.

Creates four predictable accounts the e2e suite relies on:

    admin_test    / TestAdmin2026!     role=admin
    teacher_test  / TestTeacher2026!   role=teacher
    student_test  / TestStudent2026!   role=student   (linked to students row)
    parent_test   / TestParent2026!    role=parent    (linked_parent_for=student_test row's personal_id)

Run:
    python scripts/seed_test_users.py            # local SQLite (DB_PATH or mindx.db)
    DATABASE_URL=... python scripts/seed_test_users.py   # prod Postgres

All ops are upserts -- re-running never duplicates or wipes existing
rows. Passwords are SHA-256 (matches app.hp()) so the seeded creds
authenticate through the normal login flow without any test-mode shim.
"""
from __future__ import annotations
import hashlib
import os
import sys


def _hp(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()


TEST_USERS = [
    # (username,        password,              role,      name)
    ("admin_test",      "TestAdmin2026!",      "admin",   "Test Admin"),
    ("teacher_test",    "TestTeacher2026!",    "teacher", "Test Teacher"),
    ("student_test",    "TestStudent2026!",    "student", "Test Student"),
    ("parent_test",     "TestParent2026!",     "parent",  "Test Parent"),
]
TEST_STUDENT_PID = "TEST-STUDENT-0001"
TEST_STUDENT_NAME = "Test Student"


def _connect():
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if url:
        import psycopg2  # type: ignore
        import psycopg2.extras  # type: ignore
        return ("pg", psycopg2.connect(url))
    import sqlite3
    db_path = os.environ.get("DB_PATH", "mindx.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return ("sqlite", conn)


def _q(kind: str, sql: str) -> str:
    """Translate '?' to '%s' for Postgres."""
    if kind == "pg":
        return sql.replace("?", "%s")
    return sql


def _fetchone(cur):
    row = cur.fetchone()
    if row is None:
        return None
    if hasattr(row, "keys"):
        return dict(row)
    # psycopg2 default tuple cursor
    cols = [d[0] for d in cur.description] if cur.description else []
    return dict(zip(cols, row))


def seed():
    kind, conn = _connect()
    cur = conn.cursor()
    print(f"[seed] connected -> {kind}")

    # 1. Seed students row for student_test ───────────────────────────
    cur.execute(_q(kind,
        "SELECT id FROM students WHERE personal_id=?"), (TEST_STUDENT_PID,))
    existing_student = _fetchone(cur)
    if existing_student:
        student_id = existing_student["id"]
        print(f"[seed] students row exists id={student_id}")
    else:
        cur.execute(_q(kind,
            "INSERT INTO students(personal_id, student_name, class_name) "
            "VALUES(?, ?, ?)"),
            (TEST_STUDENT_PID, TEST_STUDENT_NAME, "TestClass"))
        # Re-read so we get a portable id (psycopg2 wrapper appends
        # RETURNING id automatically but we don't depend on that here).
        cur.execute(_q(kind,
            "SELECT id FROM students WHERE personal_id=?"),
            (TEST_STUDENT_PID,))
        row = _fetchone(cur)
        student_id = row["id"] if row else 0
        print(f"[seed] inserted students row id={student_id}")

    # 2. Seed users rows ──────────────────────────────────────────────
    for username, password, role, name in TEST_USERS:
        cur.execute(_q(kind,
            "SELECT id FROM users WHERE username=?"), (username,))
        existing = _fetchone(cur)
        pw_hash = _hp(password)
        linked_sid = student_id if role in ("student", "parent") else 0
        linked_parent_for = TEST_STUDENT_PID if role == "parent" else ""
        if existing:
            cur.execute(_q(kind,
                "UPDATE users SET password=?, role=?, name=?, "
                "linked_student_id=?, linked_parent_for=? "
                "WHERE username=?"),
                (pw_hash, role, name, linked_sid,
                 linked_parent_for, username))
            print(f"[seed] updated user {username} role={role}")
        else:
            cur.execute(_q(kind,
                "INSERT INTO users(username, password, role, name, "
                "linked_student_id, linked_parent_for) "
                "VALUES(?, ?, ?, ?, ?, ?)"),
                (username, pw_hash, role, name, linked_sid,
                 linked_parent_for))
            print(f"[seed] inserted user {username} role={role}")

    conn.commit()
    conn.close()
    print("[seed] done -- test users ready.")


if __name__ == "__main__":
    try:
        seed()
    except Exception as ex:
        print(f"[seed] FAILED: {ex}", file=sys.stderr)
        sys.exit(1)
