"""Backup the DB to a timestamped file.

    python scripts/db_backup.py                  # local SQLite -> ./backups/
    DATABASE_URL=... python scripts/db_backup.py # prod -> .sql dump via pg_dump

For SQLite: copies the file plus runs the .backup API so the snapshot
is consistent under concurrent writes.

For Postgres: shells out to pg_dump (must be on PATH). The dump is
plain-text SQL so you can grep / diff / restore in pieces.
"""
from __future__ import annotations
import argparse
import os
import shutil
import subprocess
import sys
import time

BACKUP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "backups")


def backup_sqlite(db_path: str, out_path: str) -> None:
    import sqlite3
    src = sqlite3.connect(db_path)
    dst = sqlite3.connect(out_path)
    with dst:
        src.backup(dst)
    src.close()
    dst.close()


def backup_postgres(url: str, out_path: str) -> None:
    # pg_dump reads connection from libpq env or URL. Use URL form so
    # the caller doesn't have to set PGHOST/etc.
    cmd = ["pg_dump", "--no-owner", "--no-privileges",
           "--clean", "--if-exists",
           "--file", out_path, url]
    print("  $ pg_dump <DATABASE_URL> ->", out_path)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr + "\n")
        raise SystemExit(
            f"pg_dump failed (exit {proc.returncode}). "
            "Is pg_dump on PATH? Install Postgres client tools.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="",
                    help="output path; defaults to "
                         "backups/mindx-<timestamp>.<ext>")
    args = ap.parse_args()

    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if url:
        out = args.out or os.path.join(BACKUP_DIR, f"mindx-{ts}.sql")
        backup_postgres(url, out)
    else:
        db_path = os.environ.get("DB_PATH", "mindx.db")
        if not os.path.exists(db_path):
            raise SystemExit(f"local DB not found at {db_path}")
        out = args.out or os.path.join(BACKUP_DIR, f"mindx-{ts}.db")
        backup_sqlite(db_path, out)
    size = os.path.getsize(out)
    print(f"[backup] ok -- {out} ({size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
