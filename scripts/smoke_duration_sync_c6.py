"""C6 — verify the financial_attendance_duration_sync_v1 migration
on a synthetic local SQLite DB.

Strategy:
  1. Point DB_PATH at a tmp file that DOES NOT yet exist.
  2. Import app.py — init_db() runs the full schema.
  3. Insert synthetic attendance + session_durations rows so the
     migration HAS work to do on the next boot. To force the
     migration to run, DELETE its tag from schema_migrations.
  4. Re-import app.py in a child process so the boot-time migration
     code re-runs against the now-prepared DB.
  5. Inspect attendance rows + the JSON backup file.
"""
import os
import sys
import json
import sqlite3
import subprocess
import tempfile
import glob
import shutil

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DB = os.path.join(tempfile.gettempdir(), "mindx_c6_smoke.db")
BACKUP_DIR = os.path.join(REPO, "scripts", "backups")


def seed(db_path: str) -> None:
    """Add four test cases:
       A. att=empty, sd=60   → expect UPDATE to 60
       B. att=45, sd=90      → expect UPDATE to 90 (mismatch)
       C. att=60, sd=60      → expect NO UPDATE (already matches)
       D. att=30 with no SD  → expect NO UPDATE (no candidate)
    """
    db = sqlite3.connect(db_path)
    db.execute(
        "INSERT INTO attendance(id, group_name, attendance_date, student_name, "
        "                       status, class_duration, class_type) "
        "VALUES (?,?,?,?,?,?,?)",
        (1001, "G_C6_A", "2026-05-19", "S A", "حاضر", "", "حضوري"),
    )
    db.execute(
        "INSERT INTO attendance(id, group_name, attendance_date, student_name, "
        "                       status, class_duration, class_type) "
        "VALUES (?,?,?,?,?,?,?)",
        (1002, "G_C6_B", "2026-05-19", "S B", "حاضر", "45", "حضوري"),
    )
    db.execute(
        "INSERT INTO attendance(id, group_name, attendance_date, student_name, "
        "                       status, class_duration, class_type) "
        "VALUES (?,?,?,?,?,?,?)",
        (1003, "G_C6_C", "2026-05-19", "S C", "حاضر", "60", "حضوري"),
    )
    db.execute(
        "INSERT INTO attendance(id, group_name, attendance_date, student_name, "
        "                       status, class_duration, class_type) "
        "VALUES (?,?,?,?,?,?,?)",
        (1004, "G_C6_D", "2026-05-19", "S D", "حاضر", "30", "حضوري"),
    )
    db.execute(
        "INSERT INTO session_durations(group_name, session_date, "
        "                              duration_minutes, session_type) "
        "VALUES (?,?,?,?)",
        ("G_C6_A", "2026-05-19", 60, "حضور"),
    )
    db.execute(
        "INSERT INTO session_durations(group_name, session_date, "
        "                              duration_minutes, session_type) "
        "VALUES (?,?,?,?)",
        ("G_C6_B", "2026-05-19", 90, "حضور"),
    )
    db.execute(
        "INSERT INTO session_durations(group_name, session_date, "
        "                              duration_minutes, session_type) "
        "VALUES (?,?,?,?)",
        ("G_C6_C", "2026-05-19", 60, "حضور"),
    )
    # G_C6_D deliberately has no SD row.
    # Force the migration to re-run by removing its tag.
    try:
        db.execute(
            "DELETE FROM schema_migrations WHERE tag=?",
            ("financial_attendance_duration_sync_v1",),
        )
    except Exception:
        pass
    db.commit()
    db.close()


def reimport_app() -> str:
    """Spawn a fresh Python child so app.py's import-time migration
    runs against the prepared DB. Returns stderr text for assertions."""
    env = os.environ.copy()
    env["DB_PATH"] = TMP_DB
    env["DATABASE_URL"] = ""
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run(
        [sys.executable, "-c", "import app"],
        cwd=REPO, env=env, capture_output=True, text=True, encoding="utf-8",
    )
    return p.stderr or ""


def main() -> int:
    # Clean slate
    if os.path.exists(TMP_DB):
        os.remove(TMP_DB)
    # Snapshot current backup-dir state so we can identify our new file
    pre_files = set(glob.glob(os.path.join(BACKUP_DIR, "attendance_pre_duration_sync_*.json"))) \
                if os.path.exists(BACKUP_DIR) else set()

    # 1. First boot creates the schema; tag will be set by the migration
    #    but with zero rows to update.
    reimport_app()

    # 2. Seed test rows + delete the tag so the second boot re-runs the
    #    migration with real work.
    seed(TMP_DB)

    # 3. Second boot — migration runs against the prepared DB.
    stderr = reimport_app()

    # 4. Assertions
    failures = []

    if "[duration-sync]" not in stderr:
        failures.append("expected [duration-sync] log line in stderr")
    # 3 candidates (A,B,C have SD rows); only A and B differ — so
    # will_update must be 2 and the no-change row (C) must be skipped.
    if "candidates=3" not in stderr:
        failures.append("expected candidates=3 in stderr, got: "
                        + stderr.split('[duration-sync]', 1)[-1][:300])
    if "will_update=2" not in stderr:
        failures.append("expected will_update=2 in stderr, got: "
                        + stderr.split('[duration-sync]', 1)[-1][:300])
    if "updated=2" not in stderr:
        failures.append("expected updated=2 in stderr")

    db = sqlite3.connect(TMP_DB)
    expected = {1001: "60", 1002: "90", 1003: "60", 1004: "30"}
    for rid, want in expected.items():
        row = db.execute("SELECT class_duration FROM attendance WHERE id=?", (rid,)).fetchone()
        if not row:
            failures.append("row " + str(rid) + " missing")
            continue
        got = (row[0] or "").strip()
        if got != want:
            failures.append("row " + str(rid) + " expected class_duration='"
                            + want + "' got '" + got + "'")
    # Migration tag must now be set
    tag = db.execute(
        "SELECT tag FROM schema_migrations WHERE tag=?",
        ("financial_attendance_duration_sync_v1",),
    ).fetchone()
    if not tag:
        failures.append("migration tag not recorded in schema_migrations")
    db.close()

    # 5. Backup file assertion
    post_files = set(glob.glob(os.path.join(BACKUP_DIR, "attendance_pre_duration_sync_*.json")))
    new_files = post_files - pre_files
    if not new_files:
        failures.append("no new backup file created in " + BACKUP_DIR)
    else:
        # Verify the JSON has the expected rows
        latest = max(new_files)
        try:
            with open(latest, encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as ex:
            failures.append("backup file unreadable: " + str(ex))
            payload = {}
        # Only the 2 rows that actually changed are recorded; the
        # already-matching row (C) is filtered out before backup.
        if payload.get("row_count") != 2:
            failures.append("backup row_count=" + str(payload.get("row_count"))
                            + " expected 2")
        # Clean up the backup we created so we don't pollute the dir
        for f in new_files:
            try: os.remove(f)
            except Exception: pass

    if failures:
        print("[C6] FAILED:")
        for f in failures:
            print("  - " + f)
        print("---- stderr excerpt ----")
        print(stderr[-2000:])
        return 1
    print("[C6] PASS — migration backfills correctly, skips matches + "
          "no-SD rows, writes JSON backup, sets tag.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
