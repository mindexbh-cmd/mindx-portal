"""Restore the DB from a backup. **DESTRUCTIVE.**

For SQLite: replaces the live DB file with the backup file (creating a
.before-restore-<ts> copy first as a safety net).

For Postgres: pipes the .sql dump through psql. The dump must have
been produced by scripts/db_backup.py (i.e. `pg_dump --clean
--if-exists`) so the DROP/CREATE order is sane.

Usage:
    python scripts/db_restore.py path/to/backup.db        # local
    DATABASE_URL=... python scripts/db_restore.py x.sql   # prod

You MUST pass --yes-i-really-mean-it; otherwise the script exits 2
without touching anything.
"""
from __future__ import annotations
import argparse
import os
import shutil
import subprocess
import sys
import time


def restore_sqlite(backup_path: str, db_path: str) -> None:
    if not os.path.exists(backup_path):
        raise SystemExit(f"backup not found: {backup_path}")
    if os.path.exists(db_path):
        ts = time.strftime("%Y%m%d-%H%M%S")
        safety = db_path + f".before-restore-{ts}"
        shutil.copy2(db_path, safety)
        print(f"[restore] saved current DB to {safety}")
    shutil.copy2(backup_path, db_path)
    print(f"[restore] copied {backup_path} -> {db_path}")


def restore_postgres(backup_path: str, url: str) -> None:
    if not os.path.exists(backup_path):
        raise SystemExit(f"backup not found: {backup_path}")
    # psql will refuse to run if it can't connect; the dump's
    # --clean / --if-exists clauses do the DROP-then-CREATE dance.
    cmd = ["psql", url, "-v", "ON_ERROR_STOP=1", "-f", backup_path]
    print("  $ psql <DATABASE_URL> -f", backup_path)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise SystemExit(
            f"psql failed (exit {proc.returncode}). The DB may be in a "
            "partially-restored state — investigate before reconnecting "
            "the app.")
    print("[restore] psql succeeded.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("backup_path", help="path to the backup file")
    ap.add_argument("--yes-i-really-mean-it", action="store_true",
                    help="confirm you intend to overwrite the live DB")
    args = ap.parse_args()

    if not args.yes_i_really_mean_it:
        print("[restore] refusing without --yes-i-really-mean-it.",
              file=sys.stderr)
        return 2

    url = (os.environ.get("DATABASE_URL") or "").strip()
    if url:
        restore_postgres(args.backup_path, url)
    else:
        db_path = os.environ.get("DB_PATH", "mindx.db")
        restore_sqlite(args.backup_path, db_path)
    print("[restore] done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
